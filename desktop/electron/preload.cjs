const { contextBridge, ipcRenderer } = require("electron");

const apiBaseUrl =
  process.env.MEDIMAGE_DESKTOP_API_BASE_URL ||
  process.env.MEDIMAGE_API_BASE_URL ||
  "http://127.0.0.1:8765";

const runtime = {
  apiBaseUrl,
  platform: process.platform,
  backend: {
    managed: process.env.MEDIMAGE_DESKTOP_BACKEND_MANAGED === "true",
    ready: process.env.MEDIMAGE_DESKTOP_BACKEND_READY === "true",
    status: process.env.MEDIMAGE_DESKTOP_BACKEND_STATUS || "unknown",
    pid: process.env.MEDIMAGE_DESKTOP_BACKEND_PID
      ? Number(process.env.MEDIMAGE_DESKTOP_BACKEND_PID)
      : null,
    logPath: process.env.MEDIMAGE_DESKTOP_BACKEND_LOG_PATH || "",
    executablePath: process.env.MEDIMAGE_DESKTOP_BACKEND_EXE || "",
    port: process.env.MEDIMAGE_DESKTOP_BACKEND_PORT
      ? Number(process.env.MEDIMAGE_DESKTOP_BACKEND_PORT)
      : null,
  },
};

contextBridge.exposeInMainWorld("MEDIMAGE_API_BASE_URL", apiBaseUrl);
contextBridge.exposeInMainWorld("__MEDIMAGE_DESKTOP_CONFIG__", {
  backendBaseUrl: apiBaseUrl,
});
contextBridge.exposeInMainWorld("MEDIMAGE_DESKTOP_RUNTIME", runtime);
contextBridge.exposeInMainWorld("medimageDesktop", {
  runtime,
  getBackendBaseUrl: () => ipcRenderer.invoke("medimage:get-api-base-url"),
  getRuntime: () => ipcRenderer.invoke("medimage:get-runtime"),
});
contextBridge.exposeInMainWorld("medimage", {
  getApiBaseUrl: () => ipcRenderer.invoke("medimage:get-api-base-url"),
  getAgentApprovalToken: () => ipcRenderer.invoke("medimage:get-agent-approval-token"),
  getRuntime: () => ipcRenderer.invoke("medimage:get-runtime"),
  selectDirectory: () => ipcRenderer.invoke("medimage:select-directory"),
  selectFile: (filters) => ipcRenderer.invoke("medimage:select-file", filters),
  openExternalPath: (targetPath) => ipcRenderer.invoke("medimage:open-external-path", targetPath),
});
