import { requestJson } from "./legacyCore";

export async function createBundle(
  baseUrl: string,
  payload: {
    bundle_id?: string;
    include_logs?: boolean;
    include_reports?: boolean;
    include_artifact_index?: boolean;
    max_file_size_bytes?: number;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/bundles/create", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getArtifacts(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/artifacts");
}

export async function inspectBundle(baseUrl: string, bundleId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/bundles/${encodeURIComponent(bundleId)}`,
  );
}

export async function listBundles(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/bundles");
}

export async function previewArtifact(baseUrl: string, path: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/artifacts/preview", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function refreshArtifacts(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/artifacts/refresh", {
    method: "POST",
  });
}
