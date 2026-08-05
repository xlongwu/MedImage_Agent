from __future__ import annotations

from pathlib import Path

from src.backend.app.services.native_preproc_full import run_native_full_execute
from tests.integration.native_preproc_fixtures import (
    file_digest,
    make_synthetic_native_inputs,
    native_full_request,
)


def test_native_preproc_dicom_handoff_to_fc_does_not_write_rawdata(tmp_path) -> None:
    """Validate the post-DICOM-conversion handoff without running converters."""

    rawdata = tmp_path / "rawdata" / "sub-001" / "ses-01"
    rawdata.mkdir(parents=True)
    dicom = rawdata / "IM0001.dcm"
    dicom.write_bytes(b"synthetic dicom placeholder")
    raw_digest = file_digest(dicom)

    inputs = make_synthetic_native_inputs(tmp_path)
    request = native_full_request(inputs, run_id="native-dicom-handoff-to-fc")

    result = run_native_full_execute("native-phase07", request, project_dir=str(tmp_path))

    assert result.ok is True, {
        "status": result.status,
        "blocked_stages": result.blocked_stages,
        "failed_stages": result.failed_stages,
        "stage_errors": {
            stage.stage_id: stage.errors for stage in result.stage_results if stage.errors
        },
    }
    assert result.status == "succeeded"
    assert file_digest(dicom) == raw_digest
    dicom_stage = next(
        stage for stage in result.stage_results if stage.stage_id == "dicom_to_nifti"
    )
    assert dicom_stage.status == "skipped"
    assert "conversion domain" in " ".join(dicom_stage.warnings)
    for stage in result.stage_results:
        for artifact in stage.output_artifacts:
            path = Path(str(artifact["path"])).resolve()
            assert rawdata.resolve() not in path.parents
            assert path != dicom.resolve()
