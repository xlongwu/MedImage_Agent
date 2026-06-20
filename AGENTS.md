# AGENTS.md — MedImage Agent Repository Operating Contract

This file is the authoritative repository operating contract for Codex, Claude
Code, Reasonix, and other coding agents working in this repository.

Its purpose is to keep development safe, scientifically valid, reproducible,
and efficient without forcing every task into the same narrow workflow.

---

## 1. Project Boundary

MedImage Agent is a deterministic Plan-then-Execute platform for rs-fMRI
research workflows.

The LLM may plan, explain, validate, and propose actions. Actual execution must
remain inside the Pipeline Runtime and registered node runners.

This project is:

* a research engineering platform;
* a deterministic workflow system;
* a non-clinical research tool.

This project is not:

* a clinical diagnosis product;
* a clinical decision-support product;
* an unrestricted autonomous agent;
* a general-purpose external command executor.

External data execution is disabled by default.

No new external execution path may be introduced without:

* explicit task scope;
* maintainer approval;
* Approval Gate integration;
* audit logging;
* safe path handling;
* environment gating;
* failure handling;
* tests.

---

## 2. Authority and Sources of Truth

Different sources are authoritative for different questions.

### 2.1 Repository policy

`AGENTS.md` is authoritative for:

* safety invariants;
* architecture boundaries;
* task execution rules;
* scientific computing requirements;
* validation requirements;
* Git and artifact rules.

A task handoff may narrow these rules but must not weaken them.

### 2.2 Current behavior

Current executable code and tests are authoritative evidence of what the
repository currently does.

Current code and tests are not automatic proof that:

* the behavior is scientifically correct;
* the public documentation is accurate;
* a numerical implementation is validated;
* an implementation satisfies the current task.

When code behavior conflicts with a scientific or safety invariant, report the
conflict and correct it within the approved task scope.

### 2.3 Task scope

The approved task handoff, issue, plan, or direct maintainer instruction is
authoritative for:

* the delivery goal;
* task mode;
* allowed files;
* non-goals;
* acceptance criteria;
* validation commands;
* stop conditions.

### 2.4 Current project status

`PROJECT_STATE.md` records the latest verified project state, limitations,
packaging status, and next work.

Treat it as a maintained snapshot, not as stronger evidence than current code,
tests, CI, or inspected artifacts.

### 2.5 Architecture and historical documents

* `docs/architecture.md` describes current architecture.
* `README.md` and `README_CN.md` are user and developer entry points.
* `docs/releases/` contains historical records tied to specific versions.
* Historical task documents and Completion Reports must not override current
  code or current repository policy.

When sources disagree, report:

1. what the repository currently does;
2. what the governing rule or task requires;
3. what must be corrected.

---

## 3. Task Modes

Every implementation task must use one of the following modes.

The task handoff should declare the mode explicitly. If it does not, the
implementing agent must infer the narrowest mode that can fully deliver the
requested outcome and state that mode in the Completion Report.

### 3.1 Focused Fix Mode

Use for:

* isolated bug fixes;
* one-file or small-surface corrections;
* test collection fixes;
* narrow API corrections;
* documentation-only corrections.

Rules:

* inspect only listed files, read-only files, and required anchors;
* do not perform broad repository exploration;
* do not edit unlisted files (see §4.4 for unlisted-file escalation rules);
* preserve existing public behavior unless the task explicitly changes it;
* run focused regression tests.

### 3.2 Feature Bundle Mode

Use for a complete user-visible or developer-visible feature.

A feature bundle may span:

* frontend;
* API schemas;
* routes;
* services;
* runtime;
* storage;
* tests;
* documentation.

Rules:

* inspect the complete feature call chain;
* do not implement only the visible UI or only the API surface;
* include success, failure, empty, disabled, and unsafe states;
* keep the task centered on one complete delivery goal;
* edit only files required by the end-to-end feature;
* report any additional files discovered beyond the original estimate.

### 3.3 Architecture and Refactor Mode

Use for:

* splitting monolithic modules;
* dependency inversion;
* router decomposition;
* state-management restructuring;
* frontend controller extraction;
* shared service extraction.

Rules:

* targeted repository-wide search is allowed;
* exploration must have a stated architectural purpose;
* characterize current behavior before moving code;
* preserve API and execution semantics unless explicitly changed;
* do not combine unrelated product features with the refactor;
* add regression tests before or with structural changes;
* record compatibility and migration risks.

### 3.4 Scientific Validation Mode

Use for:

* ALFF or fALFF;
* ReHo;
* functional connectivity;
* filtering;
* nuisance regression;
* atlas extraction;
* numerical backend changes;
* CPU/GPU equivalence;
* scientific artifact generation.

Rules:

* inspect the complete path from request to persisted artifact;
* inspect existing numerical kernels before adding new computation;
* verify algorithm definition, parameters, artifact contents, state semantics,
  and tests;
* compare against an independent reference where feasible;
* do not declare an algorithm validated based only on route or service tests;
* apply all rules in the Scientific Computing Contract.

### 3.5 Release and Packaging Mode

Use for:

* version bumps;
* dependency updates;
* CI changes;
* PyInstaller sidecar builds;
* Electron packaging;
* installers;
* release candidates;
* release documentation.

Rules:

* inspect version sources, manifests, lockfiles, CI, packaging configuration,
  and release documentation together;
* do not claim GUI validation when only a headless build was tested;
* distinguish build success, launch success, smoke success, and user workflow
  success;
* record platform and toolchain versions;
* do not publish, tag, or upload artifacts unless explicitly requested.

---

## 4. Agent Roles and Change Ownership

The following role division is recommended:

* Planner or Scout: Reasonix, web-based GPT, or another analysis agent.
* Implementer: Codex or one designated coding agent.
* Reviewer: Claude Code or another independent reviewer.

Roles may be performed by different tools, but ownership rules remain fixed.

### 4.1 Single-owner rule

Use:

```text
One task
→ one owner agent
→ one branch or worktree
→ one coherent diff
```

Do not allow multiple coding agents to edit the same task branch concurrently.

The reviewer should review after the implementation diff exists. The reviewer
must not silently become a second parallel implementer.

### 4.2 Handoff readiness

For task documents intended for Codex, check the task `Status` before doing any
work.

Accepted implementation-ready statuses include:

* `Ready for Codex`;
* `Ready for Implementation`.

If the task status is not implementation-ready, stop and report it.

### 4.3 Required handoff fields

A complete implementation handoff should define:

* Status;
* Task Mode;
* Goal;
* Background;
* Current Behavior;
* Required Behavior;
* Non-goals;
* Files to Edit;
* Files to Read Only;
* Exact Anchors;
* Allowed Commands;
* Validation Commands;
* Acceptance Criteria;
* Safety Invariants;
* Stop Conditions;
* Completion Report Format.

### 4.4 Unlisted-file escalation

In Focused Fix Mode:

* never edit an unlisted file;
* report the required file and stop.

In Feature Bundle, Architecture, Scientific Validation, or Release Mode:

* additional files may be inspected when required by the call chain;
* additional files may be edited only when necessary for the declared goal;
* every added file must be explained in the Completion Report;
* explicit task prohibitions still take precedence.

---

## 5. Required Workflow

Before editing:

1. Read `AGENTS.md`.
2. Read any tool-specific entry guide such as `CLAUDE.md`.
3. Read the approved task handoff.
4. Check task status and task mode.
5. Read every target file before modifying it.
6. Verify required anchors, symbols, paths, and assumptions.
7. Inspect existing tests for the affected behavior.
8. Inspect existing implementations before adding a duplicate path.

During implementation:

1. Keep one coherent delivery goal.
2. Preserve safety and architecture invariants.
3. Follow the rules for the selected task mode.
4. Avoid unrelated cleanup.
5. Do not hide incomplete behavior behind successful status values.
6. Do not weaken tests to make a change pass.
7. Do not silently skip unavailable validation.

After implementation:

1. Run the required validation matrix.
2. Inspect `git status`.
3. Classify delivery files and excluded artifacts.
4. Confirm that generated outputs and user data are not staged.
5. Produce the required Completion Report.

---

## 6. Backend Architecture Rules

### 6.1 Required layering

Server-side work must preserve this layering:

```text
Route
→ Request/Response Schema
→ Service
→ Runtime / Runner or Scientific Kernel
→ State and Artifact Storage
```

Responsibilities:

* Routes handle HTTP concerns and dependency injection.
* Schemas validate structured request and response contracts.
* Services coordinate domain workflows.
* Runtime and runners execute reviewed operations.
* Scientific kernels perform numerical computation.
* Storage persists state, provenance, and artifacts.

Prohibited / 禁止:

* complex business logic in routes;
* numerical algorithms in routes;
* direct external-tool execution in routes;
* large hand-parsed `dict[str, Any]` payloads when a schema is appropriate;
* new read-side endpoints coupled directly to the global `mock_store`;
* new unrelated endpoints added to monolithic legacy routers;
* services that duplicate existing scientific kernels;
* successful API responses for artifacts that were not actually created.

Use `FastAPI Depends()` and the `ProjectStore` Protocol from
`api/dependencies.py` for new dependency-injected endpoints.

### 6.2 Middleware

The middleware stack is fixed unless the task explicitly justifies a change.

| Order, innermost first | Middleware                 | Purpose                              |
| ---------------------- | -------------------------- | ------------------------------------ |
| 1                      | `APIVersionMiddleware`     | `/api/v1/` to `/api/` rewrite        |
| 2                      | `RateLimitMiddleware`      | request rate limiting                |
| 3                      | `RequestIDMiddleware`      | `X-Request-ID` injection             |
| 4                      | `RequestLoggingMiddleware` | structured logging and response time |
| 5                      | `CORSMiddleware`           | approved local frontend origins      |

Middleware is registered in `main.py:create_app()` using
`app.add_middleware()`.

Account for Starlette middleware ordering semantics when changing or testing
middleware.

### 6.3 Exception handling

Route-level catch-all exception handling must use `raise_api_error(exc)` from
`api/_errors.py`.

Use the appropriate `MedImageError` subclass:

* `ConfigError` for configuration failures;
* `PipelineError` for pipeline or execution failures;
* `StateStoreError` for state or database failures;
* `SafetyError` for safety-policy rejections;
* `NotFoundError` for missing resources.

Do not replace structured domain errors with generic 500 responses.

### 6.4 Route ownership

* `api/routes.py` remains limited to its small core surface.
* Domain endpoints belong in domain `_routes.py` modules.
* Every new endpoint must have one clear owning domain.
* Routers must be registered in `main.py:create_app()`.
* Do not expand a legacy aggregation router with new unrelated domains.
* When touching a monolithic router in Architecture Mode, prefer extracting one
  complete domain rather than adding another layer of inline logic.
* Route modules must import only what their endpoints use.

### 6.5 Node registry

* New pipeline nodes belong in the appropriate module under
  `runtime/node_registry_plugins/`.
* Each plugin exposes a `REGISTRY` mapping stable `node_id` values to callables.
* Established `node_id` values are immutable.
* Duplicate IDs must raise an error.
* Compatibility shims must not become the primary node-registration surface.
* New executable nodes must be represented in the Tool Catalog, Approval Gate,
  audit path, and safe allowlist where applicable.

### 6.6 State, configuration, and dependency injection

* Runtime JSON state must be written with `atomic_write_json()`.
* Persisted state must include `_schema_version`.
* Do not use `Path.write_text(json.dumps(...))` for managed runtime state.
* Backend configuration is loaded through `ConfigService`.
* Environment variables use the `MEDIMAGE_` prefix.
* Legacy configuration accessors must remain available until explicitly
  migrated.
* Tests must isolate project stores using dependency overrides, `monkeypatch`,
  or temporary `SQLiteDesktopStore` instances.
* Tests must never write to the persistent desktop database.
* Persisted state changes require compatibility consideration and migration
  tests where appropriate.

---

## 7. Frontend Architecture Rules

* Frontend code communicates with the backend only through HTTP APIs and the
  approved Electron bridge.
* Frontend code must not access the filesystem directly.
* Domain API wrappers live under `src/frontend/src/lib/api/`.
* All HTTP requests use the shared API client.
* Do not recreate a root-level monolithic frontend API module.
* Shared TypeScript models belong in the appropriate type modules.
* Workflow state should be derived through domain state models and hooks.
* Do not duplicate backend workflow state independently in multiple
  components.
* Feature flags control visibility only.
* Backend gates remain authoritative for execution and safety.
* UI code must not infer success when the backend has not reported success.
* Technical details should default to a secondary or collapsed view.
* `App.tsx` should remain an application shell and orchestration boundary.
* New business features belong in `features/`.
* New complex workflows should use domain hooks or controllers rather than
  accumulating handlers and state in `App.tsx`.
* A complete feature must represent loading, empty, disabled, success, partial,
  and failure states where applicable.

API contract changes must update:

* backend schema;
* backend tests;
* frontend API wrapper;
* frontend types;
* frontend tests;
* compatibility or migration handling where needed.

Do not change API contracts as incidental cleanup.

---

## 8. Safety Invariants and Protected Changes

### 8.1 Absolute invariants

All agents must obey the following:

* Do not modify user DICOM, BIDS, NIfTI, `rawdata/`, or source research data.
* Do not bypass the Approval Gate.
* Do not introduce unrestricted autonomous execution loops.
* Do not execute unreviewed commands from LLM-generated text.
* Do not hardcode credentials, API keys, private absolute paths, or research
  dataset paths.
* Do not make optional external execution enabled by default.
* Do not weaken safe path validation.
* Do not hide destructive operations behind generic workflow actions.
* Do not make clinical diagnosis or treatment claims.

### 8.2 Protected modules

The following areas are protected, not permanently frozen:

* pipeline executor;
* node runner execution logic;
* Approval Gate;
* DICOM conversion execution;
* preprocessing algorithms;
* artifact registration;
* state migration;
* path and allowlist enforcement.

Protected modules may be modified only when:

1. the task explicitly identifies the behavior or invariant being changed;
2. current behavior is characterized with tests;
3. relevant safety tests are run;
4. backward compatibility is evaluated;
5. changed invariants are listed in the Completion Report;
6. the change does not silently weaken Approval Gate, audit, path, or raw-data
   protections.

Do not work around a core bug by duplicating logic in a route or service merely
to avoid editing a protected module.

### 8.3 External execution

MATLAB, SPM, DPABI, GPU, DICOM conversion, and similar external execution must
remain:

* explicit;
* reviewed;
* audited;
* environment-gated;
* safe-path constrained;
* disabled by default unless a reviewed task enables the path.

---

## 9. Scientific Computing Contract

Scientific correctness is a first-class repository invariant.

A route returning HTTP 200 is not sufficient evidence that a scientific
operation is implemented correctly.

### 9.1 Capability truth levels

Use the following conceptual capability levels consistently in code, status,
documentation, and UI:

| Level           | Meaning                                                                  |
| --------------- | ------------------------------------------------------------------------ |
| `unavailable`   | No executable implementation exists                                      |
| `scaffolded`    | Interface or placeholder exists, but no valid computation is performed   |
| `metadata_only` | Planning or metadata is produced without the declared numerical artifact |
| `computed`      | The declared numerical artifact was created and can be reloaded          |
| `validated`     | The computation passed defined numerical and reference validation        |

Do not report `computed`, `completed`, or `succeeded` when only metadata,
planned paths, shapes, or placeholder files exist.

Do not report `validated` merely because unit tests execute without exceptions.

### 9.2 End-to-end scientific path

A complete scientific feature must cover:

```text
Request Parameters
→ Schema Validation
→ Service Orchestration
→ Scientific Kernel
→ Numerical Artifact
→ Artifact Registration
→ Provenance
→ Workflow Status
→ Reload and Validation Tests
```

Inspect all layers before declaring the feature complete.

### 9.3 Single numerical source of truth

* Numerical algorithms belong in dedicated scientific kernel modules.
* Routes must not implement numerical algorithms.
* Services should orchestrate kernels rather than reimplement them.
* Runtime runners should call shared kernels rather than maintain divergent
  copies.
* Before adding a new implementation, search for an existing kernel.
* When duplicate implementations exist, select one canonical implementation
  and migrate callers through an explicit task.
* Do not silently preserve two implementations with different formulas under
  the same algorithm name.

### 9.4 Artifact integrity

A scientific computation is not complete unless the declared artifact:

* exists;
* contains the numerical result;
* can be reopened;
* has the expected shape and dtype;
* is registered with the project;
* is linked to its inputs and parameters;
* has failure handling for partial writes.

Examples:

* A functional-connectivity operation must persist the actual matrix, not only
  its shape or method name.
* A ReHo operation must persist the resulting map, not only a completion flag.
* An ALFF operation must persist the declared ALFF or fALFF map generated by
  the documented algorithm.
* Preview or sampled outputs must be labeled as preview or sampled outputs and
  must not be presented as full-data results.

Metadata sidecars supplement numerical artifacts. They do not replace them.

### 9.5 Provenance requirements

Scientific artifacts should record, where applicable:

* algorithm ID;
* algorithm version;
* input paths or stable input identifiers;
* input checksum or equivalent provenance identifier;
* subject and session identifiers;
* acquisition parameters;
* TR;
* frequency band;
* atlas;
* mask;
* neighborhood definition;
* nuisance-regression configuration;
* filtering configuration;
* backend;
* precision and dtype;
* random seed;
* package versions;
* parameters;
* warnings;
* output checksum;
* creation timestamp.

Do not encode private machine-specific absolute paths into portable provenance
unless explicitly required for local runtime state.

### 9.6 Numerical validation

New or changed scientific kernels require validation appropriate to the
algorithm.

At minimum, consider:

* synthetic input tests;
* known-shape tests;
* zero and constant-signal tests;
* NaN and infinite-value handling;
* insufficient-timepoint handling;
* mask and atlas mismatch handling;
* deterministic random-seed tests;
* reload tests for persisted artifacts;
* golden fixture comparison;
* independent reference comparison;
* CPU/GPU tolerance comparison when multiple backends exist.

Document numerical tolerances. Do not choose tolerances only to make a failing
test pass.

### 9.7 CPU and GPU behavior

When multiple backends exist:

* backend selection must be explicit;
* CPU must remain available unless the feature is explicitly GPU-only;
* GPU fallback behavior must be defined;
* backend-specific precision differences must be tested;
* scaffold-only GPU paths must not be described as GPU implementations;
* tests must verify that the intended backend was actually used where
  observable.

### 9.8 Simplified and partial algorithms

If an implementation is scientifically simplified:

* label it clearly;
* describe the simplification;
* do not use the full canonical algorithm name without qualification;
* expose limitations in status and documentation;
* do not silently upgrade a preview implementation to production status.

If only a subset of subjects, voxels, timepoints, or files is processed:

* make the subset rule explicit;
* record it in provenance;
* return a partial or preview status;
* do not claim full-dataset completion.

---

## 10. Dependency and Reproducibility Rules

* Do not introduce `"latest"` dependency versions.
* Frontend manifest and lockfile changes must be committed together when
  dependency changes are approved.
* Backend dependency bounds must be intentional and documented.
* Do not remove a dependency only because it appears unused without checking
  optional execution paths and packaging.
* Optional heavy dependencies must remain optional unless the task explicitly
  changes installation requirements.
* Do not hardcode a maintainer's local Python, Node, Conda, MATLAB, or CUDA
  path in stable repository documentation.
* Use the active environment interpreter unless the task supplies an explicit
  environment.
* Record exact toolchain versions in release or packaging validation records,
  not in permanent generic commands.
* Randomized scientific operations must accept or record a deterministic seed.
* A release build must be reproducible from committed manifests, lockfiles, and
  documented prerequisites.

---

## 11. Documentation and Task Lifecycle

### 11.1 Stable documents

* `AGENTS.md` defines stable repository policy.
* `CLAUDE.md` is a thin tool-specific entry point and must not duplicate this
  file.
* `PROJECT_STATE.md` records current verified state, limitations, validation
  environment, packaging status, and next work.
* `docs/architecture.md` describes current architecture.
* `README.md` and `README_CN.md` are user and developer entry points.
* `docs/releases/` contains version-specific historical records.

Define each durable rule in one authoritative location.

### 11.2 PROJECT_STATE

`PROJECT_STATE.md` is not a development diary.

Do not append:

* daily logs;
* every commit;
* every task completion report;
* long implementation narratives.

Validation counts in `PROJECT_STATE.md` are informational snapshots.

CI and current validation output remain authoritative for the latest result.

### 11.3 Task handoffs

Local temporary handoffs may live under `docs/tasks/`.

Do not assume an ignored local task file will be available:

* in another branch;
* in another worktree;
* on another machine;
* to another agent.

For cross-agent or cross-machine handoff, use one of:

* a GitHub issue;
* a pull request description;
* an explicitly approved, versioned plan file;
* a task file explicitly included in the task's delivery files.

Temporary task files should be removed after completion once durable
information has been migrated.

Completed task files must not accumulate indefinitely.

### 11.4 Completion reports

Routine Completion Reports belong in:

* the final agent response;
* the pull request description;
* a commit message when appropriate;
* a release record for release work.

Phase-level or milestone-level completion reports may be retained as
historical records under `specs/completion/` when they:

* document a completed phase's architecture decisions and outcomes;
* serve as a historical reference for future developers;
* are explicitly designated as deliverables.

Do not create a per-fix or per-sprint Markdown report for routine work
that duplicates commit history.

---

## 12. Git and Artifact Rules

### 12.1 Git operations

* Do not run `git add .`.
* Stage explicit paths only.
* Do not commit, push, tag, merge, create releases, or upload artifacts unless
  explicitly requested.
* Do not modify unrelated user changes.
* Do not use destructive Git commands to clean a working tree without explicit
  approval.
* Inspect `git status --short` before and after implementation.

### 12.2 Tracked resources versus runtime artifacts

Do not assume that an entire directory is disposable because its name resembles
runtime output.

Before deleting, restoring, ignoring, or excluding a path:

1. check whether the path is tracked;
2. inspect its repository purpose;
3. identify whether it is source, fixture, configuration, or runtime output.

Existing tracked resources under directories such as `memory/` must be
preserved unless the task explicitly migrates or removes them.

For example, a tracked knowledge-base or test resource is not equivalent to
untracked runtime memory.

Do not apply blanket cleanup rules that delete tracked source assets.

### 12.3 Generated artifacts that must not be committed

Unless an explicit release or fixture task says otherwise, do not commit:

* runtime outputs;
* converted user data;
* DICOM, BIDS, or NIfTI user datasets;
* temporary work directories;
* local logs;
* generated reports;
* generated audit packages;
* local SQLite databases;
* test caches;
* Python bytecode;
* frontend build output;
* coverage output;
* PyInstaller temporary directories;
* local installer output;
* local absolute paths;
* local agent settings;
* secrets;
* private environment files.

Common examples include:

```text
outputs/
work/
logs/
reports/
.pytest_cache/
.pytest_tmp*/
__pycache__/
src/frontend/dist/
src/frontend/coverage/
*.db
*.sqlite
*.sqlite3
_MEI*/
```

Do not blanket-ignore or blanket-delete a directory that also contains tracked
fixtures or source resources.

---

## 13. Version Governance

The authoritative application version is:

```text
APP_VERSION in src/backend/app/version.py
```

When changing the version:

1. update `APP_VERSION`;
2. update frontend package metadata;
3. update Electron package metadata;
4. update current user-facing version references;
5. update current release documentation;
6. verify all version surfaces agree.

Do not maintain independent long-term version strings.

Historical release notes remain tied to their tags and must not be rewritten
with the current main-branch version.

A version bump must be an explicit release task, not incidental cleanup.

---

## 14. Validation Policy

### 14.1 Validation authority

CI is the authoritative continuous validation source.

Local validation remains required before handoff but must not be presented as
equivalent to:

* another operating system;
* a packaged desktop launch;
* external MATLAB/SPM execution;
* GPU execution;
* full real-data validation.

Exact pass counts must not be hardcoded in `AGENTS.md`.

### 14.2 Interpreter selection

Use the active environment's interpreter:

```text
python
```

A task may provide an explicit interpreter or environment command.

Do not place a maintainer-specific absolute interpreter path in this stable
guide.

### 14.3 Backend commands

Collection:

```bash
python -m pytest --collect-only -q --basetemp=.pytest_tmp
```

Focused tests:

```bash
python -m pytest <focused-test-paths> --tb=short --basetemp=.pytest_tmp
```

Full backend suite:

```bash
python -m pytest --tb=short --basetemp=.pytest_tmp
```

If the current environment requires a different launcher, preserve the command
semantics and report the exact command used.

### 14.4 Frontend commands

When frontend source or configuration changes, run:

```bash
npm --prefix src/frontend run typecheck
npm --prefix src/frontend run test
npm --prefix src/frontend run build
```

Do not claim lint or formatting validation unless the configured toolchain was
actually installed and executed.

### 14.5 Validation matrix

#### Documentation-only task

Required:

* inspect referenced paths and commands;
* verify internal consistency;
* report that executable tests were not required, when applicable.

#### Focused Fix Mode

Required:

* collection when collection behavior may be affected;
* focused regression tests;
* broader tests when shared infrastructure is changed.

#### Feature Bundle Mode

Required:

* backend focused tests;
* frontend tests when UI or client code changes;
* API contract tests;
* success and failure-path tests;
* end-to-end state transition tests where feasible.

#### Architecture and Refactor Mode

Required:

* characterization tests;
* focused regression tests;
* full affected-layer suite;
* full backend or frontend suite when shared infrastructure changes;
* API compatibility verification.

#### Scientific Validation Mode

Required:

* kernel unit tests;
* artifact persistence and reload tests;
* provenance tests;
* edge-case tests;
* golden or reference tests;
* backend equivalence tests where applicable;
* workflow status truthfulness tests.

#### Release and Packaging Mode

Required as applicable:

* backend suite;
* frontend typecheck;
* frontend tests;
* frontend build;
* sidecar build;
* launcher smoke;
* Electron unpacked build;
* packaged launch smoke;
* version consistency check;
* artifact inventory.

A successful build must not be reported as a successful GUI workflow test.

### 14.6 Validation failures

Never hide a failed validation command.

Report:

* the exact command;
* whether failure is caused by the change;
* whether it is environmental;
* whether it is pre-existing;
* any unvalidated area.

Do not skip, delete, weaken, or mark tests as expected failures solely to obtain
a passing result.

---

## 15. Completion Report

Every completed implementation task must include the following sections.

### Task

* Task mode;
* delivery goal;
* branch or worktree when relevant.

### Files changed

Classify every changed file as:

* modified;
* created;
* restored;
* deleted.

Explain why each file changed.

### Behavior delivered

Describe:

* previous behavior;
* new behavior;
* relevant failure behavior;
* compatibility impact.

### API and schema impact

State explicitly:

* no API or schema change; or
* exact request, response, state, artifact, or migration changes.

### Scientific impact

For scientific work, state:

* canonical kernel used;
* formula or algorithm implemented;
* artifact written;
* provenance recorded;
* validation reference;
* tolerance;
* capability truth level achieved.

### Validation

List:

* exact commands;
* pass, fail, or skipped result;
* environment limitations;
* unvalidated execution paths.

### Git and artifact classification

List:

* delivery files;
* excluded runtime artifacts;
* tracked resources preserved;
* files requiring manual follow-up.

### Remaining risks

List:

* known limitations;
* compatibility risks;
* scientific validation gaps;
* packaging gaps;
* recommended next work.

Do not claim completion when acceptance criteria or required validation remain
unmet.

---

## 16. Compliance and Enforcement

### 16.1 Automated enforcement

The following critical rules are enforced by CI and pre-commit hooks:

| Rule | Enforcement | Mechanism |
|:--|:--|:--|
| `atomic_write_json()` for runtime state | pre-commit grep | `tests/test_agents_md_compliance.py` |
| No `write_text(json.dumps(...))` in services | pre-commit pygrep | `.pre-commit-config.yaml` |
| No `mock_store` coupling in new endpoints | CI compliance test | `tests/test_agents_md_compliance.py` |
| Version consistency | CI version check | GitHub Actions |
| Scientific artifact integrity | Scientific Validation CI | GitHub Actions |

### 16.2 Known compliance debt

The following gaps are tracked for phased remediation. New code must not
increase these counts.

| Issue | Current scope | Target version |
|:--|:--|:--|
| `write_text` → `atomic_write_json` migration | ~28 service files | v0.7.0 |
| `mock_store` DI migration in execution services | ~37 service files | v0.8.0 |

Compliance debt is reduced incrementally. Each release that touches an affected
file should migrate that file to the compliant pattern.

This section must be updated whenever a new enforcement mechanism is added or
a compliance debt target is met.
