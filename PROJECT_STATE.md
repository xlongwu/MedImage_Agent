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

## Phase 3 Executor Productization Contract

A formal design contract for Phase 3 executor productization has been created
at `docs/PIPELINE_EXECUTOR_PRODUCTIZATION_CONTRACT.md`. It defines the
productized execution lifecycle (14 run states, 12 node states), dry-run/execute
consistency contract, execution request/response schemas, output manifest and
artifact contracts, provenance contract, approval/audit requirements, safe
allowlist policy, Python-only MVP recommendation, failure handling, retry/resume
alignment, frontend UX contract, test strategy, implementation order, and
go/no-go decisions.

**No new execution capability is enabled by this contract.** SPM/DPABI/MATLAB
execution remains disabled and outside the safe allowlist. Rawdata remains
read-only. Research-use only.

## Phase 3 — Pipeline Execution State Schema

Pipeline execution state schema has been implemented:

- `src/backend/app/schemas/execution_state.py` — defines 15 run states
  (`RunState` Literal), 13 node states (`NodeState` Literal), terminal/
  non-terminal/success/failure sets, retry/resume/reuse eligibility sets,
  full transition tables (`RUN_ALLOWED_TRANSITIONS`, `NODE_ALLOWED_TRANSITIONS`),
  pure helper functions (`is_run_terminal`, `is_node_terminal`,
  `is_run_retry_eligible`, `is_run_resume_eligible`, `is_node_retry_eligible`,
  `is_node_reuse_eligible`, `can_transition_run`, `can_transition_node`),
  and optional Pydantic models (`RunStateTransition`, `NodeStateTransition`).
- `tests/unit/test_execution_state_schema.py` — 39 tests covering all states,
  terminal/non-terminal sets, retry/resume/reuse eligibility, allowed and
  disallowed transitions, unknown-string safety, terminal no-outgoing
  invariants, and purity (no file I/O, no runtime executor imports).
- **39 passed in 0.37s.**
- **No runtime executor behavior changed.** SPM/DPABI/MATLAB remain disabled.
  Rawdata remains read-only.

## Phase 3 — Output Manifest and Provenance Helpers

Output manifest and provenance schemas/helpers have been implemented:

- `src/backend/app/schemas/execution_manifest.py` — defines `OutputManifestItem`
  (with validation: non-empty path, non-negative size, verified→exists),
  `OutputManifest` (with auto-computed counts), `ExecutionProvenance`
  (`extra='forbid'`, no shell command field), `ExecutionFailureRecord`
  (`extra='forbid'`, 9 failure stages), 5 Literal type aliases, and 7 pure
  helper functions (`count_missing_required`, `count_verified`,
  `count_manifest_warnings`, `count_manifest_errors`, `count_previewable`,
  `summarize_output_manifest`, `build_output_manifest`).
- `tests/unit/test_execution_manifest_schema.py` — 31 tests covering
  item validation (empty path, negative size, verified→exists), manifest
  aggregation (auto-computed counts, summary dict), provenance serialization
  (no shell command field, external backend, command_template_id as identifier),
  failure records (all 9 stages, retryable/resume_eligible, unknown field
  rejection), and purity (no pipeline_executor import, no file I/O).
- **31 passed in 0.28s.**
- **No runtime executor behavior changed.** SPM/DPABI/MATLAB remain disabled.
  Rawdata remains read-only.

## Phase 3 — Dry-run / Execute Consistency Contract Helpers

Dry-run/execute consistency schemas and pure helpers have been implemented:

- `src/backend/app/schemas/execution_consistency.py` — defines 4 Literal
  type aliases (`ConsistencyStatus`, `ConsistencyIssueSeverity`,
  `ConsistencyIssueCode` with 14 codes, accepted dry-run status set),
  3 Pydantic models (`ConsistencyIssue`, `ExecutionConsistencyInput`,
  `ExecutionConsistencyReport`), and 2 pure helper functions
  (`summarize_consistency_issues`, `verify_execution_consistency`).
  The verifier runs 13 consistency checks: project_id, reviewed_plan_id,
  plan_hash, project_config_path, project_context_path, node_ids,
  node_param_hashes, output_root, output_manifest_ids,
  safe_allowlist_fingerprint, approval_context_id, audit_id, and
  dry_run_status.  Supports `require_approval`, `require_audit`, and
  `require_output_manifest` flags for flexible gating.
- `tests/unit/test_execution_consistency_schema.py` — 41 tests covering
  model serialization (6), passing consistency with 3 accepted dry-run
  statuses (5), all 13 failure checks (17), optional flags (3), summary
  helper (2), multi-issue report (1), and purity (4 — no file I/O, no
  runtime executor import, no rawdata/outputs paths).
- **41 passed in 0.39s.**
- **No runtime executor behavior changed.** SPM/DPABI/MATLAB remain disabled.
  Rawdata remains read-only.

## Phase 3 — Feature Regression Matrix

A focused Phase 3 regression matrix has been added in
`tests/unit/test_phase3_feature_regression_matrix.py`. It covers all three
completed Phase 3 schema layers with 19 tests in 5 groups:

- **Group 1 — Execution state**: run/node state helpers, retry/resume/reuse
  eligibility, allowed/disallowed transitions, unknown-string safety.
- **Group 2 — Output manifest**: item validation (empty path, negative size,
  verified→exists), auto-computed counts, optional-missing handling.
- **Group 3 — Provenance / failure record**: minimal serialization,
  shell_command rejection, external-backend metadata, retryable/resume_eligible.
- **Group 4 — Dry-run/execute consistency**: identical-input pass,
  project_id mismatch, approval/audit detection, bad dry-run status,
  optional-flag flexibility.
- **Group 5 — Purity / safety**: no runtime executor imports, no file I/O,
  no rawdata/outputs paths, no subprocess imports.

**19 passed in 0.29s.**  All existing regression matrices (Phase 1, Phase 2,
SPM preexecution) remain green.  No runtime executor behavior changed.
SPM/DPABI/MATLAB remain disabled.  Rawdata remains read-only.

Phase 3 contract coverage summary:

| Layer | File | Tests |
|---|---|---|
| Execution state | `test_execution_state_schema.py` | 39 |
| Output manifest & provenance | `test_execution_manifest_schema.py` | 31 |
| Dry-run / execute consistency | `test_execution_consistency_schema.py` | 41 |
| Regression matrix | `test_phase3_feature_regression_matrix.py` | 19 |
| Python-only MVP | `test_python_only_safe_node_mvp.py` | 16 |
| **Total Phase 3** | | **146** |

## Phase 3 — Python-only Safe Executable Node MVP

The existing `contract_smoke` node has been validated through a comprehensive
MVP test suite confirming the full safe execution pipeline works end-to-end:

- `tests/unit/test_python_only_safe_node_mvp.py` — 16 tests covering:
  **Group 1** — Catalog & validation: `contract_smoke` is Python/low-risk,
  plan validates, no external-tool approval required.
  **Group 2** — Dry-run & execution: dry-run returns `DRY_RUN_OK`, execution
  through `POST /api/plans/execute-reviewed` with `dry_run=false` succeeds
  (`EXECUTION_SUBMITTED`), produces `run_id`/`run_link_id`, run appears in
  history, run detail is readable.
  **Group 3** — Failure path: `fail=true` produces controlled failure, not crash.
  **Group 4** — Safety boundaries: rawdata mtime unchanged, SPM realign still
  not executable, no MATLAB/SPM subprocess called.
  **Group 5** — Preflight gates: env flag, `confirm_execution`, and
  `persist_audit` all still required — missing any blocks execution.

**16 passed in 2.61s.**  No production code changed.  `contract_smoke` was
already registered in `NODE_REGISTRY` and `TOOL_METADATA`; it already
executed through the full pipeline.  The MVP test suite validates the
end-to-end safety of the existing execution path.

**No new execution capability enabled.**  SPM/DPABI/MATLAB remain disabled.
Rawdata remains read-only.  Research-use only.

Phase 3 coverage summary updated:

| Layer | File | Tests |
|---|---|---|
| Execution state | `test_execution_state_schema.py` | 39 |
| Output manifest & provenance | `test_execution_manifest_schema.py` | 31 |
| Dry-run / execute consistency | `test_execution_consistency_schema.py` | 41 |
| Regression matrix | `test_phase3_feature_regression_matrix.py` | 19 |
| Python-only MVP | `test_python_only_safe_node_mvp.py` | 16 |
| Manifest / provenance integration | `test_contract_smoke_manifest_provenance.py` | 10 |
| **Total Phase 3** | | **156** |

## Phase 3 — Output Manifest / Provenance Integration

`contract_smoke` now emits standardized output manifest and execution
provenance artifacts using the Phase 3 `execution_manifest.py` schemas:

- `src/backend/app/runtime/contract_smoke_manifest.py` — new pure helper
  module that writes `contract_smoke_output_manifest.json` (using
  `OutputManifest` + `OutputManifestItem` models) and
  `contract_smoke_execution_provenance.json` (using `ExecutionProvenance`
  model, `extra='forbid'`, no shell command field).
- `src/backend/app/tools/node_contract_smoke.py` — updated runner to call
  manifest/provenance helpers in the happy path; `outputs` list now includes
  manifest and provenance paths (4 artifacts total); `artifacts_written`
  metric updated to 4.
- `tests/unit/test_contract_smoke_manifest_provenance.py` — 10 tests:
  **Group 1** — manifest artifact exists + schema-valid + items reference
  real files.  **Group 2** — provenance artifact exists + schema-valid
  (backend=python, no shell_command).  **Group 3** — both artifacts
  previewable via artifact detail API.  **Group 4** — safety: rawdata
  unchanged, no MATLAB/SPM subprocess, SPM realign still not executable.
  **Group 5** — run history/detail still readable with manifest artifacts.

**10 passed in 3.08s.**  All existing matrices pass.

**No external-tool execution enabled.**  SPM/DPABI/MATLAB remain disabled.
Rawdata remains read-only.

## Phase 3 — Dry-run / Execute Consistency Integration

The `verify_execution_consistency()` helper from Phase 3 schema layer is
now integrated into the reviewed execution preflight path:

- `src/backend/app/api/execute_reviewed_routes.py` — added
  `_run_consistency_preflight()` helper that builds `ExecutionConsistencyInput`
  from reviewed plan, adapter/preflight, and execution request data; calls
  `verify_execution_consistency()` with `require_approval=True`,
  `require_audit=False`, `require_output_manifest=False`; hard consistency
  failures return `EXECUTION_CONSISTENCY_FAILED` and block before
  `run_pipeline()`.
- `tests/unit/test_execute_reviewed_consistency_integration.py` — 10 tests:
  **Group 1** — `contract_smoke` execution still succeeds with consistency
  preflight.  **Group 2** — simulated consistency failure blocks execution
  and prevents `run_pipeline()` from being called.  **Group 3** — existing
  gates (project context, confirm_execution, external-tool blocking) still
  fire before consistency is reached.  **Group 4** — safety: rawdata
  unchanged, no MATLAB/SPM subprocess, run history/detail visible,
  manifest/provenance artifacts still produced.

**10 passed in 2.34s.**  All existing matrices pass (324 total).

**No external-tool execution enabled.**  SPM/DPABI/MATLAB remain disabled.
Rawdata remains read-only.

Phase 3 coverage summary updated:

| Layer | File | Tests |
|---|---|---|
| Execution state | `test_execution_state_schema.py` | 39 |
| Output manifest & provenance | `test_execution_manifest_schema.py` | 31 |
| Dry-run / execute consistency | `test_execution_consistency_schema.py` | 41 |
| Regression matrix | `test_phase3_feature_regression_matrix.py` | 19 |
| Python-only MVP | `test_python_only_safe_node_mvp.py` | 16 |
| Manifest / provenance integration | `test_contract_smoke_manifest_provenance.py` | 10 |
| Consistency integration | `test_execute_reviewed_consistency_integration.py` | 10 |
| Run-state timeline | `test_run_state_timeline.py` | 16 |
| **Total Phase 3** | | **182** |

## Phase 3 — Run-State Timeline Read Model

A read-only run-state timeline service and endpoint have been added:

- `src/backend/app/services/run_state_timeline.py` — pure read-only service
  with `normalize_run_state()` / `normalize_node_state()` (map legacy
  uppercase statuses to Phase 3 `RunState` / `NodeState` values),
  `build_run_state_timeline()` (derives standardized timeline from run
  link, summary preview, events, and node states), and 3 Pydantic response
  models (`RunStateTimelineEvent`, `NodeStateTimelineRecord`,
  `ProjectRunStateTimelineResponse`).  Uses `execution_state.py` helpers
  (`is_run_terminal`, `is_run_retry_eligible`, `is_run_resume_eligible`,
  `is_node_terminal`, `is_node_retry_eligible`, `is_node_reuse_eligible`).
- `src/backend/app/api/project_history_routes.py` — added read-only
  `GET /api/projects/{project_id}/runs/{run_id}/state-timeline` endpoint
  (404 for missing project/run, ignores path query params, never writes).
- `tests/unit/test_run_state_timeline.py` — 16 tests: normalization (3),
  pure builder (4), endpoint integration (5), safety boundaries (4 —
  rawdata unchanged, no MATLAB/SPM subprocess, run history unchanged).

**16 passed in 2.95s.**  All existing matrices pass (340 total).

**No runtime executor behavior changed.**  SPM/DPABI/MATLAB remain disabled.
Rawdata remains read-only.

## Phase 3 — Frontend Run-State Timeline Display

A frontend run-state timeline panel has been added to the Run Detail view:

- `src/frontend/src/types.ts` — added `RunStateTimelineEvent`,
  `NodeStateTimelineRecord`, `ProjectRunStateTimelineResponse` types.
- `src/frontend/src/api.ts` — added `getProjectRunStateTimeline()` wrapper.
- `src/frontend/src/components/run-history/RunStateTimelinePanel.tsx` —
  new component: fetches `GET .../state-timeline`, displays run state
  summary (current state badge, terminal/retry/resume eligibility
  indicators), timeline events (timestamp, state, source, node, message),
  node states (node_id, state, terminal/retry/reuse, warning/error counts).
  Handles loading, error, empty, and missing data states.  Uses `stateTone()`
  helper (green=ok, blue=info, red=error, grey=unknown).  No action buttons.
- `src/frontend/src/components/run-history/RunDetailPanel.tsx` — imports
  and renders `RunStateTimelinePanel` after `RunLogsPanel`.

**Frontend validation**: `npm run typecheck` ✓, `npm run build` ✓,
`npm run test:project-runs` ✓.  Backend tests unchanged (51 passed).

**No execution controls added.**  No backend behavior changed.
SPM/DPABI/MATLAB remain disabled.  Research-use only.

## Phase 3 — Node-State Artifact Normalization

`contract_smoke` now emits a normalized Phase 3 node-state JSON artifact
that the timeline endpoint can consume for accurate per-node state data:

- `src/backend/app/runtime/contract_smoke_manifest.py` — added
  `write_contract_smoke_node_state()` that writes
  `contract_smoke_node_state.json` with `schema_version`,
  `node_id`, `state`, `terminal`, `retry_eligible`, `reuse_eligible`
  (computed via `execution_state.py` helpers), timestamps, warnings,
  errors, and metadata.  Updated `_build_manifest_items()` to include
  the node-state artifact as `node_state_json` (required, verified,
  previewable).  Added `contract_smoke_artifact_paths()`.
- `src/backend/app/tools/node_contract_smoke.py` — calls
  `write_contract_smoke_node_state()` before manifest/provenance;
  `outputs` list expanded from 4→5 artifacts; `artifacts_written`
  metric updated to 5.
- `src/backend/app/services/run_state_timeline.py` — `build_run_state_timeline()`
  now recognizes normalized node-state artifacts by `schema_version`
  prefix; uses artifact's `state`/`terminal`/`retry_eligible`/
  `reuse_eligible` fields directly with fallback to helper functions.
- `src/backend/app/api/project_history_routes.py` — state-timeline
  endpoint now discovers and reads normalized node-state JSON
  artifacts from the artifact list and passes them to the builder.
- `tests/unit/test_contract_smoke_node_state_artifact.py` — 10 tests:
  **Group 1** — node-state artifact exists + schema fields + helpers match.
  **Group 2** — output manifest includes node-state item + previewable.
  **Group 3** — timeline consumes normalized data + corrupt fallback safe.
  **Group 4** — safety: rawdata unchanged, no MATLAB/SPM subprocess,
  SPM realign still not executable.

**10 passed in 3.55s.**  All existing matrices pass (271 total).

**No runtime executor behavior broadened.**  SPM/DPABI/MATLAB remain disabled.
Rawdata remains read-only.

## Phase 3 — End-to-End Integration Regression

Full Phase 3 end-to-end integration regression passed.  All 5 validation
groups green:

| Group | Tests | Result |
|---|---|---|
| contract_smoke / timeline | 52 | ✓ |
| project history / observability | 30 | ✓ |
| Phase 2 / Phase 3 matrices | 35 | ✓ |
| execute-reviewed / safety gates | 142 | ✓ |
| Frontend typecheck / build / smoke | — | ✓ |
| **Total backend** | **259** | ✓ |

No production code changes needed.  No cache/report/artifact files leaked.
Rawdata unchanged.  SPM/DPABI/MATLAB remain disabled.

`contract_smoke` now validates the full Phase 3 pipeline:
reviewed execution → consistency preflight → manifest/provenance/node-state
artifacts → run history → artifact preview → state timeline.

**Phase 3 is complete.**

## Phase 3 — Full Backend CI Pass and Freeze

Full backend unit suite passed after Phase 3 end-to-end integration:

```
2915 passed, 1 skipped, 0 failed in 1015.04s (0:16:55)
```

Skip: `pydicom` (expected — documented in test baseline).
Frontend: `npm run typecheck` ✓, `npm run build` ✓, `npm run test:project-runs` ✓.

**Phase 3 is frozen.**

Phase 3 delivers:
- `execution_state.py` — run/node state machine, transitions, helpers
- `execution_manifest.py` — output manifest, provenance, failure records
- `execution_consistency.py` — dry-run/execute invariant verifier
- `contract_smoke` reviewed execution with 5 artifacts:
  report, log, node-state, output manifest, execution provenance
- Consistency preflight before `run_pipeline()`
- Read-only run-state timeline endpoint + frontend panel
- Normalized node-state artifacts consumed by timeline

No external-tool execution is enabled. SPM/DPABI/MATLAB remain disabled.
Rawdata remains read-only. Research-use only.

## FunRaw/T1Raw DICOM Support

Real FunRaw/T1Raw DICOM rawdata is now detected and validated in the packaged
Windows desktop app.  No conversion is executed.  No rawdata is modified.

### Test data

```
DemoData/
├── FunRaw/
│   ├── Sub_001/*.dcm
│   ├── Sub_002/*.dcm
│   └── Sub_003/*.dcm
└── T1Raw/
    ├── Sub_001/*.dcm
    ├── Sub_002/*.dcm
    └── Sub_003/*.dcm
```

### Verified counts

| Metric | Value |
|---|---|
| Total DICOM files | **1104** |
| Subjects | **3** |
| Subject-modality groups | **6** |
| NIfTI files (.nii/.nii.gz) | **0** |

### Detection mechanism

`src/backend/app/services/funraw_t1raw_detector.py` — pure path-based detector,
no pydicom required.  Detects `FunRaw/` and `T1Raw/` directories, counts `.dcm`
files per subject, normalises `Sub_001` → `sub-001` (BIDS-style).

### Current behaviour

| Service | Status | Notes |
|---|---|---|
| Data Readiness | `warning` | Detects DICOM raw layout, displays DICOM counts; downgrades `image_validation` fail to warning |
| NIfTI QC | `warning` | `image_count=0`, `warning_count=1`; recommends Conversion Dry-Run; no synthetic fallback |
| Conversion Dry-Run | `ready` | Produces 6 BIDS/NIfTI mapping previews (3 FunRaw → bold, 3 T1Raw → T1w); `blocking_issues=[]` |
| BOLD Reference Readiness | `blocked` | No BOLD NIfTI files (expected before conversion) |
| Motion QC Readiness | `blocked` | No BOLD NIfTI files (expected before conversion) |
| BIDS Validation | `fail` | Expected for raw DICOM before BIDS conversion |

### Conversion mapping preview

1. `FunRaw/Sub_001` → `sub-001/func/sub-001_task-rest_bold.nii.gz`
2. `FunRaw/Sub_002` → `sub-002/func/sub-002_task-rest_bold.nii.gz`
3. `FunRaw/Sub_003` → `sub-003/func/sub-003_task-rest_bold.nii.gz`
4. `T1Raw/Sub_001` → `sub-001/anat/sub-001_T1w.nii.gz`
5. `T1Raw/Sub_002` → `sub-002/anat/sub-002_T1w.nii.gz`
6. `T1Raw/Sub_003` → `sub-003/anat/sub-003_T1w.nii.gz`

### Explicit non-goals

- No real DICOM conversion is executed.
- No dcm2niix or any external converter is called.
- No SPM/DPABI/MATLAB/FSL/AFNI execution.
- No rawdata modification.
- No clinical diagnosis.

### Packaged-app validation

Directory build (`win-unpacked`) validated with:

- `Data Readiness` — correctly reports DICOM raw layout as `warning`
- `NIfTI QC` — correctly reports no NIfTI, no synthetic fallback
- `Conversion Dry-Run` — produces 6 mapping previews, no blocking issues
- Backend sidecar includes latest FunRaw/T1Raw DICOM support
- GUI polish applied: DICOM callout banner, `image_validation` downgrade,
  `import_records.has_dicom` hidden, `image_source_discovery` NIfTI-only note,
  BIDS fail explanation, ASCII-only API messages

### Known UI limitations

- Dataset Summary card may not yet fully integrate DICOM counts from Data
  Readiness response.
- BIDS Validation fail is expected for raw DICOM; UI now explains this.
- Conversion execution is future work and must go through safety contract /
  approval / audit design first.

## Phase 4A — Real Preprocessing Execution Contract

A formal design contract for the complete DPARSFA-style rs-fMRI preprocessing
pipeline has been created at `docs/REAL_PREPROCESSING_EXECUTION_CONTRACT.md`.

### Contract scope

The contract defines:

- 17 preprocessing stages from DICOM conversion to derivative summary
- External-tool classification (dcm2niix / SPM12 / DPABI / Python)
- Approval and audit requirements per stage
- Output directory policy (converted_bids / derivatives / outputs)
- Rawdata read-only invariant (universal)
- External tool policy (command-template wrapper, stdout/stderr capture)
- Safe allowlist expansion requirements (16 conditions)
- Failure handling and rollback policy
- Retry/resume alignment
- Output manifest and provenance contracts
- QC report contract (subject-level + group-level)
- Subject-level execution model
- Frontend UX contract
- Testing strategy
- Staged implementation plan (Phases 4A–4F)
- Go/No-Go criteria for each phase

### Schema module

`src/backend/app/schemas/preprocessing_execution.py` — pure schema/helper
module defining `PreprocessingStage` (17 Literal values), stage metadata maps
(external-tool, approval, subject/project-level), plan models
(`PreprocessingPlan`, `PreprocessingStageConfig`, `PreprocessingSubjectPlan`),
execution models (`PreprocessingExecutionRequest`, `PreprocessingExecutionPreview`),
safety flags model, and 9 pure helper functions.

### Tests

`tests/unit/test_preprocessing_execution_schema.py` — 32 tests across 10 groups:
stage literals, external-tool classification, approval requirements,
rawdata read-only invariant, subject/project-level classification,
stage ordering validation (6 cases), default plan builder (5 cases),
environment flag validation (4 cases), Pydantic model smoke (5 cases),
and purity invariants (4 cases).

### Explicit non-goals

- No real DICOM conversion is implemented.
- No dcm2niix execution is enabled.
- No SPM/DPABI/MATLAB/FSL/AFNI execution is enabled.
- The safe allowlist is NOT expanded.
- No preprocessing node runner is implemented.
- No frontend panels are added.
- Rawdata remains read-only.

## Phase 4B — DICOM Conversion Execution Safety Wrapper

A safety wrapper for DICOM-to-NIfTI conversion has been designed and
implemented as a service skeleton.  Real dcm2niix execution is disabled
by default.

### Contract

`docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md` — 18 sections covering
command-template policy, environment flag gating (5 flags required),
approval/audit requirements, output directory safety, rawdata read-only
invariant, failure handling, rollback/cleanup, test strategy, and
Go/No-Go criteria.

### Schema module

`src/backend/app/schemas/dicom_conversion_execution.py` — pure schema/helper
module defining 6 Literal type aliases (`DicomConversionMode`, `DicomConversionStatus`,
`DicomConversionTool`, etc.), 7 Pydantic models (`Dcm2niixCommandTemplate`,
`DicomConversionMapping`, `DicomConversionPreflight`, `DicomConversionExecutionRequest`,
`DicomConversionExecutionResponse`, `DicomConversionFailureRecord`,
`DicomConversionSafetyFlags`), and 6 pure helper functions.

### Service skeleton

`src/backend/app/services/dicom_conversion_execution.py` — preflight-only
service that:
- Reads project metadata and conversion dry-run mappings
- Checks 5 environment flags (all required for execution)
- Detects dcm2niix via `shutil.which` (no subprocess call)
- Validates output root safety (under project, not under rawdata)
- Builds dcm2niix command templates from dry-run mappings
- Returns `conversion_disabled_by_default=true` in all responses
- Does NOT call dcm2niix, write NIfTI files, or modify rawdata

### Tests

`tests/unit/test_dicom_conversion_execution_schema.py` — 31 tests across
8 groups: mode/status literals, command template construction (FunRaw BOLD +
T1Raw T1w), no-shell-string enforcement, disabled-by-default response,
environment flag validation (4 cases), output root safety (6 cases),
mapping summary, preflight model defaults, failure record fields, and
purity invariants (5 cases).

### Key invariants

- `command_preview` is display-only — not an execution mechanism
- `extra='forbid'` on `Dcm2niixCommandTemplate` — no raw shell fields
- All safety flags default to safest values
- 5 environment flags must all be `"1"` for preflight readiness
- Output root must be under project dir, not under rawdata dir
- No subprocess, no file writes, no external tool imports
- No SPM/DPABI/MATLAB references in schema or service

## Phase 4C-0 — dcm2niix Availability Preflight and Fake/Sandbox Runner

Phase 4C-0 adds availability detection and sandbox execution without enabling
real DICOM conversion.

### Contract update

`docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md` Section 18 extended with:
- dcm2niix availability check contract (path detection + version query via
  injected runner, never `shell=True`)
- Fake/sandbox runner contract (`fake_outputs` and `mock_subprocess` modes)
- Synthetic output manifest and provenance policies
- Go/No-Go criteria for future real conversion smoke (Phase 4C-1)

### Schema extension

`src/backend/app/schemas/dicom_conversion_execution.py` extended with:
- `Dcm2niixAvailabilityStatus` — 5 Literal values
- `DicomConversionSandboxMode` — 3 Literal values
- `Dcm2niixAvailabilityCheck` model
- `DicomConversionSandboxResult` model
- `parse_dcm2niix_version()` pure helper
- `is_dcm2niix_availability_ready()`, `requires_fake_or_sandbox_mode()`,
  `build_disabled_sandbox_result()`, `summarize_sandbox_artifacts()`

### Service implementation

`src/backend/app/services/dicom_conversion_execution.py` extended with:
- `check_dcm2niix_availability(executable, env, runner)` — path detection
  via `shutil.which`, version query via injected runner, never `shell=True`
- `run_conversion_sandbox(project_id, request, mode, output_root, runner)` —
  `disabled` (default), `fake_outputs` (placeholder paths), `mock_subprocess`
  (simulates dcm2niix via injected runner)
- No real dcm2niix is called. No files are written. No rawdata modified.

### Tests

`tests/unit/test_dicom_conversion_availability.py` — 27 tests across 8 groups:
version parsing (6), env flag gating (3), fake runner (3), sandbox disabled
(4), mock subprocess (2), helper functions (3), safety invariants (5),
safety flag defaults (2).

### Key invariants

- All sandbox modes default to `disabled`
- `mock_subprocess` uses injected runner, never `subprocess.run` directly
- Version query uses argv list, never `shell=True`
- All safety flags default to safest values
- No real rawdata conversion in any mode

## Phase 4C-1 — Controlled Synthetic dcm2niix Smoke

Phase 4C-1 adds a tightly controlled real `dcm2niix` smoke test path that
operates exclusively on synthetic/minimal DICOM data.

### Contract update

`docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md` Section 18.11 extended with:
- Synthetic DICOM input contract (pydicom, tmp_path, no patient data)
- Required env flags (7 flags including `MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE`)
- Command-template execution policy
- Output root policy (must be under tmp_path)
- Manifest/provenance/log requirements
- Skip policy (pydicom/dcm2niix unavailable → skip)
- Go/No-Go criteria for user-data conversion (Phase 4D)

### Synthetic DICOM helper

`tests/unit/dicom_synthetic_helpers.py` — creates minimal valid DICOM series
using pydicom under pytest `tmp_path`.  Provides:
- `create_minimal_dicom_series(root, subject_id, ...)` → `Path`
- `create_synthetic_funraw_layout(root, subject_count)` → `dict[str, Path]`
- `pydicom_available()` → `bool`
- No patient-identifying data.  Deterministic metadata.

### Service implementation

`src/backend/app/services/dicom_conversion_execution.py` extended with:
- `run_synthetic_dcm2niix_smoke(input_dir, output_root, executable, env, runner)`
  — 7-step smoke: env flag check → input path safety (refuses real rawdata) →
  availability check → command template → execution via runner →
  manifest write → provenance write
- Input path safety: blocks paths containing `DemoData`, `FunRaw`, `T1Raw`,
  `rawdata`, `BIDS`
- 7 env flags required; all must be `"1"`
- Availability check uses `check_dcm2niix_availability()` with status mapping
- `shell=True` never used; all subprocess via argv list

### Tests

`tests/unit/test_dicom_conversion_synthetic_smoke.py` — 20 tests across
6 groups: env flag gating (3), input path safety (3), fake runner execution
(7), output safety (2), synthetic DICOM creation (3, skip if no pydicom),
safety invariants (2).  17 passed, 3 skipped (pydicom not installed).

### Key invariants

- `run_conversion_execute()` still returns disabled for all user projects
- Real rawdata paths (FunRaw/T1Raw/DemoData) are refused by the smoke function
- All tests use monkeypatched `shutil.which` + fake runner; no real subprocess
- Synthetic DICOM tests skip cleanly when pydicom unavailable
- SPM/DPABI/MATLAB remain disabled

## Phase 4C-2 — Conversion Preflight UI and Operator Review Flow

A read-only DICOM conversion review panel and preflight API endpoint have been
added.  No real conversion is enabled.

### Backend endpoint

`POST /api/projects/{project_id}/conversion/preflight` — read-only preflight
that returns conversion readiness, dcm2niix availability, command templates,
safety flags, and gating status.  Does NOT call dcm2niix, write NIfTI files,
or modify rawdata.

### Frontend

- `src/frontend/src/types.ts` — added `DicomConversionPreflightResponse`,
  `DicomConversionSafetyFlags`, `Dcm2niixCommandTemplate`, `DicomConversionMapping`
- `src/frontend/src/api.ts` — added `runProjectDicomConversionPreflight()`
- `src/frontend/src/components/DicomConversionReviewPanel.tsx` — new panel with:
  Conversion readiness summary, dcm2niix availability card, command template
  previews (display-only), safety flag badges, output root preview, mapping list,
  operator safety callout
- `src/frontend/src/App.tsx` — wired `DicomConversionReviewPanel` after
  `ConversionDryRunPanel`

### Tests

`tests/unit/test_dicom_conversion_preflight_api.py` — 9 tests:
returns 200, disabled by default, safety flags present, command templates,
no NIfTI writes, no rawdata modification, dcm2niix status, 404 for missing
project, no user-data execute endpoint.

### Key invariants

- No "Run real conversion" or "Execute" button
- Panel shows: "Real DICOM-to-NIfTI conversion for user data is not enabled"
- Command previews labelled "not executed for user rawdata"
- No user-data conversion execute endpoint
- Preflight is read-only; no files written

## Phase 4D — DICOM Conversion Approval Gate Design Review

A formal approval gate design review and schema have been completed.
Real user-data conversion remains NO-GO.

### Design document

`docs/DICOM_CONVERSION_APPROVAL_GATE_DESIGN.md` — 21 sections covering:
purpose, baseline, non-goals, threat model (7 threats), 17 required
preconditions, approval record fields (21), audit record requirements,
operator acknowledgements (8 explicit confirmations), output directory
policy, rawdata read-only confirmation, mapping/command-template review,
dcm2niix availability, env flags, safe allowlist (16 conditions),
manifest/provenance, failure/rollback, frontend UX requirements,
test strategy, go/no-go checklist (14 items, 0/14 met).

### Schema module

`src/backend/app/schemas/dicom_conversion_approval.py` — pure schema/helper:
- `DicomConversionApprovalStatus` (6 values), `DicomConversionOverwritePolicy` (3),
  `DicomConversionGateDecisionStatus` (5)
- `DicomConversionApprovalRecord` (21 fields covering all 17 preconditions)
- `DicomConversionAuditRecord` (14 fields)
- `DicomConversionApprovalChecklist`, `DicomConversionGateDecision`
- 5 pure helpers: `build_conversion_approval_checklist()`,
  `is_conversion_approval_complete()`, `evaluate_conversion_approval_gate()`,
  `requires_new_run_directory()`, `is_safe_overwrite_policy()`

### Frontend

`DicomConversionReviewPanel` — added "Approval Gate Requirements" section
showing 17-item read-only checklist with NO-GO badge.

### Tests

`tests/unit/test_dicom_conversion_approval_schema.py` — 24 tests across
7 groups: missing/incomplete (9), unsafe output root (2), approved path (3),
purity/safety (3), checklist (2), policy helpers (2), model defaults (3).

### Key decision

**0/14 go/no-go conditions met.  Real user-data conversion remains NO-GO.**

## Phase 4E-0 — Approval-Gated Plan Persistence and Run-Directory Reservation

Approval plan persistence and run-directory reservation have been implemented.
No dcm2niix is executed.  No NIfTI files are created.

### Schema extension

`src/backend/app/schemas/dicom_conversion_approval.py` extended with:
- `DicomConversionPersistenceStatus` (6 Literal values)
- `DicomConversionRunReservation` (16 fields)
- `DicomConversionPersistedPlan` (8 fields)
- `DicomConversionPlanPersistenceResponse` (9 fields)
- 5 pure helpers: `build_conversion_run_id()`, `build_conversion_run_paths()`,
  `validate_conversion_run_paths()`, `is_reserved_run_directory_safe()`,
  `summarize_persisted_conversion_plan()`

### Service

`src/backend/app/services/dicom_conversion_plan_persistence.py`:
- `persist_conversion_plan()` — evaluates approval gate, reserves run directory
  under `<project>/conversion_runs/<id>/`, writes 9 files (approval, audit,
  preflight, mappings, templates, manifest, provenance, 2 logs, README)
- No dcm2niix call, no NIfTI creation, no rawdata modification

### Endpoint

`POST /api/projects/{project_id}/conversion/approval/persist-plan`

### Frontend

- `DicomConversionReviewPanel` — added "Persist review package" button
  with result display showing run ID, directory, and written file count
- `api.ts` — added `persistProjectDicomConversionPlan()`
- `types.ts` — added `DicomConversionRunReservation` and
  `DicomConversionPlanPersistenceResponse`

### Tests

`tests/unit/test_dicom_conversion_plan_persistence.py` — 20 tests across
7 groups: blocked approval, safe reservation, path safety, file writes (7),
no NIfTI/dcm2niix, collision handling, pure helpers (5).

## Phase 4E-1 — Persisted Review Package UI and Audit Export

Review package reader, audit export, and UI polish have been added.
No dcm2niix is executed.  Export contains metadata only — no image data.

### Service

`src/backend/app/services/dicom_conversion_review_package.py`:
- `read_conversion_review_package()` — reads all 10 persisted files,
  returns structured response with approval summary, mapping/template counts
- `export_conversion_review_package()` — creates metadata-only ZIP audit
  bundle with SHA256SUMS.txt, excludes .dcm/.nii/.nii.gz/.img/.hdr files
- All exports include safety flags: metadata_only, no_image_data, no_conversion

### Endpoints

- `GET /api/projects/{id}/conversion/approval/packages/{run_id}` — read package
- `POST /api/projects/{id}/conversion/approval/packages/{run_id}/export` — export ZIP

### Tests

`tests/unit/test_dicom_conversion_review_package.py` — 15 tests across
3 groups: read package (5), export bundle (8), missing package (2).

### Key invariants

- Export contains only .json, .log, .md, .txt files
- Export excludes .dcm, .nii, .nii.gz, .img, .hdr
- Export uses relative paths, includes SHA256SUMS.txt
- No dcm2niix called, no image data included, no rawdata modified

## Phase 4F-0 — Controlled Synthetic-Only Real Conversion from Persisted Package

Synthetic-only real dcm2niix conversion using persisted approval packages
has been implemented.  User rawdata conversion remains disabled.

### Service

`src/backend/app/services/dicom_conversion_execution.py` extended with:
- `run_synthetic_conversion_from_persisted_package(project_id, conversion_run_id, env, runner, synthetic_only)` —
  8-step pipeline: env flag check → read persisted package → validate required
  files → validate approval gate → validate input paths are synthetic → dcm2niix
  availability → execute via runner → write manifest + provenance
- Refuses paths containing DemoData, FunRaw, T1Raw, rawdata, BIDS
- 8 env flags required including `MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION`
- Uses argv list, never shell=True

### Contract

`docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md` Section 19 added.

### Tests

`tests/unit/test_dicom_conversion_persisted_synthetic_execution.py` — 12 tests
across 5 groups: env flag gating (2), missing approval (2), rawdata refusal (1),
fake runner execution (6), safety invariants (1).

### Key invariants

- User-data conversion remains disabled (`run_conversion_execute()` returns blocked)
- Real rawdata paths refused
- All tests use monkeypatched shutil.which + fake runners
- No real dcm2niix called
- SPM/DPABI/MATLAB remain disabled

## Phase 4F-1 — Internal Smoke Result Viewer and Release Validation

Internal synthetic smoke result reader and release validation completed.
User rawdata conversion remains disabled.

### Service

`src/backend/app/services/dicom_conversion_review_package.py` extended with:
- `read_synthetic_smoke_results(project_id, conversion_run_id, project_dir)` —
  reads output manifest, provenance, stdout/stderr logs, and discovered output
  artifacts.  NIfTI files are metadata-only (no image parsing).

### Tests

`tests/unit/test_dicom_conversion_smoke_results.py` — 7 tests:
read manifest/provenance, created artifacts, nifti metadata_only,
missing manifest warning, missing logs warning, safety flags, no subprocess.

### Release validation

Full Phase 4 test suite: **162 passed, 3 skipped** (pydicom).
Safety regression (Phase 2+3+SPM): **41 passed**.
Total: **203 passed, 3 skipped**.

## Phase 4G-0 — User-Data Conversion GO/NO-GO Review

Formal GO/NO-GO review completed.  **Decision: NO-GO.**

### Review document

`docs/DICOM_USER_DATA_CONVERSION_GO_NO_GO_REVIEW.md` — 10 sections:
implementation baseline, threat model, 32 gate criteria table,
evidence summary (test/synthetic/approval/manifest/provenance/log),
6 remaining risks, GO/NO-GO criteria, weighted decision matrix,
final recommendation (NO-GO), rationale, next task.

### Gate criteria summary

- 26 of 32 gates **met** (safety wrapper, approval schema, persistence,
  export, smoke scaffold, frontend safety, env flags, no shell)
- 3 gates **partial** (rollback schema only, approval gate not integrated,
  audit not wired into execution)
- 4 gates **missing** (rawdata checksum, real dcm2niix smoke, external
  DICOM smoke, rollback implementation)

### Schema

`src/backend/app/schemas/dicom_conversion_go_no_go.py`:
- `DicomConversionGoNoGoCriterion`, `DicomConversionGoNoGoReview` models
- `evaluate_go_no_go_criteria()` — 10 critical gate IDs
- `build_default_go_no_go_review()` — reflects current Phase 4F-1 state
- `summarize_missing_go_criteria()`, `is_conditional_go_allowed()`

### Tests

`tests/unit/test_dicom_conversion_go_no_go_schema.py` — 12 tests:
decision logic (5), default review (4), purity (3).

### Key decision

**NO-GO.**  Real dcm2niix validation on synthetic DICOM, rawdata
checksum verification, and rollback are required before any user-data
conversion path can be considered.

## Phase 4H-0 — Real dcm2niix Smoke on Synthetic DICOM Only

Real `subprocess.run([dcm2niix, ...])` path added for synthetic DICOM only.
User rawdata conversion remains disabled.

### Service

`src/backend/app/services/dicom_conversion_execution.py` extended with:
- `run_real_dcm2niix_synthetic_smoke(input_dir, output_root, executable, env)` —
  first function that calls `subprocess.run([dcm2niix, ...])` behind 9 env flags,
  synthetic-only input validation, dcm2niix availability check, and argv list
  construction.  Writes manifest, provenance, stdout/stderr logs.
- New env flag: `MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE=1` required
- Path safety: blocks DemoData/FunRaw/T1Raw/rawdata/BIDS unless under tmp/pytest

### Tests

- `tests/unit/test_dicom_conversion_real_synthetic_smoke_guards.py` — 8 tests:
  env flag gating (2), path safety (2), no shell=True (2), existing safety (2)
- `tests/integration/test_dicom_conversion_real_synthetic_smoke.py` — 3 tests,
  all skipped by default (require 9 env flags + dcm2niix + pydicom)

### Key invariants

- All integration tests skip by default
- Real subprocess only after 9 env flags + path safety + availability
- Never `shell=True`
- User-data conversion still disabled (`run_conversion_execute()` blocked)
- SPM/DPABI/MATLAB remain disabled

## Phase 4H-1 — Rawdata Checksum Verification and Rollback Design

Rawdata checksum snapshot/comparison and dry-run rollback design added.
No conversion enabled.  No rawdata modified.

### Schema

`src/backend/app/schemas/dicom_conversion_safety.py` — pure schema/helper:
- `RawdataChecksumSnapshot` (10 fields), `RawdataChecksumComparison` (10 fields)
- `DicomConversionRollbackPlan` (9 fields), `DicomConversionRollbackResult` (8 fields)
- 6 pure helpers: `build_rawdata_checksum_snapshot()`, `compare_rawdata_checksum_snapshots()`,
  `is_rawdata_unchanged()`, `build_conversion_rollback_plan()`,
  `run_conversion_rollback_dry_run()`, `summarize_rollback_plan()`

### Service

`src/backend/app/services/dicom_conversion_safety.py`:
- `build_pre_conversion_rawdata_snapshot()` / `build_post_conversion_rawdata_snapshot()`
- `compare_conversion_rawdata_snapshots()`
- `build_conversion_output_rollback_plan()` / `run_conversion_output_rollback_dry_run()`
- Dry-run only: never deletes files, never modifies rawdata

### Tests

`tests/unit/test_dicom_conversion_safety.py` — 16 tests across 5 groups:
checksum snapshot (1), comparison (4), path safety (3), rollback plan (3),
purity/safety (5).

### Key invariants

- Checksum verification is metadata-only (fingerprint + file count + size)
- Rollback plan excludes rawdata paths
- Dry-run deletes nothing
- User-data conversion remains disabled
- SPM/DPABI/MATLAB remain disabled

## Phase 4H-2 — Approval/Audit Integration for Checksum Snapshots

Rawdata checksum snapshots and rollback plans are now integrated into
persisted approval packages, review package reader, and audit export.
No conversion enabled.  No rawdata modified.

### Integration

- `persist_conversion_plan()` now writes `rawdata_checksum_before.json`
  (using `build_rawdata_fingerprint()` + `RawdataChecksumSnapshot`) and
  `rollback_plan_dry_run.json`
- `read_conversion_review_package()` now lists 12 files (up from 10),
  extracts rawdata fingerprint/file_count into approval_summary
- `DicomConversionApprovalRecord` extended with 8 checksum/rollback fields
- Audit export includes checksum and rollback metadata; still excludes .dcm/.nii

### Tests

`tests/unit/test_dicom_conversion_checksum_integration.py` — 14 tests:
persisted writes (2), review package (2), export safety (3), rollback (2),
approval schema (2), existing safety (3).

### Key invariants

- Checksum snapshot is metadata-only (fingerprint + file count + size)
- Rollback dry-run never deletes files
- Rawdata paths protected in rollback plan
- Export still excludes .dcm, .nii, .nii.gz
- User-data conversion remains disabled

## Phase 4G-1 — GO/NO-GO Re-review After Checksum/Rollback Integration

GO/NO-GO review rerun.  **Decision: NO-GO — but closer to CONDITIONAL GO.**

### Gate changes

- 28 of 32 gates now **met** (up from 26)
- 3 gates **partial** (rollback dry-run, approval/audit wiring, real synthetic smoke scaffold)
- 1 gate **missing** (external DICOM smoke on real layout)

### Key movements

- Rawdata checksum: missing → **met** (persisted, in approval/review/export)
- Rollback: missing → **partial** (dry-run only, never deletes)
- Real dcm2niix smoke: missing → **partial** (scaffold exists; skipped by default)

### Primary blocker

Real dcm2niix has not been validated against synthetic DICOM in a non-skipped smoke test.

### Tests

`test_dicom_conversion_go_no_go_schema.py` — 12 passed (updated expectations)

### Next step

**Phase 4H-3 complete.**  Evidence capture infrastructure added.
`src/backend/app/services/dicom_conversion_smoke_evidence.py` provides
`capture_synthetic_smoke_evidence()` which runs real dcm2niix on synthetic
DICOM when all 9 env flags + dcm2niix + pydicom are available, and returns
structured evidence.  On this build environment, dcm2niix is not installed
— evidence capture returns `status=skipped`.  Awaiting a compatible
environment for real smoke execution.

## Next recommended work

1. **Phase 4H-3 execution** — Run `capture_synthetic_smoke_evidence()` on
   a machine with dcm2niix installed and all 9 env flags set.  Record
   the output as GO/NO-GO evidence.
2. Review Phase 4H-3 deliverables with the project maintainer.
3. Verify Electron GUI startup on a local Windows desktop.
4. Run full NSIS + portable build when a compatible environment is available.
5. Keep release validation repeatable with the mamba interpreter.
