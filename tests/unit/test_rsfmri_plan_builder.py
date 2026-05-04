from __future__ import annotations

from pathlib import Path

from src.backend.app.preprocessing.rsfmri_plan_builder import (
    build_rsfmri_preprocessing_plan,
)
from src.backend.app.preprocessing.rsfmri_step_registry import (
    get_rsfmri_core_step_registry_dict,
)


def test_rsfmri_step_registry_contains_core_steps():
    steps = get_rsfmri_core_step_registry_dict()
    step_ids = {step["step_id"] for step in steps}

    assert "dataset_inspection" in step_ids
    assert "realignment" in step_ids
    assert "motion_qc" in step_ids
    assert "normalization" in step_ids
    assert "smoothing" in step_ids
    assert "nuisance_regression" in step_ids
    assert "temporal_filtering" in step_ids
    assert "alff" in step_ids
    assert "falff" in step_ids
    assert "reho" in step_ids
    assert "dataset_qc_report" in step_ids


def test_rsfmri_plan_builder_is_plan_only(tmp_path: Path):
    work = tmp_path / "work"
    reports = tmp_path / "reports"

    result = build_rsfmri_preprocessing_plan(
        work_dir=str(work),
        report_dir=str(reports),
    )

    assert result["ok"] is True
    assert result["safety"]["plan_only"] is True
    assert result["safety"]["preprocessing_executed"] is False
    assert result["safety"]["matlab_launched"] is False
    assert result["steps_total"] >= 10

    assert (work / "preprocessing" / "rsfmri" / "rsfmri_preprocessing_plan.json").exists()
    assert (reports / "rsfmri" / "rsfmri_preprocessing_plan_report.md").exists()
