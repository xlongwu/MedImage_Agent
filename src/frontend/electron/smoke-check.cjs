const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const checks = [];

function check(name, ok, detail = "") {
  checks.push({ name, ok, detail });
}

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

const packageJson = JSON.parse(read("package.json"));
const mainPath = path.join(root, packageJson.main || "");
const preloadPath = path.join(root, "electron", "preload.cjs");
const distIndex = path.join(root, "dist", "index.html");
const importDiagnosticsPath = path.join(root, "src", "components", "ImportDiagnosticsPanel.tsx");

check("package main points to Electron entry", packageJson.main === "electron/main.cjs", packageJson.main || "");
check("Electron main exists", fs.existsSync(mainPath), mainPath);
check("Electron preload exists", fs.existsSync(preloadPath), preloadPath);
check("Vite dist index exists", fs.existsSync(distIndex), distIndex);
check("Import diagnostics panel exists", fs.existsSync(importDiagnosticsPath), importDiagnosticsPath);

if (fs.existsSync(mainPath)) {
  const main = fs.readFileSync(mainPath, "utf8");
  check("main starts FastAPI via uvicorn", main.includes("uvicorn") && main.includes("src.backend.app.main:app"));
  check("main probes existing backend before spawn", main.includes("findBackendTarget") && main.includes("status: \"existing\""));
  check("main finds available backend port", main.includes("findBackendTarget") && main.includes("net.createServer"));
  check("main checks API health", main.includes("/api/health"));
  check("main writes backend lifecycle log", main.includes("electron-backend.log") && main.includes("appendBackendLog"));
  check("main exports runtime env", main.includes("MEDIMAGE_DESKTOP_API_BASE_URL") && main.includes("MEDIMAGE_DESKTOP_BACKEND_READY"));
  check("main injects preload", main.includes("preload.cjs"));
  check("main stops backend on close", main.includes("backendProcess.kill()"));
  check("main registers safe IPC handlers", main.includes("medimage:select-directory") && main.includes("medimage:open-external-path"));
}

if (fs.existsSync(preloadPath)) {
  const preload = fs.readFileSync(preloadPath, "utf8");
  check("preload exposes runtime API base", preload.includes("MEDIMAGE_API_BASE_URL"));
  check("preload exposes desktop runtime", preload.includes("MEDIMAGE_DESKTOP_RUNTIME") && preload.includes("medimageDesktop"));
  check("preload exposes medimage bridge", preload.includes("contextBridge.exposeInMainWorld(\"medimage\"") && !preload.includes("exposeInMainWorld(\"ipcRenderer\""));
  check("preload exposes artifact opener", preload.includes("openExternalPath") && preload.includes("medimage:open-external-path"));
}

if (fs.existsSync(importDiagnosticsPath)) {
  const panel = fs.readFileSync(importDiagnosticsPath, "utf8");
  check("import diagnostics can open artifacts", panel.includes("openExternalPath") && panel.includes("Open report") && panel.includes("Open manifest"));
  check("import diagnostics can generate handoff package", panel.includes("createImportDiagnosticsPackage") && panel.includes("Generate handoff package"));
  check("import diagnostics can open handoff ZIP", panel.includes("zip_path") && panel.includes("Open ZIP") && panel.includes("Open folder"));
  check("import diagnostics loads latest handoff package", panel.includes("getLatestImportDiagnosticsPackage") && panel.includes("latestPackage"));
  check("import diagnostics exposes checksums", panel.includes("checksum_path") && panel.includes("Open checksums"));
  check("import diagnostics shows safety flags", panel.includes("safety_flags") && panel.includes("safetyFlags"));
  check("import diagnostics verifies handoff package", panel.includes("verifyImportDiagnosticsPackage") && panel.includes("Verify package"));
  check("import diagnostics exposes DICOM preflight", panel.includes("getDicomPreflight") && panel.includes("Run DICOM preflight"));
}

const ok = checks.every((item) => item.ok);
console.log(JSON.stringify({ ok, checks }, null, 2));
process.exit(ok ? 0 : 1);
