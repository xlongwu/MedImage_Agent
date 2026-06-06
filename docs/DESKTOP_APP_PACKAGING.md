# Desktop App Packaging

MedImage Agent can be packaged as a Windows desktop app with an Electron shell,
a static React frontend, and a PyInstaller FastAPI backend sidecar.

## Architecture

The desktop app is a local wrapper around the existing web architecture:

1. Electron main process starts the backend sidecar.
2. The sidecar runs `src.backend.app.main:app` through `desktop_backend_entry.py`.
3. Electron chooses an available `127.0.0.1` port starting at `8765`.
4. Electron waits for `GET /api/health`.
5. Electron exposes the runtime backend URL through `preload.cjs`.
6. The renderer loads the static React build from `src/frontend/dist`.
7. When the Electron app exits, the managed backend sidecar is stopped.

This keeps the existing FastAPI and React layers intact. The frontend still uses
HTTP APIs; it does not access the file system directly.

For Electron releases, the PyInstaller sidecar is stored as
`medimage-backend.bin` under Electron resources and copied into the app
`userData` directory as `medimage-backend.exe` before launch. This avoids
fragile portable-exe behavior where nested executables can be blocked while
NSIS self-extracts into `%TEMP%`.

## Why Electron + PyInstaller

Electron fits the current React + Vite frontend with the smallest migration
cost. PyInstaller provides a Windows executable for the FastAPI sidecar, so
users do not need to run `uvicorn`, install Node.js, or start `npm run dev`.

Tauri remains a possible future option, but it would add a Rust toolchain and a
larger migration surface. The current packaging milestone prioritizes a
low-risk Windows path for the existing code.

## Development Run

Build the frontend once, then run the desktop shell:

```powershell
npm --prefix src/frontend run build
python -m src.backend.app.desktop_backend_entry --host 127.0.0.1 --port 8765
npm --prefix desktop/electron run dev
```

The Electron shell can also start the Python backend itself in development mode
when the PyInstaller sidecar is not present.

## Windows Packaging

Run the all-in-one packaging script from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_all_windows.ps1
```

Useful variants:

```powershell
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_all_windows.ps1 -SkipFullPytest
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_backend.ps1
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_frontend.ps1
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_desktop.ps1
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_desktop.ps1 -DirOnly
```

If the build machine cannot download the Electron runtime directly, download the
matching Electron zip separately and pass it to the desktop build:

```powershell
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_desktop.ps1 `
  -ElectronRuntimeZip D:\downloads\electron-v31.7.7-win32-x64.zip
```

The all-in-one script accepts the same parameter. The wrapper copies the zip
into `desktop/electron/.electron-cache/manual-runtime` and points
electron-builder at that local cache without hard-coding a private download path
in the repository.

If the NSIS helper cannot be downloaded directly, pass the matching archive too:

```powershell
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_desktop.ps1 `
  -ElectronRuntimeZip D:\downloads\electron-v31.7.7-win32-x64.zip `
  -NsisArchive D:\downloads\nsis-3.0.4.1.7z `
  -NsisResourcesArchive D:\downloads\nsis-resources-3.4.1.7z
```

The wrapper extracts it into
`desktop/electron/.electron-builder-cache/manual-nsis/nsis-3.0.4.1` and sets
`ELECTRON_BUILDER_NSIS_DIR` for electron-builder. If
`-NsisResourcesArchive` is provided, the wrapper serves that archive through a
temporary `127.0.0.1` URL so electron-builder can use its normal
`download-artifact` path without external network access.

The Windows build is unsigned and sets `signAndEditExecutable: false` so
electron-builder does not download the `winCodeSign` helper in locked-down
environments.

`-DirOnly` builds the unpacked Electron app at
`desktop/electron/dist/win-unpacked/MedImage Agent.exe` without invoking NSIS.
Use it when NSIS cannot be downloaded but the desktop app executable itself
still needs to be verified.

## Output Files

Expected build outputs:

- Backend sidecar: `desktop/packaging/dist/backend/medimage-backend.exe`
- Backend sidecar payload for Electron: `desktop/packaging/dist/backend_payload/medimage-backend.bin`
- Windows installer: `desktop/electron/dist/MedImage Agent Setup.exe`
- Portable app: `desktop/electron/dist/MedImage Agent.exe`
- Unpacked Electron app: `desktop/electron/dist/win-unpacked/MedImage Agent.exe`
- PyInstaller launcher fallback: `desktop/packaging/dist/launcher/MedImage Agent.exe`

Exact filenames can vary slightly by electron-builder version, but artifacts
are written under `desktop/electron/dist`.

The launcher fallback is provided for constrained environments where the
Electron runtime cannot be downloaded. It still uses the same FastAPI backend
and static React build, binds only to `127.0.0.1`, opens the local UI in the
user's browser, and stops the backend when the launcher window exits. It is not
a replacement for the Electron release target. By default it creates a
workspace under `%LOCALAPPDATA%\MedImage Agent\workspace`; locked-down
environments can set `MEDIMAGE_DESKTOP_WORKSPACE` to a writable directory.

## Runtime Configuration

The renderer reads the backend base URL at runtime from Electron preload:

```ts
window.__MEDIMAGE_DESKTOP_CONFIG__ = {
  backendBaseUrl: "http://127.0.0.1:<dynamic_port>"
}
```

The preload also exposes `window.MEDIMAGE_API_BASE_URL`,
`window.MEDIMAGE_DESKTOP_RUNTIME`, and `window.medimage.getApiBaseUrl()`.
Development web mode can still use `VITE_API_BASE_URL` or the default
`http://127.0.0.1:8000`.

## Troubleshooting

- Missing frontend UI: run `npm --prefix src/frontend run build`.
- Missing backend sidecar: run `desktop/packaging/build_backend.ps1`.
- Backend health timeout: inspect the log path shown on the startup error page.
- Port occupied: Electron tries the next localhost port automatically.
- Electron build fails on missing resources: run backend and frontend build
  scripts before `build_desktop.ps1`.
- Electron install fails with `FetchError` or `EACCES`: allow npm registry
  access and rerun `npm install` from `desktop/electron`, then rerun
  `desktop/packaging/build_desktop.ps1`.
- Electron runtime download fails with a GitHub socket permission error: allow
  access to `https://github.com/electron/electron/releases/download/...`, or
  pass `-ElectronRuntimeZip` with a manually downloaded
  `electron-v31.7.7-win32-x64.zip`. The build wrapper stores Electron downloads
  in `desktop/electron/.electron-cache` and electron-builder downloads in
  `desktop/electron/.electron-builder-cache`.
- NSIS download fails with a GitHub socket permission error: run
  `build_desktop.ps1 -DirOnly` to build and test the unpacked Electron app, or
  pass `-NsisArchive` with `nsis-3.0.4.1.7z` plus
  `-NsisResourcesArchive` with `nsis-resources-3.4.1.7z` to produce installer
  and portable artifacts offline.

## Verified Build Environment (2026-06-18)

The following environment has been validated for packaging:

- Node v24.16.0 / npm 11.13.0
- Python: `D:\Anaconda3\envs\mamba\python.exe` (3.11.15)
- PyInstaller 6.20.0
- Electron 31.7.7 (offline cached at `desktop/electron/.electron-cache/manual-runtime/`)
- NSIS 3.0.4.1 (offline cached at `desktop/electron/.electron-builder-cache/manual-nsis/`)

All build stages have passed independently:

| Stage | Result |
|---|---|
| Frontend Vite production build | ✅ `npm --prefix src/frontend run build` |
| Backend PyInstaller sidecar | ✅ `build_backend.ps1 -PythonExe ...` |
| Launcher PyInstaller fallback | ✅ `build_launcher.ps1 -PythonExe ...` |
| Electron unpacked (dir-only) | ✅ `build_desktop.ps1 -DirOnly -ElectronRuntimeZip ...` |
| Electron smoke check | ✅ 51/51 checks passed |

## Recommended Full Build Command

From the repository root, with no network access and a pre-configured mamba
Python environment:

```powershell
powershell -ExecutionPolicy Bypass -File desktop/packaging/build_all_windows.ps1 `
  -SkipFullPytest `
  -SkipDependencyInstall `
  -SkipNpmInstall `
  -DirOnly `
  -PythonExe "D:\Anaconda3\envs\mamba\python.exe" `
  -ElectronRuntimeZip "desktop\electron\.electron-cache\manual-runtime\electron-v31.7.7-win32-x64.zip"
```

Remove `-DirOnly` to produce NSIS installer and portable exe artifacts. Add
`-NsisArchive` and `-NsisResourcesArchive` when those helpers are available
offline.

GUI startup verification must be performed on a local Windows desktop
environment; the Electron smoke check (51/51) validates configuration
correctness but does not exercise the full GUI launch.

## Safety Boundary

The desktop app is only a local packaging wrapper around the existing frontend
and backend. It does not enable new execution capability.

- It does not enable real GUI automation.
- It does not enable PyWinAuto.
- It does not connect a real model.
- It does not call inference.
- It does not load model weights.
- It does not change the reviewed execution allowlist.
- It does not add GUI/manual reviewed execution nodes.
- It does not open Tier 1, Tier 2, or Tier 3 GUI actions.
- It preserves the mock-only, `record_observation`-only GUI Agent boundary.
- It preserves the existing guarded reviewed execution path.

Blocked capabilities remain blocked after packaging: real model, inference,
model weights, PyWinAuto, real GUI automation, screenshots, clipboard,
mouse/keyboard control, GUI/manual reviewed execution, and GUI actions beyond
`record_observation`.
