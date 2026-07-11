from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from src.backend.app.schemas.desktop import (
    ApprovalRecord,
    DatasetImportRequest,
    DatasetImportResponse,
    DatasetSummary,
    ModelStatus,
    ProjectDetail,
    ProjectSummary,
    ReviewedPlanRecord,
    RunLinkRecord,
    StudyOverview,
    TaskDetail,
    TaskEvent,
    TaskLogEntry,
    TaskStatus,
)


DEFAULT_STORE_PATH = Path("outputs/work/desktop/desktop_state.sqlite")


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_desktop_store_path() -> Path:
    return Path(os.environ.get("MEDIMAGE_DESKTOP_STORE_PATH", DEFAULT_STORE_PATH))


class SQLiteDesktopStore:
    """SQLite-backed desktop store with deterministic seed data.

    The class keeps the old mock-store surface area so existing API routes and
    tests can keep using `mock_store`, while data now survives backend restarts.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else get_desktop_store_path()
        self._lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_if_empty()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS store_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    project_order INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS dataset_health (
                    project_id TEXT PRIMARY KEY,
                    health_status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS models (
                    project_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_events_task_id_id
                    ON task_events(task_id, id);
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_approvals_task_id_created_at
                    ON approvals(task_id, created_at);
                CREATE TABLE IF NOT EXISTS task_artifacts (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS imports (
                    dataset_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    dataset_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviewed_plans (
                    reviewed_plan_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_reviewed_plans_project_hash
                    ON reviewed_plans(project_id, plan_hash);
                CREATE INDEX IF NOT EXISTS idx_reviewed_plans_project_updated
                    ON reviewed_plans(project_id, updated_at);
                CREATE TABLE IF NOT EXISTS run_links (
                    run_link_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    reviewed_plan_id TEXT NOT NULL,
                    run_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_run_links_project_updated
                    ON run_links(project_id, updated_at);
                CREATE INDEX IF NOT EXISTS idx_run_links_reviewed_plan
                    ON run_links(reviewed_plan_id, updated_at);
                """
            )

    def _seed_if_empty(self) -> None:
        with self._lock, self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            if count:
                conn.execute(
                    """
                    INSERT INTO store_meta (key, value)
                    VALUES ('seeded_once', '1')
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """
                )
                return
            seeded = conn.execute(
                "SELECT value FROM store_meta WHERE key = 'seeded_once'"
            ).fetchone()
            if seeded:
                return

            projects = [
                ProjectDetail(
                    id="brain-tumor-study",
                    name="Brain Tumor Study",
                    study_id="BTS-2026-0525",
                    modality="MRI / rs-fMRI",
                    sequences=["T1", "T2", "FLAIR", "T1ce"],
                    subjects_count=128,
                    scans_count=1024,
                    total_size="512 GB",
                    created_date="May 25, 2026",
                    current_pipeline_id="brain-tumor-segmentation",
                    current_model_id="unet3d-v2.1",
                ),
                ProjectDetail(
                    id="ad-cohort",
                    name="AD Cohort",
                    study_id="ADC-2026-0417",
                    modality="rs-fMRI",
                    sequences=["T1", "BOLD"],
                    subjects_count=86,
                    scans_count=344,
                    total_size="224 GB",
                    created_date="April 17, 2026",
                    current_pipeline_id="rsfmri-alff-falff",
                    current_model_id="deterministic-qc-v1",
                ),
                ProjectDetail(
                    id="ms-lesion-analysis",
                    name="MS Lesion Analysis",
                    study_id="MSL-2026-0328",
                    modality="MRI",
                    sequences=["T1", "T2", "FLAIR"],
                    subjects_count=54,
                    scans_count=216,
                    total_size="118 GB",
                    created_date="March 28, 2026",
                    current_pipeline_id="lesion-detection",
                    current_model_id="unet-lesion-v1",
                ),
                ProjectDetail(
                    id="stroke-research",
                    name="Stroke Research",
                    study_id="STR-2026-0211",
                    modality="MRI / DWI",
                    sequences=["DWI", "ADC", "FLAIR"],
                    subjects_count=42,
                    scans_count=168,
                    total_size="96 GB",
                    created_date="February 11, 2026",
                    current_pipeline_id="stroke-qc",
                    current_model_id="qc-baseline-v1",
                ),
            ]
            for index, project in enumerate(projects):
                conn.execute(
                    "INSERT INTO projects (id, payload, project_order) VALUES (?, ?, ?)",
                    (project.id, self._dump_model(project), index),
                )

            dataset_health = {
                "brain-tumor-study": "Healthy",
                "ad-cohort": "Review",
                "ms-lesion-analysis": "Healthy",
                "stroke-research": "Healthy",
            }
            conn.executemany(
                "INSERT INTO dataset_health (project_id, health_status) VALUES (?, ?)",
                list(dataset_health.items()),
            )

            models = [
                ModelStatus(
                    project_id="brain-tumor-study",
                    model_name="UNet 3D",
                    version="v2.1",
                    status="Ready",
                    dice_score=0.892,
                    last_trained="May 15, 2026",
                    metrics={"dice": 0.892, "hausdorff95": 4.8, "sensitivity": 0.91},
                ),
                ModelStatus(
                    project_id="ad-cohort",
                    model_name="Deterministic rs-fMRI QC",
                    version="v1.4",
                    status="Ready",
                    dice_score=0.0,
                    last_trained="N/A",
                    metrics={"qc_pass_rate": 0.94, "mean_fd": 0.18},
                ),
                ModelStatus(
                    project_id="ms-lesion-analysis",
                    model_name="UNet Lesion",
                    version="v1.0",
                    status="Ready",
                    dice_score=0.841,
                    last_trained="April 04, 2026",
                    metrics={"dice": 0.841, "precision": 0.87},
                ),
                ModelStatus(
                    project_id="stroke-research",
                    model_name="QC Baseline",
                    version="v1.0",
                    status="Ready",
                    dice_score=0.0,
                    last_trained="N/A",
                    metrics={"qc_pass_rate": 0.9},
                ),
            ]
            for model in models:
                conn.execute(
                    "INSERT INTO models (project_id, payload) VALUES (?, ?)",
                    (model.project_id, self._dump_model(model)),
                )

            for task in self._seed_tasks():
                now = task.updated_at
                conn.execute(
                    "INSERT INTO tasks (id, payload, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (task.id, self._dump_model(task), now, now),
                )
                for log in task.logs:
                    event = TaskEvent(
                        id=0,
                        task_id=task.id,
                        status=task.status,
                        progress=task.progress,
                        message=log,
                        timestamp=now,
                        result_path=task.result_path,
                        source="seed",
                    )
                    conn.execute(
                        "INSERT INTO task_events (task_id, payload, created_at) VALUES (?, ?, ?)",
                        (task.id, self._dump_model(event, exclude={"id"}), now),
                    )
            conn.execute(
                """
                INSERT INTO store_meta (key, value)
                VALUES ('seeded_once', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )

    def _seed_tasks(self) -> list[TaskDetail]:
        return [
            TaskDetail(
                id="task-001",
                run_name="Run_2026_0525_001",
                pipeline="SPM + DPABI Smoke",
                dataset="Brain Tumor Study",
                status="running",
                progress=64,
                started_at="09:42",
                duration="00:18:24",
                owner="Dr. Alex Morgan",
                logs=["External smoke package generated", "Awaiting approved smoke run"],
                result_path=None,
                execution_mode="external_smoke",
                project_id="brain-tumor-study",
                pipeline_id="external-smoke",
                model_id="deterministic-planner",
                input_sequences=["T1", "BOLD"],
                output_type="diagnostics",
                updated_at=utc_now_iso(),
            ),
            TaskDetail(
                id="task-002",
                run_name="Run_2026_0524_014",
                pipeline="rs-fMRI ALFF/fALFF",
                dataset="AD Cohort",
                status="completed",
                progress=100,
                started_at="Yesterday",
                duration="01:42:11",
                owner="Dr. Alex Morgan",
                logs=["ALFF/fALFF report exported"],
                result_path="outputs/reports/rsfmri/alff_falff_latest.html",
                execution_mode="rsfmri_python",
                project_id="ad-cohort",
                pipeline_id="rsfmri-alff-falff",
                model_id="deterministic-qc-v1",
                input_sequences=["T1", "BOLD"],
                output_type="qc_report",
                updated_at=utc_now_iso(),
            ),
            TaskDetail(
                id="task-003",
                run_name="Run_2026_0523_009",
                pipeline="ReHo QC",
                dataset="Demo BIDS",
                status="completed",
                progress=100,
                started_at="May 23",
                duration="00:55:47",
                owner="Dr. Alex Morgan",
                logs=["ReHo QC passed"],
                result_path="outputs/reports/rsfmri/reho_latest.html",
                execution_mode="rsfmri_python",
                project_id="brain-tumor-study",
                pipeline_id="rsfmri-reho",
                model_id="deterministic-qc-v1",
                input_sequences=["BOLD"],
                output_type="qc_report",
                updated_at=utc_now_iso(),
            ),
            TaskDetail(
                id="task-004",
                run_name="Run_2026_0522_017",
                pipeline="DPABI y_Filter",
                dataset="Sandbox",
                status="failed",
                progress=20,
                started_at="May 22",
                duration="00:07:32",
                owner="Dr. Alex Morgan",
                logs=["Missing expected DPABI result JSON"],
                result_path=None,
                execution_mode="external_smoke",
                project_id="brain-tumor-study",
                pipeline_id="dpabi-y-filter",
                model_id="matlab-runner",
                input_sequences=["BOLD"],
                output_type="diagnostics",
                updated_at=utc_now_iso(),
            ),
        ]

    def list_projects(self) -> list[ProjectSummary]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT payload FROM projects ORDER BY project_order, id").fetchall()
        return [
            ProjectSummary(**self._load_payload(row["payload"], ProjectDetail).model_dump(exclude={"sequences", "scans_count", "total_size", "current_model_id", "metadata"}))
            for row in rows
        ]

    def get_project(self, project_id: str) -> ProjectDetail | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM projects WHERE id = ?", (project_id,)).fetchone()
        return self._load_payload(row["payload"], ProjectDetail) if row else None

    def add_project(
        self,
        project: ProjectDetail,
        *,
        health_status: str,
        rawdata_dir: str,
        dataset_type: str = "bids",
        overwrite: bool = False,
    ) -> ProjectDetail:
        """Persist a dashboard project and its referenced rawdata atomically."""
        dataset_id = f"created-{project.id}-rawdata"
        created_at = str(project.metadata.get("created_at") or utc_now_iso())
        rawdata_dir = rawdata_dir.strip()
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM projects WHERE id = ?",
                (project.id,),
            ).fetchone()
            if existing and not overwrite:
                raise ValueError(f"Project already exists: {project.id}")

            if existing:
                conn.execute(
                    "UPDATE projects SET payload = ? WHERE id = ?",
                    (self._dump_model(project), project.id),
                )
            else:
                next_order = conn.execute(
                    "SELECT COALESCE(MAX(project_order), -1) + 1 FROM projects"
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO projects (id, payload, project_order) VALUES (?, ?, ?)",
                    (project.id, self._dump_model(project), next_order),
                )

            conn.execute(
                """
                INSERT INTO dataset_health (project_id, health_status)
                VALUES (?, ?)
                ON CONFLICT(project_id) DO UPDATE SET health_status = excluded.health_status
                """,
                (project.id, health_status),
            )
            if rawdata_dir:
                conn.execute(
                    """
                    INSERT INTO imports (dataset_id, project_id, path, dataset_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(dataset_id) DO UPDATE SET
                        project_id = excluded.project_id,
                        path = excluded.path,
                        dataset_type = excluded.dataset_type,
                        created_at = excluded.created_at
                    """,
                    (dataset_id, project.id, rawdata_dir, dataset_type, created_at),
                )
        return project

    def remove_project(self, project_id: str) -> bool:
        """Remove dashboard records for a project without deleting filesystem data."""
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            if not existing:
                return False

            task_ids: list[str] = []
            rows = conn.execute("SELECT id, payload FROM tasks").fetchall()
            for row in rows:
                try:
                    payload = json.loads(row["payload"])
                except json.JSONDecodeError:
                    payload = {}
                if payload.get("project_id") == project_id:
                    task_ids.append(str(row["id"]))

            for task_id in task_ids:
                conn.execute("DELETE FROM approvals WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM task_events WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM task_artifacts WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

            conn.execute("DELETE FROM run_links WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM reviewed_plans WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM imports WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM dataset_health WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM models WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return True

    def add_reviewed_plan(self, record: ReviewedPlanRecord) -> ReviewedPlanRecord:
        """Insert or refresh the index entry for a stable project/plan hash."""
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                """
                SELECT reviewed_plan_id, payload FROM reviewed_plans
                WHERE project_id = ? AND plan_hash = ?
                """,
                (record.project_id, record.plan_hash),
            ).fetchone()
            if existing:
                current = ReviewedPlanRecord(**json.loads(existing["payload"]))
                updated = record.model_copy(
                    update={
                        "reviewed_plan_id": current.reviewed_plan_id,
                        "created_at": current.created_at,
                        "approval_status": current.approval_status,
                        "execution_status": current.execution_status,
                        "last_audit_id": current.last_audit_id,
                        "last_execution_id": current.last_execution_id,
                        "warnings": list(
                            dict.fromkeys([*current.warnings, *record.warnings])
                        ),
                    }
                )
                conn.execute(
                    """
                    UPDATE reviewed_plans
                    SET payload = ?, updated_at = ?
                    WHERE reviewed_plan_id = ?
                    """,
                    (
                        self._dump_model(updated),
                        updated.updated_at,
                        current.reviewed_plan_id,
                    ),
                )
                return updated

            duplicate_id = conn.execute(
                "SELECT 1 FROM reviewed_plans WHERE reviewed_plan_id = ?",
                (record.reviewed_plan_id,),
            ).fetchone()
            if duplicate_id:
                raise ValueError(
                    f"Reviewed plan id already exists: {record.reviewed_plan_id}"
                )
            conn.execute(
                """
                INSERT INTO reviewed_plans
                    (reviewed_plan_id, project_id, plan_hash, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.reviewed_plan_id,
                    record.project_id,
                    record.plan_hash,
                    self._dump_model(record),
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def get_reviewed_plan(self, reviewed_plan_id: str) -> ReviewedPlanRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM reviewed_plans WHERE reviewed_plan_id = ?",
                (reviewed_plan_id,),
            ).fetchone()
        return ReviewedPlanRecord(**json.loads(row["payload"])) if row else None

    def find_reviewed_plan(
        self,
        project_id: str,
        plan_hash: str,
    ) -> ReviewedPlanRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload FROM reviewed_plans
                WHERE project_id = ? AND plan_hash = ?
                """,
                (project_id, plan_hash),
            ).fetchone()
        return ReviewedPlanRecord(**json.loads(row["payload"])) if row else None

    def list_reviewed_plans(self, project_id: str) -> list[ReviewedPlanRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM reviewed_plans
                WHERE project_id = ?
                ORDER BY updated_at DESC, reviewed_plan_id DESC
                """,
                (project_id,),
            ).fetchall()
        return [ReviewedPlanRecord(**json.loads(row["payload"])) for row in rows]

    def update_reviewed_plan(
        self,
        reviewed_plan_id: str,
        **updates: object,
    ) -> ReviewedPlanRecord | None:
        current = self.get_reviewed_plan(reviewed_plan_id)
        if current is None:
            return None
        payload = current.model_dump()
        payload.update(updates)
        payload["updated_at"] = str(updates.get("updated_at") or utc_now_iso())
        updated = ReviewedPlanRecord(**payload)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE reviewed_plans SET payload = ?, updated_at = ?
                WHERE reviewed_plan_id = ?
                """,
                (self._dump_model(updated), updated.updated_at, reviewed_plan_id),
            )
        return updated

    def add_run_link(self, record: RunLinkRecord) -> RunLinkRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_links
                    (run_link_id, project_id, reviewed_plan_id, run_id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_link_id,
                    record.project_id,
                    record.reviewed_plan_id,
                    record.run_id,
                    self._dump_model(record),
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def get_run_link_by_run_id(
        self,
        project_id: str,
        run_id: str,
    ) -> RunLinkRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload FROM run_links
                WHERE project_id = ? AND run_id = ?
                """,
                (project_id, run_id),
            ).fetchone()
        return RunLinkRecord(**json.loads(row["payload"])) if row else None

    def list_run_links(
        self,
        project_id: str,
        reviewed_plan_id: str | None = None,
    ) -> list[RunLinkRecord]:
        query = """
            SELECT payload FROM run_links
            WHERE project_id = ?
        """
        params: tuple[object, ...] = (project_id,)
        if reviewed_plan_id:
            query += " AND reviewed_plan_id = ?"
            params = (project_id, reviewed_plan_id)
        query += " ORDER BY updated_at DESC, run_link_id DESC"
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [RunLinkRecord(**json.loads(row["payload"])) for row in rows]

    def update_run_link(
        self,
        run_link_id: str,
        **updates: object,
    ) -> RunLinkRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM run_links WHERE run_link_id = ?",
                (run_link_id,),
            ).fetchone()
            if row is None:
                return None
            payload = json.loads(row["payload"])
            payload.update(updates)
            payload["updated_at"] = str(updates.get("updated_at") or utc_now_iso())
            updated = RunLinkRecord(**payload)
            conn.execute(
                """
                UPDATE run_links SET payload = ?, updated_at = ?
                WHERE run_link_id = ?
                """,
                (self._dump_model(updated), updated.updated_at, run_link_id),
            )
        return updated

    def get_study_overview(self, study_id: str) -> StudyOverview | None:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT payload FROM projects ORDER BY project_order, id").fetchall()
        for row in rows:
            project = self._load_payload(row["payload"], ProjectDetail)
            if project.study_id == study_id:
                subjects = project.subjects_count
                scans = project.scans_count
                dicom_subjects = 0
                dicom_series = 0
                dicom_files = 0
                if project.metadata:
                    try:
                        from src.backend.app.services.data_readiness import build_data_readiness
                        dr = build_data_readiness(project.id)
                        if dr.image_source_count > 0:
                            subjects = dr.subject_count
                            scans = dr.image_source_count
                        elif dr.dicom_file_count > 0 or dr.dicom_series_count > 0:
                            subjects = 0
                            scans = 0
                            dicom_subjects = dr.subject_count
                            dicom_series = dr.dicom_series_count
                            dicom_files = dr.dicom_file_count
                    except Exception:
                        subjects = project.subjects_count
                        scans = project.scans_count

                return StudyOverview(
                    project_id=project.id,
                    study_id=project.study_id,
                    study_name=project.name,
                    modality=project.modality,
                    sequences=project.sequences,
                    subjects=subjects,
                    scans=scans,
                    total_size=project.total_size,
                    date=project.created_date,
                    dicom_subjects=dicom_subjects,
                    dicom_series=dicom_series,
                    dicom_files=dicom_files,
                )
        return None

    def get_dataset_summary(self, project_id: str) -> DatasetSummary | None:
        project = self.get_project(project_id)
        if not project:
            return None
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT health_status FROM dataset_health WHERE project_id = ?", (project_id,)).fetchone()

        subjects = project.subjects_count
        scans = project.scans_count
        dicom_subjects = 0
        dicom_series = 0
        dicom_files = 0
        if project.metadata:
            try:
                from src.backend.app.services.data_readiness import build_data_readiness
                dr = build_data_readiness(project_id)
                if dr.image_source_count > 0:
                    subjects = dr.subject_count
                    scans = dr.image_source_count
                elif dr.dicom_file_count > 0 or dr.dicom_series_count > 0:
                    subjects = 0
                    scans = 0
                    dicom_subjects = dr.subject_count
                    dicom_series = dr.dicom_series_count
                    dicom_files = dr.dicom_file_count
            except Exception:
                subjects = project.subjects_count
                scans = project.scans_count

        return DatasetSummary(
            project_id=project.id,
            subjects=subjects,
            scans=scans,
            total_size=project.total_size,
            health_status=row["health_status"] if row else "Unknown",
            dicom_subjects=dicom_subjects,
            dicom_series=dicom_series,
            dicom_files=dicom_files,
        )

    def get_model_status(self, project_id: str) -> ModelStatus | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM models WHERE project_id = ?", (project_id,)).fetchone()
        return self._load_payload(row["payload"], ModelStatus) if row else None

    def list_tasks(self) -> list[TaskLogEntry]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT payload FROM tasks ORDER BY updated_at DESC, id DESC").fetchall()
        return [TaskLogEntry(**self._load_task_payload(row["payload"]).model_dump()) for row in rows]

    def get_task(self, task_id: str) -> TaskDetail | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._load_task_payload(row["payload"]) if row else None

    def add_task(self, task: TaskDetail) -> TaskDetail:
        now = task.updated_at or utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (task.id, self._dump_model(task), now, now),
            )
        return task

    def update_task(self, task_id: str, **updates: object) -> TaskDetail | None:
        current = self.get_task(task_id)
        if not current:
            return None
        payload = current.model_dump()
        payload.update(updates)
        payload["updated_at"] = utc_now_iso()
        updated = TaskDetail(**payload)
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET payload = ?, updated_at = ? WHERE id = ?",
                (self._dump_model(updated), updated.updated_at, task_id),
            )
        return updated

    def append_task_event(
        self,
        task_id: str,
        *,
        status: TaskStatus,
        progress: int,
        message: str,
        result_path: str | None = None,
        source: str = "task_manager",
        metadata: dict[str, object] | None = None,
    ) -> TaskEvent:
        timestamp = utc_now_iso()
        event = TaskEvent(
            id=0,
            task_id=task_id,
            status=status,
            progress=progress,
            message=message,
            timestamp=timestamp,
            result_path=result_path,
            source=source,
            metadata=dict(metadata or {}),
        )
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO task_events (task_id, payload, created_at) VALUES (?, ?, ?)",
                (task_id, self._dump_model(event, exclude={"id"}), timestamp),
            )
            event = event.model_copy(update={"id": int(cursor.lastrowid)})
        return event

    def list_task_events(self, task_id: str, limit: int = 200) -> list[TaskEvent]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, payload FROM task_events
                WHERE task_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (task_id, limit),
            ).fetchall()
        events: list[TaskEvent] = []
        for row in reversed(rows):
            payload = json.loads(row["payload"])
            payload["id"] = row["id"]
            events.append(TaskEvent(**payload))
        return events

    def add_approval(
        self,
        task_id: str,
        *,
        approved: bool,
        approved_by: str,
        approval_scope: str = "external_smoke_approved_run",
        safety_flags: dict[str, bool] | None = None,
    ) -> ApprovalRecord:
        approval = ApprovalRecord(
            approval_id=f"approval-{uuid4().hex[:10]}",
            task_id=task_id,
            approved=approved,
            approved_by=approved_by,
            approved_at=utc_now_iso(),
            approval_scope=approval_scope,
            safety_flags=dict(safety_flags or {}),
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO approvals (approval_id, task_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (approval.approval_id, task_id, self._dump_model(approval), approval.approved_at),
            )
        return approval

    def get_latest_approval(self, task_id: str) -> ApprovalRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload FROM approvals
                WHERE task_id = ?
                ORDER BY created_at DESC, approval_id DESC
                LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        return ApprovalRecord(**json.loads(row["payload"])) if row else None

    def save_task_artifacts(self, task_id: str, payload: dict[str, object]) -> dict[str, object]:
        updated_at = utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_artifacts (task_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (task_id, json.dumps(payload, ensure_ascii=False), updated_at),
            )
        return payload

    def get_task_artifacts(self, task_id: str) -> dict[str, object]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM task_artifacts WHERE task_id = ?", (task_id,)).fetchone()
        return json.loads(row["payload"]) if row else {}

    def import_dataset(self, request: DatasetImportRequest) -> DatasetImportResponse:
        if not self.get_project(request.project_id):
            raise KeyError(request.project_id)
        dataset_id = f"dataset-{uuid4().hex[:8]}"
        created_at = utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO imports (dataset_id, project_id, path, dataset_type, created_at) VALUES (?, ?, ?, ?, ?)",
                (dataset_id, request.project_id, request.path, request.type, created_at),
            )
            conn.execute(
                """
                INSERT INTO dataset_health (project_id, health_status)
                VALUES (?, ?)
                ON CONFLICT(project_id) DO UPDATE SET health_status = excluded.health_status
                """,
                (request.project_id, "Imported"),
            )
        return DatasetImportResponse(success=True, dataset_id=dataset_id, message="Dataset imported")

    def list_import_paths(self, project_id: str) -> list[str]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT path FROM imports
                WHERE project_id = ?
                ORDER BY created_at DESC, dataset_id DESC
                """,
                (project_id,),
            ).fetchall()
        return [path for row in rows if (path := str(row["path"]).strip())]

    def list_import_records(self, project_id: str) -> list[dict[str, object]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT dataset_id, project_id, path, dataset_type, created_at FROM imports
                WHERE project_id = ?
                ORDER BY created_at DESC, dataset_id DESC
                """,
                (project_id,),
            ).fetchall()
        return [
            {
                "dataset_id": row["dataset_id"],
                "project_id": row["project_id"],
                "path": row["path"],
                "dataset_type": row["dataset_type"],
                "created_at": row["created_at"],
                "exists": bool(path := str(row["path"]).strip()) and Path(path).exists(),
            }
            for row in rows
        ]

    def health_check(self) -> dict[str, object]:
        try:
            with self._lock, self._connect() as conn:
                project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
                task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                event_count = conn.execute("SELECT COUNT(*) FROM task_events").fetchone()[0]
                approval_count = conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
                reviewed_plan_count = conn.execute("SELECT COUNT(*) FROM reviewed_plans").fetchone()[0]
                run_link_count = conn.execute("SELECT COUNT(*) FROM run_links").fetchone()[0]
            return {
                "name": "desktop_store",
                "ok": True,
                "path": str(self.db_path),
                "project_count": project_count,
                "task_count": task_count,
                "event_count": event_count,
                "approval_count": approval_count,
                "reviewed_plan_count": reviewed_plan_count,
                "run_link_count": run_link_count,
            }
        except Exception as exc:
            return {"name": "desktop_store", "ok": False, "path": str(self.db_path), "error": str(exc)}

    @staticmethod
    def _dump_model(model: object, exclude: set[str] | None = None) -> str:
        if hasattr(model, "model_dump"):
            payload = model.model_dump(exclude=exclude or set())
        else:
            payload = dict(model)  # type: ignore[arg-type]
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _load_payload(payload: str, model_type: type[ProjectDetail] | type[ModelStatus]) -> ProjectDetail | ModelStatus:
        return model_type(**json.loads(payload))

    @staticmethod
    def _load_task_payload(payload: str) -> TaskDetail:
        data = json.loads(payload)
        data.setdefault("execution_mode", "simulated")
        return TaskDetail(**data)


mock_store = SQLiteDesktopStore()
