# ReHo and ReHo QC Specification

Compute ReHo from filtered residual functional using Kendall's coefficient of concordance (KCC). Neighborhood 7/19/27, default 27. Boundary voxels skipped. KCC = 12 * sum(R_i - R_bar)^2 / (T^2 * (K^3 - K)). GPU and DPABI contracts without execution.
