from __future__ import annotations

from src.backend.app.schemas.desktop import DatasetSummary, ProjectDetail, ReviewedPlanRecord
from src.backend.app.services.assistant_service import build_assistant_reply


class _AssistantStore:
    def __init__(self) -> None:
        self.project = ProjectDetail(
            id="project-1",
            name="Project One",
            study_id="study-1",
            modality="rs-fMRI",
            created_date="2026-07-24",
            subjects_count=2,
            current_pipeline_id="pipeline-reviewed",
            sequences=["T1", "BOLD"],
            scans_count=4,
            total_size="1 MB",
            current_model_id="model-none",
            metadata={"latest_preprocessing_run_id": "pp-123"},
        )

    def get_project(self, project_id: str):
        return self.project if project_id == self.project.id else None

    def get_dataset_summary(self, project_id: str):
        return DatasetSummary(
            project_id=project_id,
            subjects=2,
            scans=4,
            total_size="1 MB",
            health_status="Ready",
        )

    def list_reviewed_plans(self, project_id: str):
        return [
            ReviewedPlanRecord(
                reviewed_plan_id="reviewed-1",
                project_id=project_id,
                project_config_path="project.json",
                plan_hash="a" * 64,
                created_at="2026-07-24T00:00:00Z",
                updated_at="2026-07-24T00:00:00Z",
            )
        ]

    def list_run_links(self, project_id: str, reviewed_plan_id: str | None = None):
        return []


def test_assistant_readiness_uses_persisted_project_state_without_execution_claims() -> None:
    reply = build_assistant_reply(
        store=_AssistantStore(),  # type: ignore[arg-type]
        project_id="project-1",
        message="Summarize project readiness without executing anything.",
    )

    assert reply is not None
    assert "2 subject(s)" in reply
    assert "4 scan(s)" in reply
    assert "dataset health Ready" in reply
    assert "1 reviewed plan(s)" in reply
    assert "0 registered execution run(s)" in reply
    assert "pp-123" in reply
    assert "performed no execution" in reply
    assert "TODO" not in reply


def test_assistant_returns_none_for_unknown_project() -> None:
    assert (
        build_assistant_reply(
            store=_AssistantStore(),  # type: ignore[arg-type]
            project_id="missing",
            message="Summarize readiness",
        )
        is None
    )
