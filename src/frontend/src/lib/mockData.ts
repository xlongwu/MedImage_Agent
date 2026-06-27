import type { ChatMessage } from "./types/assistant";
import type { DatasetSummary } from "./types/dataset";
import type { ImagePreview } from "./types/image";
import type { ModelStatus } from "./types/model";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "./types/project";
import type { TaskLogEntry } from "./types/task";

export const fallbackProjects: ProjectSummary[] = [];

export const fallbackProjectDetail: ProjectDetail = {
  id: "unselected-project",
  name: "No project selected",
  study_id: "not-selected",
  modality: "Research project",
  created_date: "Not loaded",
  subjects_count: 0,
  current_pipeline_id: "not-selected",
  sequences: [],
  scans_count: 0,
  total_size: "0 B",
  current_model_id: "not-selected",
  metadata: {
    source: "empty_fallback",
  },
};

export const fallbackOverview: StudyOverview = {
  project_id: "unselected-project",
  study_id: "not-selected",
  study_name: "No project selected",
  modality: "Research project",
  sequences: [],
  subjects: 0,
  scans: 0,
  total_size: "0 B",
  date: "Not loaded",
};

export const fallbackDatasetSummary: DatasetSummary = {
  project_id: "unselected-project",
  subjects: 0,
  scans: 0,
  total_size: "0 B",
  health_status: "No project selected",
};

export const fallbackModelStatus: ModelStatus = {
  project_id: "unselected-project",
  model_name: "No model selected",
  version: "",
  status: "Unavailable",
  dice_score: 0,
  last_trained: "Not loaded",
  metrics: {},
};

export const fallbackTasks: TaskLogEntry[] = [];

export const fallbackImagePreview: ImagePreview = {
  project_id: "unselected-project",
  subject_id: null,
  sequence: "T1",
  plane: "axial",
  preview_url: null,
  message: "No registered image preview is available.",
};

export const fallbackChat: ChatMessage[] = [
  {
    role: "assistant",
    text: "I can help review project readiness, explain pipeline states, and summarize auditable next steps once a project is selected.",
  },
];
