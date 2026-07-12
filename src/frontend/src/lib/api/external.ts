import { requestJson } from "./legacyCore";

export async function getExternalSmokeStatus(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/external-smoke/status");
}

export async function runExternalSmoke(
  baseUrl: string,
  payload: {
    target?: string;
    mode?: string;
    config_path?: string;
    approved?: boolean;
    approved_by?: string;
    dpabi_function?: string;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/external-smoke/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// === SessionDB ===
