import { requestJson } from "./legacyCore";

export async function getSessionRuns(baseUrl: string, status?: string) {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return requestJson<Record<string, unknown>>(baseUrl, `/api/sessions/runs${params}`);
}

export async function postSessionIndex(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/sessions/index", { method: "POST" });
}

export async function querySessions(baseUrl: string, q: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/sessions/query?q=${encodeURIComponent(q)}&limit=50`,
  );
}

// === Tool Catalog ===
