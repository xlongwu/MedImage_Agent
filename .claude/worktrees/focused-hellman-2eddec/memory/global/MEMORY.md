# MedImage Agent Memory

This file stores concise global memory for MedImage Agent.

## System Role

MedImage Agent is a visual and agent-based medical imaging preprocessing framework.

It supports:

- BIDS-like dataset inspection
- MATLAB / SPM / DPABI environment checks
- synthetic subject-level preprocessing tests
- QC metric aggregation
- dataset-level evaluation reports
- deterministic Agent Runtime with Plan Mode and Execute Mode

## Safety Rules

- Do not modify rawdata.
- Do not store PHI.
- Do not make clinical conclusions.
- Treat reports as engineering QC and research preprocessing support only.
- Require explicit approval before execution.
