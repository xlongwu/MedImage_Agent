from __future__ import annotations

from src.backend.app.planner.llm_planner import generate_plan_from_goal


def test_converted_bids_context_uses_native_full_preprocessing() -> None:
    resp = generate_plan_from_goal(
        (
            "rs-fMRI preprocessing with slice timing, realignment, motion QC, "
            "nuisance regression, detrending, temporal filtering, ROI time series, "
            "and functional connectivity"
        ),
        constraints={
            "project_context": {
                "project_id": "demodata-5",
                "project_dir": "work/projects/demodata-5",
                "diagnostics": {
                    "status": "CONVERTED_BIDS",
                    "nifti_file_count": 6,
                    "preprocessing_conversion_run_id": "conv-001",
                },
            }
        },
    )

    assert resp.ok is True
    assert resp.plan["pipeline_id"] == "native_full_preprocessing"
    node_ids = [node["id"] for node in resp.plan["nodes"]]
    assert node_ids == ["native_preproc_full_execute"]
    assert "spm_realign_subject" not in node_ids
    params = resp.plan["nodes"][0]["params"]
    assert params["project_id"] == "demodata-5"
    assert params["conversion_run_id"] == "conv-001"
    assert resp.plan["metadata"]["capability_level"] == "computed"
    assert resp.validation["approval_required_nodes"] == ["native_preproc_full_execute"]
    assert resp.validation["high_risk_nodes"] == []
