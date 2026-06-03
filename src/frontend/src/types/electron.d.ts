export {};

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
    medimage?: {
      getApiBaseUrl: () => Promise<string>;
      getRuntime?: () => Promise<Window["MEDIMAGE_DESKTOP_RUNTIME"]>;
      selectDirectory: () => Promise<string | null>;
      selectFile: (filters?: Array<{ name: string; extensions: string[] }>) => Promise<string | null>;
      openExternalPath: (path: string) => Promise<boolean>;
    };
  }
}
