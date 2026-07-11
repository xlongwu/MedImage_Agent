from __future__ import annotations

from pathlib import Path

from src.backend.app.native_preproc.orchestrator.report import run_group_summary


def test_group_summary_is_metadata_only_and_lists_subject_status(tmp_path: Path) -> None:
    result = run_group_summary(
        tmp_path / "native",
        subject_summaries=[
            {"subject_id": "sub-01", "status": "succeeded", "fc_matrix": "sub-01_fc.npy"},
            {"subject_id": "sub-02", "status": "blocked", "errors": ["missing atlas"]},
        ],
    )

    assert result.status == "metadata_only"
    assert result.capability_level == "metadata_only"
    assert result.output_artifacts[0].artifact_type == "final_report"
    report = Path(result.output_artifacts[0].path)
    text = report.read_text(encoding="utf-8")
    assert '"subject_count": 2' in text
    assert '"blocked_subject_count": 1' in text
    assert "No group-level statistical model is fitted" in text
