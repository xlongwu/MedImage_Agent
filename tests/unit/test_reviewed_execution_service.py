from __future__ import annotations

from src.backend.app.services.reviewed_execution_service import ReviewedExecutionService


def test_shared_service_invokes_reviewed_application_once() -> None:
    calls = []

    def execute(request):
        calls.append(request)
        return {"ok": True, "status": "DRY_RUN_OK"}

    result = ReviewedExecutionService(executor=execute).execute({"request": 1})

    assert result["ok"] is True
    assert calls == [{"request": 1}]
