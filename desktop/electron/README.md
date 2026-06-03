# MedImage Agent Desktop Shell

This directory contains the Electron shell used for Windows desktop packaging.
It launches the FastAPI backend sidecar, waits for `/api/health`, injects the
runtime backend URL into the renderer through `preload.cjs`, and then loads the
static React build from `src/frontend/dist`.

Packaged builds include the backend sidecar as `resources/backend/medimage-backend.bin`.
The main process copies it into Electron `userData` as `medimage-backend.exe`
before launching it on a localhost port.

Development shortcut:

```powershell
npm --prefix desktop/electron install
npm --prefix src/frontend run build
python -m src.backend.app.desktop_backend_entry --host 127.0.0.1 --port 8765
npm --prefix desktop/electron run dev
```

Production packaging is driven by `desktop/packaging/build_all_windows.ps1`.
