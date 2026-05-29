const { contextBridge, ipcRenderer } = require("electron");

const host = process.env.MEDIMAGE_BACKEND_HOST || "127.0.0.1";
const port = process.env.MEDIMAGE_BACKEND_PORT || "8000";
const apiBaseUrl = process.env.MEDIMAGE_DESKTOP_API_BASE_URL || `http://${host}:${port}`;
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
  },
};

contextBridge.exposeInMainWorld("MEDIMAGE_API_BASE_URL", apiBaseUrl);
contextBridge.exposeInMainWorld("MEDIMAGE_DESKTOP_RUNTIME", runtime);
contextBridge.exposeInMainWorld("medimageDesktop", { runtime });
contextBridge.exposeInMainWorld("medimage", {
  getApiBaseUrl: () => ipcRenderer.invoke("medimage:get-api-base-url"),
  selectDirectory: () => ipcRenderer.invoke("medimage:select-directory"),
  selectFile: (filters) => ipcRenderer.invoke("medimage:select-file", filters),
  openExternalPath: (targetPath) => ipcRenderer.invoke("medimage:open-external-path", targetPath),
});
