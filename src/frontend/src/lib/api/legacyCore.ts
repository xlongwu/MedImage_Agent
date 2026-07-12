import { requestJson as clientRequestJson } from "./client";
export { DEFAULT_API_BASE } from "./client";

declare global {
  interface Window {
    __MEDIMAGE_DESKTOP_CONFIG__?: {
      backendBaseUrl: string;
    };
    MEDIMAGE_API_BASE_URL?: string;
    MEDIMAGE_DESKTOP_RUNTIME?: {
      apiBaseUrl: string;
      platform: string;
      backend: {
        managed: boolean;
        ready: boolean;
        status: string;
        pid: number | null;
        logPath: string;
        executablePath?: string;
        port?: number | null;
      };
    };
    medimageDesktop?: {
      runtime: Window["MEDIMAGE_DESKTOP_RUNTIME"];
      getBackendBaseUrl?: () => Promise<string>;
      getRuntime?: () => Promise<Window["MEDIMAGE_DESKTOP_RUNTIME"]>;
    };
  }
}

export async function requestJson<T>(
  baseUrl: string,
  path: string,
  options?: RequestInit,
): Promise<T> {
  return clientRequestJson<T>(path, { ...options, baseUrl });
}
