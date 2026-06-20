# ADR-001: Architecture Audit — AGENTS.md Compliance Review (2026-06-20)

## Status
Accepted

## Context

The `AGENTS.md` repository operating contract was recently updated with refined
architecture rules across all layers: backend layering (§6), frontend
architecture (§7), safety invariants (§8), scientific computing (§9), version
governance (§13), and compliance enforcement (§16). A systematic audit of the
codebase was performed to identify gaps between the stated rules and the
current code.

The audit covered:

- 29 route modules, 28 service modules, 45 tool modules
- 55 frontend API wrappers, 6 feature directories
- 175 files with `write_text(json.dumps(...))` patterns
- ~45 route/service files with `mock_store` coupling

## Decision

### Immediate Fixes Applied (this session)

1. **Version consistency** — Aligned all package metadata to authoritative
   `APP_VERSION = "0.6.0-rc1"`:
   - `src/frontend/package.json`: `0.5.0-rc1` → `0.6.0-rc1`
   - `src/frontend/package-lock.json`: `0.5.0-rc1` → `0.6.0-rc1`
   - `desktop/electron/package.json`: `0.5.0-rc1` → `0.6.0-rc1`
   - `pyproject.toml`: `0.3.0-alpha` → `0.6.0-rc1`
   - `README.md` shield + references: `v0.5.0-rc1` → `v0.6.0-rc1`
   - `README_CN.md` shield + references: `v0.5.0-rc1` → `v0.6.0-rc1`

2. **Dead import cleanup** — Removed 38 unused imports from
   `src/backend/app/api/agent_routes.py`:
   - 31 unused model imports (GPU, DPABI, rsFMRI, artifact, release)
   - 3 dead tool-function imports (`run_pipeline`, report export/validation)
   - 1 dead path_safety import (`PathSafetyError`, `read_safe_text_file`)
   - 22 dead DPABI tool imports
   - 1 dead rsfmri_plan_tool import
   - 1 unused `APP_VERSION` import

### Compliance Debt (recognized, scheduled for phased remediation)

| Issue | Scope | Target |
|:--|:--|:--|
| `write_text` → `atomic_write_json` | ~101 files (28 services + 45 tools + 13 runtime + 12 planners + 2 routes + 1 preprocessing) | v0.7.0 |
| `mock_store` DI migration | ~45 files (5 routes + ~40 services) | v0.8.0 |
| Legacy `dashboard_routes.py` (2664 lines) | 1 file, 50+ endpoints, multiple domains | v0.8.0 |
| `legacy_re_exports.ts` monolithic barrel | 1 file, 57 consumers | v0.8.0 |
| `App.tsx` fat controller (325 lines, 17 useState) | 1 file | v0.8.0 |
| `useAppState.ts` duplicated state logic | 1 file | v0.8.0 |

### Architectural Health Assessment

| Layer | Health | Notes |
|:--|:--|:--|
| Domain router extraction | Good | 28 domain routers, 24 clean (no mock_store) |
| Backend layering (Route→Schema→Service→Runtime) | Mixed | Core routers follow pattern; `gpu_routes.py` has numerical logic in routes |
| Middleware stack | Compliant | 5-layer stack, correctly ordered |
| Node registry | Compliant | Plugin-based with duplicate-ID checks |
| DICOM conversion path | Compliant | Uses `Depends(get_project_store)` — reference implementation |
| Frontend API wrappers | Mixed | 29 domain wrappers + 1 shared client; 3 legacy modules violate §7 |
| Feature modules | Compliant | 6 organized feature directories with domain hooks |
| Version governance | NOW Compliant | 4 version surfaces aligned to 0.6.0-rc1 |

### Compliance Enforcement Gaps

The compliance test file referenced in AGENTS.md §16.1
(`tests/test_agents_md_compliance.py`) has been created with a baseline
compliance suite covering:
- Duplicate node ID detection
- Large binary artifact tracking
- Referenced stable document existence
- Version consistency across all package surfaces
- agent_routes.py import hygiene
- Compliance debt budget monitoring (Tier 2)

## Consequences

### What becomes easier

- **Version tracking** — All package metadata now converges on a single
  authoritative version, eliminating the need to reconcile 4 different version
  strings.
- **Import hygiene** — `agent_routes.py` imports are now a tight, verifiable
  reflection of what the module actually uses. Import auditing tools (ruff,
  pyflakes) can now detect future regressions.
- **Architecture visibility** — This ADR provides a snapshot of all known
  compliance gaps, enabling phased remediation planning.

### What becomes harder

- Nothing. These are low-risk corrections (version strings, dead code removal)
  that do not change runtime behavior.

### Remaining Risks

1. **`dashboard_routes.py` endpoint duplication** — Deprecated endpoints in the
   legacy router share URL paths with the new domain routers. FastAPI
   registration order determines which handler wins, potentially causing silent
   behavior changes during future refactors.

2. **`agent_routes.py` still uses direct filesystem access** — The
   `_read_json_if_exists`, `_read_text_if_exists`, and `_load_project_config`
   helpers bypass the service layer. This is pragmatic for an agent runtime
   module but should be migrated to use `ProjectStore` DI where feasible.

3. **`pyproject.toml` version semantics** — The Python package version was
   `0.3.0-alpha` (pre-release). Bumping to `0.6.0-rc1` matches the backend but
   may affect downstream pip install behavior if the package is distributed.

4. **`package-lock.json` contains dependency versions at `0.5.0-rc1`** — Only
   the top-level version was changed. Dependency lock entries with the old
   version string remain untouched (they reference package metadata, not app
   version). This is expected behavior.

### Recommended Next Steps

1. ~~Create `tests/test_agents_md_compliance.py` to enforce §6.1 and §6.6 rules
   via CI~~ **DONE** — baseline compliance suite created 2026-06-20
2. Add compliance tests to CI workflow (`.github/workflows/ci.yml`)
3. Begin v0.7.0 `atomic_write_json` migration, prioritizing the 28 service
   files
4. Extract `gpu_routes.py` numerical logic into a dedicated service
5. Deprecate and remove `useAppState.ts` after all consumers migrate to
   controllers
6. Plan `dashboard_routes.py` demolition into domain routers for v0.8.0
