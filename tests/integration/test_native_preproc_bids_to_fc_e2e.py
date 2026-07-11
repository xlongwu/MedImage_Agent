from __future__ import annotations

from pathlib import Path

import numpy as np

from src.backend.app.services.native_preproc_full import run_native_full_execute
from tests.integration.native_preproc_fixtures import (
    file_digest,
    make_synthetic_native_inputs,
    native_full_request,
)


def test_native_preproc_bids_to_fc_e2e_generates_reloadable_fc_chain(tmp_path) -> None:
    inputs = make_synthetic_native_inputs(tmp_path)
    original_input_digests = {
        name: file_digest(path)
        for name, path in inputs.items()
        if name in {"bold", "sidecar", "t1w", "template", "atlas", "labels"}
    }
    request = native_full_request(inputs, run_id="native-bids-to-fc")

    result = run_native_full_execute("native-phase07", request, project_dir=str(tmp_path))

    assert result.ok is True
    assert result.status == "succeeded"
    assert not result.blocked_stages
    assert not result.failed_stages
    assert result.safety_flags["no_external_tools_executed"] is True
    assert result.safety_flags["no_matlab_spm_dpabi"] is True
    assert result.safety_flags["third_party_runtime_not_used"] is True

    dicom_stage = next(stage for stage in result.stage_results if stage.stage_id == "dicom_to_nifti")
    assert dicom_stage.status == "skipped"

    fc_stage = next(stage for stage in result.stage_results if stage.stage_id == "functional_connectivity")
    artifact_paths = {
        artifact["artifact_type"]: Path(str(artifact["path"]))
        for artifact in fc_stage.output_artifacts
    }
    fc_matrix = np.load(artifact_paths["fc_matrix"])
    fisher_z = np.load(artifact_paths["fisher_z_matrix"])
    assert fc_matrix.shape == (2, 2)
    assert fisher_z.shape == (2, 2)
    assert np.allclose(fc_matrix, fc_matrix.T, atol=1e-6)
    assert np.allclose(np.diag(fc_matrix), 1.0, atol=1e-6)

    for stage in result.stage_results:
        for artifact in stage.output_artifacts:
            path = Path(str(artifact["path"]))
            assert path.exists()
            assert path.stat().st_size > 0
            assert "third_party" not in {part.lower() for part in path.parts}
            assert not path.name.endswith(".m")

    assert result.manifest_path
    assert result.validation_report_path
    assert result.final_report_path
    assert Path(result.manifest_path).exists()
    assert Path(result.validation_report_path).exists()
    assert Path(result.final_report_path).exists()

    assert original_input_digests == {
        name: file_digest(path)
        for name, path in inputs.items()
        if name in original_input_digests
    }
