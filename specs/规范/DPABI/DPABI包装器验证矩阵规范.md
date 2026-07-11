# DPABI Wrapper Validation Specification

This document defines the MVP DPABI wrapper validation matrix.

## Goals

The validation matrix summarizes the compatibility and readiness of DPABI wrapper functions.

It should answer:

- Which functions exist?
- Which functions are blocked?
- Which functions are wrapper candidates?
- Which functions passed sandbox testing?
- Which functions passed subject-level synthetic testing?
- Which functions need manual review?
- Which functions can be promoted to pipeline templates?

## Scope

Supported in this step:

- aggregate signature probe output
- aggregate wrapper contracts
- aggregate sandbox wrapper result
- aggregate subject-level wrapper result
- generate JSON matrix
- generate CSV matrix
- generate Markdown validation report
- API and frontend visibility
- lightweight validation test

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- GUI automation
- real medical image preprocessing
- rawdata modification
- DPABI source modification
- deletion of files

## Inputs

```text
work/dpabi/dpabi_function_signatures.json
work/dpabi/dpabi_wrapper_contracts.json
work/dpabi/single_function_sandbox/dpabi_single_function_result.json
reports/dpabi/dpabi_subject_wrapper_summary.json
```

## Outputs

```text
work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/dpabi_wrapper_compatibility_matrix.csv
reports/dpabi/dpabi_wrapper_validation_report.md
```

## Readiness Levels

- BLOCKED
- MISSING
- CONTRACT_ONLY
- SANDBOX_PASSED
- SUBJECT_SYNTHETIC_PASSED
- MANUAL_REVIEW_REQUIRED
- PROMOTABLE_TO_TEMPLATE

## Promotion Rules

A function can be PROMOTABLE_TO_TEMPLATE only if:

- it exists
- it is a wrapper_candidate
- it is not GUI_BLOCKED
- it is not FULL_PIPELINE_BLOCKED
- sandbox test passed
- subject-level synthetic test passed, if subject-level test applies

## Safety Rules

- Do not execute DPABI.
- Do not call DPARSF_run.
- Do not call DPARSFA_run.
- Do not call DPABI GUI.
- Do not modify rawdata.
- Do not modify DPABI source.
- Do not delete files.
