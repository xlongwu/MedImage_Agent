import { getJson } from "./client";
import type { ImagePlane, ImagePreview, ImageSources, ImageValidationReport } from "../types/image";

export function getImagePreview(
  projectId: string,
  sequence: string,
  subjectId?: string,
  sliceIndex?: number | null,
  plane: ImagePlane = "axial",
): Promise<ImagePreview> {
  const params = new URLSearchParams({ project_id: projectId, sequence });
  params.set("plane", plane);
  if (subjectId) {
    params.set("subject_id", subjectId);
  }
  if (sliceIndex !== undefined && sliceIndex !== null) {
    params.set("slice_index", String(sliceIndex));
  }
  return getJson<ImagePreview>(`/api/images/preview?${params.toString()}`);
}

export function getImageSources(projectId: string): Promise<ImageSources> {
  const params = new URLSearchParams({ project_id: projectId });
  return getJson<ImageSources>(`/api/images/sources?${params.toString()}`);
}

export function getImageManifest(projectId: string): Promise<ImageSources> {
  const params = new URLSearchParams({ project_id: projectId });
  return getJson<ImageSources>(`/api/images/manifest?${params.toString()}`);
}

export function getImageValidation(projectId: string): Promise<ImageValidationReport> {
  const params = new URLSearchParams({ project_id: projectId });
  return getJson<ImageValidationReport>(`/api/images/validation?${params.toString()}`);
}
