# Run Monitor Specification

This document defines the MVP run monitor for MedImage Agent.

## Goals

The Run Monitor helps users inspect completed or partially completed pipeline runs.

It should show:

- pipeline summary
- project-level node states
- subject-level node states
- subject-level success/failure
- logs paths
- errors and warnings
- node outputs
- node metrics

## Scope

Supported:

- Read run summary JSON
- Read node state JSON files
- Read safe log files through backend allowlist
- Display run status in frontend
- Display subject-level state table
- Display selected state detail
- Display stdout/stderr logs when available

Unsupported:

- WebSocket streaming
- real-time log tail
- database-backed run history
- parallel execution visualization
- task cancellation
- retry from UI
- editing state files
- deleting outputs

## State Locations

Pipeline summary:

```text
work/pipeline_runs/{run_id}/summary.json
```

Project-level states:

```text
work/states/{run_id}/{node_id}.json
```

Subject-level states:

```text
work/states/{run_id}/{subject_id}/{node_id}.json
```

Agent run summary:

```text
work/agent_runs/{agent_run_id}/agent_summary.json
```

Background review:

```text
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
```

## Safety Rules

- The monitor is read-only.
- It must not modify state files.
- It must not delete logs.
- It must use safe file reading.
- It must not expose raw medical images.
- It must not read arbitrary system files.
