from __future__ import annotations

import json
from pathlib import Path

from src.backend.app.services.native_preproc_full import run_native_full_execute
from src.backend.app.tools.native_preproc_run_validator import validate_native_preproc_run
from tests.integration.native_preproc_fixtures import (
    load_atomic_json,
    make_synthetic_native_inputs,
    native_full_request,
    run_synthetic_native_full,
)


def test_native_preproc_run_validator_passes_numeric_artifacts(tmp_path: Path) -> None:
    _, result = run_synthetic_native_full(tmp_path, run_id="native-validator-pass")

    validation = validate_native_preproc_run(result.run_dir, require_fc_numerics=True)

    assert validation["ok"] is True
    assert validation["stats"]["failed_errors_total"] == 0
    assert not [
        check
        for check in validation["checks"]
        if check["name"].startswith("numeric:") and check["status"] != "PASS"
    ]
    for name in {
        "fc_artifacts_present",
        "roi_timeseries_finite",
        "fc_matrix_finite",
        "roi_timeseries_rows_match_timepoints",
        "fc_matrix_square",
        "fc_matrix_symmetric",
        "fc_matrix_diagonal_unit",
        "fc_matrix_range",
        "roi_count_matches_fc_dimension",
        "roi_count_matches_roi_labels",
        "roi_count_matches_atlas_labels",
    }:
        check = next(item for item in validation["checks"] if item["name"] == name)
        assert check["status"] == "PASS"


def test_native_preproc_run_validator_flags_roi_timepoint_mismatch(tmp_path: Path) -> None:
    _, result = run_synthetic_native_full(tmp_path, run_id="native-validator-fc-mismatch")
    roi_tsv = next(Path(result.run_dir).glob("artifacts/roi_timeseries/**/*.tsv"))
    rows = roi_tsv.read_text(encoding="utf-8").splitlines()
    roi_tsv.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")

    validation = validate_native_preproc_run(result.run_dir, require_fc_numerics=True)

    check = next(
        item
        for item in validation["checks"]
        if item["name"] == "roi_timeseries_rows_match_timepoints"
    )
    assert validation["ok"] is False
    assert check["status"] == "FAIL"
    assert check["metrics"]["roi_rows"] == check["metrics"]["expected_timepoints"] - 1


def test_native_preproc_run_validator_flags_unknown_subject_when_required(tmp_path: Path) -> None:
    _, result = run_synthetic_native_full(tmp_path, run_id="native-validator-unknown-subject")
    group_path = Path(result.run_dir) / "artifacts" / "group_summary" / "native_group_summary.json"
    payload = load_atomic_json(group_path)
    payload["subject_summaries"][0]["subject_id"] = "unknown"
    group_path.write_text(
        json.dumps({"_schema_version": 1, "data": payload}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    validation = validate_native_preproc_run(result.run_dir, require_subject_ids=True)

    subject_check = next(
        check for check in validation["checks"] if check["name"] == "subject_ids_resolved"
    )
    assert validation["ok"] is False
    assert subject_check["status"] == "FAIL"
    assert subject_check["severity"] == "error"


def test_native_preproc_infers_subject_id_from_bids_paths(tmp_path: Path) -> None:
    inputs = make_synthetic_native_inputs(tmp_path)
    request = native_full_request(inputs, run_id="native-validator-inferred-subject")
    request = request.model_copy(update={"subject_id": ""})

    result = run_native_full_execute("native-phase07", request, project_dir=str(tmp_path))

    group_path = Path(result.run_dir) / "artifacts" / "group_summary" / "native_group_summary.json"
    group = load_atomic_json(group_path)
    assert group["subject_summaries"][0]["subject_id"] == "sub-001"
    validation = validate_native_preproc_run(result.run_dir, require_subject_ids=True)
    assert validation["ok"] is True


def test_native_preproc_run_validator_accepts_report_export_bridge(tmp_path: Path) -> None:
    _, result = run_synthetic_native_full(tmp_path, run_id="native-validator-report-chain")

    validation = validate_native_preproc_run(
        result.run_dir,
        project_dir=tmp_path,
        require_report_chain=True,
        probe_exporter=True,
    )

    bridge_check = next(
        check
        for check in validation["checks"]
        if check["name"] == "report_exporter_group_summary_source"
    )
    probe_check = next(
        check
        for check in validation["checks"]
        if check["name"] == "report_exporter_probe_uses_native_outputs"
    )
    assert validation["ok"] is True
    assert bridge_check["status"] == "PASS"
    assert probe_check["status"] == "PASS"
