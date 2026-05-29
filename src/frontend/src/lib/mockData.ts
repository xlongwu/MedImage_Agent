import type { ChatMessage } from "./types/assistant";
import type { DatasetSummary } from "./types/dataset";
import type { ImagePreview } from "./types/image";
import type { ModelStatus } from "./types/model";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "./types/project";
import type { TaskLogEntry } from "./types/task";

export const fallbackProjects: ProjectSummary[] = [
  {
    id: "brain-tumor-study",
    name: "Brain Tumor Study",
    study_id: "BTS-2026-0525",
    modality: "MRI / rs-fMRI",
    created_date: "May 25, 2026",
    subjects_count: 128,
    current_pipeline_id: "brain-tumor-segmentation",
  },
  {
    id: "ad-cohort",
    name: "AD Cohort",
    study_id: "ADC-2026-0417",
    modality: "rs-fMRI",
    created_date: "April 17, 2026",
    subjects_count: 86,
    current_pipeline_id: "rsfmri-alff-falff",
  },
  {
    id: "ms-lesion-analysis",
    name: "MS Lesion Analysis",
    study_id: "MSL-2026-0328",
    modality: "MRI",
    created_date: "March 28, 2026",
    subjects_count: 54,
    current_pipeline_id: "lesion-detection",
  },
  {
    id: "stroke-research",
    name: "Stroke Research",
    study_id: "STR-2026-0211",
    modality: "MRI / DWI",
    created_date: "February 11, 2026",
    subjects_count: 42,
    current_pipeline_id: "stroke-qc",
  },
];

export const fallbackProjectDetail: ProjectDetail = {
  ...fallbackProjects[0],
  sequences: ["T1", "T2", "FLAIR", "T1ce"],
  scans_count: 1024,
  total_size: "512 GB",
  current_model_id: "unet3d-v2.1",
};

export const fallbackOverview: StudyOverview = {
  project_id: "brain-tumor-study",
  study_id: "BTS-2026-0525",
  study_name: "Brain Tumor Study",
  modality: "MRI / rs-fMRI",
  sequences: ["T1", "T2", "FLAIR", "T1ce"],
  subjects: 128,
  scans: 1024,
  total_size: "512 GB",
  date: "May 25, 2026",
};

export const fallbackDatasetSummary: DatasetSummary = {
  project_id: "brain-tumor-study",
  subjects: 128,
  scans: 1024,
  total_size: "512 GB",
  health_status: "Healthy",
};

export const fallbackModelStatus: ModelStatus = {
  project_id: "brain-tumor-study",
  model_name: "UNet 3D",
  version: "v2.1",
  status: "Ready",
  dice_score: 0.892,
  last_trained: "May 15, 2026",
  metrics: {
    dice: 0.892,
    sensitivity: 0.91,
    hausdorff95: 4.8,
  },
};

export const fallbackTasks: TaskLogEntry[] = [
  {
    id: "task-001",
    run_name: "Run_2026_0525_001",
    pipeline: "SPM + DPABI Smoke",
    dataset: "Brain Tumor Study",
    status: "running",
    progress: 64,
    started_at: "09:42",
    duration: "00:18:24",
    owner: "Dr. Alex Morgan",
    logs: ["External smoke package generated"],
    result_path: null,
  },
  {
    id: "task-002",
    run_name: "Run_2026_0524_014",
    pipeline: "rs-fMRI ALFF/fALFF",
    dataset: "AD Cohort",
    status: "completed",
    progress: 100,
    started_at: "Yesterday",
    duration: "01:42:11",
    owner: "Dr. Alex Morgan",
    logs: ["ALFF/fALFF report exported"],
    result_path: "outputs/reports/rsfmri/alff_falff_latest.html",
  },
  {
    id: "task-003",
    run_name: "Run_2026_0523_009",
    pipeline: "ReHo QC",
    dataset: "Demo BIDS",
    status: "completed",
    progress: 100,
    started_at: "May 23",
    duration: "00:55:47",
    owner: "Dr. Alex Morgan",
    logs: ["ReHo QC passed"],
    result_path: "outputs/reports/rsfmri/reho_latest.html",
  },
  {
    id: "task-004",
    run_name: "Run_2026_0522_017",
    pipeline: "DPABI y_Filter",
    dataset: "Sandbox",
    status: "failed",
    progress: 20,
    started_at: "May 22",
    duration: "00:07:32",
    owner: "Dr. Alex Morgan",
    logs: ["Missing expected DPABI result JSON"],
    result_path: null,
  },
];

export const fallbackImagePreview: ImagePreview = {
  project_id: "brain-tumor-study",
  subject_id: null,
  sequence: "T1",
  plane: "axial",
  preview_url: null,
  message: "Using synthetic MRI fallback.",
};

export const fallbackChat: ChatMessage[] = [
  {
    role: "assistant",
    text: "Hi Dr. Morgan. I can help configure auditable SPM/DPABI smoke checks, inspect QC reports, and summarize pipeline readiness.",
  },
];
