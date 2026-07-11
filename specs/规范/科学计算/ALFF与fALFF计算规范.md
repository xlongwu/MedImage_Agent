# ALFF / fALFF and QC Specification

Compute ALFF/fALFF from nuisance-regressed and filtered synthetic rs-fMRI derivatives using NumPy FFT. ALFF = mean amplitude in low-frequency band (excl. DC). fALFF = low-freq mean amplitude / non-DC full-spectrum mean amplitude. Default band 0.01-0.08 Hz. TR from temporal_filtering_qc.json, slice_timing_qc.json, or fallback. GPU and DPABI backends are contract-only in this step.
