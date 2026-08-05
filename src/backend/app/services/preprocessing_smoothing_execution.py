"""Smoothing Sandbox Execution Service — Phase 5J."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.preprocessing_smoothing_execution import (
    SmoothingSandboxExecutionRequest,
    SmoothingSandboxExecutionResponse,
    smoothing_safety_flags,
    validate_smoothing_env,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def run_smoothing_sandbox_execution(
    project_id: str,
    run_id: str,
    request: SmoothingSandboxExecutionRequest,
    *,
    project_dir: str = "",
    env: dict[str, str] | None = None,
) -> SmoothingSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_smoothing_env(eff_env)
    if not ok_flags:
        return SmoothingSandboxExecutionResponse(
            ok=False,
            status="disabled",
            project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"],
            safety_flags=smoothing_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    dry_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id
        if effective_pd
        else None
    )
    if not dry_dir or not dry_dir.exists():
        return SmoothingSandboxExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"],
            safety_flags=smoothing_safety_flags(),
        )

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    func_path = Path(func_input) if func_input else None
    if not func_path or not func_path.exists():
        return SmoothingSandboxExecutionResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["Functional input not found."],
            safety_flags=smoothing_safety_flags(),
        )

    bold_files = [
        p
        for p in sorted(func_path.rglob("*.nii*"))
        if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())
    ]

    exec_id = (
        "s-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
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

    copied = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        dest = sandbox_in / subj
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bf, dest / bf.name)
        copied.append(dest / bf.name)

    batch_lines = ["%% SPM Smoothing (Sandbox)", "spm('defaults','FMRI');", "matlabbatch={};"]
    for i, cp in enumerate(copied):
        batch_lines.append(f"matlabbatch{{{i + 1}}}.spm.spatial.smooth.data={{'{cp},1'}};")
        batch_lines.append(f"matlabbatch{{{i + 1}}}.spm.spatial.smooth.fwhm=[6,6,6];")
    batch_lines.append("spm_jobman('run',matlabbatch);")
    batch_lines.append("disp('SMOOTHING_SANDBOX_COMPLETE'); exit;")
    batch_path = exec_dir / "spm_smoothing_batch.m"
    batch_path.write_text("\n".join(batch_lines), encoding="utf-8")

    cmd_tmpl = {
        "tool": "matlab",
        "executable": request.matlab_executable,
        "args": ["-nodisplay", "-nosplash", "-nodesktop", "-r", f"run('{batch_path}');exit;"],
        "shell": False,
        "sandbox_only": True,
    }
    (exec_dir / "command_template.json").write_text(json.dumps(cmd_tmpl, indent=2))

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

    (exec_dir / "manifest.json").write_text(
        json.dumps({"status": "succeeded" if rc == 0 else "failed"})
    )
    (exec_dir / "provenance.json").write_text(json.dumps({"sandbox_only": True}))
    (exec_dir / "subject_status.json").write_text(json.dumps({"total": len(copied)}))
    (exec_dir / "README.md").write_text("# Smoothing Sandbox Execution\n")

    status = "succeeded" if rc == 0 else "failed"
    return SmoothingSandboxExecutionResponse(
        ok=rc == 0,
        status=status,
        project_id=project_id,
        preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id,
        execution_id=exec_id,
        execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in),
        sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied),
        subjects_succeeded=len(copied) if rc == 0 else 0,
        subjects_failed=0 if rc == 0 else len(copied),
        command_template_path=str(exec_dir / "command_template.json"),
        batch_script_path=str(batch_path),
        stdout_log_path=str(stdout_log),
        stderr_log_path=str(stderr_log),
        manifest_path=str(exec_dir / "manifest.json"),
        provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        safety_flags=smoothing_safety_flags(),
    )
