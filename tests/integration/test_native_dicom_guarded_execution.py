from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.unit.test_native_dicom_to_nifti import _write_classic_series

pytest.importorskip("pydicom")
pytest.importorskip("nibabel")


_FLAGS = {
    "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
}


def _hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def test_guarded_persisted_execution_uses_native_backend_and_preserves_rawdata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.backend.app.services.dicom_conversion_execution import (
        run_internal_user_dicom_conversion_from_persisted_package,
    )

    project = tmp_path / "project"
    rawdata = project / "rawdata"
    source = rawdata / "T1Raw" / "Sub_001"
    _write_classic_series(source)
    output_root = project / "converted_bids"
    output_dir = output_root / "sub-001" / "anat"
    run_id = "conv-native-test"
    run_dir = project / "conversion_runs" / run_id
    run_dir.mkdir(parents=True)

    approval = {
        "approval_id": "approval-native",
        "project_id": "project-native",
        "status": "approved",
        "approved": True,
        "approved_by": "tester",
        "mappings_reviewed": True,
        "output_root": str(output_root),
        "output_root_confirmed": True,
        "output_root_under_project": True,
        "output_root_not_rawdata": True,
        "rawdata_read_only_confirmed": True,
        "command_templates_reviewed": True,
        "no_shell_string_confirmed": True,
        "dcm2niix_availability_confirmed": True,
        "env_flags_confirmed": True,
        "overwrite_policy": "fail_if_exists",
        "rollback_policy_acknowledged": True,
        "clinical_use_prohibited_acknowledged": True,
        "external_tool_acknowledgement": True,
        "risk_acknowledgement": True,
        "confirm_execution": True,
    }
    mapping = {
        "source_path": str(source),
        "subject_id": "sub-001",
        "modality": "anat",
        "suffix": "T1w",
        "output_filename": "sub-001_T1w.nii.gz",
    }
    template = {
        "tool": "medimage-native",
        "executable": "",
        "input_dir": str(source),
        "output_dir": str(output_dir),
        "filename_pattern": "sub-001_T1w",
        "compress": "y",
        "bids_sidecar": True,
        "create_bids": True,
    }
    from src.backend.app.services.dicom_conversion_safety import (
        build_pre_conversion_rawdata_snapshot,
    )

    checksum_before = build_pre_conversion_rawdata_snapshot([str(rawdata)])
    files = {
        "approval_record.json": approval,
        "audit_preview.json": {"audit_id": "audit-native", "project_id": "project-native"},
        "preflight_snapshot.json": {"ok": True, "status": "ready"},
        "mapping_snapshot.json": {"mappings": [mapping]},
        "command_templates.json": {"templates": [template]},
        "rawdata_checksum_before.json": checksum_before.model_dump(mode="json"),
        "rollback_plan_dry_run.json": {"rollback_allowed": True},
    }
    for name, payload in files.items():
        (run_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    before = _hashes(rawdata)
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("subprocess must not be called")
        ),
    )
    denied = run_internal_user_dicom_conversion_from_persisted_package(
        "project-native",
        run_id,
        env=_FLAGS,
        project_dir=str(project),
        rawdata_dir=str(rawdata),
        validate_only=True,
        input_roots=(str(rawdata),),
        output_roots=(str(tmp_path / "different-project"),),
        readonly_roots=(str(rawdata),),
    )
    assert denied.status == "blocked"
    assert "execution-ticket output roots" in " ".join(denied.blocking_issues)

    result = run_internal_user_dicom_conversion_from_persisted_package(
        "project-native",
        run_id,
        env=_FLAGS,
        project_dir=str(project),
        rawdata_dir=str(rawdata),
    )

    assert result.ok is True
    assert result.status == "succeeded"
    assert result.mode == "native"
    assert _hashes(rawdata) == before
    assert (output_dir / "sub-001_T1w.nii.gz").exists()
    assert (output_dir / "sub-001_T1w.json").exists()
    provenance = json.loads((run_dir / "execution_provenance.json").read_text(encoding="utf-8"))
    assert provenance["backend"] == "python"
    assert provenance["metadata"]["no_external_process"] is True
    assert provenance["metadata"]["rawdata_unchanged"] is True
    manifest = json.loads((run_dir / "output_manifest.json").read_text(encoding="utf-8"))
    assert manifest["verified_count"] == 2
