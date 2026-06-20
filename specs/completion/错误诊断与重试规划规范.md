# Error Diagnosis Specification

This document defines the MVP error diagnosis and retry planning behavior.

## Goals

The Error Diagnoser helps users understand failed or suspicious pipeline runs.

It should:

- Read pipeline summary.
- Read project-level node states.
- Read subject-level node states.
- Collect errors and warnings.
- Read safe stdout/stderr logs.
- Match known patterns from ERROR_KB.yaml.
- Generate diagnosis.json.
- Generate diagnosis_report.md.
- Generate retry_plan.json.
- Generate retry_plan.md.

## Scope

Supported:

- deterministic diagnosis
- ERROR_KB pattern matching
- state-based failure detection
- log-based pattern matching
- safe retry recommendations
- Markdown report generation

Unsupported:

- automatic retry execution
- automatic file deletion
- automatic state modification
- automatic memory modification
- clinical diagnosis
- real LLM inference
- DPABI-specific deep diagnosis
- GPU-specific scheduling diagnosis

## Inputs

```text
work/pipeline_runs/{run_id}/summary.json
work/states/{run_id}/...
logs/*.log
memory/global/ERROR_KB.yaml
```

## Outputs

```text
work/diagnosis/{run_id}/diagnosis.json
work/diagnosis/{run_id}/diagnosis_report.md
work/diagnosis/{run_id}/retry_plan.json
work/diagnosis/{run_id}/retry_plan.md
```

## Diagnosis Categories

- ENVIRONMENT_ERROR
- MATLAB_ERROR
- SPM_ERROR
- PYTHON_DEPENDENCY_ERROR
- NIFTI_IO_ERROR
- DATASET_STRUCTURE_ERROR
- QC_FAILURE
- UNKNOWN_ERROR

## Retry Recommendation Types

- NO_RETRY
- SAFE_RETRY
- FIX_CONFIG_THEN_RETRY
- FIX_DEPENDENCY_THEN_RETRY
- MANUAL_REVIEW
- RERUN_ENVIRONMENT_CHECK

## Safety Rules

- Do not execute retry automatically.
- Do not delete outputs.
- Do not modify rawdata.
- Do not modify derivatives.
- Do not modify state files.
- Retry plan is advisory only.
- Any future retry execution must require explicit user approval.
