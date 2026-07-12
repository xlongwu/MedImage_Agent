import type { ImagePreview } from "../../lib/types/image";

export function hasRealImagePreview(preview: ImagePreview | null): boolean {
  return Boolean(preview?.preview_url);
}
