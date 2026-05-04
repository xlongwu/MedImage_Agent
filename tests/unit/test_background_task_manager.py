import time
from pathlib import Path

from src.backend.app.runtime.background_task_manager import (
    submit_background_task,
    get_task_status,
    list_tasks,
)


def test_background_task_executes_and_completes(tmp_path: Path):
    status_dir = str(tmp_path / "bg_tasks")

    def sample_task(message: str = "hello") -> dict:
        return {"ok": True, "message": message}

    task_id = submit_background_task(
        task_type="test",
        func=sample_task,
        kwargs={"message": "world"},
        status_dir=status_dir,
    )

    # Small delay for file write to complete
    time.sleep(0.05)
    # Poll for completion
    for _ in range(30):
        status = get_task_status(task_id, status_dir)
        if status["status"] in ("SUCCESS", "FAILED"):
            break
        time.sleep(0.2)

    assert status["status"] == "SUCCESS"
    assert status["result"]["message"] == "world"


def test_task_status_not_found(tmp_path: Path):
    result = get_task_status("nonexistent", str(tmp_path / "bg_tasks"))
    assert result["ok"] is False


def test_list_tasks_returns_submitted_tasks(tmp_path: Path):
    status_dir = str(tmp_path / "bg_tasks")

    task_id = submit_background_task(
        task_type="review",
        func=lambda: {"ok": True},
        status_dir=status_dir,
    )

    # Wait for completion
    for _ in range(30):
        status = get_task_status(task_id, status_dir)
        if status["status"] == "SUCCESS":
            break
        time.sleep(0.2)

    tasks_result = list_tasks(status_dir=status_dir)
    assert tasks_result["ok"] is True
    assert tasks_result["total"] >= 1
    assert any(t["task_id"] == task_id for t in tasks_result["tasks"])
