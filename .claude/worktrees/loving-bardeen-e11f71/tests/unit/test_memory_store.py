from __future__ import annotations

import json
from pathlib import Path

from backend.app.runtime.memory_store import append_run_history, ensure_memory_layout


def test_memory_layout_and_run_history(tmp_path: Path):
    ensure_memory_layout(str(tmp_path))

    history_path = append_run_history(
        project_name="test_project",
        record={"agent_run_id": "agent_test", "phi": "should_not_store"},
        root_dir=str(tmp_path),
    )

    assert history_path.exists()
    line = history_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["agent_run_id"] == "agent_test"
    assert "phi" not in payload
