# DPABI Execution Sandbox Specification

This document defines the MVP approved DPABI sandbox execution.

## Goals

The sandbox smoke run verifies that MedImage Agent can safely call DPABI-related MATLAB functions without running full preprocessing.

It should validate:

- explicit approval gate
- MATLAB launch
- DPABI path setup
- selected safe DPABI function discovery
- synthetic NIfTI read/write in sandbox
- result JSON
- stdout/stderr logs
- approval record
- execution audit

## Scope

Supported in this step:

- approved sandbox smoke run
- synthetic NIfTI created under work/dpabi/sandbox
- DPABI addpath
- safe function probing
- optional y_Read / y_Write test
- optional rest_readfile / rest_writefile test
- execution audit JSON
- Markdown audit report
- API and frontend visibility

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- GUI automation
- rawdata modification
- DPABI source modification
- deletion of files
- real medical image processing

## Inputs

```text
work/dpabi/dpabi_run_plan.json
work/dpabi/dpabi_capabilities.json
examples/project_config_dataset.yaml
```

## Outputs

```text
work/dpabi/sandbox/input_synthetic.nii
work/dpabi/sandbox/output_synthetic.nii
work/dpabi/sandbox/dpabi_sandbox_smoke_result.json
work/dpabi/approvals/dpabi_sandbox_smoke_approval.json
work/dpabi/audit/dpabi_sandbox_execution_audit.json
reports/dpabi/dpabi_sandbox_execution_audit.md
logs/dpabi_sandbox_smoke_stdout.log
logs/dpabi_sandbox_smoke_stderr.log
```

## Approval Rules

- Sandbox run requires approved=true.
- Approval must be recorded before MATLAB execution.
- Approval record must include timestamp, execution_type, and safety flags.
- Missing approval must fail safely.

## Safety Rules

- Do not read rawdata.
- Do not modify rawdata.
- Do not call DPABI GUI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not modify DPABI source.
- Do not delete files.
- Sandbox output must be written only under work/dpabi/sandbox.
