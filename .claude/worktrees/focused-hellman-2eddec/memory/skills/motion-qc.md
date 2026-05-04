---
name: motion-qc
description: Compute and assess motion quality metrics (FD, DVARS, motion plots) for rs-fMRI subject-level QC.
---

# Motion QC Skill

## Inputs
- Realignment parameters (6-column motion file from SPM)
- Realigned BOLD NIfTI (4D)

## Outputs
- FD summary JSON (mean, max, threshold counts)
- DVARS summary JSON
- Motion plot (optional image)
- Motion QC status: PASS / WARNING / FAIL

## Procedure
1. Load realignment parameters (6 columns: x, y, z, pitch, roll, yaw).
2. Compute Framewise Displacement (FD) using Jenkinson formula.
3. Compute DVARS (RMS intensity change across volumes).
4. Count volumes exceeding thresholds (FD > 0.2, 0.5, 1.0 mm).
5. Generate motion summary.
6. Assign QC status based on thresholds.

## Thresholds (default)
- mean FD ≤ 0.2 mm → PASS
- mean FD > 0.5 mm → FAIL
- mean FD 0.2–0.5 mm → WARNING
- max FD > 3.0 mm → flag for review

## Rules
- Motion QC does not modify data.
- Thresholds are configurable per project.
- Never exclude subjects automatically; flag for manual review.
- Always report mean FD, max FD, and threshold counts.
