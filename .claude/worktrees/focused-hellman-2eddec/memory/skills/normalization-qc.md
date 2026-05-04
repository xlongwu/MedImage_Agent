---
name: normalization-qc
description: Assess spatial normalization quality by comparing normalized images to MNI template.
---

# Normalization QC Skill

## Inputs
- Normalized anatomical (wT1w) or functional NIfTI
- MNI template NIfTI (optional, for reference)
- Coregistered T1w NIfTI (for comparison)

## Outputs
- Normalization QC JSON
- Normalization QC report MD
- Center distance metrics
- Boundary overlap metrics

## Procedure
1. Load normalized and reference images.
2. Compute world center distance from MNI origin.
3. Compute boundary box overlap with MNI template.
4. Check image dimensions against expected MNI dimensions.
5. Assign QC status: PASS / WARNING / FAIL.

## Rules
- Do not modify rawdata.
- Flag subjects with center distance > 30 mm for review.
- Normalization QC is advisory only; does not block pipeline.
- Always report metrics numerically for downstream filtering.
