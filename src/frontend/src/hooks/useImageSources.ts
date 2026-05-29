import { useCallback } from "react";
import { getImageSources } from "../lib/api";
import type { ImageSources } from "../lib/types/image";
import { useAsyncResource } from "./useAsyncResource";

const emptySources: ImageSources = {
  project_id: "",
  subjects: [],
  sequences: [],
  roots: [],
  manifest: [],
  manifest_path: null,
  warnings: [],
};

export function useImageSources(projectId: string | null) {
  const loader = useCallback(() => {
    if (!projectId) {
      return Promise.resolve(emptySources);
    }
    return getImageSources(projectId);
  }, [projectId]);

  return useAsyncResource<ImageSources>(loader, emptySources, [projectId]);
}
