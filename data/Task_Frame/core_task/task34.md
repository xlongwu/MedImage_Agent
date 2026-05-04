你是我的工程搭建助手。前三十三步已经完成了 MedImage Agent 的工程外壳、安全执行框架、DPABI wrapper 探测、模板化、实验追踪、artifact browser、reproducibility bundle、release readiness 和 deployment profile。

但现在项目需要回到核心目标：

构建一个面向医学影像数据，尤其是 rs-fMRI 数据的智能预处理 Agent。

当前项目已经具备：

- Pipeline runtime
- Agent runtime
- Plan / Execute / Approval 机制
- MATLAB / SPM / DPABI 环境探测
- DPABI wrapper sandbox
- DPABI single-function wrapper
- 前后端可视化
- 报告系统
- 实验追踪
- artifact browser
- release / deployment readiness

但是还没有真正建立医学影像预处理的核心流程。

现在开始第三十四步。

第三十四步目标：实现 “rs-fMRI Core Preprocessing Protocol + Step Registry + Real Pipeline DAG 闭环”。

本步骤的核心目标不是执行完整真实预处理，而是正式定义 rs-fMRI 的核心预处理协议、步骤注册表、pipeline DAG、参数 schema 和 plan report，为后续真实 wrapper 实现打基础。

本步骤要实现：

1. 定义 rs-fMRI 标准预处理协议。
2. 定义每个 preprocessing step 的统一 schema。
3. 建立 preprocessing step registry。
4. 建立 rs-fMRI core pipeline DAG。
5. 区分 SPM step、DPABI step、Python QC step、GPU candidate step。
6. 定义每个 step 的输入、输出、参数、并行能力、GPU 能力、QC 指标和失败诊断。
7. 生成 preprocessing plan JSON。
8. 生成 preprocessing plan Markdown report。
9. 将 rsfmri_preprocessing_plan 作为 project-level pipeline node 接入。
10. 后端 API 暴露 rs-fMRI preprocessing plan。
11. 前端新增 rs-fMRI Core Pipeline Plan 面板。
12. 增加轻量 unit test。

本步骤不要做：

- 不要运行完整 rs-fMRI preprocessing。
- 不要调用 DPARSF_run。
- 不要调用 DPARSFA_run。
- 不要调用 DPABI GUI。
- 不要处理真实医学影像数据。
- 不要修改 rawdata。
- 不要修改 SPM / DPABI 源码。
- 不要删除文件。
- 不要实现所有 wrapper。
- 不要继续做 Docker / release / CI 这类外围功能。

本步骤只做核心预处理协议、step registry、pipeline DAG 和 plan report。

---

## 1. 创建 specs/rsfmri_preprocessing_protocol.md

创建文件：

```text
specs/rsfmri_preprocessing_protocol.md

内容：

# rs-fMRI Preprocessing Protocol

This document defines the MVP rs-fMRI preprocessing protocol for MedImage Agent.

## Goal

The goal is to define a transparent, auditable, and extensible preprocessing pipeline for resting-state fMRI datasets.

This protocol is not a clinical recommendation. It is an engineering protocol used to structure preprocessing execution, QC, acceleration, and reporting.

## Core Pipeline

The MVP rs-fMRI preprocessing pipeline contains the following stages:

1. Dataset inspection
2. Subject/session/run indexing
3. Anatomical-functional pairing
4. Slice timing correction
5. Realignment
6. Motion QC
7. Coregistration
8. Segmentation
9. Normalization
10. Spatial smoothing
11. Nuisance regression
12. Temporal filtering
13. ALFF
14. fALFF
15. ReHo
16. Functional connectivity preparation
17. Subject-level QC
18. Dataset-level report

## Step Categories

Each step belongs to one of these categories:

- data_inspection
- spm_preprocessing
- dpabi_preprocessing
- python_qc
- gpu_candidate
- reporting

## Backend Types

Supported backend types:

- python
- matlab-spm
- matlab-dpabi
- python-gpu
- report

## Parallelization Levels

Supported parallelization levels:

- project
- subject
- session
- run
- volume

## Safety Rules

The protocol must not:

- modify rawdata
- call DPARSF_run
- call DPARSFA_run
- call DPABI GUI
- execute full DPABI pipelines without explicit approval
- delete files
- overwrite source data

## QC Metrics

The protocol should support at least:

- framewise displacement
- mean FD
- max FD
- number of high-motion frames
- DVARS
- tSNR
- registration quality
- normalization quality
- output existence
- shape consistency
- voxel size consistency
- subject-level pass/warning/fail state

## Agent Responsibilities

The preprocessing agent should:

1. inspect the dataset
2. infer a preprocessing plan
3. explain the plan
4. request approval before execution
5. execute approved steps
6. monitor progress
7. diagnose failures
8. collect QC metrics
9. generate reports

## Current Step Scope

This step only defines the protocol, registry, DAG, and plan report.

It does not execute real preprocessing.
2. 创建 backend/app/preprocessing/step_schema.py

创建目录：

backend/app/preprocessing/

创建文件：

backend/app/preprocessing/step_schema.py

内容：

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


BackendType = Literal[
    "python",
    "matlab-spm",
    "matlab-dpabi",
    "python-gpu",
    "report",
]

ParallelLevel = Literal[
    "project",
    "subject",
    "session",
    "run",
    "volume",
]

StepCategory = Literal[
    "data_inspection",
    "spm_preprocessing",
    "dpabi_preprocessing",
    "python_qc",
    "gpu_candidate",
    "reporting",
]


@dataclass(frozen=True)
class PreprocessingStepSpec:
    step_id: str
    name: str
    category: StepCategory
    backend: BackendType
    description: str
    inputs: list[str]
    outputs: list[str]
    parameters: dict[str, Any]
    depends_on: list[str]
    parallel_level: ParallelLevel
    gpu_supported: bool
    matlab_required: bool
    approval_required: bool
    cacheable: bool
    qc_metrics: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    diagnostic_hints: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)


def step_to_dict(step: PreprocessingStepSpec) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "name": step.name,
        "category": step.category,
        "backend": step.backend,
        "description": step.description,
        "inputs": step.inputs,
        "outputs": step.outputs,
        "parameters": step.parameters,
        "depends_on": step.depends_on,
        "parallel_level": step.parallel_level,
        "gpu_supported": step.gpu_supported,
        "matlab_required": step.matlab_required,
        "approval_required": step.approval_required,
        "cacheable": step.cacheable,
        "qc_metrics": step.qc_metrics,
        "failure_modes": step.failure_modes,
        "diagnostic_hints": step.diagnostic_hints,
        "safety_notes": step.safety_notes,
    }
3. 创建 backend/app/preprocessing/rsfmri_step_registry.py

创建文件：

backend/app/preprocessing/rsfmri_step_registry.py

内容：

from __future__ import annotations

from backend.app.preprocessing.step_schema import PreprocessingStepSpec, step_to_dict


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
4. 创建 backend/app/preprocessing/rsfmri_plan_builder.py

创建文件：

backend/app/preprocessing/rsfmri_plan_builder.py

内容：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.preprocessing.rsfmri_step_registry import (
    get_rsfmri_core_step_registry_dict,
)


def build_rsfmri_preprocessing_plan(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    modality: str = "rs-fMRI",
    pipeline_id: str = "rsfmri_core_preprocessing",
) -> dict[str, Any]:
    steps = get_rsfmri_core_step_registry_dict()

    out_dir = Path(work_dir) / "preprocessing" / "rsfmri"
    report_out = Path(report_dir) / "rsfmri"

    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    approval_required_steps = [
        step["step_id"]
        for step in steps
        if step.get("approval_required")
    ]

    matlab_steps = [
        step["step_id"]
        for step in steps
        if step.get("matlab_required")
    ]

    gpu_candidate_steps = [
        step["step_id"]
        for step in steps
        if step.get("gpu_supported")
    ]

    dpabi_steps = [
        step["step_id"]
        for step in steps
        if step.get("backend") == "matlab-dpabi"
    ]

    spm_steps = [
        step["step_id"]
        for step in steps
        if step.get("backend") == "matlab-spm"
    ]

    plan = {
        "ok": True,
        "node_id": "rsfmri_preprocessing_plan",
        "backend": "python",
        "pipeline_id": pipeline_id,
        "modality": modality,
        "version": "0.1.0",
        "description": "Core rs-fMRI preprocessing plan. This is a planning artifact and does not execute preprocessing.",
        "steps_total": len(steps),
        "steps": steps,
        "summary": {
            "approval_required_steps": approval_required_steps,
            "approval_required_count": len(approval_required_steps),
            "matlab_steps": matlab_steps,
            "matlab_steps_count": len(matlab_steps),
            "spm_steps": spm_steps,
            "dpabi_steps": dpabi_steps,
            "gpu_candidate_steps": gpu_candidate_steps,
            "gpu_candidate_count": len(gpu_candidate_steps),
        },
        "safety": {
            "plan_only": True,
            "preprocessing_executed": False,
            "matlab_launched": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dparsfa_run_executed": False,
            "dpabi_gui_called": False,
            "rawdata_modified": False,
            "files_deleted": False,
        },
        "warnings": [],
        "errors": [],
    }

    json_path = out_dir / "rsfmri_preprocessing_plan.json"
    report_path = report_out / "rsfmri_preprocessing_plan_report.md"

    json_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Core Preprocessing Plan")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Pipeline ID: {pipeline_id}")
    lines.append(f"- Modality: {modality}")
    lines.append(f"- Steps total: {len(steps)}")
    lines.append(f"- Approval-required steps: {len(approval_required_steps)}")
    lines.append(f"- MATLAB-required steps: {len(matlab_steps)}")
    lines.append(f"- GPU candidate steps: {len(gpu_candidate_steps)}")
    lines.append("")
    lines.append("## Step DAG")
    lines.append("")
    lines.append("| Step | Backend | Parallel | GPU | Approval | Depends On |")
    lines.append("|---|---|---|---:|---:|---|")

    for step in steps:
        lines.append(
            f"| {step['step_id']} | {step['backend']} | "
            f"{step['parallel_level']} | {step['gpu_supported']} | "
            f"{step['approval_required']} | {', '.join(step['depends_on']) or '-'} |"
        )

    lines.append("")
    lines.append("## DPABI Safety")
    lines.append("")
    lines.append("- DPARSF_run is not used.")
    lines.append("- DPARSFA_run is not used.")
    lines.append("- DPABI GUI is not used.")
    lines.append("- DPABI steps require explicit wrappers and approval.")
    lines.append("")
    lines.append("## Safety State")
    lines.append("")
    for key, value in plan["safety"].items():
        lines.append(f"- {key}: {value}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    plan["outputs"] = [str(json_path), str(report_path)]
    return plan
5. 创建 backend/app/tools/rsfmri_plan_tool.py

创建文件：

backend/app/tools/rsfmri_plan_tool.py

内容：

from __future__ import annotations

from typing import Any

from backend.app.preprocessing.rsfmri_plan_builder import (
    build_rsfmri_preprocessing_plan,
)


def write_rsfmri_preprocessing_plan(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    return build_rsfmri_preprocessing_plan(
        work_dir=work_dir,
        report_dir=report_dir,
    )
6. 修改 backend/app/runtime/node_registry.py

新增节点：

rsfmri_preprocessing_plan

新增导入：

from backend.app.tools.rsfmri_plan_tool import write_rsfmri_preprocessing_plan

新增 runner：

def run_rsfmri_preprocessing_plan_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_rsfmri_preprocessing_plan(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"rsfmri_preprocessing_plan": run_rsfmri_preprocessing_plan_node,
7. 创建 examples/pipeline_rsfmri_core_plan.yaml

创建文件：

examples/pipeline_rsfmri_core_plan.yaml

内容：

pipeline_id: rsfmri_core_plan_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Generate rs-fMRI core preprocessing protocol, step registry, DAG, and plan report. No preprocessing execution."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_core_plan_001"
  scheduler:
    mode: "sequential"
    max_workers: 1
    matlab_max_workers: 1

nodes:
  - id: rsfmri_preprocessing_plan
    name: rs-fMRI Core Preprocessing Plan
    agent: preprocessing-planner
    backend: python
    depends_on: []
    inputs: []
    outputs:
      - "./work/preprocessing/rsfmri/rsfmri_preprocessing_plan.json"
      - "./reports/rsfmri/rsfmri_preprocessing_plan_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false
8. 创建 backend/app/tools/run_rsfmri_core_plan_cli.py

创建文件：

backend/app/tools/run_rsfmri_core_plan_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_rsfmri_core_plan.yaml")

    summary = run_pipeline(project_config, pipeline)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    status = summary.get("status")
    if status == "SUCCESS":
        return 0
    if status == "INVALID":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
9. 修改 backend/app/api/routes.py

新增 API：

GET  /api/rsfmri/preprocessing-plan
POST /api/rsfmri/preprocessing-plan/refresh

新增导入：

from backend.app.tools.rsfmri_plan_tool import write_rsfmri_preprocessing_plan

新增路由：

@router.get("/api/rsfmri/preprocessing-plan")
def api_get_rsfmri_preprocessing_plan() -> dict[str, Any]:
    work_base = Path("work") / "preprocessing" / "rsfmri"
    report_base = Path("reports") / "rsfmri"

    plan = _read_json_if_exists(work_base / "rsfmri_preprocessing_plan.json")
    report = _read_text_if_exists(report_base / "rsfmri_preprocessing_plan_report.md")

    if plan is None:
        plan = write_rsfmri_preprocessing_plan(
            work_dir="./work",
            report_dir="./reports",
        )

    return {
        "ok": True,
        "plan": plan,
        "report": report,
    }


@router.post("/api/rsfmri/preprocessing-plan/refresh")
def api_refresh_rsfmri_preprocessing_plan() -> dict[str, Any]:
    result = write_rsfmri_preprocessing_plan(
        work_dir="./work",
        report_dir="./reports",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result
10. 修改 frontend/src/api.ts

新增：

export async function getRsfmriPreprocessingPlan(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/preprocessing-plan"
  );
}

export async function refreshRsfmriPreprocessingPlan(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/preprocessing-plan/refresh",
    { method: "POST" }
  );
}
11. 创建 frontend/src/components/RsfmriPreprocessingPlanPanel.tsx

创建文件：

frontend/src/components/RsfmriPreprocessingPlanPanel.tsx

内容：

import { useState } from "react";
import {
  getRsfmriPreprocessingPlan,
  refreshRsfmriPreprocessingPlan
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriPreprocessingPlanPanel({ baseUrl }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getRsfmriPreprocessingPlan(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleRefresh() {
    setStatus("REFRESHING");
    setError("");

    try {
      const result = await refreshRsfmriPreprocessingPlan(baseUrl);
      setPayload({
        ok: true,
        plan: result
      });
      setStatus("REFRESHED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const plan = payload?.plan as Record<string, unknown> | undefined;
  const summary = plan?.summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleLoad}>加载 rs-fMRI Preprocessing Plan</button>
        <button onClick={handleRefresh}>刷新 Plan</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Steps</span>
          <strong>{String(plan?.steps_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Approval Steps</span>
          <strong>{String(summary?.approval_required_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>MATLAB Steps</span>
          <strong>{String(summary?.matlab_steps_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>GPU Candidates</span>
          <strong>{String(summary?.gpu_candidate_count ?? "-")}</strong>
        </div>
      </div>

      <h3>rs-fMRI Preprocessing Plan JSON</h3>
      <JsonBlock value={plan} emptyText="尚未加载 plan" />

      <h3>rs-fMRI Preprocessing Plan Report</h3>
      <TextViewer
        text={
          typeof payload?.report === "string"
            ? payload.report
            : null
        }
        emptyText="暂无 plan report"
      />
    </div>
  );
}
12. 修改 frontend/src/App.tsx

新增导入：

import { RsfmriPreprocessingPlanPanel } from "./components/RsfmriPreprocessingPlanPanel";

在比较靠前的位置，建议放在 Environment / DPABI Panel 前后，新增 Section：

<Section
  title="rs-fMRI Core Preprocessing Plan"
  description="定义 rs-fMRI 预处理协议、step registry、DAG、参数 schema、QC 指标和安全约束。"
>
  <RsfmriPreprocessingPlanPanel baseUrl={baseUrl} />
</Section>
13. 新增轻量测试

创建文件：

tests/unit/test_rsfmri_plan_builder.py

内容：

from __future__ import annotations

from pathlib import Path

from backend.app.preprocessing.rsfmri_plan_builder import (
    build_rsfmri_preprocessing_plan,
)
from backend.app.preprocessing.rsfmri_step_registry import (
    get_rsfmri_core_step_registry_dict,
)


def test_rsfmri_step_registry_contains_core_steps():
    steps = get_rsfmri_core_step_registry_dict()
    step_ids = {step["step_id"] for step in steps}

    assert "dataset_inspection" in step_ids
    assert "realignment" in step_ids
    assert "motion_qc" in step_ids
    assert "normalization" in step_ids
    assert "smoothing" in step_ids
    assert "nuisance_regression" in step_ids
    assert "temporal_filtering" in step_ids
    assert "alff" in step_ids
    assert "falff" in step_ids
    assert "reho" in step_ids
    assert "dataset_qc_report" in step_ids


def test_rsfmri_plan_builder_is_plan_only(tmp_path: Path):
    work = tmp_path / "work"
    reports = tmp_path / "reports"

    result = build_rsfmri_preprocessing_plan(
        work_dir=str(work),
        report_dir=str(reports),
    )

    assert result["ok"] is True
    assert result["safety"]["plan_only"] is True
    assert result["safety"]["preprocessing_executed"] is False
    assert result["safety"]["matlab_launched"] is False
    assert result["steps_total"] >= 10

    assert (work / "preprocessing" / "rsfmri" / "rsfmri_preprocessing_plan.json").exists()
    assert (reports / "rsfmri" / "rsfmri_preprocessing_plan_report.md").exists()
14. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/rsfmri/preprocessing-plan")

不要在 smoke test 中运行 POST refresh。

15. 更新 README.md

追加第三十四步说明：

## Step 34: rs-fMRI Core Preprocessing Plan

This step introduces the core rs-fMRI preprocessing protocol.

It defines:

- preprocessing protocol
- step registry
- step schema
- pipeline DAG
- SPM-backed steps
- DPABI-backed steps
- Python QC steps
- GPU candidate steps
- QC metrics
- failure modes
- diagnostic hints
- safety gates

It does not execute preprocessing.

### Run

```bash
python -m backend.app.tools.run_rsfmri_core_plan_cli

Expected outputs:

work/preprocessing/rsfmri/rsfmri_preprocessing_plan.json
reports/rsfmri/rsfmri_preprocessing_plan_report.md
work/pipeline_runs/run_rsfmri_core_plan_001/summary.json
API
curl http://127.0.0.1:8000/api/rsfmri/preprocessing-plan

Refresh:

curl -X POST http://127.0.0.1:8000/api/rsfmri/preprocessing-plan/refresh
Frontend

Use:

rs-fMRI Core Preprocessing Plan
Safety

This step:

does not execute preprocessing
does not launch MATLAB
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not modify rawdata
does not delete files

---

## 16. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/rsfmri_preprocessing_protocol.md
backend/app/preprocessing/step_schema.py
backend/app/preprocessing/rsfmri_step_registry.py
backend/app/preprocessing/rsfmri_plan_builder.py
backend/app/tools/rsfmri_plan_tool.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_core_plan.yaml
backend/app/tools/run_rsfmri_core_plan_cli.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriPreprocessingPlanPanel.tsx
frontend/src/App.tsx
tests/unit/test_rsfmri_plan_builder.py
backend/app/tools/api_smoke_test.py
README.md

运行：

python -m backend.app.tools.run_rsfmri_core_plan_cli

应生成：

work/preprocessing/rsfmri/rsfmri_preprocessing_plan.json
reports/rsfmri/rsfmri_preprocessing_plan_report.md
work/pipeline_runs/run_rsfmri_core_plan_001/summary.json

plan JSON 必须包含：

{
  "node_id": "rsfmri_preprocessing_plan",
  "pipeline_id": "rsfmri_core_preprocessing",
  "safety": {
    "plan_only": true,
    "preprocessing_executed": false,
    "matlab_launched": false,
    "dpabi_executed": false,
    "dparsf_run_executed": false,
    "dparsfa_run_executed": false,
    "dpabi_gui_called": false,
    "rawdata_modified": false,
    "files_deleted": false
  }
}

step registry 中必须包含这些核心步骤：

dataset_inspection
anat_func_pairing
slice_timing
realignment
motion_qc
coregistration
segmentation
normalization
smoothing
nuisance_regression
temporal_filtering
alff
falff
reho
subject_qc_report
dataset_qc_report

运行测试：

python -m pytest tests/unit/test_rsfmri_plan_builder.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/rsfmri/preprocessing-plan
curl -X POST http://127.0.0.1:8000/api/rsfmri/preprocessing-plan/refresh

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 rs-fMRI Core Preprocessing Plan 区域。
可以加载 plan。
可以刷新 plan。
显示 step 总数。
显示 approval step 数量。
显示 MATLAB step 数量。
显示 GPU candidate 数量。
显示 plan JSON。
显示 plan report。
不执行 preprocessing。
不启动 MATLAB。
不运行 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不修改 rawdata。
17. 重要限制

本步骤只做 rs-fMRI 核心预处理协议、step registry、DAG 和 plan report。

不要实现：

真实预处理执行
SPM realign wrapper
SPM normalize wrapper
DPABI nuisance regression wrapper
DPABI bandpass wrapper
ReHo wrapper
真实数据处理
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
rawdata 修改
文件删除

完成后请总结：

新增了哪些文件
修改了哪些文件
rs-fMRI core pipeline 包含哪些步骤
每个 step schema 包含哪些字段
哪些步骤需要 MATLAB
哪些步骤是 GPU candidate
哪些步骤需要 approval
为什么本步骤仍然只是 plan，不是 preprocessing execution
下一步如何实现第一个真实核心 wrapper：SPM realignment + motion QC

'''
这一步正式定义了 MedImage Agent 的 rs-fMRI 核心预处理协议和规划层，但没有执行任何真实预处理。

具体做了四件事：

**第一，定义了协议文档。** 在 `specs/rsfmri_preprocessing_protocol.md` 中写明了 rs-fMRI 预处理应该包含哪 18 个阶段（从数据集扫描到最终报告），每个阶段属于什么类型（SPM 步骤、DPABI 步骤、Python QC 步骤、GPU 候选步骤），以及安全红线：不修改 rawdata、不调用 DPARSF_run、不调用 DPABI GUI 等。

**第二，建立了步骤注册表。** 创建了 `PreprocessingStepSpec` 这个统一的数据结构，每个预处理步骤都用 17 个字段精确描述：输入是什么、输出是什么、依赖谁、需要什么参数、能不能并行、用不用 GPU、需不需要审批、可能怎么失败、怎么排查问题。然后用这个 schema 把 16 个核心步骤全部注册进去了，形成了一个可查询、可序列化的 registry。

**第三，生成了预处理计划。** `rsfmri_plan_builder.py` 把这个 registry 组装成一份完整的 plan JSON 和一份 Markdown 报告，里面包含了步骤 DAG 表、审批步骤清单、MATLAB 步骤清单、GPU 候选步骤清单，以及一个 safety 状态对象——明确标注 `plan_only: true`、`preprocessing_executed: false`，表示这只是计划，没有执行。

**第四，接入了全栈。** 这个 plan 通过 node_registry 注册为 pipeline 节点，通过 API 暴露了 GET 和 POST refresh 两个端点，前端新增了一个面板可以加载和刷新 plan，显示步骤总数、审批步骤数、MATLAB 步骤数、GPU 候选数，以及完整的 JSON 和报告。

简单说，这一步是把 "rs-fMRI 预处理到底要做什么、怎么做、每一步的参数和依赖是什么" 这件事用代码系统性地写清楚了，为下一步真正写 SPM realignment wrapper 铺好了路。
'''