from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from src.backend.app.native_preproc.orchestrator.artifact_registry import (  # noqa: E402
    build_artifact_ref,  # noqa: E402
)
from src.backend.app.native_preproc.orchestrator.validation import (  # noqa: E402
    validate_stage_result_artifacts,  # noqa: E402
)
from src.backend.app.native_preproc.stages.dummy_scan import run_dummy_scan_removal  # noqa: E402


def _save_nifti(path: Path, data: np.ndarray) -> Path:
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine=np.eye(4)), str(path))
    return path


def test_dummy_scan_stage_writes_reloadable_artifact_and_sidecars(tmp_path: Path) -> None:
    bold = _save_nifti(
        tmp_path / "sub-01_task-rest_bold.nii.gz", np.ones((3, 4, 2, 5), dtype=np.float32)
    )

    result = run_dummy_scan_removal(bold, tmp_path / "native", remove_first=2, subject_id="sub-01")

    assert result.status == "succeeded"
    assert result.capability_level == "numerically_implemented"
    assert validate_stage_result_artifacts(result) == []
    out_img = nib.load(result.output_artifacts[0].path)
    assert out_img.shape == (3, 4, 2, 3)

    manifest = tmp_path / "native" / "manifests" / "dummy_scan_removal_manifest.json"
    provenance = tmp_path / "native" / "provenance" / "dummy_scan_removal_provenance.json"
    qc_json = tmp_path / "native" / "qc" / "dummy_scan_removal_qc.json"
    for path in (manifest, provenance, qc_json):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["_schema_version"] == 1

    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["stage_id"] == "dummy_scan_removal"
    assert manifest_payload["output_artifacts"][0]["artifact_type"] == "bold_4d"
    assert manifest_payload["parameters"]["remove_first"] == 2


def test_dummy_scan_blocks_when_removing_all_timepoints(tmp_path: Path) -> None:
    bold = _save_nifti(
        tmp_path / "sub-01_task-rest_bold.nii.gz", np.ones((2, 2, 2, 2), dtype=np.float32)
    )

    result = run_dummy_scan_removal(bold, tmp_path / "native", remove_first=2)

    assert result.status == "blocked"
    assert result.output_artifacts == []
    assert "remove_first must be smaller" in result.errors[0]


def test_build_artifact_ref_marks_absolute_paths_as_absolute_local(tmp_path: Path) -> None:
    bold = _save_nifti(
        tmp_path / "sub-01_task-rest_bold.nii.gz", np.ones((2, 2, 2, 3), dtype=np.float32)
    )

    ref = build_artifact_ref(bold, artifact_type="bold_4d")

    assert Path(ref.path).is_absolute()
    assert ref.path_kind == "absolute_local"
