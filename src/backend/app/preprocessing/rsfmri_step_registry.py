from __future__ import annotations

from src.backend.app.preprocessing.step_schema import PreprocessingStepSpec, step_to_dict


def get_rsfmri_core_step_registry() -> list[PreprocessingStepSpec]:
    return [
        PreprocessingStepSpec(
            step_id="dataset_inspection",
            name="Dataset Inspection",
            category="data_inspection",
            backend="python",
            description="Scan BIDS-like dataset, index subjects, sessions, anatomical files, and functional runs.",
            inputs=["rawdata_dir"],
            outputs=[
                "outputs/work/dataset_index/dataset_index.json",
                "outputs/work/dataset_index/subject_table.csv",
                "outputs/work/dataset_index/data_completeness_report.json",
            ],
            parameters={
                "read_nifti_metadata": True,
                "synthetic_only_default": True,
            },
            depends_on=[],
            parallel_level="project",
            gpu_supported=False,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "subjects_total",
                "subjects_complete",
                "missing_anat_count",
                "missing_func_count",
            ],
            failure_modes=[
                "rawdata_dir_missing",
                "invalid_bids_layout",
                "missing_subjects",
            ],
            diagnostic_hints=[
                "Check dataset_description.json.",
                "Check participants.tsv.",
                "Check subject/session folder naming.",
            ],
            safety_notes=[
                "Read-only scan.",
                "Do not modify rawdata.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="anat_func_pairing",
            name="Anatomical-Functional Pairing",
            category="data_inspection",
            backend="python",
            description="Pair each functional run with the best available anatomical image.",
            inputs=["outputs/work/dataset_index/dataset_index.json"],
            outputs=["outputs/work/preprocessing/rsfmri/anat_func_pairs.json"],
            parameters={
                "allow_missing_anat": False,
                "prefer_same_session_anat": True,
            },
            depends_on=["dataset_inspection"],
            parallel_level="subject",
            gpu_supported=False,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "paired_subjects",
                "unpaired_subjects",
            ],
            failure_modes=[
                "missing_anatomical_image",
                "multiple_ambiguous_anat_candidates",
            ],
            diagnostic_hints=[
                "Inspect anat/ folder.",
                "Check whether session-specific anatomical image exists.",
            ],
            safety_notes=[
                "Read-only pairing.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="slice_timing",
            name="Slice Timing Correction",
            category="spm_preprocessing",
            backend="matlab-spm",
            description="Correct slice acquisition timing differences using SPM.",
            inputs=["func_bold"],
            outputs=["outputs/derivatives/rsfmri_preproc/{subject_id}/func/a{run_id}_bold.nii"],
            parameters={
                "slice_order": "auto_or_user_defined",
                "reference_slice": "middle",
                "tr": "from_metadata_or_user_defined",
            },
            depends_on=["anat_func_pairing"],
            parallel_level="run",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "output_exists",
                "shape_consistency",
            ],
            failure_modes=[
                "missing_tr",
                "missing_slice_order",
                "spm_slice_timing_failed",
            ],
            diagnostic_hints=[
                "Check JSON sidecar for RepetitionTime.",
                "Ask user for slice order if metadata missing.",
            ],
            safety_notes=[
                "Write outputs only under derivatives.",
                "Do not overwrite rawdata.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="realignment",
            name="Realignment",
            category="spm_preprocessing",
            backend="matlab-spm",
            description="Estimate and correct head motion using SPM realignment.",
            inputs=["slice_timing_output_or_func_bold"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/func/r{run_id}_bold.nii",
                "outputs/derivatives/rsfmri_preproc/{subject_id}/func/rp_{run_id}.txt",
            ],
            parameters={
                "quality": 0.9,
                "separation": 4,
                "fwhm": 5,
                "register_to_mean": True,
            },
            depends_on=["slice_timing"],
            parallel_level="run",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "mean_fd",
                "max_fd",
                "high_motion_frame_count",
                "motion_parameter_file_exists",
            ],
            failure_modes=[
                "spm_realign_failed",
                "motion_parameter_missing",
                "excessive_motion",
            ],
            diagnostic_hints=[
                "Check SPM realign stdout/stderr logs.",
                "Check whether input BOLD is 4D.",
                "Check whether motion parameters were written.",
            ],
            safety_notes=[
                "Motion parameters are derivatives.",
                "Do not overwrite rawdata.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="motion_qc",
            name="Motion QC",
            category="python_qc",
            backend="python",
            description="Compute framewise displacement and motion summary metrics.",
            inputs=["rp_{run_id}.txt"],
            outputs=[
                "outputs/derivatives/rsfmri_qc/{subject_id}/motion_qc.json",
                "outputs/derivatives/rsfmri_qc/{subject_id}/motion_qc.md",
            ],
            parameters={
                "fd_threshold": 0.5,
                "head_radius_mm": 50,
            },
            depends_on=["realignment"],
            parallel_level="subject",
            gpu_supported=False,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "mean_fd",
                "max_fd",
                "fd_threshold",
                "high_motion_frame_count",
                "high_motion_fraction",
            ],
            failure_modes=[
                "motion_parameter_file_missing",
                "motion_parameter_shape_invalid",
            ],
            diagnostic_hints=[
                "Check realignment output.",
                "Check rp_*.txt format.",
            ],
            safety_notes=[
                "QC only.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="coregistration",
            name="Coregistration",
            category="spm_preprocessing",
            backend="matlab-spm",
            description="Coregister functional image to anatomical image using SPM.",
            inputs=["mean_func", "anat_t1w"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/coregistered_t1w.nii"
            ],
            parameters={
                "cost_function": "nmi",
            },
            depends_on=["realignment", "anat_func_pairing"],
            parallel_level="subject",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "coreg_output_exists",
                "registration_quality_score",
            ],
            failure_modes=[
                "missing_mean_func",
                "missing_t1w",
                "spm_coregister_failed",
            ],
            diagnostic_hints=[
                "Check mean functional image.",
                "Check T1w image orientation.",
            ],
            safety_notes=[
                "Write only derivatives.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="segmentation",
            name="T1 Segmentation",
            category="spm_preprocessing",
            backend="matlab-spm",
            description="Segment anatomical image into tissue probability maps using SPM.",
            inputs=["anat_t1w"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/c1_t1w.nii",
                "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/c2_t1w.nii",
                "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/c3_t1w.nii",
                "outputs/derivatives/rsfmri_preproc/{subject_id}/anat/y_t1w.nii",
            ],
            parameters={
                "spm_tpm": "default",
            },
            depends_on=["coregistration"],
            parallel_level="subject",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "gm_exists",
                "wm_exists",
                "csf_exists",
                "deformation_field_exists",
            ],
            failure_modes=[
                "spm_segment_failed",
                "deformation_field_missing",
            ],
            diagnostic_hints=[
                "Check T1w contrast.",
                "Check SPM TPM path.",
            ],
            safety_notes=[
                "Write only derivatives.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="normalization",
            name="Normalization",
            category="spm_preprocessing",
            backend="matlab-spm",
            description="Normalize functional images to template space using deformation field.",
            inputs=["realigned_func", "deformation_field"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/func/w{run_id}_bold.nii"
            ],
            parameters={
                "voxel_size": [3, 3, 3],
                "bounding_box": "mni_default",
            },
            depends_on=["segmentation"],
            parallel_level="run",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "normalized_output_exists",
                "voxel_size",
                "shape_consistency",
                "normalization_quality_score",
            ],
            failure_modes=[
                "deformation_field_missing",
                "spm_normalize_failed",
            ],
            diagnostic_hints=[
                "Check y_*.nii deformation field.",
                "Check SPM normalization logs.",
            ],
            safety_notes=[
                "Write only derivatives.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="smoothing",
            name="Spatial Smoothing",
            category="spm_preprocessing",
            backend="matlab-spm",
            description="Apply Gaussian smoothing to normalized functional images.",
            inputs=["normalized_func"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/func/sw{run_id}_bold.nii"
            ],
            parameters={
                "fwhm": [6, 6, 6],
                "backend_options": ["spm_smooth", "dpabi_y_Smooth"],
            },
            depends_on=["normalization"],
            parallel_level="run",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "smoothed_output_exists",
                "shape_consistency",
            ],
            failure_modes=[
                "spm_smooth_failed",
                "dpabi_smooth_failed",
            ],
            diagnostic_hints=[
                "Check normalized functional image.",
                "Check smoothing backend selection.",
            ],
            safety_notes=[
                "Write only derivatives.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="nuisance_regression",
            name="Nuisance Regression",
            category="dpabi_preprocessing",
            backend="matlab-dpabi",
            description="Regress nuisance covariates such as motion, WM, CSF, and optional global signal.",
            inputs=["smoothed_or_normalized_func", "motion_params", "tissue_masks"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/func/regressed_{run_id}_bold.nii"
            ],
            parameters={
                "motion_model": "Friston24",
                "wm": True,
                "csf": True,
                "global_signal": False,
                "linear_trend": True,
            },
            depends_on=["smoothing", "motion_qc", "segmentation"],
            parallel_level="run",
            gpu_supported=False,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "regressed_output_exists",
                "covariate_count",
            ],
            failure_modes=[
                "covariate_file_missing",
                "dpabi_regression_failed",
            ],
            diagnostic_hints=[
                "Check nuisance covariate table.",
                "Check DPABI regression wrapper contract.",
            ],
            safety_notes=[
                "Do not call DPARSF_run.",
                "Use explicit single-function wrappers only.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="temporal_filtering",
            name="Temporal Filtering",
            category="dpabi_preprocessing",
            backend="matlab-dpabi",
            description="Apply band-pass filtering for rs-fMRI time series.",
            inputs=["regressed_func"],
            outputs=[
                "outputs/derivatives/rsfmri_preproc/{subject_id}/func/filtered_{run_id}_bold.nii"
            ],
            parameters={
                "low_hz": 0.01,
                "high_hz": 0.08,
            },
            depends_on=["nuisance_regression"],
            parallel_level="run",
            gpu_supported=True,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "filtered_output_exists",
                "frequency_band",
            ],
            failure_modes=[
                "invalid_tr",
                "filter_failed",
            ],
            diagnostic_hints=[
                "Check TR.",
                "Check number of time points.",
            ],
            safety_notes=[
                "GPU implementation may be added later.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="alff",
            name="ALFF",
            category="gpu_candidate",
            backend="python-gpu",
            description="Compute ALFF from filtered or cleaned rs-fMRI signal.",
            inputs=["filtered_func"],
            outputs=[
                "outputs/derivatives/rsfmri_metrics/{subject_id}/ALFF.nii"
            ],
            parameters={
                "low_hz": 0.01,
                "high_hz": 0.08,
                "cpu_fallback": True,
            },
            depends_on=["temporal_filtering"],
            parallel_level="subject",
            gpu_supported=True,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "alff_output_exists",
                "backend_used",
                "runtime_seconds",
            ],
            failure_modes=[
                "gpu_unavailable",
                "fft_failed",
                "input_shape_invalid",
            ],
            diagnostic_hints=[
                "Use CPU fallback if GPU unavailable.",
                "Check time dimension.",
            ],
            safety_notes=[
                "Metric computation only.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="falff",
            name="fALFF",
            category="gpu_candidate",
            backend="python-gpu",
            description="Compute fALFF from rs-fMRI signal.",
            inputs=["filtered_func_or_cleaned_func"],
            outputs=[
                "outputs/derivatives/rsfmri_metrics/{subject_id}/fALFF.nii"
            ],
            parameters={
                "low_hz": 0.01,
                "high_hz": 0.08,
                "full_band_low_hz": 0.0,
                "full_band_high_hz": 0.25,
                "cpu_fallback": True,
            },
            depends_on=["temporal_filtering"],
            parallel_level="subject",
            gpu_supported=True,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "falff_output_exists",
                "backend_used",
                "runtime_seconds",
            ],
            failure_modes=[
                "gpu_unavailable",
                "fft_failed",
                "division_by_zero",
            ],
            diagnostic_hints=[
                "Check frequency band.",
                "Check TR.",
            ],
            safety_notes=[
                "Metric computation only.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="reho",
            name="ReHo",
            category="dpabi_preprocessing",
            backend="matlab-dpabi",
            description="Compute regional homogeneity using DPABI or a future Python implementation.",
            inputs=["filtered_func"],
            outputs=[
                "outputs/derivatives/rsfmri_metrics/{subject_id}/ReHo.nii"
            ],
            parameters={
                "neighbor_size": 27,
            },
            depends_on=["temporal_filtering"],
            parallel_level="subject",
            gpu_supported=True,
            matlab_required=True,
            approval_required=True,
            cacheable=True,
            qc_metrics=[
                "reho_output_exists",
                "neighbor_size",
            ],
            failure_modes=[
                "dpabi_reho_failed",
                "input_shape_invalid",
            ],
            diagnostic_hints=[
                "Check DPABI ReHo wrapper.",
                "Check mask and voxel size.",
            ],
            safety_notes=[
                "Do not call DPARSF_run.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="subject_qc_report",
            name="Subject QC Report",
            category="python_qc",
            backend="python",
            description="Aggregate subject-level QC metrics and produce a subject report.",
            inputs=[
                "motion_qc.json",
                "registration_qc.json",
                "normalization_qc.json",
                "metric_outputs",
            ],
            outputs=[
                "outputs/reports/rsfmri/{subject_id}_qc_report.md",
                "outputs/reports/rsfmri/{subject_id}_qc_summary.json",
            ],
            parameters={
                "fd_threshold": 0.5,
                "include_metric_snapshots": True,
            },
            depends_on=["motion_qc", "normalization", "alff", "falff", "reho"],
            parallel_level="subject",
            gpu_supported=False,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "subject_qc_status",
                "warnings_count",
                "failed_steps",
            ],
            failure_modes=[
                "missing_qc_inputs",
            ],
            diagnostic_hints=[
                "Check upstream QC outputs.",
            ],
            safety_notes=[
                "Report only.",
            ],
        ),
        PreprocessingStepSpec(
            step_id="dataset_qc_report",
            name="Dataset QC Report",
            category="reporting",
            backend="report",
            description="Aggregate all subject QC summaries into a dataset-level report.",
            inputs=["outputs/reports/rsfmri/*_qc_summary.json"],
            outputs=[
                "outputs/reports/rsfmri/dataset_qc_summary.json",
                "outputs/reports/rsfmri/dataset_qc_report.md",
                "outputs/reports/rsfmri/dataset_qc_report.html",
            ],
            parameters={
                "include_outlier_table": True,
                "include_group_motion_summary": True,
            },
            depends_on=["subject_qc_report"],
            parallel_level="project",
            gpu_supported=False,
            matlab_required=False,
            approval_required=False,
            cacheable=True,
            qc_metrics=[
                "subjects_total",
                "subjects_pass",
                "subjects_warning",
                "subjects_fail",
                "group_mean_fd",
            ],
            failure_modes=[
                "missing_subject_qc",
            ],
            diagnostic_hints=[
                "Check subject-level reports.",
            ],
            safety_notes=[
                "Report only.",
            ],
        ),
    ]


def get_rsfmri_core_step_registry_dict() -> list[dict]:
    return [step_to_dict(step) for step in get_rsfmri_core_step_registry()]
