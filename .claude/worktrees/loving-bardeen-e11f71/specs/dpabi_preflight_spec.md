# DPABI Preflight Specification

This document defines the MVP DPABI dataset adapter and preflight validator.

## Goals

Before running any DPABI / DPARSF preprocessing, the system should verify:

- DPABI path and capabilities
- dataset completeness
- BIDS-like subject mapping
- T1w and BOLD availability
- functional metadata such as TR
- output workspace safety
- wrapper configuration readiness

## Scope

Supported in this step:

- read dataset_index.json
- read dpabi_capabilities.json
- read dpabi_wrapper_config_template.yaml
- generate dpabi_input_manifest.json
- generate dpabi_batch_config_draft.yaml
- generate dpabi_preflight_report.json
- generate dpabi_preflight_report.md
- create a safe DPABI workspace scaffold

Unsupported in this step:

- full DPABI preprocessing
- DPARSF batch execution
- GUI automation
- rawdata modification
- DPABI source modification
- deletion of files
- real clinical interpretation

## Outputs

```text
work/dpabi/dpabi_input_manifest.json
work/dpabi/dpabi_workspace/
work/dpabi/dpabi_batch_config_draft.yaml
work/dpabi/dpabi_preflight_report.json
reports/dpabi/dpabi_preflight_report.md
```

## Subject Status

- READY_FOR_DPABI_DRY_RUN
- MISSING_T1W
- MISSING_BOLD
- MISSING_TR
- INCOMPLETE
- SKIPPED

## Preflight Status

- PASS: all required checks passed
- WARNING: non-blocking warnings exist
- FAIL: blocking errors exist

## Safety Rules

- Do not run DPABI.
- Do not call DPABI GUI.
- Do not modify rawdata.
- Do not delete files.
- Do not modify DPABI source.
- Create workspace scaffold only under work/dpabi.
