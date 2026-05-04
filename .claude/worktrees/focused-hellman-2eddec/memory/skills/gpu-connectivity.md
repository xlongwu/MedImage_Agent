---
name: gpu-connectivity
description: GPU-accelerated functional connectivity (ROI correlation matrix and seed-to-voxel maps) with CuPy backend.
---

# GPU Functional Connectivity Skill

## Inputs
- Filtered functional NIfTI (4D)
- ROI atlas NIfTI or synthetic atlas parameters
- ROI definitions JSON

## Outputs
- ROI timeseries TSV
- Correlation matrix (TSV + JSON)
- Fisher Z matrix (TSV + JSON)
- Seed correlation map (optional)
- FC QC JSON

## Procedure
1. Load filtered data and ROI atlas.
2. Extract ROI mean timeseries (GPU batch extraction).
3. Compute correlation matrix (GPU matmul).
4. Apply Fisher Z transform.
5. Optionally generate seed-to-voxel correlation maps.
6. Run QC: finite fractions, symmetry check, empty ROIs.

## Rules
- GPU must validate against CPU reference.
- Atlas must be safe (in derivatives/ or work/).
- Handle empty ROIs gracefully (exclude from matrix).
- Correlation matrix must be symmetric within tolerance.
