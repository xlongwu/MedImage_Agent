import { getProjectBidsValidation } from "../lib/api/dicom";
import type { BidsValidationResponse } from "../types";
import { useAsyncResource } from "./useAsyncResource";

export function useProjectBidsValidation(baseUrl: string, projectId: string | null) {
  return useAsyncResource<BidsValidationResponse | null>(
    projectId ? () => getProjectBidsValidation(baseUrl, projectId) : null,
    null,
    [baseUrl, projectId],
  );
}
