from __future__ import annotations

from pathlib import Path

from src.backend.app.memory.session_db import SessionDB
from src.backend.app.tools.insights import build_insights


def test_insights_generates_from_session_db(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))
    db.upsert_run(
        {"run_id": "r1", "pipeline_id": "p1", "status": "SUCCESS", "duration_seconds": 120.0}
    )
    db.upsert_run(
        {"run_id": "r2", "pipeline_id": "p1", "status": "FAILED", "duration_seconds": 45.0}
    )
    db.insert_node(
        {
            "run_id": "r1",
            "node_id": "motion_qc",
            "ok": True,
            "status": "SUCCESS",
            "duration_seconds": 5.0,
        }
    )
    db.insert_node(
        {"run_id": "r2", "node_id": "normalize", "ok": False, "status": "FAILED", "errors": ["err"]}
    )
    db.insert_error(
        {"run_id": "r2", "node_id": "normalize", "category": "SPM_ERROR", "message": "fail"}
    )
    db.close()

    report_dir = str(tmp_path / "reports" / "insights")
    insights = build_insights(db_path=str(db_path), report_dir=report_dir)

    assert insights["ok"] is True
    assert insights["summary"]["total_runs"] == 2
    assert insights["summary"]["success_rate"] == 50.0
    assert len(insights["most_failed_nodes"]) >= 1
    assert Path(report_dir, "insights_summary.json").exists()


def test_insights_handles_empty_db(tmp_path: Path):
    db_path = tmp_path / "empty.sqlite"
    db = SessionDB(str(db_path))
    db.close()  # Just create the schema, no data

    report_dir = str(tmp_path / "reports" / "insights")
    insights = build_insights(db_path=str(db_path), report_dir=report_dir)

    assert insights["ok"] is True
    assert insights["summary"]["total_runs"] == 0
    assert insights["summary"]["success_rate"] == 0
    assert insights["summary"]["avg_duration_seconds"] == 0
    assert len(insights["slowest_nodes"]) == 0
    assert len(insights["most_failed_nodes"]) == 0
    assert len(insights["top_error_categories"]) == 0
    assert len(insights["recent_trend"]) == 0
