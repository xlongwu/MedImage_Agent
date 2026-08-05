"""Coregistration + Normalization Sandbox Execution Service — Phase 5H."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.preprocessing_coreg_norm_execution import (
    CoregNormSandboxExecutionRequest,
    CoregNormSandboxExecutionResponse,
    coreg_norm_safety_flags,
    validate_coreg_norm_env,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def run_coreg_norm_sandbox_execution(
    project_id: str,
    run_id: str,
    request: CoregNormSandboxExecutionRequest,
    *,
    project_dir: str = "",
    env: dict[str, str] | None = None,
) -> CoregNormSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_coreg_norm_env(eff_env)
    if not ok_flags:
        return CoregNormSandboxExecutionResponse(
            ok=False,
            status="disabled",
            project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"],
            safety_flags=coreg_norm_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    # Locate dry-run
    dry_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id
        if effective_pd
        else None
    )
    if not dry_dir or not dry_dir.exists():
        return CoregNormSandboxExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"],
            safety_flags=coreg_norm_safety_flags(),
        )

    # Functional input (from sandbox registration)
    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    func_path = Path(func_input) if func_input else None
    if not func_path or not func_path.exists():
        return CoregNormSandboxExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Functional input not found."],
            safety_flags=coreg_norm_safety_flags(),
        )

    # T1w from converted BIDS / request override
    conv_input = request.t1w_input_dir or str(meta.get("preprocessing_input_dir") or "")
    t1w_path = Path(conv_input) if conv_input else None
    t1w_files = (
        [p for p in sorted(t1w_path.rglob("*.nii*")) if p.is_file() and "t1" in p.name.lower()]
        if t1w_path
        else []
    )

    # Create sandbox execution directory
    exec_id = (
        "cn-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    )
    exec_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / exec_id
        if effective_pd
        else Path(f"outputs/spm_exec/{exec_id}")
    )
    exec_dir.mkdir(parents=True, exist_ok=True)
    sandbox_in = exec_dir / "sandbox_input"
    sandbox_in.mkdir()
    sandbox_out = exec_dir / "sandbox_output"
    sandbox_out.mkdir()
    logs_dir = exec_dir / "logs"
    logs_dir.mkdir()

    # Copy functional BOLD files
    bold_files = [
        p
        for p in sorted(func_path.rglob("*.nii*"))
        if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())
    ]
    copied_func: list[Path] = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        dest = sandbox_in / subj
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bf, dest / bf.name)
        copied_func.append(dest / bf.name)

    # Copy T1w files
    copied_t1w: list[Path] = []
    for tf in t1w_files[:10]:
        subj = "sub-unknown"
        for part in tf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        dest = sandbox_in / subj / "anat"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tf, dest / tf.name)
        copied_t1w.append(dest / tf.name)

    # Generate batch script
    batch_lines = [
        "%% SPM Coregistration + Normalization (Sandbox)",
        "spm('defaults','FMRI');",
        "matlabbatch={};",
    ]
    bid = 0
    for i, cf in enumerate(copied_func):
        subj_parts = [p for p in cf.parts if p.startswith("sub-")]
        subj = subj_parts[-1] if subj_parts else f"sub-{i:03d}"
        t1 = next((t for t in copied_t1w if subj in str(t)), None)
        t1_ref = f"'{t1},1'" if t1 else "T1W_MISSING"
        batch_lines.append(f"%% {subj}")
        bid += 1
        batch_lines.append(f"matlabbatch{{{bid}}}.spm.spatial.coreg.estimate.ref={{'{cf},1'}};")
        batch_lines.append(f"matlabbatch{{{bid}}}.spm.spatial.coreg.estimate.source={t1_ref};")
        bid += 1
        batch_lines.append(f"matlabbatch{{{bid}}}.spm.spatial.preproc.channel.vols={t1_ref};")
        bid += 1
        batch_lines.append(
            f"matlabbatch{{{bid}}}.spm.spatial.normalise.estwrite.subj.vol={{'{cf},1'}};"
        )
    batch_lines.append("spm_jobman('run',matlabbatch);")
    batch_lines.append("disp('COREG_NORM_SANDBOX_COMPLETE'); exit;")
    batch_path = exec_dir / "spm_coreg_norm_batch.m"
    batch_path.write_text("\n".join(batch_lines), encoding="utf-8")

    # Command template
    cmd_tmpl = {
        "tool": "matlab",
        "executable": request.matlab_executable,
        "args": ["-nodisplay", "-nosplash", "-nodesktop", "-r", f"run('{batch_path}');exit;"],
        "shell": False,
        "sandbox_only": True,
    }
    tmpl_path = exec_dir / "command_template.json"
    tmpl_path.write_text(json.dumps(cmd_tmpl, indent=2))

    # Execute
    stdout_log = logs_dir / "stdout.log"
    stderr_log = logs_dir / "stderr.log"
    try:
        import subprocess as _sp

        argv = [
            request.matlab_executable,
            "-nodisplay",
            "-nosplash",
            "-nodesktop",
            "-r",
            f"run('{batch_path}');exit;",
        ]
        result = _sp.run(argv, capture_output=True, text=True, timeout=request.timeout_seconds)
        stdout_log.write_text(result.stdout or "", encoding="utf-8")
        stderr_log.write_text(result.stderr or "", encoding="utf-8")
        rc = result.returncode
    except Exception as exc:
        stdout_log.write_text("", encoding="utf-8")
        stderr_log.write_text(str(exc), encoding="utf-8")
        rc = 1

    # Manifest/provenance
    (exec_dir / "manifest.json").write_text(
        json.dumps({"exec_id": exec_id, "status": "succeeded" if rc == 0 else "failed"})
    )
    (exec_dir / "provenance.json").write_text(
        json.dumps({"exec_id": exec_id, "sandbox_only": True})
    )
    (exec_dir / "subject_status.json").write_text(
        json.dumps({"total": len(copied_func), "succeeded": len(copied_func) if rc == 0 else 0})
    )
    (exec_dir / "README.md").write_text(f"# Coreg/Norm Sandbox Execution {exec_id}\n")

    status = "succeeded" if rc == 0 else "failed"
    return CoregNormSandboxExecutionResponse(
        ok=rc == 0,
        status=status,
        project_id=project_id,
        preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id,
        execution_id=exec_id,
        execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in),
        sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied_func),
        subjects_succeeded=len(copied_func) if rc == 0 else 0,
        subjects_failed=0 if rc == 0 else len(copied_func),
        command_template_path=str(tmpl_path),
        batch_script_path=str(batch_path),
        stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log),
        manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        next_actions=["Review results.", "Register outputs for smoothing if ready."],
        safety_flags=coreg_norm_safety_flags(),
    )
