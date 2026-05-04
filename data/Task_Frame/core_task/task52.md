# 第五十二步 Prompt：Quickstart Demo Orchestrator + 一键安全演示流程闭环

```text
你是我的工程搭建助手。前五十一步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Slice Timing Correction + Metadata QC
- SPM Realignment + Motion QC
- Slice Timing → Realignment → Motion QC 链式核心 pipeline
- SPM Coregistration + Registration QC
- SPM Segmentation + Tissue QC
- SPM Normalization + Normalization QC
- SPM Smoothing + Smoothing QC
- Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计
- Temporal Filtering + Filtering QC
- ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计
- ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract
- Functional Connectivity ROI/Seed 相关分析 + FC QC + GPU/DPABI Backend Contract
- Group-level Dataset Summary + Cross-subject Metrics Dashboard
- Dataset Report Exporter + 可交付报告包
- Report Package Validator + Integrity / Safety Audit
- Project Release Readiness Check + MVP 发布准备度审计
- MVP User Guide + Developer Guide 文档体系

现在开始第五十二步。

第五十二步目标：实现 “Quickstart Demo Orchestrator + 一键安全演示流程闭环”。

当前项目已经具备完整的工程模块，但新用户仍然需要手动按顺序运行多个 CLI / API：

1. 准备 synthetic derivatives。
2. temporal filtering。
3. ALFF/fALFF。
4. ReHo。
5. Functional Connectivity。
6. Group summary。
7. Report export。
8. Report validation。
9. Docs inventory。
10. Release readiness。

这对演示、评审、MVP walkthrough 来说仍然不够友好。

本步骤要建立一个 **一键安全演示 orchestrator**，让用户可以在完全不运行 SPM / MATLAB / DPABI / GPU 的前提下，生成一个自包含的 synthetic quickstart demo workspace，并自动完成最小可演示闭环：

synthetic demo derivative fixture
→ Python temporal filtering
→ ALFF / fALFF
→ ReHo
→ Functional Connectivity
→ DPABI/GPU contracts
→ Group summary
→ Report exporter
→ Report validator
→ Docs inventory
→ Release readiness
→ Quickstart demo summary

本步骤重点是：**让项目具备“5 分钟内可跑通的安全 MVP 演示路径”**。

---

## 0. 总体约束

本步骤必须满足：

- 默认只运行 safe quickstart demo。
- 只生成 synthetic demo fixture。
- 不处理真实医学影像数据。
- 不读取真实 rawdata。
- 不修改 rawdata。
- 不修改已有 derivatives / reports / work / exports，除非用户显式指定 demo workspace 为这些目录。
- 默认写入：

```text
demo_runs/{demo_id}/
```

- 不运行 SPM。
- 不运行 MATLAB。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不执行 GPU。
- 不要求 CUDA / CuPy / Torch。
- 不做医学结论。
- 不做 clinical interpretation。
- 不做 group-level statistics / inference。
- 不自动排除 subject。
- 不删除文件。
- 不自动修复项目。

本步骤不要实现：

- 真实 SPM preprocessing demo。
- 真实 DPABI demo。
- 真实 GPU demo。
- 真实医学影像处理。
- Docker / CI / release。
- PDF / Word / PPT 生成。
- 在线文档部署。
- 临床报告生成。

本步骤只做：**安全 quickstart demo orchestration**。

---

## 1. 创建 specs/quickstart_demo_orchestrator_spec.md

创建文件：

```text
specs/quickstart_demo_orchestrator_spec.md
```

内容：

```markdown
# Quickstart Demo Orchestrator Specification

This document defines the MVP quickstart demo orchestrator for the MedImage Agent project.

## Goals

The quickstart demo orchestrator creates a self-contained synthetic rs-fMRI demo workspace and runs a safe end-to-end engineering demonstration without requiring MATLAB, SPM, DPABI, GPU, or real medical imaging data.

The goal is to provide a fast MVP walkthrough path for users, developers, reviewers, and demos.

## Scope

Supported in this step:

- synthetic derivative fixture generation
- isolated demo workspace under demo_runs/{demo_id}
- Python temporal filtering
- Python ALFF/fALFF
- Python ReHo
- Python functional connectivity
- group summary
- report export
- report validation
- docs inventory
- release readiness
- quickstart summary JSON
- quickstart Markdown report
- quickstart API
- frontend quickstart panel
- lightweight unit tests

Unsupported in this step:

- real medical image preprocessing
- real rawdata processing
- SPM execution
- MATLAB execution
- DPABI execution
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- GPU execution
- clinical interpretation
- statistical inference
- Docker / CI / release automation

## Default Workspace

```text
demo_runs/{demo_id}/
  derivatives/
  reports/
  work/
  exports/
  logs/
```

## Main Outputs

```text
demo_runs/{demo_id}/quickstart_demo_summary.json
demo_runs/{demo_id}/quickstart_demo_report.md
demo_runs/{demo_id}/derivatives/
demo_runs/{demo_id}/reports/
demo_runs/{demo_id}/work/
demo_runs/{demo_id}/exports/
```

## Demo Stages

Default stage order:

1. create_demo_workspace
2. create_synthetic_derivative_fixture
3. temporal_filtering
4. alff_falff
5. reho
6. functional_connectivity
7. backend_contracts
8. group_summary
9. report_export
10. report_validation
11. docs_inventory
12. release_readiness
13. quickstart_summary

## Safety Rules

- The demo does not read rawdata.
- The demo does not modify rawdata.
- The demo does not execute SPM.
- The demo does not execute MATLAB.
- The demo does not execute DPABI.
- The demo does not execute GPU code.
- The demo writes to the demo workspace only.
- The demo does not make clinical conclusions.
- The demo does not perform statistical inference.
```

---

## 2. 创建 backend/app/tools/quickstart_demo.py

创建文件：

```text
backend/app/tools/quickstart_demo.py
```

目标：实现一键 safe quickstart demo orchestrator。

提供函数：

```python
run_quickstart_demo(
    demo_root: str = "./demo_runs",
    demo_id: str | None = None,
    subject_count: int = 2,
    n_timepoints: int = 40,
    tr: float = 2.0,
    force: bool = False,
) -> dict

get_latest_quickstart_demo(
    demo_root: str = "./demo_runs",
) -> dict

list_quickstart_demos(
    demo_root: str = "./demo_runs",
) -> dict
```

实现要求：

1. 默认生成 demo_id：

```text
quickstart_YYYYmmdd_HHMMSS
```

2. demo workspace：

```text
demo_runs/{demo_id}/
  derivatives/
  reports/
  work/
  exports/
  logs/
```

3. 如果 workspace 已存在且 force=false，则失败。
4. 生成 synthetic derivative fixture：
   - subjects: `sub-001`, `sub-002`, ...
   - 每个 subject 创建：

```text
derivatives/rsfmri_preproc/{subject_id}/func/resid_swra{subject_id}_bold.nii
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
derivatives/rsfmri_qc/{subject_id}/motion_qc.json
derivatives/rsfmri_qc/{subject_id}/registration_qc.json
derivatives/rsfmri_qc/{subject_id}/tissue_qc.json
derivatives/rsfmri_qc/{subject_id}/normalization_qc.json
derivatives/rsfmri_qc/{subject_id}/smoothing_qc.json
derivatives/rsfmri_confounds/{subject_id}/confound_qc.json
```

5. NIfTI 数据：
   - shape 默认 `(6, 6, 6, n_timepoints)`。
   - 每个 subject 使用 deterministic random seed。
   - 数据包含低频成分、少量高频成分和噪声。
   - 只用于工程测试。
6. 调用已有 Python tools：
   - `run_python_temporal_filter_subject`
   - `run_python_alff_falff_subject`
   - `run_python_reho_subject`
   - `run_python_functional_connectivity_subject`
   - `write_dpabi_temporal_filtering_contract`
   - `write_dpabi_alff_falff_contract`
   - `write_dpabi_reho_contract`
   - `write_dpabi_functional_connectivity_contract`
   - `write_alff_falff_gpu_candidate_contract`
   - `write_reho_gpu_candidate_contract`
   - `write_functional_connectivity_gpu_candidate_contract`
   - `build_group_dataset_summary`
   - `export_rsfmri_report_package`
   - `validate_rsfmri_report_package`
   - `build_docs_inventory`
   - `run_project_release_readiness_check`
7. 所有输出必须指向 demo workspace 内部：
   - derivatives_dir = demo_workspace / derivatives
   - reports_dir = demo_workspace / reports
   - work_dir = demo_workspace / work
   - exports_dir = demo_workspace / exports
8. docs inventory 和 release readiness 可以读取 project root `"."`，但输出写到 demo workspace reports。
9. 不通过 subprocess 调用 CLI。
10. 不运行 pipeline_executor，避免 nested pipeline side effects；本 orchestrator 直接调用工具函数。
11. 每个 stage 都要记录：
   - stage_id
   - ok
   - started_at
   - finished_at
   - duration_seconds
   - outputs
   - warnings
   - errors
12. 任一核心 stage 失败，不要删除 workspace；继续记录失败并停止后续依赖 stage。
13. 生成：

```text
demo_runs/{demo_id}/quickstart_demo_summary.json
demo_runs/{demo_id}/quickstart_demo_report.md
```

14. summary 包含：
   - demo_id
   - workspace
   - subject_ids
   - stages
   - outputs
   - safety
   - warnings
   - errors
15. 不复制 rawdata。
16. 不删除文件。

参考实现：

```python
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _demo_id() -> str:
    return datetime.now().strftime("quickstart_%Y%m%d_%H%M%S")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _subject_ids(subject_count: int) -> list[str]:
    return [f"sub-{idx:03d}" for idx in range(1, subject_count + 1)]


def _stage(stage_id: str, func, *args, **kwargs) -> dict[str, Any]:
    started = _iso_now()
    t0 = time.time()
    try:
        result = func(*args, **kwargs)
        ok = bool(result.get("ok", False)) if isinstance(result, dict) else True
        warnings = result.get("warnings", []) if isinstance(result, dict) else []
        errors = result.get("errors", []) if isinstance(result, dict) else []
        outputs = result.get("outputs", []) if isinstance(result, dict) else []
        payload = result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        ok = False
        warnings = []
        errors = [str(exc)]
        outputs = []
        payload = {"exception": str(exc)}
    finished = _iso_now()
    return {
        "stage_id": stage_id,
        "ok": ok,
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": round(time.time() - t0, 4),
        "outputs": outputs,
        "warnings": warnings,
        "errors": errors,
        "result": payload,
    }


def _write_demo_report(path: Path, summary: dict[str, Any]) -> None:
    lines = []
    lines.append("# Quickstart Demo Report")
    lines.append("")
    lines.append(f"- Demo ID: `{summary.get('demo_id')}`")
    lines.append(f"- Status: **{summary.get('demo_status')}**")
    lines.append(f"- Workspace: `{summary.get('workspace')}`")
    lines.append(f"- Subjects: {', '.join(summary.get('subject_ids', []))}")
    lines.append("")
    lines.append("## Stages")
    lines.append("")
    lines.append("| Stage | OK | Duration seconds | Warnings | Errors |")
    lines.append("|---|---|---:|---:|---:|")
    for stage in summary.get("stages", []):
        lines.append(
            f"| {stage.get('stage_id')} | {stage.get('ok')} | {stage.get('duration_seconds')} | "
            f"{len(stage.get('warnings', []))} | {len(stage.get('errors', []))} |"
        )
    lines.append("")
    lines.append("## Key Outputs")
    lines.append("")
    for output in summary.get("outputs", []):
        lines.append(f"- `{output}`")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    for key, value in summary.get("safety", {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("This quickstart demo uses synthetic derivative fixtures only. It is not a clinical workflow and does not process real medical images.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_workspace(demo_root: str, demo_id: str, force: bool) -> tuple[Path, dict[str, Path]]:
    workspace = Path(demo_root) / demo_id
    if workspace.exists():
        if not force:
            raise FileExistsError(f"Demo workspace already exists: {workspace}")
        shutil.rmtree(workspace)

    dirs = {
        "workspace": workspace,
        "derivatives": workspace / "derivatives",
        "reports": workspace / "reports",
        "work": workspace / "work",
        "exports": workspace / "exports",
        "logs": workspace / "logs",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return workspace, dirs


def _create_synthetic_derivative_fixture(
    derivatives_dir: str,
    subject_ids: list[str],
    n_timepoints: int,
    tr: float,
) -> dict[str, Any]:
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    derivatives = Path(derivatives_dir)
    outputs = []

    for sidx, subject_id in enumerate(subject_ids):
        func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
        qc_dir = derivatives / "rsfmri_qc" / subject_id
        conf_dir = derivatives / "rsfmri_confounds" / subject_id

        func_dir.mkdir(parents=True, exist_ok=True)
        qc_dir.mkdir(parents=True, exist_ok=True)
        conf_dir.mkdir(parents=True, exist_ok=True)

        rng = np.random.default_rng(1000 + sidx)
        shape = (6, 6, 6, int(n_timepoints))
        t = np.arange(n_timepoints, dtype=np.float32) * float(tr)

        low = np.sin(2 * np.pi * 0.03 * t)
        high = 0.25 * np.sin(2 * np.pi * 0.18 * t)
        drift = 0.05 * np.linspace(-1, 1, n_timepoints)
        base = low + high + drift

        data = np.zeros(shape, dtype=np.float32)
        for x in range(shape[0]):
            for y in range(shape[1]):
                for z in range(shape[2]):
                    scale = 1.0 + 0.02 * (x + y + z)
                    noise = 0.05 * rng.normal(size=n_timepoints)
                    data[x, y, z, :] = (scale * base + noise).astype(np.float32)

        nii = func_dir / f"resid_swra{subject_id}_bold.nii"
        nib.save(nib.Nifti1Image(data, affine=np.eye(4)), str(nii))
        outputs.append(str(nii))

        qc_payloads = {
            "slice_timing_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "slice_timing_status": "PASS",
                "tr": float(tr),
                "warnings": [],
                "errors": [],
            },
            "motion_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "motion_qc_status": "PASS",
                "mean_fd": round(0.05 + 0.01 * sidx, 4),
                "max_fd": round(0.12 + 0.01 * sidx, 4),
                "warnings": [],
                "errors": [],
            },
            "registration_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "registration_qc_status": "PASS",
                "warnings": [],
                "errors": [],
            },
            "tissue_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "segmentation_qc_status": "PASS",
                "gm_volume_mm3": 500000 + 1000 * sidx,
                "wm_volume_mm3": 420000 + 1000 * sidx,
                "csf_volume_mm3": 180000 + 500 * sidx,
                "warnings": [],
                "errors": [],
            },
            "normalization_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "normalization_qc_status": "PASS",
                "finite_fraction": 1.0,
                "warnings": [],
                "errors": [],
            },
            "smoothing_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "smoothing_qc_status": "PASS",
                "variance_reduction_ratio": 0.85,
                "warnings": [],
                "errors": [],
            },
            "nuisance_regression_qc.json": {
                "ok": True,
                "subject_id": subject_id,
                "regression_qc_status": "PASS",
                "variance_ratio": 0.75,
                "warnings": [],
                "errors": [],
            },
        }

        for filename, payload in qc_payloads.items():
            path = qc_dir / filename
            _write_json(path, payload)
            outputs.append(str(path))

        confound_qc = {
            "ok": True,
            "subject_id": subject_id,
            "confound_qc_status": "PASS",
            "qc": {
                "rows": int(n_timepoints),
                "columns": 8,
                "rank": 8,
            },
            "warnings": [],
            "errors": [],
        }
        conf_path = conf_dir / "confound_qc.json"
        _write_json(conf_path, confound_qc)
        outputs.append(str(conf_path))

    return {
        "ok": True,
        "node_id": "quickstart_synthetic_derivative_fixture",
        "backend": "python",
        "subject_ids": subject_ids,
        "outputs": outputs,
        "warnings": [],
        "errors": [],
    }


def run_quickstart_demo(
    demo_root: str = "./demo_runs",
    demo_id: str | None = None,
    subject_count: int = 2,
    n_timepoints: int = 40,
    tr: float = 2.0,
    force: bool = False,
) -> dict[str, Any]:
    demo_id = demo_id or _demo_id()
    subject_count = int(subject_count)
    n_timepoints = int(n_timepoints)
    tr = float(tr)

    if subject_count < 1:
        raise ValueError("subject_count must be >= 1.")
    if n_timepoints < 8:
        raise ValueError("n_timepoints must be >= 8.")
    if tr <= 0:
        raise ValueError("tr must be positive.")

    workspace, dirs = _create_workspace(demo_root, demo_id, force=force)
    subject_ids = _subject_ids(subject_count)

    stages = []
    outputs = []

    fixture_stage = _stage(
        "create_synthetic_derivative_fixture",
        _create_synthetic_derivative_fixture,
        derivatives_dir=str(dirs["derivatives"]),
        subject_ids=subject_ids,
        n_timepoints=n_timepoints,
        tr=tr,
    )
    stages.append(fixture_stage)

    if not fixture_stage["ok"]:
        return _finalize_quickstart_summary(workspace, demo_id, subject_ids, stages)

    from backend.app.tools.temporal_filtering import run_python_temporal_filter_subject
    from backend.app.tools.alff_falff import run_python_alff_falff_subject
    from backend.app.tools.reho import run_python_reho_subject
    from backend.app.tools.functional_connectivity import run_python_functional_connectivity_subject
    from backend.app.tools.dpabi_filtering_contract import write_dpabi_temporal_filtering_contract
    from backend.app.tools.dpabi_alff_contract import write_dpabi_alff_falff_contract
    from backend.app.tools.dpabi_reho_contract import write_dpabi_reho_contract
    from backend.app.tools.dpabi_fc_contract import write_dpabi_functional_connectivity_contract
    from backend.app.tools.gpu_alff_contract import write_alff_falff_gpu_candidate_contract
    from backend.app.tools.gpu_reho_contract import write_reho_gpu_candidate_contract
    from backend.app.tools.gpu_fc_contract import write_functional_connectivity_gpu_candidate_contract
    from backend.app.tools.group_dataset_summary import build_group_dataset_summary
    from backend.app.tools.report_exporter import export_rsfmri_report_package
    from backend.app.tools.report_package_validator import validate_rsfmri_report_package
    from backend.app.tools.docs_inventory import build_docs_inventory
    from backend.app.tools.release_readiness import run_project_release_readiness_check

    for subject_id in subject_ids:
        stages.append(_stage(
            f"temporal_filtering:{subject_id}",
            run_python_temporal_filter_subject,
            subject_id=subject_id,
            derivatives_dir=str(dirs["derivatives"]),
            low_hz=0.01,
            high_hz=0.08,
            fallback_tr=tr,
        ))

        stages.append(_stage(
            f"alff_falff:{subject_id}",
            run_python_alff_falff_subject,
            subject_id=subject_id,
            derivatives_dir=str(dirs["derivatives"]),
            fallback_tr=tr,
        ))

        stages.append(_stage(
            f"reho:{subject_id}",
            run_python_reho_subject,
            subject_id=subject_id,
            derivatives_dir=str(dirs["derivatives"]),
            neighborhood=27,
            use_gm_mask=False,
        ))

        stages.append(_stage(
            f"functional_connectivity:{subject_id}",
            run_python_functional_connectivity_subject,
            subject_id=subject_id,
            derivatives_dir=str(dirs["derivatives"]),
            roi_count=4,
            generate_seed_map=True,
        ))

    stages.append(_stage("dpabi_temporal_filtering_contract", write_dpabi_temporal_filtering_contract, work_dir=str(dirs["work"])))
    stages.append(_stage("dpabi_alff_falff_contract", write_dpabi_alff_falff_contract, work_dir=str(dirs["work"])))
    stages.append(_stage("dpabi_reho_contract", write_dpabi_reho_contract, work_dir=str(dirs["work"])))
    stages.append(_stage("dpabi_functional_connectivity_contract", write_dpabi_functional_connectivity_contract, work_dir=str(dirs["work"])))
    stages.append(_stage("gpu_alff_falff_contract", write_alff_falff_gpu_candidate_contract, work_dir=str(dirs["work"])))
    stages.append(_stage("gpu_reho_contract", write_reho_gpu_candidate_contract, work_dir=str(dirs["work"])))
    stages.append(_stage("gpu_functional_connectivity_contract", write_functional_connectivity_gpu_candidate_contract, work_dir=str(dirs["work"])))

    stages.append(_stage(
        "group_dataset_summary",
        build_group_dataset_summary,
        derivatives_dir=str(dirs["derivatives"]),
        reports_dir=str(dirs["reports"]),
        work_dir=str(dirs["work"]),
    ))

    stages.append(_stage(
        "report_export",
        export_rsfmri_report_package,
        derivatives_dir=str(dirs["derivatives"]),
        reports_dir=str(dirs["reports"]),
        work_dir=str(dirs["work"]),
        exports_dir=str(dirs["exports"]),
        export_id=f"{demo_id}_report",
    ))

    stages.append(_stage(
        "report_validation",
        validate_rsfmri_report_package,
        exports_dir=str(dirs["exports"]),
        export_id=f"{demo_id}_report",
    ))

    stages.append(_stage(
        "docs_inventory",
        build_docs_inventory,
        project_root=".",
        reports_dir=str(dirs["reports"]),
    ))

    stages.append(_stage(
        "release_readiness",
        run_project_release_readiness_check,
        project_root=".",
        reports_dir=str(dirs["reports"]),
        exports_dir=str(dirs["exports"]),
        strict=False,
    ))

    return _finalize_quickstart_summary(workspace, demo_id, subject_ids, stages)


def _finalize_quickstart_summary(
    workspace: Path,
    demo_id: str,
    subject_ids: list[str],
    stages: list[dict[str, Any]],
) -> dict[str, Any]:
    warnings = []
    errors = []
    outputs = []

    for stage in stages:
        warnings.extend(stage.get("warnings", []))
        errors.extend(stage.get("errors", []))
        outputs.extend(stage.get("outputs", []))

    fail_count = sum(1 for stage in stages if not stage.get("ok"))
    warning_count = sum(len(stage.get("warnings", [])) for stage in stages)

    if fail_count > 0:
        status = "FAIL"
    elif warning_count > 0:
        status = "WARNING"
    else:
        status = "PASS"

    summary_path = workspace / "quickstart_demo_summary.json"
    report_path = workspace / "quickstart_demo_report.md"

    summary = {
        "ok": status in {"PASS", "WARNING"},
        "node_id": "quickstart_demo",
        "backend": "python",
        "demo_id": demo_id,
        "demo_status": status,
        "workspace": str(workspace),
        "subject_ids": subject_ids,
        "stages": stages,
        "stage_counts": {
            "total": len(stages),
            "failed": fail_count,
            "warnings": warning_count,
        },
        "outputs": [
            str(summary_path),
            str(report_path),
            *outputs,
        ],
        "safety": {
            "synthetic_demo_only": True,
            "rawdata_read": False,
            "rawdata_modified": False,
            "spm_executed": False,
            "matlab_executed": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dparsfa_run_executed": False,
            "dpabi_gui_called": False,
            "gpu_executed": False,
            "statistical_inference_performed": False,
            "clinical_conclusions_generated": False,
            "files_deleted": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    _write_json(summary_path, summary)
    _write_demo_report(report_path, summary)
    return summary


def list_quickstart_demos(
    demo_root: str = "./demo_runs",
) -> dict[str, Any]:
    root = Path(demo_root)
    demos = []

    if root.exists():
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue

            summary = _read_json(child / "quickstart_demo_summary.json") or {}
            demos.append({
                "demo_id": child.name,
                "workspace": str(child),
                "demo_status": summary.get("demo_status"),
                "ok": summary.get("ok"),
                "subject_ids": summary.get("subject_ids"),
                "stage_counts": summary.get("stage_counts"),
            })

    return {
        "ok": True,
        "demos_total": len(demos),
        "demos": demos,
    }


def get_latest_quickstart_demo(
    demo_root: str = "./demo_runs",
) -> dict[str, Any]:
    root = Path(demo_root)
    if not root.exists():
        return {
            "ok": False,
            "warnings": [],
            "errors": ["No quickstart demo root found."],
        }

    demos = sorted([child for child in root.iterdir() if child.is_dir()])
    if not demos:
        return {
            "ok": False,
            "warnings": [],
            "errors": ["No quickstart demo found."],
        }

    latest = demos[-1]
    summary = _read_json(latest / "quickstart_demo_summary.json")
    report_path = latest / "quickstart_demo_report.md"

    return {
        "ok": bool(summary),
        "demo_id": latest.name,
        "workspace": str(latest),
        "summary": summary,
        "report": report_path.read_text(encoding="utf-8") if report_path.exists() else None,
    }
```

---

## 3. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
quickstart_demo
```

新增导入：

```python
from backend.app.tools.quickstart_demo import run_quickstart_demo
```

新增 runner：

```python
def run_quickstart_demo_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_quickstart_demo(
        demo_root=node.params.get("demo_root", "./demo_runs"),
        demo_id=node.params.get("demo_id"),
        subject_count=int(node.params.get("subject_count", 2)),
        n_timepoints=int(node.params.get("n_timepoints", 40)),
        tr=float(node.params.get("tr", 2.0)),
        force=bool(node.params.get("force", False)),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"quickstart_demo": run_quickstart_demo_node,
```

---

## 4. 创建 examples/pipeline_quickstart_demo.yaml

创建文件：

```text
examples/pipeline_quickstart_demo.yaml
```

内容：

```yaml
pipeline_id: quickstart_demo_pipeline
version: "0.1.0"
modality: project
description: "Run a safe one-command synthetic quickstart demo without SPM, MATLAB, DPABI, or GPU execution."

execution:
  stop_on_failure: true
  run_id: "run_quickstart_demo_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: quickstart_demo
    name: Quickstart Demo Orchestrator
    agent: demo-runner
    backend: python
    depends_on: []
    inputs:
      - "."
    outputs:
      - "./demo_runs"
    params:
      demo_root: "./demo_runs"
      demo_id: null
      subject_count: 2
      n_timepoints: 40
      tr: 2.0
      force: false
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只生成 synthetic demo workspace，并运行 Python-only safe demo workflow。

---

## 5. 创建 backend/app/tools/run_quickstart_demo_cli.py

创建文件：

```text
backend/app/tools/run_quickstart_demo_cli.py
```

内容：

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    args = sys.argv[1:]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_quickstart_demo.yaml")

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
```

---

## 6. 修改 backend/app/api/models.py

新增 request model：

```python
class QuickstartDemoRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_quickstart_demo.yaml")
```

---

## 7. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/quickstart-demo/run
GET  /api/quickstart-demo/latest
GET  /api/quickstart-demo/list
```

新增导入：

```python
from backend.app.api.models import QuickstartDemoRequest
from backend.app.runtime.pipeline_executor import run_pipeline
from backend.app.tools.quickstart_demo import (
    get_latest_quickstart_demo,
    list_quickstart_demos,
)
```

新增路由：

```python
@router.post("/api/quickstart-demo/run")
def api_run_quickstart_demo(
    request: QuickstartDemoRequest,
) -> dict[str, Any]:
    try:
        summary = run_pipeline(
            request.project_config_path,
            request.pipeline_path,
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/quickstart-demo/latest")
def api_get_latest_quickstart_demo() -> dict[str, Any]:
    return get_latest_quickstart_demo(demo_root="./demo_runs")


@router.get("/api/quickstart-demo/list")
def api_list_quickstart_demos() -> dict[str, Any]:
    return list_quickstart_demos(demo_root="./demo_runs")
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只运行 synthetic Python-only quickstart demo。

---

## 8. 修改 frontend/src/api.ts

新增：

```ts
export async function runQuickstartDemo(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/quickstart-demo/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getLatestQuickstartDemo(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/quickstart-demo/latest"
  );
}

export async function listQuickstartDemos(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/quickstart-demo/list"
  );
}
```

---

## 9. 创建 frontend/src/components/QuickstartDemoPanel.tsx

创建文件：

```text
frontend/src/components/QuickstartDemoPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  getLatestQuickstartDemo,
  listQuickstartDemos,
  runQuickstartDemo
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function QuickstartDemoPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [demoList, setDemoList] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Quickstart Demo？该流程只生成 synthetic demo workspace，不运行 SPM/MATLAB/DPABI/GPU，不修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runQuickstartDemo(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_quickstart_demo.yaml"
      });
      setResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadLatest() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getLatestQuickstartDemo(baseUrl);
      setLatest(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleList() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await listQuickstartDemos(baseUrl);
      setDemoList(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const summary = latest?.summary as Record<string, unknown> | undefined;
  const stageCounts = summary?.stage_counts as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          运行 Quickstart Demo
        </button>
        <button onClick={handleLoadLatest}>加载最新 Demo</button>
        <button onClick={handleList}>列出 Demo</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Demo ID</span>
          <strong>{String(latest?.demo_id ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Status</span>
          <strong>{String(summary?.demo_status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Subjects</span>
          <strong>
            {Array.isArray(summary?.subject_ids)
              ? String(summary.subject_ids.length)
              : "-"}
          </strong>
        </div>
        <div className="metricCard">
          <span>Stages</span>
          <strong>{String(stageCounts?.total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Failed</span>
          <strong>{String(stageCounts?.failed ?? "-")}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Latest Demo Summary</h3>
      <JsonBlock value={latest?.summary} emptyText="暂无最新 demo summary" />

      <h3>Quickstart Demo Report</h3>
      <TextViewer
        text={
          typeof latest?.report === "string"
            ? latest.report
            : null
        }
        emptyText="暂无 quickstart demo report"
      />

      <h3>Demo List</h3>
      <JsonBlock value={demoList} emptyText="暂无 demo list" />
    </div>
  );
}
```

---

## 10. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { QuickstartDemoPanel } from "./components/QuickstartDemoPanel";
```

建议放在首页靠前位置，也可以放在 Documentation Center 后。新增 Section：

```tsx
<Section
  title="Quickstart Demo"
  description="一键生成 synthetic demo workspace，并运行 Python-only 安全演示闭环：metrics、QC、group summary、report export、validation、docs inventory 和 release readiness。"
>
  <QuickstartDemoPanel baseUrl={baseUrl} />
</Section>
```

---

## 11. 新增轻量测试

创建文件：

```text
tests/unit/test_quickstart_demo.py
```

内容：

```python
from __future__ import annotations

from pathlib import Path

from backend.app.tools.quickstart_demo import (
    get_latest_quickstart_demo,
    list_quickstart_demos,
    run_quickstart_demo,
)


def test_quickstart_demo_runs_safe_workspace(tmp_path: Path):
    demo_root = tmp_path / "demo_runs"

    result = run_quickstart_demo(
        demo_root=str(demo_root),
        demo_id="test_demo",
        subject_count=1,
        n_timepoints=20,
        tr=2.0,
        force=False,
    )

    assert result["node_id"] == "quickstart_demo"
    assert result["demo_id"] == "test_demo"
    assert Path(result["workspace"]).exists()
    assert result["safety"]["spm_executed"] is False
    assert result["safety"]["matlab_executed"] is False
    assert result["safety"]["dpabi_executed"] is False
    assert result["safety"]["gpu_executed"] is False

    workspace = demo_root / "test_demo"
    assert (workspace / "quickstart_demo_summary.json").exists()
    assert (workspace / "quickstart_demo_report.md").exists()
    assert (workspace / "derivatives").exists()
    assert (workspace / "reports").exists()
    assert (workspace / "work").exists()
    assert (workspace / "exports").exists()

    latest = get_latest_quickstart_demo(demo_root=str(demo_root))
    assert latest["ok"] is True
    assert latest["demo_id"] == "test_demo"

    listing = list_quickstart_demos(demo_root=str(demo_root))
    assert listing["ok"] is True
    assert listing["demos_total"] == 1
```

---

## 12. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/quickstart-demo/latest")
call("GET", "/api/quickstart-demo/list")
```

不要在 smoke test 中调用 POST run，避免改变 demo_runs。

---

## 13. 更新 docs/user_guide.md

追加 Quickstart Demo 说明：

```markdown
## Quickstart Demo

The fastest way to evaluate the MVP is to run the safe quickstart demo.

```bash
python -m backend.app.tools.run_quickstart_demo_cli
```

This creates:

```text
demo_runs/{demo_id}/
```

The demo generates synthetic derivative fixtures and runs Python-only metrics, QC, report export, report validation, docs inventory, and release readiness checks.

It does not run SPM, MATLAB, DPABI, or GPU code.
```

---

## 14. 更新 docs/pipeline_guide.md

在 pipeline 列表中加入：

```text
pipeline_quickstart_demo.yaml
```

并追加：

```markdown
## Quickstart Demo Pipeline

```bash
python -m backend.app.tools.run_quickstart_demo_cli
```

This pipeline is safe by default and does not require MATLAB, SPM, DPABI, or GPU hardware.
```

---

## 15. 更新 docs/api_reference.md

新增：

```markdown
### Quickstart Demo

```text
POST /api/quickstart-demo/run
GET  /api/quickstart-demo/latest
GET  /api/quickstart-demo/list
```
```

---

## 16. 更新 docs/frontend_guide.md

在 panels 列表中加入：

```text
Quickstart Demo
```

并说明：

```markdown
## Quickstart Demo Panel

The Quickstart Demo panel runs a safe Python-only synthetic demonstration workflow and loads the latest demo summary and report.
```

---

## 17. 更新 docs/troubleshooting.md

追加：

```markdown
## Quickstart Demo Fails

Open:

```text
demo_runs/{demo_id}/quickstart_demo_report.md
```

Check failed stages and stage-level errors.

The quickstart demo should not require MATLAB, SPM, DPABI, or GPU.
```

---

## 18. 更新 README.md

追加第五十二步说明：

```markdown
## Step 52: Quickstart Demo Orchestrator

This step adds a safe one-command quickstart demo.

It creates a synthetic demo workspace under:

```text
demo_runs/{demo_id}/
```

The demo runs:

- synthetic derivative fixture generation
- Python temporal filtering
- Python ALFF/fALFF
- Python ReHo
- Python functional connectivity
- backend contract generation
- group dataset summary
- report export
- report validation
- docs inventory
- release readiness

It does not execute SPM, MATLAB, DPABI, or GPU code.

### Run

```bash
python -m backend.app.tools.run_quickstart_demo_cli
```

Expected outputs:

```text
demo_runs/{demo_id}/quickstart_demo_summary.json
demo_runs/{demo_id}/quickstart_demo_report.md
demo_runs/{demo_id}/derivatives/
demo_runs/{demo_id}/reports/
demo_runs/{demo_id}/work/
demo_runs/{demo_id}/exports/
work/pipeline_runs/run_quickstart_demo_001/summary.json
```

### API

```bash
curl http://127.0.0.1:8000/api/quickstart-demo/latest
curl http://127.0.0.1:8000/api/quickstart-demo/list
```

Run demo:

```bash
curl -X POST http://127.0.0.1:8000/api/quickstart-demo/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_quickstart_demo.yaml"
  }'
```

### Frontend

Use:

```text
Quickstart Demo
```

### Safety

This step:

- creates synthetic derivative fixtures only
- writes under demo_runs by default
- does not read rawdata
- does not modify rawdata
- does not run SPM
- does not run MATLAB
- does not run DPABI
- does not run GPU
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not perform group-level statistical inference
- does not make clinical conclusions
```

---

## 19. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/quickstart_demo_orchestrator_spec.md
backend/app/tools/quickstart_demo.py
backend/app/runtime/node_registry.py
examples/pipeline_quickstart_demo.yaml
backend/app/tools/run_quickstart_demo_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/QuickstartDemoPanel.tsx
frontend/src/App.tsx
tests/unit/test_quickstart_demo.py
backend/app/tools/api_smoke_test.py
docs/user_guide.md
docs/pipeline_guide.md
docs/api_reference.md
docs/frontend_guide.md
docs/troubleshooting.md
README.md
```

运行 quickstart demo：

```bash
python -m backend.app.tools.run_quickstart_demo_cli
```

应生成：

```text
demo_runs/{demo_id}/quickstart_demo_summary.json
demo_runs/{demo_id}/quickstart_demo_report.md
demo_runs/{demo_id}/derivatives/
demo_runs/{demo_id}/reports/
demo_runs/{demo_id}/work/
demo_runs/{demo_id}/exports/
```

quickstart_demo_summary JSON 必须包含：

```json
{
  "node_id": "quickstart_demo",
  "demo_id": "quickstart_...",
  "demo_status": "PASS",
  "workspace": "outputs/demo_runs/quickstart_...",
  "subject_ids": ["sub-001", "sub-002"],
  "stages": [],
  "safety": {
    "synthetic_demo_only": true,
    "rawdata_read": false,
    "rawdata_modified": false,
    "spm_executed": false,
    "matlab_executed": false,
    "dpabi_executed": false,
    "gpu_executed": false
  }
}
```

实际状态可为 PASS / WARNING / FAIL，取决于文档库存、release readiness、已有依赖和环境。

运行测试：

```bash
python -m pytest tests/unit/test_quickstart_demo.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/quickstart-demo/latest
curl http://127.0.0.1:8000/api/quickstart-demo/list

curl -X POST http://127.0.0.1:8000/api/quickstart-demo/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 Quickstart Demo 区域。
2. 点击运行前有 confirm 弹窗。
3. 可以运行 quickstart demo。
4. 可以加载最新 demo。
5. 可以列出历史 demo。
6. 显示 demo id。
7. 显示 demo status。
8. 显示 subject 数量。
9. 显示 stage 总数。
10. 显示 failed stage 数量。
11. 显示 quickstart demo summary JSON。
12. 显示 quickstart demo Markdown report。
13. 不修改 rawdata。
14. 不运行 SPM / MATLAB。
15. 不运行 DPABI。
16. 不运行 GPU。
17. 不执行统计推断。
18. 不生成临床结论。

---

## 20. 重要限制

本步骤只做 Quickstart Demo Orchestrator。

不要实现：

- 真实 SPM demo
- 真实 MATLAB demo
- 真实 DPABI demo
- 真实 GPU demo
- 真实医学影像处理
- Docker build
- CI/CD
- PDF / Word / PPT 报告生成
- group-level statistical testing
- clinical interpretation
- subject exclusion automation
- 自动修复项目
- rawdata 修改
- 文件删除

完成后请总结：

1. 新增了哪些文件
2. 修改了哪些文件
3. quickstart demo workspace 如何组织
4. synthetic derivative fixture 如何生成
5. orchestrator 依次运行哪些 stage
6. 为什么不通过 subprocess 调 CLI
7. 为什么本 demo 不需要 SPM / MATLAB / DPABI / GPU
8. quickstart_demo_summary.json 包含什么
9. Quickstart Demo 前端如何展示演示状态
10. 为什么本步骤不是完整真实数据 preprocessing
11. 下一步如何实现 Demo Replay / Run History Browser：查看历史 demo、pipeline run 和 report package 的统一运行历史

```
写了一个不依赖 MATLAB 的全链集成测试，从 synthetic 数据出发，依次验证 confound matrix（Friston24 产 26 列）、ALFF/fALFF、ReHo（KCC）、functional connectivity（ROI 提取 + 相关矩阵）、group dataset summary 这 5 个 Python 后处理模块的输出文件和 QC 状态。
```
