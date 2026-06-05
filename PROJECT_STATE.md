# Project State

## Current milestone

Desktop real-project execution and run artifact inspection loop completed.

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
- Safe real-project smoke test passed.

## Test baseline

- `pytest --tb=short`: `2413 passed, 8 skipped, 1 warning`.
- Skipped reasons:
  - Missing optional `pydicom`.
  - Missing optional `cupy`.
  - Missing `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.

## Python test environment

Use:

```powershell
$env:PYTHONPATH="D:\deep_learning_code\MedImage_Agent\.venv\Lib\site-packages"
D:\Python311\python.exe -m pytest --tb=short
```

Do not rely on the default `D:\Anaconda3\python.exe`; it lacks FastAPI in this
workspace.

## Explicit non-goals

- No MATLAB/SPM/DPABI/GPU real execution.
- No NIfTI viewer.
- No complete QC dashboard.
- No report editor.
- No clinical validation.
- No Advanced Agent Controls project-context integration yet.
- No external user BIDS smoke unless `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR` is provided.

## Next recommended work

1. Resolve Git tracked/untracked state.
2. Then mechanically split `ProjectRunsPanel.tsx`.
3. Then split `project_history_routes.py`.
4. Then run external BIDS smoke if user provides a small read-only BIDS path.
