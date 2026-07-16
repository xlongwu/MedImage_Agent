from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.backend.app.services import reviewed_native_conversion_handoff as handoff


class _Store:
    def __init__(self, metadata):
        self.project = SimpleNamespace(metadata=metadata)

    def get_project(self, project_id):
        return self.project


def _context(project_id: str, store: _Store, root: Path):
    return SimpleNamespace(
        project_id=project_id,
        ticket_service=SimpleNamespace(store=store),
        input_roots=(root,),
        output_roots=(root,),
        readonly_roots=(root / "rawdata",),
    )


def test_already_registered_conversion_is_not_executed(tmp_path, monkeypatch) -> None:
    registry = tmp_path / "registry.json"
    converted = tmp_path / "converted_bids" / "sub-001" / "func" / "bold.nii.gz"
    converted.parent.mkdir(parents=True)
    converted.write_bytes(b"converted")
    registry.write_text(
        json.dumps(
            {
                "conversion_run_id": "conv-001",
                "artifacts": [{"path": str(converted)}],
            }
        ),
        encoding="utf-8",
    )
    store = _Store(
        {
            "project_dir": str(tmp_path),
            "preprocessing_input_registry_path": str(registry),
            "preprocessing_conversion_run_id": "conv-001",
        }
    )
    monkeypatch.setattr(
        handoff,
        "run_internal_user_dicom_conversion_from_persisted_package",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("registered conversion must not execute again")
        ),
    )

    result = handoff.ensure_reviewed_native_conversion_handoff(
        store,
        project_id="project-1",
        conversion_run_id="conv-001",
        project_dir=str(tmp_path),
        rawdata_dir=str(tmp_path / "rawdata"),
        execution_context=_context("project-1", store, tmp_path),
    )

    assert result["ok"] is True
    assert result["status"] == "already_registered"


def test_completed_conversion_is_registered_after_crash_without_reexecution(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    run_dir = project_dir / "conversion_runs" / "conv-001"
    output_root = project_dir / "converted_bids"
    output = output_root / "sub-001" / "func" / "sub-001_task-rest_bold.nii.gz"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"verified-nifti")
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    run_dir.mkdir(parents=True)
    (run_dir / "audit_execution_final.json").write_text(
        json.dumps(
            {
                "audit_state": "execution_succeeded",
                "mapping_success_count": 1,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "output_manifest.json").write_text(
        json.dumps(
            {
                "output_root": str(output_root),
                "error_count": 0,
                "items": [
                    {
                        "path": str(output),
                        "verified": True,
                        "checksum_sha256": checksum,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "execution_provenance.json").write_text("{}", encoding="utf-8")
    (run_dir / "rawdata_checksum_comparison.json").write_text(
        json.dumps({"unchanged": True}),
        encoding="utf-8",
    )
    store = _Store({})
    registrations = []
    monkeypatch.setattr(
        handoff,
        "_register",
        lambda *args, **kwargs: registrations.append(kwargs) or {"ok": True},
    )
    monkeypatch.setattr(
        handoff,
        "run_internal_user_dicom_conversion_from_persisted_package",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("verified conversion evidence must prevent reexecution")
        ),
    )

    result = handoff.ensure_reviewed_native_conversion_handoff(
        store,
        project_id="project-1",
        conversion_run_id="conv-001",
        project_dir=str(project_dir),
        rawdata_dir=str(project_dir / "rawdata"),
        execution_context=_context("project-1", store, project_dir),
    )

    assert result["ok"] is True
    assert result["status"] == "recovered_registration"
    assert result["recovered"] is True
    assert registrations[0]["checksum_verified"] is True
