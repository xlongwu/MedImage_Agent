# Run State Machine

This document defines the minimal execution state model for MedImage Agent.

## Node Status

- PENDING: node is created but not ready
- READY: all inputs are available
- RUNNING: node is executing
- SUCCESS: node completed and outputs validated
- FAILED: node failed
- SKIPPED: node skipped by rule or user
- CACHED: outputs reused from previous run
- RETRYING: node is being retried
- NEEDS_REVIEW: automatic QC is uncertain
- EXCLUDED: subject or node is excluded from downstream analysis

## Minimal State Record

```json
{
  "run_id": "run_001",
  "subject": "project",
  "node": "environment_check",
  "status": "SUCCESS",
  "started_at": "2026-05-01T10:00:00",
  "ended_at": "2026-05-01T10:01:00",
  "log_path": "outputs/logs/matlab_check_stdout.log",
  "outputs": ["outputs/work/environment_check.json"],
  "errors": []
}
```

## Rules

- Every executable step must create a state record.
- FAILED nodes must preserve logs.
- SUCCESS nodes must validate required outputs.
- CACHED nodes must record the source cache entry.
- NEEDS_REVIEW must not be treated as SUCCESS automatically.
