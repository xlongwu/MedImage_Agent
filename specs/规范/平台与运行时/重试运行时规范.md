# Retry Runtime Specification

This document defines the MVP approved retry runtime for MedImage Agent.

## Goals

The retry runtime executes selected safe retry steps from retry_plan.json.

It must be:

- explicit
- approved
- auditable
- non-destructive
- limited to allowlisted actions
- safe for medical imaging workflows

## Inputs

```text
work/diagnosis/{run_id}/retry_plan.json
work/dataset_index/dataset_index.json
examples/project_config_dataset.yaml
```

## Outputs

```text
work/retry_runs/{retry_run_id}/retry_execution_summary.json
work/retry_runs/{retry_run_id}/dry_run_summary.json
work/states/{retry_run_id}/...
```

## Supported Retry Actions

### RERUN_ENVIRONMENT_CHECK

Runs the existing environment_check node.

### SAFE_RETRY

Only allowed for allowlisted nodes:

- spm_smooth_subject
- subject_qc
- dataset_evaluation

### FIX_CONFIG_THEN_RETRY

Dry-run only in MVP. Requires user to fix config manually.

### FIX_DEPENDENCY_THEN_RETRY

Dry-run only in MVP. Requires user to install dependencies manually.

### MANUAL_REVIEW

Dry-run only. No automatic execution.

### NO_RETRY

No execution.

## Approval Rules

- Dry run does not require approval.
- Execution requires approved=true.
- Execution must never run automatically after diagnosis.
- Execution must never delete old outputs.
- Execution must write a new retry run ID.

## State Rules

Original run state must remain unchanged.

Retry execution writes new state files:

```text
work/states/{retry_run_id}/...
```

## Safety Rules

- Do not delete files.
- Do not modify rawdata.
- Do not modify third_party.
- Do not edit original state JSON.
- Do not execute unsupported actions.
- Do not execute retry without approval.
- Do not execute MANUAL_REVIEW steps.
