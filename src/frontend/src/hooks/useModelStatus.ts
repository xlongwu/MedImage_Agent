import { getModelStatus } from "../lib/api";
import { fallbackModelStatus } from "../lib/mockData";
import type { ModelStatus } from "../lib/types/model";
import { useAsyncResource } from "./useAsyncResource";

export function useModelStatus(projectId: string | null) {
  return useAsyncResource<ModelStatus>(
    () => (projectId ? getModelStatus(projectId) : Promise.resolve(fallbackModelStatus)),
    fallbackModelStatus,
    [projectId],
  );
}
