# DPABI Run Plan Specification

This document defines the MVP DPABI parameter review and approved run plan stage.

## Goals

Before any DPABI execution, the system must generate a human-reviewable run plan.

The run plan should combine:

- DPABI capabilities
- input manifest
- preflight results
- parameter schema
- parameter review YAML
- safety checks
- approval status

## Scope

Supported in this step:

- DPABI parameter schema
- default parameter review YAML
- parameter validation
- approved run plan JSON
- run plan Markdown report
- API and frontend visibility

Unsupported in this step:

- full DPABI execution
- DPARSF_run execution
- DPABI GUI automation
- rawdata modification
- DPABI source modification
- deletion of files
- real clinical interpretation

## Outputs

```text
work/dpabi/dpabi_parameter_schema.json
work/dpabi/dpabi_params_review.yaml
work/dpabi/dpabi_params_validation.json
work/dpabi/dpabi_run_plan.json
reports/dpabi/dpabi_run_plan_report.md
```

## Run Plan Status

- READY_FOR_REVIEW: all inputs exist, but human approval is required
- BLOCKED: blocking error exists
- WARNING: non-blocking issue exists
- APPROVED: future state only; not set automatically in this step

## Safety Rules

- Do not execute DPABI.
- Do not call DPABI GUI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
- Run plan must default to approved=false.
- Run plan must require explicit future approval before execution.
