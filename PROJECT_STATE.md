# Project State

Current as of 2026-07-16.

## Version and Branch

- Current source/release line: `v0.6.0-rc1`.
- Release convergence target: `v0.6.0-rc2`. This is a stabilization release;
  `v0.7.0-rc1` is reserved for a separately approved capability or contract
  expansion.
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
  a default-blocked native conversion handoff inside the sole reviewed execution
  gateway.
- The in-project Python DICOM converter supports classic single-frame MR and
  Siemens single-frame mosaic MR. All three DemoData subjects were converted on
  Windows into six reloadable NIfTI/JSON pairs with the 1,104-file rawdata
  snapshot unchanged. The reviewed native handoff can reuse this verified
  conversion registry without rerunning conversion.
- Feature-flagged frontend execute UI for DICOM conversion; hidden by default.
- Reviewed rs-fMRI preprocessing workflow for converted inputs, including a
  unified stage catalog, artifact registry and lineage, Minimal FC backend
  chain, optional DPARSFA-like stage semantics, reviewed orchestrator endpoint,
  stage output registration, validation, report export, and a frontend
  reviewed flow that can create a preprocessing run from registered converted
  input, submit the reviewed gate, show stage status, and expose FC artifact
  metadata handoff links.
- Frontend API wrappers under `src/frontend/src/lib/api/` with a shared client.
- A server-issued Execution Ticket and single Execution Gateway bind reviewed
  plans, approvals, project identity, allowlists, paths, audit context, expiry,
  and retry policy before Pipeline Runtime dispatch.
- Runner dispatch enforces node, backend, input-root, output-root, rawdata,
  allowlist-fingerprint, and ticket constraints before invoking registered
  execution code.
- A persistent Agent lifecycle now separates execution status, observations,
  goal evaluation, recovery proposals, approvals, attempts, and human handoff.
- Observation, deterministic Goal Evaluation, side-effect-free recovery
  proposals, and controlled retry/resume/local-replan services are implemented
  and covered by source-level regression tests.

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
- During the `v0.6.0-rc2` convergence window, `main` is frozen for new execution
  paths, scientific algorithms, capability-level upgrades, public API expansion,
  and dependency expansion. Only release-blocking fixes, tests, evidence, and
  documentation corrections may enter without reopening capability review.

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
- The current RC2 working tree was validated on Windows with Python 3.11.15:
  backend `4108 passed, 16 skipped`; frontend format check, typecheck, `238`
  tests, and production build passed. The only backend skip caused by Windows
  privilege rather than an intentionally disabled optional/external path was
  the symlink-escape case.
- Exact source candidate `1d93922c302dfbd8557ad3495594e9cc5b37d479`
  completed GitHub Actions run `29464470010` successfully. Its `backend`,
  `frontend`, and `desktop` jobs all passed. This closes the remote-CI evidence
  gate for that source candidate; later runtime-affecting commits require new
  CI and packaging evidence.
- Current task-level validation is recorded in the final Completion Report and
  the local phase execution record rather than appended here as a development
  diary.
- Native DICOM validation includes synthetic geometry/affine/error tests,
  guarded approval/audit/artifact/provenance execution tests, and an opt-in
  three-subject DemoData conversion test that prohibits subprocess execution.
- A source-level reviewed gateway E2E converted all three DemoData subjects and
  produced 21 native-space preprocessing NIfTI artifacts, including ALFF and
  fALFF maps. A second reviewed run reused the verified conversion registry,
  required the GPU scheduler, executed with CuPy, and recorded a non-zero
  55.23-second pipeline duration. These results are not packaged-GUI evidence.

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
- Source candidate `1d93922c302dfbd8557ad3495594e9cc5b37d479` was rebuilt
  with the `mamba` Python 3.11.15 environment into a PyInstaller backend
  sidecar, launcher, and Electron unpacked directory. Packaged smoke confirmed
  backend readiness, a mounted React renderer, no renderer console errors, and
  sidecar cleanup after application exit. The directory build is exact-SHA
  evidence; an NSIS installer and packaged real-data workflow are still pending.

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
- Full DICOM-to-preprocessing-to-report packaged GUI E2E remains unproven;
  the corresponding source-level reviewed gateway path is now demonstrated.
  Preview/subset runs and synthetic-atlas FC remain labeled `preview_only` or
  `partial`.
- The controlled recovery implementation is source-tested, but packaged-app
  exit, forced termination, restart recovery, failed-subject isolation, and
  local retry have not yet been demonstrated on the three-subject DemoData set.

## Next Work

1. Run the real three-subject DemoData workflow through the exact-candidate
   packaged application, including conversion, reviewed preprocessing,
   artifact reload, validation, and report handoff.
2. Validate running-state graceful exit, forced termination, restart recovery,
   failed-subject isolation, and approved local retry without modifying rawdata.
3. Build the NSIS release artifact when required packaging caches are available,
   then repeat the exact-candidate launch smoke for that artifact.
4. Align version surfaces and release documentation, inventory/checksum the
   Windows artifacts, and publish `v0.6.0-rc2` only after all release gates pass.

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
- RC2 release convergence: `specs/阶段记录/阶段九/README.md`
