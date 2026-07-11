from __future__ import annotations

from tests.integration.native_preproc_fixtures import load_atomic_json, run_synthetic_native_full


def test_native_preproc_reports_do_not_upgrade_without_reference_evidence(tmp_path) -> None:
    _, result = run_synthetic_native_full(tmp_path, run_id="native-truthfulness")

    validation = load_atomic_json(result.validation_report_path)
    final_report = load_atomic_json(result.final_report_path)

    assert validation["overall_status"] == "pass"
    assert validation["reference_validation"]["status"] == "not_provided"
    assert "not reference_validated" in validation["reference_validation"]["note"]
    assert final_report["validation_summary"]["reference_validation_status"] == "not_provided"

    allowed_metadata_only = {
        "input_validation",
        "bids_sidecar_validation",
        "subject_qc",
        "group_summary",
        "validation_report",
        "final_report",
    }
    for stage in result.stage_results:
        assert stage.validation_status != "reference_validated"
        assert stage.capability_level != "reference_validated"
        if stage.status == "metadata_only":
            assert stage.stage_id in allowed_metadata_only
        if stage.capability_level in {"simplified", "affine_only"}:
            assert stage.validation_status != "reference_validated"

    assert all(item["passed"] for item in validation["safety_checks"])
    assert validation["truthfulness"]["failed_count"] == 0
