import { getDatasetSummary } from "../lib/api";
import { fallbackDatasetSummary } from "../lib/mockData";
import type { DatasetSummary } from "../lib/types/dataset";
import { useAsyncResource } from "./useAsyncResource";

export function useDatasetSummary(projectId: string | null) {
  return useAsyncResource<DatasetSummary>(
    projectId ? () => getDatasetSummary(projectId) : null,
    fallbackDatasetSummary,
    [projectId],
  );
}
