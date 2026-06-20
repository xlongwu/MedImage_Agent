from __future__ import annotations

from typing import Any, Protocol

from src.backend.app.schemas.desktop import (
    DatasetSummary,
    ProjectDetail,
    ProjectSummary,
    ReviewedPlanRecord,
    RunLinkRecord,
    StudyOverview,
)
class ProjectStore(Protocol):
    def list_projects(self) -> list[ProjectSummary]: ...

    def get_project(self, project_id: str) -> ProjectDetail | None: ...

    def get_study_overview(self, study_id: str) -> StudyOverview | None: ...

    def get_dataset_summary(self, project_id: str) -> DatasetSummary | None: ...

    def list_import_records(self, project_id: str) -> list[dict[str, Any]]: ...

    def list_import_paths(self, project_id: str) -> list[str]: ...

    def list_reviewed_plans(self, project_id: str) -> list[ReviewedPlanRecord]: ...

    def get_reviewed_plan(self, reviewed_plan_id: str) -> ReviewedPlanRecord | None: ...

    def list_run_links(
        self,
        project_id: str,
        reviewed_plan_id: str | None = None,
    ) -> list[RunLinkRecord]: ...

    def get_run_link_by_run_id(
        self,
        project_id: str,
        run_id: str,
    ) -> RunLinkRecord | None: ...


def get_project_store() -> ProjectStore:
    from src.backend.app.services.mock_store import mock_store
    return mock_store
