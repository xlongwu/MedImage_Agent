export {};

declare global {
  interface Window {
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
      };
    };
    medimageDesktop?: {
      runtime: Window["MEDIMAGE_DESKTOP_RUNTIME"];
    };
    medimage?: {
      getApiBaseUrl: () => Promise<string>;
      selectDirectory: () => Promise<string | null>;
      selectFile: (filters?: Array<{ name: string; extensions: string[] }>) => Promise<string | null>;
      openExternalPath: (path: string) => Promise<boolean>;
    };
  }
}
