from __future__ import annotations

from src.backend.app.api.dependencies import ProjectStore


def build_assistant_reply(
    *,
    store: ProjectStore,
    project_id: str,
    message: str,
) -> str | None:
    """Build a deterministic, project-scoped assistant response.

    The local assistant is intentionally read-only. It summarizes persisted
    backend state and never treats a chat message as execution authority.
    """

    project = store.get_project(project_id)
    if project is None:
        return None

    dataset = store.get_dataset_summary(project_id)
    subjects = dataset.subjects if dataset else project.subjects_count
    scans = dataset.scans if dataset else project.scans_count
    health = dataset.health_status if dataset else "Unknown"
    reviewed_plan_count = len(store.list_reviewed_plans(project_id))
    execution_run_count = len(store.list_run_links(project_id))
    preprocessing_run_id = str(
        project.metadata.get("latest_preprocessing_run_id") or ""
    ).strip()

    normalized = message.casefold()
    asks_about_pipeline = any(
        token in normalized for token in ("pipeline", "workflow", "流程", "管线")
    )
    asks_about_failure = any(
        token in normalized for token in ("failed", "error", "log", "失败", "错误", "日志")
    )
    asks_about_dataset = any(
        token in normalized for token in ("dataset", "data", "bids", "数据")
    )
    asks_about_readiness = any(
        token in normalized
        for token in ("ready", "readiness", "summarize", "summary", "就绪", "总结", "概括")
    )

    if asks_about_failure:
        return (
            f"{project.name} has {execution_run_count} registered execution run(s). "
            "Open the Runs workspace to inspect persisted events, diagnostics, and logs for a "
            "selected run. External-tool failures require their recorded stdout, stderr, and "
            "result evidence. This response performed no execution."
        )

    if asks_about_pipeline:
        pipeline = project.current_pipeline_id or "not selected"
        return (
            f"{project.name} currently references pipeline '{pipeline}'. "
            f"The backend contains {reviewed_plan_count} reviewed plan(s) and "
            f"{execution_run_count} registered execution run(s). Rawdata remains read-only; "
            "execution still requires a matching reviewed plan, approval summary, execution "
            "ticket, and environment gates. This response performed no execution."
        )

    setup_detail = (
        f"Preprocessing setup run {preprocessing_run_id} is registered"
        if preprocessing_run_id
        else "No preprocessing setup run is registered"
    )
    readiness_reply = (
        f"{project.name} readiness from persisted backend state: {subjects} subject(s), "
        f"{scans} scan(s), dataset health {health}; {reviewed_plan_count} reviewed plan(s) and "
        f"{execution_run_count} registered execution run(s). {setup_detail}. Rawdata remains "
        "read-only, and external MATLAB/SPM/DPABI/GPU execution remains subject to backend "
        "approval and environment gates. This response performed no execution."
    )

    if asks_about_dataset or asks_about_readiness:
        return readiness_reply

    return (
        readiness_reply
        + " The local mock provider can explain this state, summarize failures, or draft "
        "review steps; it is not a real LLM provider and cannot approve or run a pipeline."
    )
