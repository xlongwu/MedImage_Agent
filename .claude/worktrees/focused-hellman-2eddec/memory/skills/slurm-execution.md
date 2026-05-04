---
name: slurm-execution
description: Schedule subject-level parallel preprocessing jobs on Slurm HPC clusters with array job support and resource planning.
---

# Slurm Execution Skill

## Inputs
- Pipeline YAML with parallel_level annotations
- Subject list
- Slurm cluster configuration (partition, QoS, account)

## Outputs
- Slurm job scripts per subject
- Array job submission file
- Resource estimation report
- Job monitoring dashboard data

## Procedure
1. Parse pipeline YAML for parallel_level: subject nodes.
2. Estimate resources per subject (CPU cores, memory, walltime).
3. Generate Slurm job script with proper resource requests.
4. Bundle subjects into Slurm array jobs.
5. Submit with dependency chains (e.g., QC after preprocessing).
6. Monitor job status and collect outputs.

## Slurm Job Template
```bash
#!/bin/bash
#SBATCH --job-name=rsfmri_sub-${SUBJECT}
#SBATCH --output=logs/slurm_%A_%a.out
#SBATCH --error=logs/slurm_%A_%a.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
```

## Rules
- Estimate resources conservatively; add 20% buffer.
- Never submit to production partition without explicit approval.
- MATLAB license checkout must respect job queue limits.
- Log all Slurm job IDs for traceability.
- Validate outputs before marking job complete.
