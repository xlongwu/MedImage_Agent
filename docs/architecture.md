# MedImage Agent Architecture

This document describes the current architecture. It is not a roadmap,
completion report, or test baseline.

## 1. System Overview

```text
Frontend (React + TypeScript + Vite)
    -> HTTP API / Electron bridge
API Layer (FastAPI + Pydantic)
    -> Request/response schemas
    -> Services and read models
Agent Runtime (Plan-then-Execute + Approval Gate)
    -> Pipeline Runtime (DAG executor + scheduler)
    -> Plugin Node Registry
    -> Tool Catalog
Storage (SQLite project store + atomic JSON state/artifacts)
```

The LLM is advisory. Pipeline execution is deterministic and must flow through
the Pipeline Runtime and registered node runners.

## 2. Frontend

Location: `src/frontend/src/`

Primary responsibilities:

- Project selection and workflow navigation.
- Plan review, run history, artifact preview, QC/readiness panels, DICOM review,
  and preprocessing workspace UI.
- Frontend-only visibility controls for feature-flagged panels.

Current structure:

| Path | Responsibility |
| --- | --- |
| `App.tsx` | top-level app composition |
| `features/` | feature-level UI areas such as dashboard composition |
| `components/` | reusable and domain-specific panels |
| `hooks/` | shared React hooks |
| `lib/api/client.ts` | shared HTTP client and base URL resolution |
| `lib/api/*.ts` | domain API modules |
| `lib/api/legacy_re_exports.ts` | compatibility export surface |
| `state/` | workflow state models |
| `types.ts`, `types/` | frontend type definitions |

Rules:

- Frontend code must call backend HTTP APIs through `src/frontend/src/lib/api/`.
- The removed root-level frontend API module must not be recreated.
- The UI must not directly access local files.
- Feature flags control visibility only; backend gates remain authoritative.

## 3. API Layer

Location: `src/backend/app/api/`

`main.py:create_app()` registers middleware and includes domain routers.

### Middleware

Registered order in `create_app()`:

1. `CORSMiddleware`
2. `RequestLoggingMiddleware`
3. `RequestIDMiddleware`
4. `RateLimitMiddleware`
5. `APIVersionMiddleware`

Starlette executes the last registered middleware first on the request path, so
`APIVersionMiddleware` handles inbound `/api/v1/` rewrites before inner route
handling.

### Router Ownership

`api/routes.py` is limited to:

- `GET /health`
- `GET /api/project-config`
- `_load_project_config()`

Domain routers include advisor, agent, artifact, approval/audit,
dashboard/conversion workflow, desktop, DPABI, execute-reviewed, experiment,
external smoke, GPU, GUI agent, LLM planner, pipeline, planner, plan validator,
preset, project, project history, realdata, rs-fMRI, session, and tool catalog.

`dashboard_routes.py` remains a large legacy aggregation and conversion
workflow surface. New unrelated execution domains should be split into new
domain routers rather than added there.

### Error Handling

Routes should raise structured errors through `raise_api_error()` and the
`MedImageError` hierarchy. The global error middleware converts unhandled
exceptions into structured 500 responses.

## 4. Schemas

Location: `src/backend/app/schemas/`

Schemas define stable request/response contracts and pure validation helpers.
They should not perform filesystem writes, launch subprocesses, or import the
Pipeline Runtime for side effects.

Major schema areas include pipeline definitions, execution state and manifests,
DICOM conversion safety/readiness/approval, preprocessing execution, GUI agent
contracts, and advisor models.

## 5. Services

Location: `src/backend/app/services/`

Services contain business logic, read models, persistence helpers, readiness
evaluations, and controlled wrappers around domain operations. Routes should
delegate non-trivial work to services.

Important service areas:

- Project and desktop store access.
- Data readiness, BIDS validation, DICOM detection, conversion planning,
  conversion safety/readiness/review package services.
- Preprocessing dry-runs, sandbox execution coordination, output registration,
  validation, and report generation.
- Run artifact discovery/preview, run event/log reading, run summaries, and run
  state timeline read models.
- QC dashboard reports and cache fingerprinting.

## 6. Agent Runtime

Location: `src/backend/app/runtime/agent_runtime.py`

The Agent Runtime creates plans and invokes reviewed execution. It must not
become an open-ended autonomous control loop. Execution remains gated by the
Approval Gate and Tool Catalog.

## 7. Pipeline Runtime

Location: `src/backend/app/runtime/pipeline_executor.py`

Responsibilities:

- Validate DAG dependency order.
- Execute registered nodes through node runners.
- Schedule project-level and subject-level work.
- Persist run/node state and summaries.
- Keep execution deterministic and auditable.

Cleanup, documentation, and route refactors must not change Pipeline Runtime
semantics unless explicitly authorized.

## 8. Node Registry

Locations:

- `src/backend/app/runtime/node_registry.py`
- `src/backend/app/runtime/node_registry_plugins/`

`node_registry.py` is a compatibility shim. Actual node registrations live in
plugin modules:

- `core_nodes.py`
- `dpabi_nodes.py`
- `gpu_nodes.py`
- `spm_nodes.py`
- `qc_nodes.py`
- `rsfmri_nodes.py`
- `report_nodes.py`

`create.py` merges plugin `REGISTRY` dicts and duplicate IDs must fail. New
nodes belong in the proper plugin, must keep stable `node_id` strings, and
must be covered by Tool Catalog and safety allowlist rules when executable.

## 9. Tool Catalog and Approval Gate

Locations:

- `src/backend/app/runtime/tool_registry.py`
- `src/backend/app/runtime/tool_catalog.py`
- approval/audit routes and planner modules

The Tool Catalog describes permissions such as read-only status, file writes,
destructive behavior, confirmation requirements, and path scopes. File-writing
and execution actions must preserve explicit approval/audit paths.

## 10. Storage

Storage is local and project-scoped:

- SQLite desktop/project store for project metadata and run links.
- JSON run state, node state, summaries, manifests, and audit artifacts.
- Runtime outputs under ignored work/output roots.

State JSON must use `atomic_write_json()` and carry `_schema_version`.
Rawdata is read-only.

## 11. Desktop Packaging Boundary

Locations:

- `desktop/electron/`
- `desktop/packaging/`

The desktop app uses Electron as the shell and a PyInstaller backend sidecar.
The frontend uses HTTP APIs and the approved Electron bridge. Offline Electron
runtime zips and NSIS caches are local build resources and should not be
deleted during cleanup.

Generated packaging output such as unpacked app directories, installers,
portable EXEs, and PyInstaller `_MEI*` temp directories are runtime/build
artifacts unless explicitly promoted by a release artifact process.

## 12. Safety Boundary

Core invariants:

- No rawdata modification.
- No Approval Gate bypass.
- No direct frontend filesystem access.
- No hidden external-tool execution.
- No hardcoded secrets or private data paths.
- Research use only.

Detailed agent rules live in `AGENTS.md`; this document references those rules
instead of duplicating them.
