# Project State

Current as of 2026-06-14.

## Version and Branch

- Current source/release line: `v0.5.0-rc1`.
- Backend `APP_VERSION` and frontend package version should use `0.5.0-rc1`.
- Current working branch: `main`.
- Local Git tags present:
  - `v0.3.0-rc1` tagged 2026-06-06
  - `v0.4.0-rc1` tagged 2026-06-10
  - `v0.5.0-rc1` tagged 2026-06-11

Historical release notes live under `docs/releases/` and should remain tied to
their tag state.

## Implemented Capabilities

- Deterministic Plan-then-Execute architecture.
- FastAPI backend with domain routers, structured errors, request IDs,
  structured logging, API v1 compatibility rewrite, rate limiting, and CORS.
- `ConfigService` backed configuration and legacy `get_backend_settings()`.
- Project store dependency protocol for read-side routes.
- Atomic runtime state JSON writes with `_schema_version`.
- Plugin-based node registry with duplicate-ID checks and compatibility shim.
- Tool Catalog and Approval Gate for file-writing or execution actions.
- Real-project creation from BIDS/rawdata directories, project config and
  dataset index generation, reviewed plan persistence, run links, run history,
  run summaries, and artifact previews.
- DICOM/FunRaw/T1Raw detection, DICOM conversion dry-run, conversion review
  packages, release readiness, release approval metadata, rollback support, and
  a public conversion endpoint that is default-blocked by environment flags and
  approval/readiness gates.
- Feature-flagged frontend execute UI for DICOM conversion; hidden by default.
- Phase 5 preprocessing workflow for converted inputs, including dry-run plans,
  sandbox workspaces, stage output registration, validation, and report export.
- Frontend API wrappers under `src/frontend/src/lib/api/` with a shared client.

## Current Execution Boundaries

- Rawdata is read-only.
- The Pipeline Runtime remains the only pipeline execution path.
- LLM output is advisory only.
- DICOM conversion execution is not automatic. It requires explicit environment
  flags, release approval/readiness evidence, confirmation payloads, audit
  package evidence, checksum/rollback checks, and safe output roots.
- SPM/MATLAB sandbox preprocessing requires explicit opt-in flags and local
  tool availability.
- DPABI remains disabled by default.
- Full-brain FC, group statistics, classification, clinical diagnosis, report
  editing, and auto-update are not current capabilities.

## Validation Baseline

- Required backend interpreter:

```powershell
D:\Anaconda3\envs\mamba\python.exe
```

- Use `--basetemp=.pytest_tmp` when Windows temp directories contain locked
  pytest temp entries.
- Expected optional skips commonly include missing `pydicom`, missing `cupy`,
  and missing `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.
- The latest committed source-level frontend refactor fix
  (`904c3ec`, 2026-06-13) recorded `109 passed, 4 skipped`.
- Current cleanup validation is recorded in the final Completion Report rather
  than appended here as a development diary.

## Packaging State

- Windows desktop packaging uses Electron plus a PyInstaller backend sidecar.
- Current local test EXE location to preserve:
  `desktop/electron/dist/win-unpacked/MedImage Agent.exe`.
- Offline Electron runtime and NSIS caches under `desktop/electron/` are local
  build resources and must not be deleted during cleanup.
- `desktop/packaging/build_all_windows.ps1` is the main Windows packaging
  entry point.
- Packaging output directories are generated artifacts unless explicitly
  promoted through a release artifact process.

## Known Limitations and Risks

- `dashboard_routes.py` remains a large legacy aggregation/conversion workflow
  router. New unrelated domain endpoints should be split into domain routers.
- Some historical docs still describe earlier route and frontend API layouts;
  long-term docs should point to the current domain-router and `lib/api/`
  structure.
- Desktop GUI validation requires a local interactive Windows desktop.
- Default Windows temp folders can retain locked pytest directories; use the
  mamba interpreter and `--basetemp=.pytest_tmp`.
- The desktop SQLite state store is ignored runtime state and can accumulate
  stale local paths.

## Next Work

1. Keep public DICOM conversion execution default-blocked unless a maintainer
   explicitly approves a release enablement path.
2. Continue splitting large legacy route and frontend modules only through
   focused, tested changes.
3. Validate desktop packaging and GUI smoke in an interactive Windows session.
4. Keep documentation lifecycle clean: completed task handoffs and temporary
   reports should not become long-term state.

## Reference Documents

- Stable agent rules: `AGENTS.md`
- Current architecture: `docs/architecture.md`
- Desktop packaging: `docs/DESKTOP_APP_PACKAGING.md`
- Release notes: `docs/releases/`
- Safety boundaries: `docs/SAFETY_BOUNDARIES.md`
- Run lifecycle: `docs/REAL_PROJECT_RUN_LIFECYCLE.md`
