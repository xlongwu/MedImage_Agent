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

## Run Retry / Resume Contract

A retry/resume contract has been designed and documented in
`docs/RUN_RETRY_RESUME_CONTRACT.md`. This document defines API contracts, state
semantics, safety rules, provenance requirements, and a test matrix for future
retry/resume support. **No retry or resume execution has been implemented.**
The contract is a design reference for a future implementation phase.

## SPM Realign Wrapper Safety Contract

An SPM realign wrapper safety contract has been designed and documented in
`docs/SPM_REALIGN_WRAPPER_SAFETY_CONTRACT.md`. It defines node identity,
preconditions, inputs/outputs, dry-run/execution contracts, approval gate
requirements, audit requirements, environment detection, path safety rules,
failure modes, provenance requirements, frontend UX contract, test matrix,
recommended implementation order, and completion criteria.
**No real MATLAB/SPM execution has been implemented.**
The contract is a design reference for a future implementation phase.

## SPM Realign Pre-execution Regression Matrix

A focused regression matrix has been added in
`tests/unit/test_spm_realign_preexecution_matrix.py`. It covers the full
non-executing SPM realign preparation chain with 9 tests: Tool Catalog metadata,
params validation, plan validation, environment health, dry-run manifest,
approval/audit gate, wrapper skeleton, and retry/resume not available.
**Real MATLAB/SPM execution remains not implemented.**
`spm_realign_subject` remains outside the safe execution allowlist.

## SPM Realign Real Execution Design Review

A formal design-review document has been created at
`docs/SPM_REALIGN_REAL_EXECUTION_DESIGN_REVIEW.md`. It evaluates readiness
for enabling real MATLAB/SPM execution, identifies gaps across 16 areas,
proposes execution architecture, defines safety gates, and recommends a
**NO-GO** decision for real execution in the current phase.  Immediate
next tasks are command-template unit tests, execution contract schema,
synthetic smoke design, and output/provenance schema alignment.

## QC Dashboard Performance and Cache Strategy

A performance and cache strategy has been designed in
`docs/QC_DASHBOARD_PERFORMANCE_CACHE_STRATEGY.md`. It defines cache key
design, invalidation rules, storage options (recommended: project-local JSON),
API contract, frontend UX contract, test strategy, and implementation order.
**Single-module cache prototype implemented for NIfTI QC Snapshot.**
Full dashboard caching is not yet implemented. Other modules still run normally.
Cache remains read-only with respect to rawdata.

## Phase 2 Feature Regression Matrix

A focused Phase 2 feature regression matrix has been added in
`tests/unit/test_phase2_feature_regression_matrix.py`. It covers:

- Read-only data readiness and validation endpoints
- NIfTI QC snapshot and thumbnail preview
- QC Dashboard report, latest reload, fingerprint, and NIfTI QC module cache
- SPM realign non-executing guards

Real preprocessing execution remains not implemented. SPM/MATLAB/DPABI
execution remains disabled and outside the safe allowlist.

## Phase 1 Execution Observability Regression Matrix

A focused regression test matrix has been added in
`tests/unit/test_phase1_execution_observability_matrix.py`. It covers the
complete Phase 1 observability loop:

- **Dry-run blocked states** — REVIEWED_EXECUTION_DISABLED,
  CONFIRMATION_REQUIRED, AUDIT_REQUIRED, PROJECT_CONFIG_REQUIRED,
  PIPELINE_YAML_REQUIRED all remain non-executing with structured status
- **Execution traceability** — reviewed_plan_id, run_link_id, run_id,
  pipeline_path, summary_path are present after successful execution
- **Run list + detail resolution** — run appears in project list, run detail
  returns summary_preview or controlled error, warnings as list
- **Events/logs safety scoping** — events/logs return ok, max_bytes respected,
  irrelevant path params ignored
- **Artifacts safety** — stable required fields, missing artifacts have
  exists=false, invalid artifact_ids rejected, discovered preview succeeds
- **Retry/resume not implemented** — POST to /retry, /resume, /rerun returns 404

The frontend smoke script (`project-runs-panel-smoke.cjs`) was strengthened
with `describeExecuteReviewedStatus` tests for DRY_RUN_OK, AUDIT_REQUIRED,
APPROVAL_GATE_BLOCKED, EXECUTION_POLICY_BLOCKED, EXECUTION_FAILED, unknown
status, and undefined input.

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
