import { getJson, postJson } from "./client";

export function getDesktopConfig(baseUrl: string): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/desktop/config", { baseUrl });
}

export function getDesktopHealth(baseUrl: string): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/desktop/health", { baseUrl });
}

export function saveDesktopConfig(
  baseUrl: string,
  payload: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>("/api/desktop/config", payload, { baseUrl });
}
