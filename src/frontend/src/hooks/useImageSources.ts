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
  return useAsyncResource<ImageSources>(
    projectId ? () => getImageSources(projectId) : null,
    emptySources,
    [projectId],
  );
}
