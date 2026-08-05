from __future__ import annotations

from pathlib import Path

from src.backend.app.memory.session_db import SessionDB


def test_session_db_create_and_upsert_run(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))

    db.upsert_run(
        {
            "run_id": "test-run-1",
            "pipeline_id": "rsfmri_mvp",
            "status": "SUCCESS",
            "started_at": "2026-01-01T00:00:00",
            "finished_at": "2026-01-01T00:05:00",
            "duration_seconds": 300.0,
        }
    )

    runs = db.query_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "test-run-1"
    assert runs[0]["status"] == "SUCCESS"
    db.close()


def test_session_db_insert_and_query_nodes(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))
    db.upsert_run({"run_id": "r1", "pipeline_id": "p1", "status": "SUCCESS"})

    db.insert_node(
        {
            "run_id": "r1",
            "node_id": "motion_qc",
            "subject_id": "sub-001",
            "ok": True,
            "status": "SUCCESS",
        }
    )
    db.insert_node(
        {
            "run_id": "r1",
            "node_id": "normalize",
            "subject_id": "sub-002",
            "ok": False,
            "status": "FAILED",
            "errors": ["bad norm"],
        }
    )

    nodes = db.query_nodes_by_run("r1")
    assert len(nodes) == 2
    assert db.query_nodes(run_id="r1") == nodes

    sub_nodes = db.query_nodes_by_subject("sub-002")
    assert len(sub_nodes) == 1
    assert sub_nodes[0]["status"] == "FAILED"

    stats = db.stats()
    assert stats["total_nodes"] == 2
    assert stats["failed_nodes"] == 1
    db.close()


def test_session_db_error_and_fts(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    db = SessionDB(str(db_path))
    db.upsert_run({"run_id": "r1", "pipeline_id": "p1", "status": "FAILED"})
    db.insert_error(
        {
            "run_id": "r1",
            "node_id": "normalize",
            "category": "SPM_ERROR",
            "message": "Undefined function spm",
        }
    )

    errors = db.query_errors(category="SPM_ERROR")
    assert len(errors) == 1

    db.index_document(
        "r1", "pipeline_run", "Run r1", "SPM normalization failed with Undefined function spm"
    )
    results = db.search("spm")
    assert len(results) == 1
    assert results[0]["record_id"] == "r1"
    assert db.fts_search(query="spm") == results
    db.close()


def test_session_indexer_from_pipeline_runs(tmp_path: Path):
    import json

    from src.backend.app.tools.session_indexer import index_pipeline_runs

    work = tmp_path / "work"
    run_dir = work / "pipeline_runs" / "test_run_001"
    run_dir.mkdir(parents=True)

    summary = {
        "run_id": "test_run_001",
        "pipeline_id": "rsfmri_mvp",
        "status": "SUCCESS",
        "started_at": "2026-01-01T00:00:00",
        "ended_at": "2026-01-01T00:05:00",
        "duration_seconds": 300.0,
        "node_results": [
            {
                "node_id": "motion_qc",
                "subject_id": "sub-001",
                "ok": True,
                "outputs": [],
                "warnings": [],
                "errors": [],
            },
        ],
        "errors": [],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    db_path = str(tmp_path / "test.sqlite")
    result = index_pipeline_runs(work_dir=str(work), db_path=db_path)

    assert result["ok"] is True
    assert result["indexed_runs"] == 1
    assert result["indexed_nodes"] == 1

    # Verify data is queryable
    db = SessionDB(db_path)
    runs = db.query_runs()
    assert len(runs) == 1
    assert runs[0]["pipeline_id"] == "rsfmri_mvp"
    db.close()
