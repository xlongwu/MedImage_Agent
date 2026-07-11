# Reviewed Preprocessing Pipeline Contract

Current as of 2026-06-28.

This contract summarizes the current reviewed preprocessing pipeline boundary
for developers. `AGENTS.md` remains the authoritative repository operating
contract.

## Architecture Boundary

The frontend may configure and submit reviewed preprocessing requests, but
backend services and registered node runners remain the source of truth for
execution, safety, state, provenance, and artifact registration.

Server-side layering remains:

```text
Route
-> Request/Response Schema
-> Service
-> Runtime / Runner or Scientific Kernel
-> State and Artifact Storage
```

Frontend code must use `src/frontend/src/lib/api/preprocessing.ts` and shared
types from `src/frontend/src/types.ts`. It must not access the filesystem
directly.

## Reviewed Execution Request

The frontend reviewed flow submits
`PreprocessingPipelineExecuteRequest` to:

```text
POST /api/projects/{project_id}/preprocessing/runs/{preprocessing_run_id}/execute-reviewed
```

Required user-side confirmations are:

- `confirm_rawdata_readonly`
- `confirm_reviewed_execution`
- `confirm_external_tools_if_needed`
- `confirm_research_use_only`
- `confirm_no_clinical_use`

The backend still decides whether execution is allowed. UI confirmations do
not bypass Approval Gate, environment gates, safe-path checks, or artifact
precondition checks.

## Status Semantics

UI, report, validation, and docs must preserve these distinctions:

- `blocked` is not a failed computation; it means execution did not proceed
  because required evidence or gates were missing.
- `metadata_only` must not be counted as computed.
- `preview_only` must not be counted as full research output.
- `partial` must disclose the subset or missing stage.
- `succeeded` requires backend evidence and registered artifacts for the stage.

`execution_limits.preview_limit` is the reviewed preview switch. When it is
present, affected stage results, manifests, reports, validation summaries, and
UI summaries must label the run `preview_only`. `max_subjects` is a subset
limit and must be reported as `partial` when it truncates the discovered
subject scope.

## Realignment And Motion QC Contract

Minimal FC v1 may resume from reviewed registered realignment outputs. A
realignment output is not complete for downstream nuisance regression unless
the registry contains:

- realigned BOLD;
- motion parameters;
- FD time series;
- motion QC JSON or summary evidence.

Registering reviewed SPM sandbox outputs may compute deterministic Python
motion QC from derivative `rp_*.txt` files. This does not enable MATLAB/SPM
execution and does not modify rawdata.

SPM sandbox execution must not silently cap discovered BOLD files. The default
selection policy is `all`; if `preview_limit` is supplied, manifest,
provenance, subject status, and API response must record
`selection_policy=explicit_preview_limit` and `preview_only=true`.

## FC Artifact Contract

Formal FC output should expose, when available:

- ROI time series;
- correlation matrix;
- Fisher-z matrix;
- labels;
- QC;
- provenance;
- artifact registry ids or paths returned by the backend.

Synthetic atlas output remains preview-only. A real atlas path must be reviewed
and must pass backend space/shape checks before the output can be treated as
atlas-grounded.

## Validation Expectations

For frontend changes touching reviewed preprocessing flow, run:

```powershell
npm.cmd --prefix src/frontend run typecheck
npm.cmd --prefix src/frontend run test
npm.cmd --prefix src/frontend run build
```

For backend contract changes, also run focused preprocessing tests and backend
collection:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_preprocessing_orchestrator.py tests/unit/test_preprocessing_pipeline_report.py tests/unit/test_preprocessing_pipeline_validation.py --tb=short --basetemp=.pytest_tmp
.\.venv\Scripts\python.exe -m pytest --collect-only -q --basetemp=.pytest_tmp
```
