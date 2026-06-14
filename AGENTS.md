# AGENTS.md - MedImage Agent Agent Guide

This guide is the authoritative repository operating contract for Codex,
Claude Code, Reasonix, and other coding agents working in this repository.
Keep changes focused, reproducible, and safe for a research engineering
platform.

## Project Boundary

MedImage Agent is a deterministic Plan-then-Execute platform for rs-fMRI
research workflows. The LLM plans and advises; execution must remain inside
the Pipeline Runtime and registered node runners. This is not a clinical
diagnosis or clinical decision product.

External data execution is off by default. No new external execution path may
be introduced without explicit maintainer approval, approval/audit wiring,
safe path handling, and tests.

## Source of Truth

When documents, task handoffs, and code disagree, use this priority order:

1. Current executable code and tests
2. `AGENTS.md` stable rules
3. `PROJECT_STATE.md` current state
4. Architecture documentation
5. Release notes for their tagged historical version
6. Task handoff documents

Historical task files and Completion Reports must never override current code
facts. If code and documentation conflict, follow current code and tests, then
report the conflict and correction.

## Required Workflow

1. Read `AGENTS.md` and any tool-specific guide such as `CLAUDE.md` before
   making changes.
2. Read the current contents of every target file before editing it.
3. For focused handoff tasks, inspect only the files and anchors needed for the
   task.
4. Keep each change scoped to one delivery goal.
5. Report modified files, tests run, results, excluded artifacts, and remaining
   risks.

## Backend Architecture Rules

### Layering

Server-side work must preserve this layering:

```text
Route
-> Request/Response Schema
-> Service
-> Runtime / Runner
-> State or Artifact Storage
```

Prohibited:
- Implementing complex business logic in routes.
- Executing external tools directly in routes.
- Hand-parsing large `dict[str, Any]` payloads when a schema belongs in
  `schemas/`.
- Coupling new read-side endpoints to the global `mock_store`; prefer
  `FastAPI Depends()` and the `ProjectStore` Protocol from
  `api/dependencies.py`.
- Stacking new domain endpoints into a single monolithic router.

### Middleware

The middleware stack is fixed unless a change is explicitly justified:

| Order (innermost first) | Middleware | Purpose |
| --- | --- | --- |
| 1 | `APIVersionMiddleware` | `/api/v1/` -> `/api/` path rewrite |
| 2 | `RateLimitMiddleware` | request rate limiting |
| 3 | `RequestIDMiddleware` | `X-Request-ID` injection |
| 4 | `RequestLoggingMiddleware` | structured request log + response time |
| 5 | `CORSMiddleware` | local frontend origins |

Middleware is registered in `main.py:create_app()` with
`app.add_middleware()`. Starlette stack semantics apply: the first registered
middleware is outermost on the response path, and the last is outermost on the
request path.

### Exception Handling

- Route-level catch-all exceptions must use `raise_api_error(exc)` from
  `api/_errors.py`.
- Use the appropriate `MedImageError` subclass:
  - `ConfigError` for configuration or project-config failures
  - `PipelineError` for general pipeline or execution failures
  - `StateStoreError` for state store or database operation failures
  - `SafetyError` for safety-policy rejections
  - `NotFoundError` for missing resources
- Explicit `HTTPException` and `MedImageError` subclasses pass through
  `raise_api_error` unchanged.
- The global exception handler in `api/middleware/error_handler.py` converts
  otherwise unhandled exceptions into structured 500 responses.

### Route Ownership

- `api/routes.py` holds only `/health`, `/api/project-config`, and the
  `_load_project_config` helper. No new endpoints may be added here.
- Domain endpoints belong in domain `_routes.py` modules under `api/`.
  Every new endpoint must be assigned to a clear domain router.
- All routers must be registered in `main.py:create_app()` via
  `app.include_router()`.
- `dashboard_routes.py` is legacy aggregation/read-model and conversion
  workflow surface. Do not add new unrelated domain execution endpoints there;
  split new domains into their own router.
- Route and plugin files must import only what their endpoints or nodes use.

### Node Registry

- New pipeline nodes are registered in the appropriate module under
  `runtime/node_registry_plugins/`: `core_nodes`, `dpabi_nodes`, `gpu_nodes`,
  `spm_nodes`, `qc_nodes`, `rsfmri_nodes`, or `report_nodes`.
- Each plugin exposes a `REGISTRY` dict mapping stable `node_id` strings to
  callables.
- `node_id` strings are immutable once established.
- `create.py` merges plugin registries; duplicate IDs must raise `ValueError`.
- `node_registry.py` is the compatibility shim exporting `NODE_REGISTRY` and
  `get_node_runner()`. Do not add new nodes directly to the shim.
- New executable nodes must be represented in the Tool Catalog, Approval Gate,
  and safe allowlist as appropriate.

### State, Configuration, and DI

- Runtime state files must be written with `atomic_write_json()` from
  `runtime/atomic_file.py`.
- State files carry a `_schema_version` field.
- Do not use `Path.write_text(json.dumps(...))` directly for state paths.
- Backend configuration is loaded through `ConfigService` in `core/config.py`.
- Environment variables use the `MEDIMAGE_` prefix.
- `get_backend_settings()` is the legacy accessor and must remain available.
- Write-side tests should isolate stores with `monkeypatch`, dependency
  overrides, or `SQLiteDesktopStore(tmp_path)`, never the persistent desktop
  database.

## Frontend Architecture Rules

- Frontend code communicates with the backend only through HTTP APIs and the
  approved Electron bridge; it must not access the filesystem directly.
- Domain API wrappers live under `src/frontend/src/lib/api/` and use the
  shared client in `client.ts`. All HTTP requests must go through this client.
- Do not recreate or add to the removed root-level frontend API module.
- Frontend TypeScript types belong in `types/` or `types.ts`, not scattered
  across component files.
- Workflow state should be derived through project workflow models and hooks in
  `state/`, not duplicated ad hoc in UI components.
- Feature flags control visibility only; backend safety gates remain
  authoritative.
- UI must not infer execution success without backend status.
- Technical details should default to a collapsed or secondary view.
- Do not keep adding large independent business modules directly to `App.tsx`.
  New feature areas belong in `features/`.

## Safety Rules

禁止事项: the following boundaries are mandatory for all agents.

- Do not modify `data/`, `rawdata/`, or user DICOM/BIDS/NIfTI data.
- Do not bypass the Approval Gate.
- Do not modify `pipeline_executor.py`, node runner execution logic, DICOM
  conversion execution logic, Approval Gate code, or preprocessing algorithms
  unless the task explicitly requires it.
- Do not introduce an open-ended LLM autonomous execution loop.
- Do not hardcode API keys, credentials, private absolute paths, or
  experimental data paths.
- Do not change API request/response contracts as part of cleanup.
- MATLAB/SPM/DPABI/GPU and DICOM conversion execution must remain explicit,
  audited, env-gated, and off by default unless the task is specifically about
  enabling a reviewed execution path.

## Documentation Lifecycle

- `AGENTS.md` defines stable repository rules. Define each rule in one
  authoritative location and reference it elsewhere; never duplicate rules
  across multiple long-term documents.
- `CLAUDE.md` is a thin Claude Code entry point and must not duplicate this
  guide.
- `PROJECT_STATE.md` records current state, current limitations, validation
  baseline, packaging state, and next work. It is not a running development
  diary. Do not append daily logs, per-phase completion reports, or detailed
  commit histories to it.
- `README.md` and `README_CN.md` are user/new-developer entry points.
- `docs/architecture.md` describes current architecture only. Do not put phase
  progress, test counts, roadmaps, or completion reports there.
- `docs/releases/` preserves historical release notes for real tags. Do not
  rewrite old release notes with main-branch current state except to fix
  misleading facts or broken links. When reading old release notes, treat them
  as historical artifacts tied to their tag.
- `docs/tasks/` is temporary agent handoff space. Plan documents have a
  completion lifecycle: when a task or phase is complete, migrate any durable
  information to the correct long-term document, then delete the task handoff.
  Completed tasks must not accumulate indefinitely.
- Completion Reports belong in final replies, commit messages, or tag
  annotations — not in new long-term Markdown files for routine work.
- Do not create per-fix, per-sprint, or per-phase "completion report" files
  that duplicate what release notes or commit history already record.
- Each rule must be defined in exactly one authoritative location.

## Git and Artifact Rules

- Do not run `git add .`.
- Stage explicit paths only, and never stage runtime artifacts.
- Do not commit, push, tag, create GitHub releases, or upload artifacts unless
  explicitly requested.
- Prohibited from staging or committing:
  - `outputs/`, `work/`, `logs/`, `reports/`, `memory/`
  - `.pytest_cache/`, `.pytest_tmp*/`, `__pycache__/`
  - `docs/tasks/`, `docs/DEV_LOG/`
  - SQLite runtime databases (`*.db`, `*.sqlite`, `*.sqlite3`)
  - generated reviewed pipelines, audit packages, reports, or exports
  - frontend build output and coverage (`src/frontend/dist/`,
    `src/frontend/coverage/`)
  - PyInstaller `_MEI*` directories
  - local EXE/build output unless an explicit release artifact process says so
  - user data or converted outputs
  - local absolute paths or local agent settings
- Generated artifacts that must never be committed include: build output,
  runtime output, temporary reports, local SQLite, test cache, PyInstaller
  temp directories, user data, converted outputs, and local absolute paths.

## Version Governance

- The single authoritative version is `APP_VERSION` in
  `src/backend/app/version.py`.
- `src/frontend/package.json`, `desktop/electron/package.json`, `README.md`,
  `README_CN.md`, `PROJECT_STATE.md`, and current release notes must reference
  the same version line. No long-term document may maintain its own independent
  version string.
- When bumping the version, update `version.py` first, then propagate to all
  referencing locations.
- Historical release notes tie to their specific tag and must not be rewritten
  with the current main-branch version.

## Test Baseline Governance

- `AGENTS.md` specifies the test commands and categories to run, not exact
  passing counts.
- Exact passing counts, date, and environment belong in `PROJECT_STATE.md` or
  the current validation record, not in stable rule documents.
- Do not hardcode test pass counts in `AGENTS.md`. These change frequently and
  create false sources of truth.

## Validation

Use the restored mamba validation interpreter for backend tests:

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest --tb=short
```

For cleanup and documentation work, run at least collection plus relevant
focused tests:

```powershell
D:\Anaconda3\envs\mamba\python.exe -m pytest --collect-only -q --basetemp=.pytest_tmp
```

If full pytest hits Windows temp permission errors, retry with
`--basetemp=.pytest_tmp`. If stale desktop SQLite records point at locked temp
directories, report the issue; the ignored desktop store can be regenerated.

When frontend source or frontend configuration changes, run:

```powershell
cmd /c npm --prefix src/frontend run typecheck
cmd /c npm --prefix src/frontend run test
cmd /c npm --prefix src/frontend run build
```

## Completion Report

Every completed task must report:

- Git status classification: delivery files, excluded artifacts, and files
  requiring manual follow-up.
- Modified, created, restored, or deleted files.
- Exact validation commands and pass/fail results.
- Remaining risks and recommended next work.
