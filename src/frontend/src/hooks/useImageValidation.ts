import { getImageValidation } from "../lib/api";
import type { ImageValidationReport } from "../lib/types/image";
import { useAsyncResource } from "./useAsyncResource";

const emptyValidation: ImageValidationReport = {
  ok: false,
  project_id: "",
  status: "fail",
  checked_at: "",
  source_count: 0,
  subject_count: 0,
  sequence_count: 0,
  expected_sequences: [],
  issues: [],
  report_path: null,
  json_path: null,
  manifest_path: null,
};

export function useImageValidation(projectId: string | null) {
  return useAsyncResource<ImageValidationReport>(
    projectId ? () => getImageValidation(projectId) : null,
    emptyValidation,
    [projectId],
  );
}
