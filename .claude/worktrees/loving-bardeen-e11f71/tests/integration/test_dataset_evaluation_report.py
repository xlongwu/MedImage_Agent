from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.report_writer import write_dataset_evaluation_report


def test_report_writer_generates_markdown_and_html(tmp_path: Path):
    report_dir = tmp_path / "reports" / "dataset_evaluation"
    report_dir.mkdir(parents=True)

    summary_path = report_dir / "dataset_summary.json"
    table_path = report_dir / "subject_qc_table.csv"
    exclusion_path = report_dir / "exclusion_recommendations.csv"

    summary_path.write_text(
        json.dumps({
            "run_id": "run_test",
            "subjects_total": 1,
            "subjects_complete": 1,
            "subjects_preprocess_success": 1,
            "subjects_qc_success": 1,
            "subjects_include": 1,
            "subjects_manual_review": 0,
            "subjects_exclude": 0,
            "dataset_quality_score": 100,
            "dataset_index": "dataset_index.json",
        }),
        encoding="utf-8",
    )

    table_path.write_text("subject_id,recommendation\nsub-001,INCLUDE\n", encoding="utf-8")
    exclusion_path.write_text("subject_id,recommendation,reasons\n", encoding="utf-8")

    result = write_dataset_evaluation_report(
        dataset_summary_path=str(summary_path),
        subject_qc_table_path=str(table_path),
        exclusion_recommendations_path=str(exclusion_path),
        output_dir=str(report_dir),
    )

    assert result["ok"] is True
    assert (report_dir / "dataset_evaluation_report.md").exists()
    assert (report_dir / "dataset_evaluation_report.html").exists()
