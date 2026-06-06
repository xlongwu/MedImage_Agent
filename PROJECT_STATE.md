# Project State

## Current milestone

Desktop real-project execution and run artifact inspection loop completed.
Current focus is MVP release hardening: validation, delivery-state cleanup,
documentation sync, and smoke-check repeatability. No new features are in
scope for this phase.

## Completed capabilities

- Create project from real BIDS/rawdata directory.
- Generate `project_config.yaml`.
- Generate `dataset_index.json`.
- Persist project to dashboard SQLite store.
- Inject real project context into Plan Review.
- Validate reviewed execute context before execution.
- Persist reviewed plans.
- Persist run links.
- Generate unique run IDs.
- Run history UI.
- Run summary preview.
- Run-scoped artifact API.
- CSV / JSON / Markdown / text / log preview.
- Key Artifacts grouping and filtering.
- QC / Error Summary card.
- `ProjectRunsPanel.tsx` split from run-history model helpers.
- `project_history_routes.py` split to route wiring backed by run summary,
  artifact discovery, and artifact preview services.
- Safe real-project smoke test passed.

## Test baseline

- Recommended backend interpreter: `D:\Anaconda3\envs\mamba\python.exe`.
- Default `D:\Anaconda3\python.exe` is not the validation baseline because it
  lacks FastAPI in this workspace.
- Current local full backend validation on 2026-06-18:
  `D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short --basetemp=.pytest_tmp` ->
  `2426 passed, 8 skipped, 0 failed`.
- Expected skip reasons:
  - Missing optional `pydicom`.
  - Missing optional `cupy`.
  - Missing `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.

## Python test environment

Use:

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short
```

If the default Windows temp directory causes `PermissionError`, redirect
pytest temp with `--basetemp`:

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short --basetemp=.pytest_tmp
```

## Explicit non-goals

- No MATLAB/SPM/DPABI/GPU real execution.
- No NIfTI viewer.
- No complete QC dashboard.
- No report editor.
- No clinical validation.
- No Advanced Agent Controls project-context integration yet.
- No external user BIDS smoke unless `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR` is provided.

## Open delivery risks

- `contract_smoke` internal validation scope has been resolved: committed as
  `fa8aada` ("test: add node contract smoke validation"). It is documented as a
  non-user-visible internal validation node in
  `docs/MVP_RELEASE_SMOKE_CHECKLIST.md`.
- Windows default temp directory (`C:\Users\...\AppData\Local\Temp`) may contain
  stale permission-locked `pytest-of-*` entries from prior sessions. When full
  pytest fails with `PermissionError` on temp, use `--basetemp=.pytest_tmp`.
  `.pytest_tmp/` is now in `.gitignore`.
- The desktop SQLite store (`outputs/work/desktop/desktop_state.sqlite`)
  accumulates stale import records referencing temp directories. When the store
  contains paths to locked temp dirs, `list_image_sources()` will fail with
  `PermissionError`. The fix is to delete the store (gitignored; regenerated on
  next test run): `del outputs\work\desktop\desktop_state.sqlite`.

## Desktop packaging status (2026-06-18)

- Node v24.16.0 / npm 11.13.0 verified for Vite production build.
- PyInstaller 6.20.0 installed in mamba environment.
- Backend sidecar (`medimage-backend.exe`, 38.9 MB) built and verified.
- Launcher fallback (`MedImage Agent.exe`, 49.2 MB) built and verified.
- Electron unpacked app (`win-unpacked/MedImage Agent.exe`, 180 MB) built
  with offline Electron runtime and NSIS caches.
- Electron smoke check: 51/51 passed.
- `build_all_windows.ps1` supports `-PythonExe` for mamba path forwarding.
- GUI startup verification pending (requires local Windows desktop).
- NSIS installer / portable full build is next stage.
- See `docs/DESKTOP_APP_PACKAGING.md` for verified build command.

## Next recommended work

1. Verify Electron GUI startup on a local Windows desktop.
2. Run full NSIS + portable build with `-NsisArchive` and `-NsisResourcesArchive`.
3. Keep release validation repeatable with the mamba interpreter.
4. Run external BIDS smoke only when the user provides a deliberately bounded
   read-only `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.
5. Consider a future `project_create_service` only if project creation routes
   grow again.
6. Consider a future execution orchestration service only if
   `execute_reviewed_routes.py` needs more separation after MVP release.
