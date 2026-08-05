"""SPM Runtime Service — Phase 5C.

SPM/MATLAB runtime preflight and synthetic-only Slice Timing + Realign smoke.
No user rawdata. No real converted BIDS. No full preprocessing. Env-gated.
"""

from __future__ import annotations

import json
import os
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.spm_runtime import (
    _REQUIRED_SYNTHETIC_SPM_FLAGS,
    SpmRuntimePreflightResponse,
    SpmSyntheticSmokeRequest,
    SpmSyntheticSmokeResponse,
    safety_flags_spm,
    validate_synthetic_spm_env,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def spm_runtime_preflight(
    project_id: str, *, env: dict[str, str] | None = None
) -> SpmRuntimePreflightResponse:
    _warnings: list[str] = []
    _errors: list[str] = []
    eff_env = env or dict(os.environ)
    # Check env flags
    ok_flags, missing = validate_synthetic_spm_env(eff_env)
    if not ok_flags:
        return SpmRuntimePreflightResponse(
            ok=True,
            status="disabled",
            project_id=project_id,
            required_env_flags=list(_REQUIRED_SYNTHETIC_SPM_FLAGS),
            missing_env_flags=missing,
            warnings=[f"SPM runtime disabled: {len(missing)} env flag(s) missing."],
            safety_flags=safety_flags_spm(),
        )

    # Check MATLAB
    import shutil

    matlab_exe = eff_env.get("MEDIMAGE_MATLAB_COMMAND", "matlab")
    matlab_path = shutil.which(matlab_exe)
    if not matlab_path:
        return SpmRuntimePreflightResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            matlab_executable=matlab_exe,
            required_env_flags=list(_REQUIRED_SYNTHETIC_SPM_FLAGS),
            errors=[f"MATLAB executable not found: {matlab_exe}"],
            safety_flags=safety_flags_spm(),
        )

    # Check SPM (simplified — just check SPM path or default)
    spm_path = eff_env.get("MEDIMAGE_SPM_DIR", "")
    spm_found = bool(spm_path) and Path(spm_path).exists()
    if not spm_found:
        return SpmRuntimePreflightResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            matlab_available=True,
            matlab_executable=matlab_path,
            spm_path=spm_path,
            errors=[f"SPM directory not found: {spm_path}"],
            safety_flags=safety_flags_spm(),
        )

    return SpmRuntimePreflightResponse(
        ok=True,
        status="ready_for_synthetic_smoke",
        project_id=project_id,
        matlab_available=True,
        matlab_executable=matlab_path,
        spm_available=True,
        spm_path=spm_path,
        required_env_flags=list(_REQUIRED_SYNTHETIC_SPM_FLAGS),
        next_actions=["Run synthetic SPM Slice Timing + Realign smoke."],
        safety_flags=safety_flags_spm(),
    )


def _gen_synthetic_nifti(output_dir: Path) -> Path:
    """Generate a tiny synthetic 4D BOLD NIfTI."""
    import nibabel as nib
    import numpy as np

    data = np.random.randn(8, 8, 6, 10).astype(np.float32)
    affine = np.eye(4)
    img = nib.Nifti1Image(data, affine)
    path = output_dir / "synth_bold.nii"
    nib.save(img, str(path))
    return path


def run_synthetic_spm_smoke(
    project_id: str,
    request: SpmSyntheticSmokeRequest,
    *,
    project_dir: str = "",
    env: dict[str, str] | None = None,
) -> SpmSyntheticSmokeResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_synthetic_spm_env(eff_env)
    if not ok_flags:
        return SpmSyntheticSmokeResponse(
            ok=False,
            status="disabled",
            project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"],
            safety_flags=safety_flags_spm(),
        )

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or f"outputs/{project_id}")

    import hashlib

    smoke_id = "spm-smoke-" + hashlib.sha256(f"{project_id}:{_now_iso()}".encode()).hexdigest()[:10]
    smoke_dir = Path(effective_pd) / "spm_smoke_runs" / smoke_id
    smoke_dir.mkdir(parents=True, exist_ok=True)
    input_dir = smoke_dir / "input"
    input_dir.mkdir()
    output_dir = smoke_dir / "output"
    output_dir.mkdir()
    logs_dir = smoke_dir / "logs"
    logs_dir.mkdir()

    # Generate synthetic NIfTI
    try:
        nifti_path = _gen_synthetic_nifti(input_dir)
    except ImportError:
        return SpmSyntheticSmokeResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            smoke_run_id=smoke_id,
            blocking_issues=["nibabel not available for synthetic NIfTI generation."],
            safety_flags=safety_flags_spm(),
        )

    # Generate SPM batch script
    batch = f"""%% synthetic_spm_slice_timing_realign_smoke
spm('defaults','FMRI');
matlabbatch={{}};
matlabbatch{{1}}.spm.temporal.st.scans={{'{nifti_path},1'}};
matlabbatch{{1}}.spm.temporal.st.nslices=6;
matlabbatch{{1}}.spm.temporal.st.tr=2.0;
matlabbatch{{1}}.spm.temporal.st.ta=1.8;
matlabbatch{{1}}.spm.temporal.st.so={{1 3 5 2 4 6}};
matlabbatch{{1}}.spm.temporal.st.refslice=1;
matlabbatch{{2}}.spm.spatial.realign.estwrite.data={{'{nifti_path},1'}};
matlabbatch{{2}}.spm.spatial.realign.estwrite.eoptions.quality=0.9;
matlabbatch{{2}}.spm.spatial.realign.estwrite.roptions.which={{2 1}};
spm_jobman('run',matlabbatch);
disp('SPM_SMOKE_COMPLETE');
exit;
"""
    batch_path = smoke_dir / "spm_batch.m"
    batch_path.write_text(batch, encoding="utf-8")
    template_path = smoke_dir / "command_template.json"
    template_path.write_text(
        json.dumps(
            {
                "tool": "matlab",
                "executable": request.matlab_executable,
                "args": [
                    "-nodisplay",
                    "-nosplash",
                    "-nodesktop",
                    "-r",
                    f"run('{batch_path}');exit;",
                ],
                "shell": False,
                "synthetic_only": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Write manifest + provenance stubs
    (smoke_dir / "manifest.json").write_text(
        json.dumps({"smoke_id": smoke_id, "status": "generated"}, indent=2)
    )
    (smoke_dir / "provenance.json").write_text(
        json.dumps({"smoke_id": smoke_id, "synthetic_only": True}, indent=2)
    )
    (smoke_dir / "README.md").write_text(f"# SPM Synthetic Smoke {smoke_id}\nResearch use only.\n")

    return SpmSyntheticSmokeResponse(
        ok=True,
        status="generated",
        project_id=project_id,
        smoke_run_id=smoke_id,
        smoke_dir=str(smoke_dir),
        synthetic_input_path=str(nifti_path),
        synthetic_output_dir=str(output_dir),
        command_template_path=str(template_path),
        batch_script_path=str(batch_path),
        stdout_log_path=str(logs_dir / "stdout.log"),
        stderr_log_path=str(logs_dir / "stderr.log"),
        manifest_path=str(smoke_dir / "manifest.json"),
        provenance_path=str(smoke_dir / "provenance.json"),
        completed_steps=["synthetic_nifti_generation", "batch_script_generation", "manifest_write"],
        next_actions=["Review batch script.", "Execute MATLAB/SPM smoke locally."],
        safety_flags=safety_flags_spm(),
    )
