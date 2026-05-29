export type DatasetType = "nifti" | "dicom" | "bids";

export interface DatasetSummary {
  project_id: string;
  subjects: number;
  scans: number;
  total_size: string;
  health_status: string;
}

export interface DatasetImportRequest {
  project_id: string;
  path: string;
  type: DatasetType;
}

export interface DatasetImportResponse {
  success: boolean;
  dataset_id: string;
  message: string;
  manifest_path?: string | null;
  image_source_count?: number;
  validation_report_path?: string | null;
  validation_report_text?: string | null;
  validation_issue_count?: number;
  warnings?: string[];
}
