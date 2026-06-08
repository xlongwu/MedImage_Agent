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

## Next recommended work

1. **Phase 4 planning** — review Phase 3 deliverables, decide on next
   productization priority (Python-only executor state machine wiring,
   retry/resume implementation, or external-tool re-review per
   `docs/SPM_REALIGN_REAL_EXECUTION_DESIGN_REVIEW.md`).
2. Verify Electron GUI startup on a local Windows desktop.
3. Run full NSIS + portable build with `-NsisArchive` and `-NsisResourcesArchive`.
4. Keep release validation repeatable with the mamba interpreter.
5. Run external BIDS smoke only when the user provides a deliberately bounded
   read-only `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.
6. Consider a future `project_create_service` only if project creation routes
   grow again.
7. Consider a future execution orchestration service only if
   `execute_reviewed_routes.py` needs more separation after MVP release.
