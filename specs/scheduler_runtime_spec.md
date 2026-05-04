# Scheduler Runtime Specification

This document defines the MVP local scheduler for MedImage Agent.

## Goals

The scheduler improves subject-level execution by supporting safe local parallelism.

It should:

- keep project-level nodes sequential
- allow subject-level nodes to run in parallel
- limit concurrency with max_workers
- limit MATLAB concurrency with matlab_max_workers
- preserve per-subject state files
- preserve pipeline summary
- avoid modifying rawdata
- avoid deleting files

## Scope

Supported:

- local sequential execution
- local subject-level parallel execution
- ThreadPoolExecutor-based scheduling
- max_workers
- matlab_max_workers
- scheduler dry-run resource plan
- per-subject state files
- summary scheduler metadata

Unsupported:

- Slurm
- Celery
- Redis
- database queues
- WebSocket progress
- GPU scheduling
- remote workers
- job cancellation
- distributed execution

## Execution Modes

### sequential

Default mode.

Subject-level nodes run one subject at a time.

### local_parallel

Subject-level nodes run across subjects using local worker threads.

This mode is safe only when:

- rawdata is read-only
- each subject writes to isolated output paths
- MATLAB worker count is limited
- state files are subject-specific

## Pipeline Config Example

```yaml
execution:
  stop_on_failure: true
  run_id: "run_subject_preprocess_parallel_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1
```

## Safety Rules

- Default max_workers must be 1.
- matlab_max_workers must not exceed max_workers.
- Subject-level task failures must not crash the whole executor.
- Other subjects can continue after one subject fails.
- Original rawdata must not be modified.
- No files should be deleted.
