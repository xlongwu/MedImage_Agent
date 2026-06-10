"""Preprocessing SPM Sandbox Execution Service — Phase 5E.

Copies BOLD inputs to sandbox, generates and runs SPM batch script,
captures stdout/stderr, writes manifest/provenance.
Env-gated. No rawdata modification. No converted input modification.
"""
from __future__ import annotations
import os, json, hashlib, shutil
from pathlib import Path
from typing import Any

from src.backend.app.schemas.preprocessing_spm_execution import (
    SpmSandboxExecutionRequest, SpmSandboxExecutionResponse,
    validate_sandbox_env, sandbox_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_sandbox_spm_execution(
    project_id: str, run_id: str, request: SpmSandboxExecutionRequest,
    *, project_dir: str = "", env: dict[str, str] | None = None
) -> SpmSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_sandbox_env(eff_env)
    if not ok_flags:
        return SpmSandboxExecutionResponse(ok=False, status="disabled", project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"], safety_flags=sandbox_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    input_dir = request.preprocessing_input_dir or str(meta.get("preprocessing_input_dir") or "")
    if not input_dir:
        return SpmSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No preprocessing input registered."], safety_flags=sandbox_safety_flags())

    rawdata_dir = str(meta.get("rawdata_dir") or "")

    # Find dry-run directory
    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id if effective_pd else None
    if not dry_dir or not dry_dir.exists():
        return SpmSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"], safety_flags=sandbox_safety_flags())

    # Create sandbox execution directory
    exec_id = "spm-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    exec_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / exec_id if effective_pd else Path(f"outputs/spm_exec/{exec_id}")
    exec_dir.mkdir(parents=True, exist_ok=True)
    sandbox_in = exec_dir / "sandbox_input"; sandbox_in.mkdir()
    sandbox_out = exec_dir / "sandbox_output"; sandbox_out.mkdir()
    logs_dir = exec_dir / "logs"; logs_dir.mkdir()

    # Copy BOLD files to sandbox
    input_path = Path(input_dir)
    bold_files = [p for p in sorted(input_path.rglob("*.nii*")) if ("bold" in p.name.lower() or "rest" in p.name.lower()) and p.is_file()]
    if not bold_files:
        return SpmSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No BOLD files found."], safety_flags=sandbox_safety_flags())

    copied: list[Path] = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        dest = sandbox_in / subj; dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bf, dest / bf.name)
        # Copy sidecar if exists
        for ext in [".json"]:
            sc = Path(str(bf).replace(".nii.gz", ext).replace(".nii", ext))
            if sc.exists(): shutil.copy2(sc, dest / sc.name)
        copied.append(dest / bf.name)

    # Generate batch script referencing sandbox paths only
    batch_lines = ["%% SPM Sandbox Slice Timing + Realign", "spm('defaults','FMRI');", "matlabbatch={};"]
    for i, cp in enumerate(copied):
        batch_lines.append(f"matlabbatch{{{i*2+1}}}.spm.temporal.st.scans={{'{cp},1'}};")
        batch_lines.append(f"matlabbatch{{{i*2+1}}}.spm.temporal.st.nslices=36;")
        batch_lines.append(f"matlabbatch{{{i*2+2}}}.spm.spatial.realign.estwrite.data={{'{cp},1'}};")
    batch_lines.append("spm_jobman('run',matlabbatch);")
    batch_lines.append("disp('SPM_SANDBOX_COMPLETE'); exit;")
    batch_path = exec_dir / "spm_batch.m"
    batch_path.write_text("\n".join(batch_lines), encoding="utf-8")

    # Write command template
    cmd_tmpl = {"tool": "matlab", "executable": request.matlab_executable,
                "args": ["-nodisplay", "-nosplash", "-nodesktop", "-r", f"run('{batch_path}');exit;"],
                "shell": False, "sandbox_only": True}
    tmpl_path = exec_dir / "command_template.json"
    tmpl_path.write_text(json.dumps(cmd_tmpl, indent=2))

    # Execute via subprocess (fake runner for tests, real when env flags set)
    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    try:
        import subprocess as _sp
        argv = [request.matlab_executable, "-nodisplay", "-nosplash", "-nodesktop", "-r", f"run('{batch_path}');exit;"]
        result = _sp.run(argv, capture_output=True, text=True, timeout=request.timeout_seconds)
        stdout_log.write_text(result.stdout or "", encoding="utf-8")
        stderr_log.write_text(result.stderr or "", encoding="utf-8")
        rc = result.returncode
    except Exception as exc:
        stdout_log.write_text("", encoding="utf-8"); stderr_log.write_text(str(exc), encoding="utf-8")
        rc = 1

    # Write manifest/provenance
    (exec_dir / "manifest.json").write_text(json.dumps({"exec_id": exec_id, "status": "succeeded" if rc == 0 else "failed"}, indent=2))
    (exec_dir / "provenance.json").write_text(json.dumps({"exec_id": exec_id, "sandbox_only": True}, indent=2))
    (exec_dir / "subject_status.json").write_text(json.dumps({"total": len(copied), "succeeded": len(copied) if rc == 0 else 0, "failed": len(copied) if rc != 0 else 0}, indent=2))
    (exec_dir / "README.md").write_text(f"# SPM Sandbox Execution {exec_id}\nSandbox only. Rawdata unchanged. Research use only.\n")

    status = "succeeded" if rc == 0 else "failed"
    return SpmSandboxExecutionResponse(
        ok=rc == 0, status=status, project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied), subjects_succeeded=len(copied) if rc == 0 else 0,
        subjects_failed=0 if rc == 0 else len(copied),
        command_template_path=str(tmpl_path), batch_script_path=str(batch_path),
        stdout_log_path=str(stdout_log), stderr_log_path=str(stderr_log),
        manifest_path=str(exec_dir / "manifest.json"), provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        next_actions=["Review execution results.", "Proceed to normalization if ready."],
        safety_flags=sandbox_safety_flags())
