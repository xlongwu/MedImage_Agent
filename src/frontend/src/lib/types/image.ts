export type ImagePlane = "axial" | "sagittal" | "coronal";

export interface ImagePreview {
  project_id: string;
  subject_id?: string | null;
  sequence: string;
  plane?: ImagePlane;
  preview_url?: string | null;
  message: string;
  source?: string;
  source_path?: string | null;
  slice_index?: number | null;
  slice_count?: number | null;
  dimensions?: number[];
}

export interface ImageSourceFile {
  subject_id: string;
  sequence: string;
  file_path: string;
  relative_path: string;
  format: string;
  session_id?: string | null;
  source_root?: string | null;
  size_bytes?: number | null;
  modified_at?: string | null;
  dimensions: number[];
  voxel_spacing: number[];
  plane_slice_counts: Record<ImagePlane, number>;
  warnings: string[];
}

export interface ImageSourceSubject {
  subject_id: string;
  sequences: string[];
  files: Record<string, string>;
  file_details?: ImageSourceFile[];
}

export interface ImageSources {
  project_id: string;
  subjects: ImageSourceSubject[];
  sequences: string[];
  roots: string[];
  manifest?: ImageSourceFile[];
  manifest_path?: string | null;
  warnings?: string[];
}

export type ImageValidationSeverity = "info" | "warning" | "error";

export interface ImageValidationIssue {
  severity: ImageValidationSeverity;
  code: string;
  message: string;
  subject_id?: string | null;
  sequence?: string | null;
  file_path?: string | null;
}

export interface ImageValidationReport {
  ok: boolean;
  project_id: string;
  status: "pass" | "warning" | "fail";
  checked_at: string;
  source_count: number;
  subject_count: number;
  sequence_count: number;
  expected_sequences: string[];
  issues: ImageValidationIssue[];
  report_path?: string | null;
  json_path?: string | null;
  manifest_path?: string | null;
}
