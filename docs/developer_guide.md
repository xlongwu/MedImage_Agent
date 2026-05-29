# MedImage Agent Developer Guide

## Adding a New Pipeline Stage

1. Create MATLAB wrapper in `matlab/` (if SPM step) or Python module in `src/backend/app/tools/`
2. Create QC module in `src/backend/app/tools/`
3. Create runner orchestration module
4. Register node in `src/backend/app/runtime/node_registry.py`
5. Create pipeline YAML in `examples/`
6. Create CLI runner in `src/backend/app/tools/`
7. Add API endpoints in `src/backend/app/api/routes.py` and model in `models.py`
8. Add frontend panel in `src/frontend/src/components/`
9. Update `App.tsx`, `api.ts`
10. Add unit test in `tests/unit/`
11. Update README.md

## New Planning and Desktop Surfaces

- Planner endpoints live in `src/backend/app/api/planner_routes.py` and keep LLM output advisory until validated by the deterministic runtime.
- GUI Agent endpoints live in `src/backend/app/api/gui_agent_routes.py`; the default provider records mock SPM/DPABI GUI steps only.
- Shared external process metadata should use `ExternalToolRunResult` from `src/backend/app/runtime/external_tool_result.py`.
- Electron development files live under `src/frontend/electron/`; the renderer reads the API base URL from runtime config instead of a hard-coded URL.

## Project Structure

```
└── src/
│   ├── backend/
│   │   └── app/
│   │       ├── api/          # FastAPI routes & models
│   │       ├── runtime/       # Pipeline executor, node registry, scheduler, safety
│   │       ├── tools/         # All processing modules, QC, contracts, runners
│   │       ├── schemas/       # Pipeline schema validation
│   │       ├── nodes/         # GPU-accelerated node handlers
│   │       └── advisor/       # LLM advisor modules
│   └── frontend/src/          # React components & API client
├── matlab/                    # SPM wrapper scripts
├── examples/                  # Pipeline YAMLs
├── tests/unit/                # Unit tests
├── specs/                     # Feature specifications
├── docs/                      # Documentation
└── outputs/                   # Runtime outputs (work, logs, derivatives, reports, exports)
```

## Key Patterns

- **Subject-level nodes**: Accept optional `subject_record` and `subject_id` parameters
- **Safety**: All derivative inputs validated with path checks; rawdata never modified
- **QC**: Every processing stage has a companion QC module
- **Contracts**: DPABI/GPU backends are contract-only; never executed
