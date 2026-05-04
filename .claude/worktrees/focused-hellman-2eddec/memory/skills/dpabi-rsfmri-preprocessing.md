---
name: dpabi-rsfmri-preprocessing
description: Run DPABI/DPARSF-based rs-fMRI preprocessing with safety sandbox and contract-mode execution.
---

# DPABI rs-fMRI Preprocessing Skill

## Inputs
- BIDS / BIDS-like NIfTI data
- DPABI parameter template
- Subject list

## Outputs
- DPABI derivatives directory
- Execution contract (safety wrapper)
- DPABI node-level QC
- Reproducibility manifest

## Procedure
1. Validate DPABI environment (MATLAB + DPABI paths).
2. Generate DPABI parameter file from template.
3. Run preflight checks (license, disk space, path safety).
4. Execute in sandbox/contract mode (default: contract-only).
5. Collect DPABI outputs and stage-level QC.
6. Validate output integrity.

## Rules
- Default mode: contract-only (no real execution).
- Real execution requires explicit opt-in.
- Never call DPARSF_run directly.
- All outputs must be in derivatives/.
- Save parameter files for reproducibility.
