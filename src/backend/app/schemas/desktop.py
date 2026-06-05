from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["running", "completed", "failed", "pending", "disconnected"]
ExecutionMode = Literal["simulated", "external_smoke", "rsfmri_python"]
ExternalSmokeMode = Literal["manual_package", "approved_smoke"]
DatasetType = Literal["nifti", "dicom", "bids"]
ImagePlane = Literal["axial", "sagittal", "coronal"]
ImageValidationSeverity = Literal["info", "warning", "error"]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "medimage-agent-backend"
    version: str = "0.1.0"


class ProjectSummary(BaseModel):
    id: str
    name: str
    study_id: str
    modality: str
    created_date: str
    subjects_count: int
    current_pipeline_id: str


class ProjectDetail(ProjectSummary):
    sequences: list[str]
    scans_count: int
    total_size: str
    current_model_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewedPlanRecord(BaseModel):
    reviewed_plan_id: str
    project_id: str
    project_config_path: str
    dataset_index_path: str | None = None
    rawdata_dir: str | None = None
    plan_hash: str
    plan_path: str | None = None
    status: str = "REVIEWED"
    created_at: str
    updated_at: str
    approval_status: str = "PENDING"
    execution_status: str = "NOT_RUN"
    last_audit_id: str | None = None
    last_execution_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class RunLinkRecord(BaseModel):
    run_link_id: str
    project_id: str
    reviewed_plan_id: str
    run_id: str
    task_id: str | None = None
    pipeline_path: str | None = None
    summary_path: str | None = None
    project_config_path: str
    audit_id: str | None = None
    status: str = "REQUESTED"
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class StudyOverview(BaseModel):
    project_id: str
    study_id: str
    study_name: str
    modality: str
    sequences: list[str]
    subjects: int
    scans: int
    total_size: str
    date: str


class DatasetSummary(BaseModel):
    project_id: str
    subjects: int
    scans: int
    total_size: str
    health_status: str


class ModelStatus(BaseModel):
    project_id: str
    model_name: str
    version: str
    status: str
    dice_score: float
    last_trained: str
    metrics: dict[str, float]


class TaskLogEntry(BaseModel):
    id: str
    run_name: str
    pipeline: str
    dataset: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    started_at: str
    duration: str
    owner: str
    logs: list[str] = Field(default_factory=list)
    result_path: str | None = None
    execution_mode: ExecutionMode = "simulated"


class TaskDetail(TaskLogEntry):
    project_id: str
    pipeline_id: str
    model_id: str
    input_sequences: list[str]
    output_type: str
    updated_at: str


class TaskEvent(BaseModel):
    id: int
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: str
    timestamp: str
    result_path: str | None = None
    source: str = "task_manager"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRecord(BaseModel):
    approval_id: str
    task_id: str
    approved: bool
    approved_by: str
    approved_at: str
    approval_scope: str = "external_smoke_approved_run"
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class TaskApprovalRequest(BaseModel):
    approved: bool = False
    approved_by: str = ""
    approval_scope: str = "external_smoke_approved_run"
    safety_flags: dict[str, bool] = Field(
        default_factory=lambda: {
            "rawdata_read_only": True,
            "no_dparsf_blackbox": True,
            "matlab_external_execution": True,
        }
    )


class TaskApprovalResponse(BaseModel):
    ok: bool
    approval: ApprovalRecord | None = None
    message: str


class TaskDiagnosticsResponse(BaseModel):
    ok: bool
    task_id: str
    status: TaskStatus
    diagnosis: list[dict[str, Any]] = Field(default_factory=list)
    external_tool_results: list[dict[str, Any]] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    approval: ApprovalRecord | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TaskArtifactsResponse(BaseModel):
    ok: bool
    task_id: str
    result_path: str | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    approval: ApprovalRecord | None = None
    errors: list[str] = Field(default_factory=list)


class TaskAuditPackageResponse(BaseModel):
    ok: bool
    task_id: str
    generated_at: str
    package_dir: str
    report_path: str
    json_path: str
    report_text: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class DatasetImportRequest(BaseModel):
    project_id: str
    path: str
    type: DatasetType


class DatasetImportResponse(BaseModel):
    success: bool
    dataset_id: str
    message: str
    manifest_path: str | None = None
    image_source_count: int = 0
    validation_report_path: str | None = None
    validation_report_text: str | None = None
    validation_issue_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class DatasetImportRecord(BaseModel):
    dataset_id: str
    project_id: str
    path: str
    dataset_type: DatasetType
    created_at: str
    exists: bool = False


class DatasetImportHistoryResponse(BaseModel):
    ok: bool
    project_id: str
    imports: list[DatasetImportRecord] = Field(default_factory=list)


class DatasetDiagnosticsPackageResponse(BaseModel):
    ok: bool
    project_id: str
    generated_at: str
    package_dir: str
    report_path: str
    json_path: str
    zip_path: str
    checksum_path: str | None = None
    report_text: str
    checksums: dict[str, str] = Field(default_factory=dict)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
    file_inventory: dict[str, Any] = Field(default_factory=dict)
    manifest_path: str | None = None
    validation_report_path: str | None = None
    import_count: int = 0
    image_source_count: int = 0
    validation_issue_count: int = 0
    dicom_preflight_report_path: str | None = None
    dicom_preflight_json_path: str | None = None
    dicom_file_count: int = 0
    dicom_series_count: int = 0
    errors: list[str] = Field(default_factory=list)


class DatasetDiagnosticsPackageStatusResponse(BaseModel):
    ok: bool
    project_id: str
    latest: DatasetDiagnosticsPackageResponse | None = None
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class DatasetDiagnosticsPackageVerifyResponse(BaseModel):
    ok: bool
    project_id: str
    checked_at: str
    zip_path: str | None = None
    checksum_path: str | None = None
    checked_files: int = 0
    passed_files: int = 0
    failed_files: list[str] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomSeriesSummary(BaseModel):
    series_instance_uid: str
    study_instance_uid: str | None = None
    subject_id: str | None = None
    modality: str | None = None
    series_description: str | None = None
    protocol_name: str | None = None
    sequence_name: str | None = None
    manufacturer: str | None = None
    magnetic_field_strength: float | None = None
    repetition_time: float | None = None
    echo_time: float | None = None
    flip_angle: float | None = None
    rows: int | None = None
    columns: int | None = None
    instances: int = 0
    sample_file: str | None = None
    warnings: list[str] = Field(default_factory=list)


class DicomPreflightResponse(BaseModel):
    ok: bool
    project_id: str
    checked_at: str
    roots: list[str] = Field(default_factory=list)
    dicom_file_count: int = 0
    sampled_file_count: int = 0
    series_count: int = 0
    subjects: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    series: list[DicomSeriesSummary] = Field(default_factory=list)
    report_path: str | None = None
    json_path: str | None = None
    report_text: str | None = None
    safety_flags: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PipelineRunRequest(BaseModel):
    project_id: str
    pipeline_id: str
    model_id: str
    input_sequences: list[str]
    output_type: str
    execution_mode: ExecutionMode = "simulated"
    external_smoke_mode: ExternalSmokeMode = "manual_package"
    approved: bool = False
    approved_by: str | None = None
    dpabi_function: str = "y_Smooth"


class PipelineRunResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStreamMessage(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: str
    timestamp: str
    result_path: str | None = None


class AssistantChatRequest(BaseModel):
    project_id: str
    message: str


class AssistantChatResponse(BaseModel):
    reply: str


class ImagePreviewResponse(BaseModel):
    project_id: str
    subject_id: str | None = None
    sequence: str
    plane: ImagePlane = "axial"
    preview_url: str | None = None
    message: str
    source: str = "fallback"
    source_path: str | None = None
    slice_index: int | None = None
    slice_count: int | None = None
    dimensions: list[int] = Field(default_factory=list)


class ImageSourceFile(BaseModel):
    subject_id: str
    sequence: str
    file_path: str
    relative_path: str
    format: str = "nifti"
    session_id: str | None = None
    source_root: str | None = None
    size_bytes: int | None = None
    modified_at: str | None = None
    dimensions: list[int] = Field(default_factory=list)
    voxel_spacing: list[float] = Field(default_factory=list)
    plane_slice_counts: dict[ImagePlane, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ImageSourceSubject(BaseModel):
    subject_id: str
    sequences: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    file_details: list[ImageSourceFile] = Field(default_factory=list)


class ImageSourcesResponse(BaseModel):
    project_id: str
    subjects: list[ImageSourceSubject] = Field(default_factory=list)
    sequences: list[str] = Field(default_factory=list)
    roots: list[str] = Field(default_factory=list)
    manifest: list[ImageSourceFile] = Field(default_factory=list)
    manifest_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ImageValidationIssue(BaseModel):
    severity: ImageValidationSeverity
    code: str
    message: str
    subject_id: str | None = None
    sequence: str | None = None
    file_path: str | None = None


class ImageValidationReport(BaseModel):
    ok: bool
    project_id: str
    status: Literal["pass", "warning", "fail"]
    checked_at: str
    source_count: int = 0
    subject_count: int = 0
    sequence_count: int = 0
    expected_sequences: list[str] = Field(default_factory=list)
    issues: list[ImageValidationIssue] = Field(default_factory=list)
    report_path: str | None = None
    json_path: str | None = None
    manifest_path: str | None = None
    report_text: str | None = None
