"""Index existing run histories into SessionDB."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.memory.session_db import SessionDB
from src.backend.app.tools.error_classifier import classify_error


def index_pipeline_runs(work_dir: str = "./work", db_path: str = "outputs/memory/sessions/archive.sqlite") -> dict[str, Any]:
    db = SessionDB(db_path)
    work = Path(work_dir)
    pipeline_runs_dir = work / "pipeline_runs"

    indexed_runs = 0
    indexed_nodes = 0
    indexed_errors = 0
    skipped = 0

    if pipeline_runs_dir.exists():
        for run_dir in sorted(pipeline_runs_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_path = run_dir / "summary.json"
            if not summary_path.exists():
                skipped += 1
                continue

            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                skipped += 1
                continue

            run_id = summary.get("run_id", run_dir.name)
            db.upsert_run({
                "run_id": run_id,
                "pipeline_id": summary.get("pipeline_id", ""),
                "status": summary.get("status", "UNKNOWN"),
                "started_at": summary.get("started_at"),
                "finished_at": summary.get("ended_at"),
                "duration_seconds": summary.get("duration_seconds"),
                "source_path": str(summary_path),
                "errors": summary.get("errors", []),
            })
            indexed_runs += 1

            for nr in summary.get("node_results", []):
                db.insert_node({
                    "run_id": run_id,
                    "node_id": nr.get("node_id", ""),
                    "subject_id": nr.get("subject_id", nr.get("subject", "project")),
                    "status": "SUCCESS" if nr.get("ok") else "FAILED",
                    "ok": nr.get("ok", False),
                    "outputs": nr.get("outputs", []),
                    "warnings": nr.get("warnings", []),
                    "errors": nr.get("errors", []),
                })
                indexed_nodes += 1

                for err_msg in nr.get("errors", []):
                    classified = classify_error(str(err_msg))
                    db.insert_error({
                        "run_id": run_id,
                        "node_id": nr.get("node_id", ""),
                        "subject_id": nr.get("subject_id", nr.get("subject", "project")),
                        "category": classified.get("category", "UNKNOWN_ERROR"),
                        "message": str(err_msg),
                        "retryable": classified.get("retryable", False),
                    })
                    indexed_errors += 1

            db.index_document(
                record_id=run_id,
                record_type="pipeline_run",
                title=f"{run_id} ({summary.get('pipeline_id', '')})",
                body=json.dumps(summary, ensure_ascii=False),
            )

    db.close()
    return {
        "ok": True,
        "indexed_runs": indexed_runs,
        "indexed_nodes": indexed_nodes,
        "indexed_errors": indexed_errors,
        "skipped": skipped,
    }


def index_demo_runs(demo_dir: str = "./demo_runs", db_path: str = "outputs/memory/sessions/archive.sqlite") -> dict[str, Any]:
    db = SessionDB(db_path)
    demo = Path(demo_dir)
    count = 0
    if demo.exists():
        for run_dir in sorted(demo.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_path = run_dir / "quickstart_demo_summary.json"
            if not summary_path.exists():
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                continue
            run_id = f"demo_{run_dir.name}"
            db.upsert_run({
                "run_id": run_id,
                "pipeline_id": "quickstart_demo",
                "status": "SUCCESS" if summary.get("ok") else "FAILED",
                "started_at": summary.get("started_at"),
                "finished_at": summary.get("ended_at"),
                "source_path": str(summary_path),
            })
            count += 1
            db.index_document(
                record_id=run_id,
                record_type="demo_run",
                title=f"Demo: {run_dir.name}",
                body=json.dumps(summary, ensure_ascii=False),
            )
    db.close()
    return {"ok": True, "indexed_demo_runs": count}
