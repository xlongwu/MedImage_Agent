export interface ProjectSummary {
  id: string;
  name: string;
  study_id: string;
  modality: string;
  created_date: string;
  subjects_count: number;
  current_pipeline_id: string;
}

export interface ProjectDetail extends ProjectSummary {
  sequences: string[];
  scans_count: number;
  total_size: string;
  current_model_id: string;
}

export interface StudyOverview {
  project_id: string;
  study_id: string;
  study_name: string;
  modality: string;
  sequences: string[];
  subjects: number;
  scans: number;
  total_size: string;
  date: string;
}

