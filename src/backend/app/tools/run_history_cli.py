"""Run history CLI — display indexed run history from SessionDB or JSONL."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    history_index_path = Path("outputs/reports/run_history/run_history_index.json")
    if history_index_path.exists():
        data = json.loads(history_index_path.read_text(encoding="utf-8"))
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    # Fallback: scan memory/projects for RUN_HISTORY.jsonl
    projects_dir = Path("outputs/memory/projects")
    records: list[dict] = []
    if projects_dir.is_dir():
        for proj_dir in sorted(projects_dir.iterdir()):
            if not proj_dir.is_dir():
                continue
            jl_path = proj_dir / "RUN_HISTORY.jsonl"
            if jl_path.exists():
                for line in jl_path.read_text(encoding="utf-8").strip().splitlines():
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

    work_pipeline_dir = Path("outputs/work/pipeline_runs")
    pipeline_runs: list[str] = []
    if work_pipeline_dir.is_dir():
        pipeline_runs = [d.name for d in sorted(work_pipeline_dir.iterdir()) if d.is_dir()]

    summary = {
        "ok": True,
        "run_history_records": len(records),
        "pipeline_runs_found": len(pipeline_runs),
        "pipeline_run_ids": pipeline_runs[-20:],
        "records": records[-10:],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
