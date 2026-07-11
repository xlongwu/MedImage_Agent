from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np

from tests.integration.native_preproc_fixtures import load_atomic_json, run_synthetic_native_full


def test_native_preproc_validation_report_matches_manifest_artifacts(tmp_path) -> None:
    _, result = run_synthetic_native_full(tmp_path, run_id="native-artifact-integrity")

    manifest = load_atomic_json(result.manifest_path)
    validation = load_atomic_json(result.validation_report_path)

    manifest_artifacts = [
        {"stage_id": stage["stage_id"], **artifact}
        for stage in manifest["stage_results"]
        for artifact in stage["output_artifacts"]
    ]
    validation_artifacts = validation["artifact_validation"]["artifacts"]

    assert validation["overall_status"] == "pass"
    assert validation["artifact_validation"]["failed_count"] == 0
    assert validation["truthfulness"]["failed_count"] == 0
    assert validation["summary"]["artifact_count"] == len(validation_artifacts)
    assert validation["summary"]["artifact_count"] == len(manifest_artifacts) - 2

    validation_paths = {item["path"] for item in validation_artifacts}
    manifest_paths_before_validation_stage = {
        str(artifact["path"])
        for artifact in manifest_artifacts
        if artifact["stage_id"] not in {"validation_report", "final_report"}
    }
    assert validation_paths == manifest_paths_before_validation_stage

    for artifact in manifest_artifacts:
        path = Path(str(artifact["path"]))
        assert path.exists()
        assert path.stat().st_size > 0
        if artifact["artifact_type"] in {"fc_matrix", "fisher_z_matrix"}:
            array = np.load(path)
            assert list(array.shape) == artifact["shape"]
            assert str(array.dtype) == artifact["dtype"]
        elif path.name.endswith(".nii") or path.name.endswith(".nii.gz"):
            image = nib.load(str(path))
            assert list(image.shape) == artifact["shape"]
