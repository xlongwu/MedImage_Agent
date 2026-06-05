# AGENTS.md - MedImage Agent Agent Guide

This guide is for Codex, Claude Code, and other coding agents working in this
repository. Keep changes focused, reproducible, and safe for a research
engineering platform.

## Project Snapshot

MedImage Agent is a deterministic Plan-then-Execute platform for rs-fMRI
research workflows. The LLM plans and advises; execution must remain inside the
Pipeline Runtime and registered node runners. This is not a clinical diagnosis
or clinical decision product.

Current handoff state:

- Desktop real-project execution and run artifact inspection loop is complete.
- Real BIDS/rawdata project creation, `project_config.yaml`, `dataset_index.json`,
  project persistence, Plan Review project context, reviewed plan/run
  persistence, run history UI, run summary preview, run-scoped artifacts, and
  QC/Error summary are implemented.
- Current P0 work is delivery-state repair only: no new features, no broad
  refactor, and no external data execution.

## Required Workflow

1. Read `AGENTS.md` and `CLAUDE.md` before making changes.
2. Before editing any target file, read its current contents.
3. Do not perform broad repository exploration for focused handoff tasks; inspect
   only the files and anchors needed for the task.
4. Keep each change scoped to one delivery goal.
5. After changes, report modified files, tests run, results, and remaining risks.

## Safety Rules

- 禁止事项: the following boundaries are mandatory for all agents.
- Do not modify `data/` or any raw BIDS/rawdata input. Raw data is read-only.
- Do not bypass the Approval Gate. File-writing, MATLAB/SPM/DPABI, derivatives,
  and execution actions must keep the explicit approval path.
- Do not modify `pipeline_executor.py`, node runners, or Approval Gate code unless
  the task explicitly requires it.
- Do not introduce an open-ended LLM autonomous execution loop.
- Do not hardcode API keys, credentials, private absolute paths, or experimental
  data paths.
- Frontend code must communicate through backend HTTP APIs and must not access
  the local filesystem directly.

## Runtime Artifacts

Do not stage or commit runtime artifacts, including:

- `outputs/`
- `work/`
- `logs/`
- `reports/`
- `.pytest_cache/`
- `__pycache__/`
- SQLite runtime databases
- generated reviewed pipelines
- generated audit/report artifacts
- frontend build output

## Python Test Environment

Use the project Python interpreter explicitly:

```powershell
$env:PYTHONPATH="D:\deep_learning_code\MedImage_Agent\.venv\Lib\site-packages"
D:\Python311\python.exe -m pytest --tb=short
```

Do not rely on the default `D:\Anaconda3\python.exe`; it lacks FastAPI in this
workspace.

## Current Validation Baseline

- Full backend baseline: `pytest --tb=short` -> `2413 passed, 8 skipped, 1 warning`.
- Expected skips are optional `pydicom`, optional `cupy`, and missing
  `MEDIMAGE_EXTERNAL_BIDS_SMOKE_DIR`.
- Frontend delivery should include the ProjectRunsPanel smoke check,
  TypeScript compile, and Vite production build when touching frontend code.

## Completion Report

Every completed task must report:

- Git status classification: staged delivery files, excluded files, and files
  needing manual follow-up.
- Modified, created, restored, or deleted files.
- Exact test commands and pass/fail results.
- Remaining risks and recommended next work.
