# Phase B4：Async Background Review 异步后台审查

> 目标版本：v0.2.0 | 预计工期：1–2 天 | 前置条件：Phase B1 SessionDB 完成

---

## 1. 目标与范围

将 `background_review.py` 从同步模式改为异步后台任务，pipeline 可先返回结果，review 在后台执行，状态可轮询。

**不做**：消息推送、cron 调度、多任务并发管理。

---

## 2. 前置条件检查

- [ ] `background_review.py` 当前为同步模式
- [ ] Phase B1 SessionDB 可用

---

## 3. 新增/修改文件清单

```text
backend/app/runtime/background_task_manager.py   # 新增：后台任务管理器
backend/app/runtime/background_review.py          # 修改：支持异步调用
backend/app/tools/background_review_status.py     # 新增：状态查询工具
backend/app/api/routes.py                         # 修改：新增 3 个端点
tests/unit/test_background_task_manager.py        # 新增：测试
```

---

## 4. 逐步实施步骤

### Step 1：创建后台任务管理器

文件：`backend/app/runtime/background_task_manager.py`

```python
"""Background task manager — run tasks asynchronously with status tracking."""
from __future__ import annotations

import json
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


_executor = ThreadPoolExecutor(max_workers=2)
_tasks: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def submit_background_task(
    task_type: str,
    func: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    status_dir: str = "./work/background_tasks",
) -> str:
    task_id = f"{task_type}_{uuid.uuid4().hex[:12]}"
    status_path = Path(status_dir) / f"{task_id}.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    task_record = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "PENDING",
        "submitted_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }
    _write_status(status_path, task_record)
    _tasks[task_id] = task_record

    def _wrapper():
        task_record["status"] = "RUNNING"
        task_record["started_at"] = _now_iso()
        _write_status(status_path, task_record)
        try:
            result = func(*args, **(kwargs or {}))
            task_record["status"] = "SUCCESS"
            task_record["result"] = result
        except Exception as exc:
            task_record["status"] = "FAILED"
            task_record["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        task_record["finished_at"] = _now_iso()
        _write_status(status_path, task_record)

    _executor.submit(_wrapper)
    return task_id


def get_task_status(task_id: str, status_dir: str = "./work/background_tasks") -> dict[str, Any]:
    status_path = Path(status_dir) / f"{task_id}.json"
    if not status_path.exists():
        return {"ok": False, "task_id": task_id, "errors": ["Task not found"]}
    record = json.loads(status_path.read_text(encoding="utf-8"))
    return {"ok": True, **record}


def list_tasks(status_dir: str = "./work/background_tasks", limit: int = 50) -> dict[str, Any]:
    sd = Path(status_dir)
    if not sd.exists():
        return {"ok": True, "tasks": [], "total": 0}
    tasks = []
    for f in sorted(sd.glob("*.json"), key=lambda p: -p.stat().st_mtime)[:limit]:
        try:
            tasks.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, IOError):
            continue
    return {"ok": True, "tasks": tasks, "total": len(tasks)}


def _write_status(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
```

### Step 2：修改 background_review.py

在 `run_background_review` 函数不变的前提下，新增一个用于异步提交的包装：

```python
# 在 background_review.py 末尾新增：

def submit_background_review_async(
    agent_run_id: str,
    project_config_path: str,
    agent_summary_path: str,
) -> str:
    """Submit background review as an async task. Returns task_id for polling."""
    from backend.app.runtime.background_task_manager import submit_background_task

    return submit_background_task(
        task_type="background_review",
        func=run_background_review,
        kwargs={
            "agent_run_id": agent_run_id,
            "project_config_path": project_config_path,
            "agent_summary_path": agent_summary_path,
        },
    )
```

### Step 3：新增 API 端点

```python
from backend.app.runtime.background_task_manager import get_task_status, list_tasks
from backend.app.runtime.background_review import run_background_review, submit_background_review_async


@router.post("/api/background-review/start")
async def background_review_start(request: dict[str, Any]):
    """Start a background review (sync or async)."""
    agent_run_id = request["agent_run_id"]
    project_config_path = request.get("project_config_path", "examples/project_config_dataset.yaml")
    agent_summary_path = request.get("agent_summary_path", f"work/agent_runs/{agent_run_id}/agent_summary.json")

    async_mode = request.get("async", True)
    if async_mode:
        task_id = submit_background_review_async(agent_run_id, project_config_path, agent_summary_path)
        return {"ok": True, "async": True, "task_id": task_id}
    else:
        result = run_background_review(agent_run_id, project_config_path, agent_summary_path)
        return result


@router.get("/api/background-review/status/{task_id}")
async def background_review_status(task_id: str):
    """Get background review task status."""
    return get_task_status(task_id)


@router.get("/api/background-review/latest")
async def background_review_latest():
    """Get latest background review result."""
    tasks = list_tasks()
    for t in tasks.get("tasks", []):
        if t.get("task_type") == "background_review" and t.get("status") == "SUCCESS":
            return {"ok": True, "latest": t}
    return {"ok": False, "errors": ["No completed background review found"]}
```

### Step 4：测试

```python
import time
from pathlib import Path
from backend.app.runtime.background_task_manager import submit_background_task, get_task_status


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
```

---

## 5. 验收标准

- [ ] 后台任务可在 ThreadPoolExecutor 中异步执行
- [ ] pipeline 无需等待 review 完成即返回
- [ ] task status 包含 PENDING / RUNNING / SUCCESS / FAILED 四种状态
- [ ] 状态文件写入 `work/background_tasks/{task_id}.json`
- [ ] `POST /api/background-review/start` 支持 async=true 模式
- [ ] `GET /api/background-review/status/{id}` 可轮询状态
- [ ] `GET /api/background-review/latest` 返回最近完成的 review
- [ ] review 失败时不影响 pipeline 结果
- [ ] 2 个单元测试通过
