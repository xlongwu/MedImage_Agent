# Validation Runtime Specification

This document defines the MVP validation and regression suite for MedImage Agent.

## Goals

The validation suite ensures that core modules remain stable as the project grows.

It should validate:

- pipeline schema parsing
- path safety
- synthetic BIDS generation
- dataset inspection
- ALFF / fALFF CPU computation
- GPU detection and CPU fallback
- agent plan safety
- report generation existence
- API smoke checks
- frontend build readiness

## Scope

Supported:

- pytest-based unit tests
- lightweight integration tests
- deterministic synthetic data
- CPU-only execution by default
- optional GPU checks
- optional API checks
- optional frontend build check
- validation summary JSON
- validation report Markdown

Unsupported:

- real medical imaging datasets
- long-running SPM/DPABI validation
- clinical validation
- statistical group analysis
- production CI/CD
- GPU requirement
- external network calls

## Outputs

```text
reports/validation/validation_summary.json
reports/validation/validation_report.md
```

## Test Categories

- unit
- integration
- api
- frontend
- gpu_optional

## Safety Rules

- Do not modify rawdata.
- Do not delete files.
- Do not modify third_party.
- Do not require GPU.
- Do not require MATLAB for default unit tests.
- Do not make clinical conclusions.
