import { getImagePreview } from "../lib/api";
import { fallbackImagePreview } from "../lib/mockData";
import type { ImagePlane, ImagePreview } from "../lib/types/image";
import { useAsyncResource } from "./useAsyncResource";

export function useImagePreview(
  projectId: string | null,
  sequence: string,
  subjectId?: string | null,
  sliceIndex?: number | null,
  plane: ImagePlane = "axial",
) {
  return useAsyncResource<ImagePreview>(
    () =>
      projectId
        ? getImagePreview(projectId, sequence, subjectId || undefined, sliceIndex, plane)
        : Promise.resolve(fallbackImagePreview),
    { ...fallbackImagePreview, sequence, subject_id: subjectId, plane },
    [projectId, sequence, subjectId, sliceIndex, plane],
  );
}
