# MedImage Agent Developer Guide

## Adding a New Pipeline Stage

1. Create MATLAB wrapper in `matlab/` (if SPM step) or Python module in `backend/app/tools/`
2. Create QC module in `backend/app/tools/`
3. Create runner orchestration module
4. Register node in `backend/app/runtime/node_registry.py`
5. Create pipeline YAML in `examples/`
6. Create CLI runner in `backend/app/tools/`
7. Add API endpoints in `backend/app/api/routes.py` and model in `models.py`
8. Add frontend panel in `frontend/src/components/`
9. Update `App.tsx`, `api.ts`
10. Add unit test in `tests/unit/`
11. Update README.md

## Project Structure

```
└── backend/
│   └── app/
│       ├── api/          # FastAPI routes & models
│       ├── runtime/       # Pipeline executor, node registry, scheduler
│       ├── tools/         # All processing modules, QC, contracts, runners
│       └── schemas/       # Pipeline schema validation
├── frontend/src/           # React components & API client
├── matlab/                 # SPM wrapper scripts
├── examples/               # Pipeline YAMLs
├── tests/unit/             # Unit tests
├── specs/                  # Feature specifications
├── docs/                   # Documentation
└── reports/                # Generated reports
```

## Key Patterns

- **Subject-level nodes**: Accept optional `subject_record` and `subject_id` parameters
- **Safety**: All derivative inputs validated with path checks; rawdata never modified
- **QC**: Every processing stage has a companion QC module
- **Contracts**: DPABI/GPU backends are contract-only; never executed
