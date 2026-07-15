# Project State

Current as of 2026-07-15.

## Version and Branch

- Current source/release line: `v0.6.0-rc1`.
- Backend `APP_VERSION` (`src/backend/app/version.py`) is `0.6.0-rc1`.
  All package surface versions (frontend, desktop/electron, pyproject.toml)
  aligned to `0.6.0-rc1` as of 2026-06-20 architecture audit.
- Current working branch: `main`.
- Local Git tags present:
  - `v0.3.0-rc1` tagged 2026-06-06
  - `v0.4.0-rc1` tagged 2026-06-10
  - `v0.5.0-rc1` tagged 2026-06-11

Historical release notes live under `docs/发布记录/` and should remain tied to
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
- The in-project Python DICOM converter supports classic single-frame MR and
  Siemens single-frame mosaic MR. One DemoData subject (240 functional mosaic
  instances and 128 structural slices) was converted and reload-checked on
  Windows with exact pre/post rawdata hashes, sizes, and mtimes unchanged.
- Feature-flagged frontend execute UI for DICOM conversion; hidden by default.
- Reviewed rs-fMRI preprocessing workflow for converted inputs, including a
  unified stage catalog, artifact registry and lineage, Minimal FC backend
  chain, optional DPARSFA-like stage semantics, reviewed orchestrator endpoint,
  stage output registration, validation, report export, and a frontend
  reviewed flow that can create a preprocessing run from registered converted
  input, submit the reviewed gate, show stage status, and expose FC artifact
  metadata handoff links.
- Frontend API wrappers under `src/frontend/src/lib/api/` with a shared client.

## Current Execution Boundaries

- Rawdata is read-only.
- The Pipeline Runtime remains the only pipeline execution path.
- LLM output is advisory only.
- DICOM conversion execution is not automatic. It requires explicit environment
  flags, release approval/readiness evidence, confirmation payloads, audit
  package evidence, checksum/rollback checks, and safe output roots.
- Reviewed preprocessing uses in-project Python kernels. MATLAB, SPM, and
  DPABI executables are outside the supported execution path.
- Reviewed Minimal FC can continue from already registered realignment outputs;
  this is a resume/registration path. It is not a one-click local SPM
  realignment execution claim while MATLAB/SPM gates remain unsatisfied.
- Full DICOM-to-reviewed-FC GUI E2E on real multi-subject data, true
  multi-subject workflow validation, group statistics, classification,
  clinical diagnosis, report editing, and auto-update are not current capabilities.

## Validation Baseline

- Required backend interpreter: use the Python interpreter from the active
  project environment (e.g. `.venv/Scripts/python.exe` on Windows). The
  maintainer's local validation environment is recorded in release-specific
  validation evidence, not as a repository requirement. Do NOT hardcode
  maintainer-local interpreter paths in stable documentation.

- Use `--basetemp=.pytest_tmp` when Windows temp directories contain locked
  pytest temp entries.
- Expected optional skips commonly include missing `pydicom`, missing `cupy`,
  and missing `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.
- The latest committed source-level frontend refactor fix
  (`904c3ec`, 2026-06-13) recorded `109 passed, 4 skipped`.
- Current task-level validation is recorded in the final Completion Report and
  the local phase execution record rather than appended here as a development
  diary.
- Native DICOM validation includes synthetic geometry/affine/error tests,
  guarded approval/audit/artifact/provenance execution tests, and an opt-in
  one-subject DemoData reload comparison.

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

- Per-stage real capability is recorded in `docs/项目概览/能力矩阵.md`.
  ALFF/fALFF/ReHo/FC are **Numerically Implemented** on the Python backend
  where their required inputs exist; atlas-grounded FC requires a registered
  safe atlas artifact or a controlled repository-template copy into
  derivatives, and numeric metric maps plus atlas artifacts are reload-checked
  by pipeline validation. The full DICOM-to-reviewed-FC GUI workflow is not
  yet E2E validated. Compatibility labels derived from SPM/DPABI conventions
  do not imply those external products are executed.
- Scientific-computation sandbox services previously reported `succeeded` for
  both "sandbox prepared" and "numeric result produced". Per-metric status
  now distinguishes these; older manifests are read with backward-compatible
  fallback.
- `dashboard_routes.py` remains a large legacy aggregation/conversion workflow
  router. New unrelated domain endpoints should be split into domain routers.
- Some historical docs still describe earlier route and frontend API layouts;
  long-term docs should point to the current domain-router and `lib/api/`
  structure.
- Desktop GUI validation requires a local interactive Windows desktop.
- Default Windows temp folders can retain locked pytest directories; use the
  active project interpreter and `--basetemp=.pytest_tmp`.
- The desktop SQLite state store is ignored runtime state and can accumulate
  stale local paths.
- Full DICOM-to-preprocessing-to-report GUI E2E remains unproven.
  Preview/subset runs and synthetic-atlas FC remain labeled `preview_only` or
  `partial`.

## Next Work

1. Keep public DICOM conversion execution default-blocked unless a maintainer
   explicitly approves a release enablement path.
2. Validate the reviewed preprocessing UI against a real project with a
   prepared preprocessing run, real atlas artifact, and recorded backend
   report/validation outputs.
3. Continue splitting large legacy route and frontend modules only through
   focused, tested changes.
4. Validate desktop packaging and GUI smoke in an interactive Windows session.
5. Keep documentation lifecycle clean: completed task handoffs and temporary
   reports should not become long-term state.

## Reference Documents

- Stable agent rules: `AGENTS.md`
- Per-stage real capability: `docs/项目概览/能力矩阵.md`
- Reviewed preprocessing user guide: `docs/用户指南/完整预处理流程.md`
- Reviewed preprocessing developer contract:
  `docs/预处理与科学计算/原生预处理/预处理流水线契约.md`
- Current architecture: `docs/架构与决策/系统架构.md`
- Desktop packaging: `docs/桌面与前端/桌面应用打包.md`
- Release notes: `docs/发布记录/`
- Safety boundaries: `docs/安全与审批/安全边界.md`
- Run lifecycle: `docs/安全与审批/真实项目运行生命周期.md`
