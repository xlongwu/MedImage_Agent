---
name: gpu-alff
description: GPU-accelerated ALFF/fALFF computation using CuPy with automatic CPU fallback and benchmark comparison.
---

# GPU ALFF/fALFF Skill

## Inputs
- Filtered residual NIfTI (4D)
- TR (repetition time)
- Frequency band (low_hz, high_hz)

## Outputs
- ALFF map (`alff.nii`)
- fALFF map (`falff.nii`)
- CPU vs GPU benchmark report
- ALFF/fALFF QC JSON

## Procedure
1. Detect GPU availability (CuPy).
2. Benchmark CPU (NumPy) vs GPU (CuPy) on sample.
3. Select backend based on benchmark and preferences.
4. Compute ALFF: mean amplitude in frequency band.
5. Compute fALFF: ALFF / total amplitude ratio.
6. Run QC: finite fraction, frequency bin count, value ranges.
7. Fall back to CPU if GPU fails.

## Rules
- Always provide CPU fallback.
- Never trust GPU results without CPU validation.
- Log backend selection for reproducibility.
- QC must pass before downstream use.
