# Memory Runtime Specification

This document defines the MVP memory and background review system for MedImage Agent.

## Goals

The memory system should help the agent preserve useful knowledge across runs:

- environment configuration
- project-level lessons
- known errors and fixes
- run history
- dataset evaluation outcomes
- pipeline reliability observations

## Memory Layers

### Global Prompt Memory

Files:

```text
memory/global/MEMORY.md
memory/global/USER.md
memory/global/ENVIRONMENT.md
memory/global/ERROR_KB.yaml
```

Purpose:

Store high-level stable context.
Keep concise.
Do not store raw imaging data.
Do not store PHI.

### Project Memory

Files:

```text
memory/projects/{project_name}/PROJECT.md
memory/projects/{project_name}/LESSONS.md
memory/projects/{project_name}/RUN_HISTORY.jsonl
```

Purpose:

Store project-specific decisions, run summaries, and lessons.

### Run Review

Files:

```text
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
```

Purpose:

Summarize what happened in the run.
Propose memory updates.
Do not automatically rewrite stable memory without review.

## What to Store

Allowed:

- pipeline ID and version
- run ID
- software paths
- success/failure status
- QC metrics summary
- dataset quality score
- known error patterns
- non-sensitive subject IDs
- recommendations such as INCLUDE / MANUAL_REVIEW / EXCLUDE counts

Forbidden:

- patient names
- hospital IDs
- raw DICOM headers
- raw NIfTI content
- PHI
- clinical diagnosis
- disease conclusions

## Background Review Inputs

The MVP background reviewer reads:

```text
work/agent_runs/{agent_run_id}/agent_summary.json
work/pipeline_runs/{run_id}/summary.json
reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/exclusion_recommendations.csv
work/states/{run_id}/...
```

## Background Review Outputs

```text
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
memory/projects/{project_name}/RUN_HISTORY.jsonl
```

## Safety Rules

- Do not modify rawdata.
- Do not delete files.
- Do not store PHI.
- Do not make clinical conclusions.
- Proposed memory patches require human review before merging.
- RUN_HISTORY.jsonl can be appended automatically.
