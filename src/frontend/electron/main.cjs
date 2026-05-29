const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const net = require("node:net");

const API_HOST = process.env.MEDIMAGE_BACKEND_HOST || "127.0.0.1";
const DEFAULT_API_PORT = Number(process.env.MEDIMAGE_BACKEND_PORT || "8000");
const REPO_ROOT = path.resolve(__dirname, "../../..");
const BACKEND_LOG_DIR = path.join(REPO_ROOT, "outputs", "work", "desktop");
const BACKEND_LOG_PATH = path.join(BACKEND_LOG_DIR, "electron-backend.log");

let backendProcess = null;
let backendState = {
  apiBaseUrl: `http://${API_HOST}:${DEFAULT_API_PORT}`,
  managed: false,
  ready: false,
  status: "pending",
  pid: null,
  logPath: BACKEND_LOG_PATH,
  error: null,
};

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function appendBackendLog(channel, chunk) {
  try {
    fs.mkdirSync(BACKEND_LOG_DIR, { recursive: true });
    fs.appendFileSync(
      BACKEND_LOG_PATH,
      `[${new Date().toISOString()}] ${channel}: ${chunk.toString()}`,
      "utf8"
    );
  } catch {
    // Logging must not stop the desktop app from opening.
  }
}

function syncRuntimeEnv() {
  process.env.MEDIMAGE_DESKTOP_API_BASE_URL = backendState.apiBaseUrl;
  process.env.MEDIMAGE_DESKTOP_BACKEND_MANAGED = String(backendState.managed);
  process.env.MEDIMAGE_DESKTOP_BACKEND_READY = String(backendState.ready);
  process.env.MEDIMAGE_DESKTOP_BACKEND_STATUS = backendState.status;
  process.env.MEDIMAGE_DESKTOP_BACKEND_LOG_PATH = backendState.logPath;
  process.env.MEDIMAGE_DESKTOP_BACKEND_PID = backendState.pid ? String(backendState.pid) : "";
}

function requestHealth(apiBaseUrl = backendState.apiBaseUrl, timeoutMs = 500) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (result) => {
      if (!done) {
        done = true;
        resolve(result);
      }
    };
    const req = http.get(`${apiBaseUrl}/api/health`, (res) => {
      res.resume();
      finish({
        ok: res.statusCode >= 200 && res.statusCode < 300,
        statusCode: res.statusCode,
      });
    });
    req.on("error", (error) => finish({ ok: false, error: error.message }));
    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error("timeout"));
    });
  });
}

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, API_HOST);
  });
}

async function findBackendTarget(startPort = DEFAULT_API_PORT) {
  for (let offset = 0; offset < 30; offset += 1) {
    const port = startPort + offset;
    const apiBaseUrl = `http://${API_HOST}:${port}`;
    const existing = await requestHealth(apiBaseUrl);
    if (existing.ok) {
      return { port, apiBaseUrl, existing: true };
    }
    if (await isPortFree(port)) {
      return { port, apiBaseUrl, existing: false };
    }
  }
  throw new Error(`No available backend port from ${startPort} to ${startPort + 29}`);
}

async function waitForBackend(apiBaseUrl = backendState.apiBaseUrl, attempts = 50) {
  for (let index = 0; index < attempts; index += 1) {
    const result = await requestHealth(apiBaseUrl);
    if (result.ok) {
      return true;
    }
    await delay(500);
  }
  return false;
}

async function startBackend() {
  if (process.env.MEDIMAGE_DESKTOP_SKIP_BACKEND === "true") {
    backendState = { ...backendState, managed: false, ready: false, status: "skipped" };
    syncRuntimeEnv();
    return;
  }

  const target = await findBackendTarget();
  backendState = { ...backendState, apiBaseUrl: target.apiBaseUrl };
  if (target.existing) {
    backendState = { ...backendState, managed: false, ready: true, status: "existing" };
    syncRuntimeEnv();
    return;
  }

  const python = process.env.MEDIMAGE_PYTHON || "python";
  appendBackendLog("desktop", `starting backend with ${python} at ${target.apiBaseUrl}\n`);
  backendProcess = spawn(
    python,
    ["-m", "uvicorn", "src.backend.app.main:app", "--host", API_HOST, "--port", String(target.port)],
    {
      cwd: REPO_ROOT,
      env: {
        ...process.env,
        MEDIMAGE_DESKTOP: "true",
        MEDIMAGE_BACKEND_HOST: API_HOST,
        MEDIMAGE_BACKEND_PORT: String(target.port),
      },
      stdio: "pipe",
      windowsHide: true,
    }
  );
  backendState = {
    ...backendState,
    managed: true,
    ready: false,
    status: "starting",
    pid: backendProcess.pid || null,
    error: null,
  };
  backendProcess.stdout.on("data", (chunk) => appendBackendLog("stdout", chunk));
  backendProcess.stderr.on("data", (chunk) => appendBackendLog("stderr", chunk));
  backendProcess.on("error", (error) => {
    backendState = { ...backendState, status: "error", error: error.message };
    syncRuntimeEnv();
    appendBackendLog("error", `${error.message}\n`);
  });
  backendProcess.on("exit", (code, signal) => {
    backendState = {
      ...backendState,
      ready: false,
      status: "stopped",
      pid: null,
      error: code === 0 ? null : `backend exited code=${code} signal=${signal}`,
    };
    syncRuntimeEnv();
    appendBackendLog("exit", `code=${code} signal=${signal}\n`);
  });
  syncRuntimeEnv();
}

function stopBackend() {
  if (backendProcess && backendState.managed) {
    backendProcess.kill();
    backendProcess = null;
  }
}

function registerIpcHandlers() {
  ipcMain.handle("medimage:get-api-base-url", () => backendState.apiBaseUrl);
  ipcMain.handle("medimage:select-directory", async (event) => {
    const result = await dialog.showOpenDialog(BrowserWindow.fromWebContents(event.sender), {
      properties: ["openDirectory"],
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });
  ipcMain.handle("medimage:select-file", async (event, filters) => {
    const result = await dialog.showOpenDialog(BrowserWindow.fromWebContents(event.sender), {
      properties: ["openFile"],
      filters: Array.isArray(filters) ? filters : undefined,
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });
  ipcMain.handle("medimage:open-external-path", async (_event, targetPath) => {
    if (typeof targetPath !== "string" || !targetPath.trim()) {
      return false;
    }
    const result = await shell.openPath(targetPath);
    return result === "";
  });
}

async function createWindow() {
  await startBackend();
  const ready = backendState.ready || (backendState.managed ? await waitForBackend(backendState.apiBaseUrl) : false);
  backendState = {
    ...backendState,
    ready,
    status: ready ? (backendState.managed ? "started" : backendState.status) : backendState.status,
  };
  syncRuntimeEnv();

  const win = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1100,
    minHeight: 720,
    title: "MedImage Agent",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (!ready) {
    dialog.showMessageBox(win, {
      type: "warning",
      title: "Backend not ready",
      message: "The local FastAPI backend did not respond yet. The app will still open.",
      detail: `Expected backend at ${backendState.apiBaseUrl}`,
    });
  }

  if (process.env.MEDIMAGE_DESKTOP_DEV_URL) {
    await win.loadURL(process.env.MEDIMAGE_DESKTOP_DEV_URL);
  } else {
    await win.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(() => {
  registerIpcHandlers();
  createWindow();
});

app.on("before-quit", stopBackend);

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
