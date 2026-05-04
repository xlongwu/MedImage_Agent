# Dataset Report Exporter Specification

Packages existing synthetic rs-fMRI QC outputs, metrics, contracts, and pipeline summaries into a reproducible ZIP report package with SHA256 checksums and manifest. Read-only from derivatives/reports/work, writes only to exports. Excludes .nii/.gz/.mat binary files.
