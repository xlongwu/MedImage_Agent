你是我的工程搭建助手。前三十六步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Slice Timing Correction + Metadata QC
- SPM Realignment + Motion QC

现在开始第三十七步。

第三十七步目标：实现 “Slice Timing → Realignment → Motion QC 链式核心 pipeline 闭环”。

当前系统已经有两个独立核心步骤：

1. `spm_slice_timing_subject`
   - 输入 synthetic raw BOLD
   - 输出 `a{sub}_bold.nii`
   - 输出 slice timing QC

2. `spm_realign_subject`
   - 输入 synthetic raw BOLD
   - 输出 `r{sub}_bold.nii`
   - 输出 `mean{sub}_bold.nii`
   - 输出 `rp_{sub}_bold.txt`
   - 输出 motion QC

但目前二者还不是连续链路。  
本步骤要把它们串起来：

```text
synthetic raw BOLD
→ SPM slice timing correction
→ slice timing corrected BOLD
→ SPM realignment
→ motion parameters
→ motion QC
→ dataset-level chain report

本步骤要实现：

定义 chained rs-fMRI core pipeline spec。
修改或扩展 realignment runner，使其可以安全接受 slice timing derivative 输入。
新增 chain input resolver：
优先使用 a{sub}_bold.nii
如果未启用 slice timing，则回退 raw synthetic BOLD
新增 chain-level summary：
每个 subject 的 slice timing 状态
realignment 状态
motion QC 状态
输出文件完整性
新增 chained pipeline YAML。
新增 chained pipeline CLI。
新增后端 API：
run chained pipeline
get chained results
新增前端面板：
rs-fMRI Slice Timing → Realignment → Motion QC
新增轻量 unit test。
更新 README。

本步骤允许调用 SPM，但必须满足：

只处理 synthetic BIDS-like 数据。
必须 approved=true 才执行 SPM slice timing 和 SPM realignment。
不处理真实医学影像数据。
不修改 rawdata。
不调用 DPABI。
不调用 DPARSF_run。
不调用 DPARSFA_run。
不调用 DPABI GUI。
不修改 SPM / DPABI 源码。
不删除文件。

本步骤不要实现：

coregistration
segmentation
normalization
smoothing
nuisance regression
temporal filtering
ALFF / fALFF / ReHo
完整 preprocessing pipeline
真实数据处理
自动参数优化
Docker / release / CI 等外围功能

本步骤只做：Slice Timing → Realignment → Motion QC 链式核心 pipeline。

1. 创建 specs/rsfmri_st_realign_motion_chain_spec.md

创建文件：

specs/rsfmri_st_realign_motion_chain_spec.md

内容：

# rs-fMRI Slice Timing to Realignment Chain Specification

This document defines the MVP chained rs-fMRI core preprocessing pipeline:

```text
Slice Timing Correction → Realignment → Motion QC
Goals

The goal is to connect existing SPM slice timing and SPM realignment wrappers into a continuous synthetic rs-fMRI preprocessing chain.

The pipeline should:

generate or use synthetic BIDS-like rs-fMRI data
validate acquisition metadata
run approved SPM slice timing correction
use slice-timing-corrected BOLD as realignment input
run approved SPM realignment
compute motion QC from SPM motion parameters
generate subject-level and dataset-level chain reports
Scope

Supported in this step:

synthetic BIDS-like input only
approved SPM slice timing
approved SPM realignment
derivative input handoff from slice timing to realignment
motion QC
chain-level subject summary
chain-level dataset report
API and frontend visibility
lightweight unit test

Unsupported in this step:

real medical image preprocessing
coregistration
segmentation
normalization
smoothing
nuisance regression
temporal filtering
ALFF / fALFF / ReHo
DPABI execution
DPARSF_run execution
DPARSFA_run execution
DPABI GUI automation
rawdata modification
source modification in SPM / DPABI
file deletion
Inputs
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.nii or *.nii.gz
examples/synthetic_bids/rawdata/{subject_id}/func/*_bold.json
work/dataset_index/dataset_index.json
Intermediate Outputs
derivatives/rsfmri_preproc/{subject_id}/func/{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/r{sub}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/mean{sub}_bold.nii
derivatives/rsfmri_preproc/{subject_id}/func/rp_{sub}_bold.txt
QC Outputs
derivatives/rsfmri_qc/{subject_id}/slice_timing_qc.json
derivatives/rsfmri_qc/{subject_id}/motion_qc.json
reports/rsfmri/st_realign_motion_chain_summary.json
reports/rsfmri/st_realign_motion_chain_report.md
Chain Rules
Realignment should use a{sub}_bold.nii when slice timing is enabled and successful.
Realignment may fall back to raw synthetic BOLD only when use_slice_timing_output=false.
Derivative input must remain under derivatives/rsfmri_preproc.
Rawdata must never be modified.
Realignment must not accept arbitrary derivative files.
Both SPM stages require explicit approval.
Safety Rules
Execution requires approved=true.
Only synthetic BIDS-like input is allowed.
Do not modify rawdata.
Do not delete files.
Do not call DPABI.
Do not call DPARSF_run.
Do not call DPARSFA_run.
Do not call DPABI GUI.

---

## 2. 创建 backend/app/tools/rsfmri_chain_resolver.py

创建文件：

```text
backend/app/tools/rsfmri_chain_resolver.py

目标：统一解析 subject 的链式输入输出，尤其是 realignment 应该用哪个 BOLD 输入。

提供函数：

find_subject_raw_bold(subject_record: dict) -> str | None

get_slice_timing_derivative(
    subject_id: str,
    derivatives_dir: str,
) -> str | None

resolve_realign_input(
    subject_id: str,
    subject_record: dict,
    derivatives_dir: str,
    use_slice_timing_output: bool = True,
) -> dict

is_safe_synthetic_raw_bold(path: str) -> bool

is_safe_slice_timing_derivative(path: str, subject_id: str, derivatives_dir: str) -> bool

实现要求：

raw BOLD 必须来自：
examples/synthetic_bids/rawdata
slice timing derivative 必须是：
derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii
如果 use_slice_timing_output=true：
优先返回 slice timing derivative
如果不存在，返回 ok=false
如果 use_slice_timing_output=false：
返回 synthetic raw BOLD
不读取 voxel data。
不修改文件。
不删除文件。

参考实现：

from __future__ import annotations

from pathlib import Path
from typing import Any


def find_subject_raw_bold(subject_record: dict[str, Any]) -> str | None:
    for session in subject_record.get("sessions", []):
        for func in session.get("func", []):
            bold = func.get("bold")
            if bold:
                return bold
    return None


def is_safe_synthetic_raw_bold(path: str) -> bool:
    normalized = str(path).replace("\\", "/")
    return "examples/synthetic_bids/rawdata" in normalized and (
        normalized.endswith(".nii") or normalized.endswith(".nii.gz")
    )


def get_slice_timing_derivative(
    subject_id: str,
    derivatives_dir: str,
) -> str | None:
    path = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    )

    return str(path) if path.exists() else None


def is_safe_slice_timing_derivative(
    path: str,
    subject_id: str,
    derivatives_dir: str,
) -> bool:
    target = Path(path).resolve()
    expected = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    ).resolve()

    try:
        target.relative_to(Path(derivatives_dir).resolve())
    except ValueError:
        return False

    return target == expected and target.exists()


def resolve_realign_input(
    subject_id: str,
    subject_record: dict[str, Any],
    derivatives_dir: str,
    use_slice_timing_output: bool = True,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    raw_bold = find_subject_raw_bold(subject_record)

    if not raw_bold:
        return {
            "ok": False,
            "subject_id": subject_id,
            "input_type": None,
            "input_bold": None,
            "warnings": warnings,
            "errors": ["No raw BOLD found in subject record."],
        }

    if not is_safe_synthetic_raw_bold(raw_bold):
        return {
            "ok": False,
            "subject_id": subject_id,
            "input_type": None,
            "input_bold": None,
            "warnings": warnings,
            "errors": [f"Raw BOLD is not a safe synthetic input: {raw_bold}"],
        }

    if use_slice_timing_output:
        derivative = get_slice_timing_derivative(
            subject_id=subject_id,
            derivatives_dir=derivatives_dir,
        )

        if not derivative:
            return {
                "ok": False,
                "subject_id": subject_id,
                "input_type": "slice_timing_derivative",
                "input_bold": None,
                "raw_bold": raw_bold,
                "warnings": warnings,
                "errors": [
                    "Slice timing output was requested but not found.",
                    f"Expected: derivatives/rsfmri_preproc/{subject_id}/func/a{subject_id}_bold.nii",
                ],
            }

        if not is_safe_slice_timing_derivative(derivative, subject_id, derivatives_dir):
            return {
                "ok": False,
                "subject_id": subject_id,
                "input_type": "slice_timing_derivative",
                "input_bold": None,
                "raw_bold": raw_bold,
                "warnings": warnings,
                "errors": [f"Unsafe slice timing derivative: {derivative}"],
            }

        return {
            "ok": True,
            "subject_id": subject_id,
            "input_type": "slice_timing_derivative",
            "input_bold": derivative,
            "raw_bold": raw_bold,
            "warnings": warnings,
            "errors": errors,
        }

    return {
        "ok": True,
        "subject_id": subject_id,
        "input_type": "synthetic_raw_bold",
        "input_bold": raw_bold,
        "raw_bold": raw_bold,
        "warnings": warnings,
        "errors": errors,
    }
3. 修改 backend/app/tools/spm_realign_runner.py

目标：让 realignment runner 可以安全接受 slice timing derivative 输入。

当前 run_spm_realign_subject 只允许：

examples/synthetic_bids/rawdata

本步骤修改为：

run_spm_realign_subject(
    matlab_command: str,
    spm_dir: str,
    subject_id: str,
    input_bold: str,
    derivatives_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool = False,
    matlab_script_dir: str = "./matlab",
    allow_derivative_input: bool = False,
) -> dict

新增规则：

如果 input 是 synthetic rawdata，仍然允许。
如果 input 是 slice timing derivative，则只有 allow_derivative_input=true 时允许。
derivative 输入必须满足：
在 derivatives/rsfmri_preproc/{subject_id}/func/
文件名为 a{subject_id}_bold.nii
如果 input 已经是 derivative .nii，不要再复制覆盖同一路径；可以直接使用它作为 prepared_input。
rawdata 输入仍然复制到 derivatives。
不允许任意 derivatives 输入。
保持不修改 rawdata。
保持不调用 DPABI。

建议增加内部函数：

def _is_safe_synthetic_input(input_bold: str) -> bool:
    normalized = str(input_bold).replace("\\", "/")
    return "examples/synthetic_bids/rawdata" in normalized


def _is_safe_slice_timing_derivative(input_bold: str, subject_id: str, derivatives_dir: str) -> bool:
    target = Path(input_bold).resolve()
    expected = (
        Path(derivatives_dir)
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    ).resolve()
    return target == expected and target.exists()

修改安全检查逻辑为：

safe_synthetic = _is_safe_synthetic_input(input_bold)
safe_derivative = (
    allow_derivative_input
    and _is_safe_slice_timing_derivative(input_bold, subject_id, derivatives_dir)
)

if not safe_synthetic and not safe_derivative:
    return {
        "ok": False,
        "node_id": "spm_realign_subject",
        "backend": "matlab-spm",
        "subject_id": subject_id,
        "outputs": [],
        "warnings": [],
        "errors": [
            "Refusing to run SPM realignment on unsafe input.",
            f"Input was: {input_bold}",
        ],
    }

修改 input preparation：

if safe_derivative:
    prepared_input = input_bold
else:
    prepared_input = _prepare_bold_input(...)

其他逻辑保持不变。

4. 创建 backend/app/tools/rsfmri_chain_report.py

创建文件：

backend/app/tools/rsfmri_chain_report.py

目标：聚合 slice timing QC、realignment result、motion QC，生成 chain-level summary/report。

提供函数：

write_st_realign_motion_chain_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict

输出：

reports/rsfmri/st_realign_motion_chain_summary.json
reports/rsfmri/st_realign_motion_chain_report.md

实现要求：

扫描：
derivatives/rsfmri_qc/*/slice_timing_qc.json
derivatives/rsfmri_preproc/*/func/spm_realign_result.json
derivatives/rsfmri_qc/*/motion_qc.json
每个 subject 汇总：
subject_id
slice_timing_ok
slice_timing_status
realign_ok
realigned_file
mean_file
motion_parameter_file
motion_qc_ok
motion_qc_status
mean_fd
max_fd
chain_status
chain_status 规则：
三者都 ok 且 motion PASS → PASS
任一失败 → FAIL
motion WARNING → WARNING
输出 JSON 和 Markdown。
不读取 voxel data。
不修改文件。

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _subject_ids_from_derivatives(derivatives: Path) -> list[str]:
    ids = set()

    for path in (derivatives / "rsfmri_qc").glob("*/slice_timing_qc.json"):
        ids.add(path.parent.name)

    for path in (derivatives / "rsfmri_qc").glob("*/motion_qc.json"):
        ids.add(path.parent.name)

    for path in (derivatives / "rsfmri_preproc").glob("*/func/spm_realign_result.json"):
        ids.add(path.parent.parent.name)

    return sorted(ids)


def _chain_status(slice_ok: bool, realign_ok: bool, motion_ok: bool, motion_status: str | None) -> str:
    if not slice_ok or not realign_ok or not motion_ok:
        return "FAIL"
    if motion_status == "FAIL":
        return "FAIL"
    if motion_status == "WARNING":
        return "WARNING"
    return "PASS"


def write_st_realign_motion_chain_report(
    derivatives_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    derivatives = Path(derivatives_dir)
    report_out = Path(report_dir) / "rsfmri"
    report_out.mkdir(parents=True, exist_ok=True)

    subjects: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for subject_id in _subject_ids_from_derivatives(derivatives):
        slice_qc = _read_json(
            derivatives / "rsfmri_qc" / subject_id / "slice_timing_qc.json"
        )
        realign = _read_json(
            derivatives / "rsfmri_preproc" / subject_id / "func" / "spm_realign_result.json"
        )
        motion_qc = _read_json(
            derivatives / "rsfmri_qc" / subject_id / "motion_qc.json"
        )

        slice_ok = bool(slice_qc and slice_qc.get("ok"))
        realign_ok = bool(realign and realign.get("ok"))
        motion_ok = bool(motion_qc and motion_qc.get("ok"))
        motion_status = motion_qc.get("motion_qc_status") if motion_qc else None

        item = {
            "subject_id": subject_id,
            "slice_timing_ok": slice_ok,
            "slice_timing_status": slice_qc.get("slice_timing_status") if slice_qc else "MISSING",
            "realign_ok": realign_ok,
            "realigned_file": (realign.get("realigned_files") or [None])[0] if realign else None,
            "mean_file": realign.get("mean_file") if realign else None,
            "motion_parameter_file": realign.get("motion_parameter_file") if realign else None,
            "motion_qc_ok": motion_ok,
            "motion_qc_status": motion_status or "MISSING",
            "mean_fd": motion_qc.get("mean_fd") if motion_qc else None,
            "max_fd": motion_qc.get("max_fd") if motion_qc else None,
            "chain_status": _chain_status(slice_ok, realign_ok, motion_ok, motion_status),
        }

        subjects.append(item)

    subjects_total = len(subjects)
    pass_count = sum(1 for item in subjects if item["chain_status"] == "PASS")
    warning_count = sum(1 for item in subjects if item["chain_status"] == "WARNING")
    fail_count = sum(1 for item in subjects if item["chain_status"] == "FAIL")

    summary = {
        "ok": subjects_total > 0 and fail_count == 0,
        "node_id": "st_realign_motion_chain_report",
        "backend": "python",
        "subjects_total": subjects_total,
        "subjects_pass": pass_count,
        "subjects_warning": warning_count,
        "subjects_fail": fail_count,
        "subjects": subjects,
        "safety": {
            "rawdata_modified": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dparsfa_run_executed": False,
            "dpabi_gui_called": False,
            "files_deleted": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    summary_path = report_out / "st_realign_motion_chain_summary.json"
    report_path = report_out / "st_realign_motion_chain_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# rs-fMRI Slice Timing → Realignment → Motion QC Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Subjects total: {subjects_total}")
    lines.append(f"- PASS: {pass_count}")
    lines.append(f"- WARNING: {warning_count}")
    lines.append(f"- FAIL: {fail_count}")
    lines.append("")
    lines.append("## Subjects")
    lines.append("")
    lines.append("| Subject | Slice Timing | Realign | Motion QC | Mean FD | Max FD | Chain Status |")
    lines.append("|---|---|---:|---|---:|---:|---|")

    for item in subjects:
        lines.append(
            f"| {item['subject_id']} | {item['slice_timing_status']} | "
            f"{item['realign_ok']} | {item['motion_qc_status']} | "
            f"{item['mean_fd']} | {item['max_fd']} | {item['chain_status']} |"
        )

    lines.append("")
    lines.append("## Safety")
    lines.append("")
    for key, value in summary["safety"].items():
        lines.append(f"- {key}: {value}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "st_realign_motion_chain_report",
        "backend": "python",
        "outputs": [str(summary_path), str(report_path)],
        "metrics": {
            "subjects_total": subjects_total,
            "subjects_pass": pass_count,
            "subjects_warning": warning_count,
            "subjects_fail": fail_count,
        },
        "warnings": warnings,
        "errors": errors,
    }
5. 修改 backend/app/runtime/node_registry.py

新增节点：

st_realign_motion_chain_report

修改 realignment subject runner，使其支持链式输入：

找到已有：

run_spm_realign_subject_node

修改逻辑：

from backend.app.tools.rsfmri_chain_resolver import resolve_realign_input

在 runner 中替换原来的 raw BOLD 查找逻辑：

use_slice_timing_output = bool(node.params.get("use_slice_timing_output", False))

resolved = resolve_realign_input(
    subject_id=context.subject_id,
    subject_record=context.subject_record,
    derivatives_dir=context.derivatives_dir,
    use_slice_timing_output=use_slice_timing_output,
)

if not resolved.get("ok"):
    return {
        "ok": False,
        "node_id": node.id,
        "backend": "matlab-spm",
        "subject_id": context.subject_id,
        "outputs": [],
        "warnings": resolved.get("warnings", []),
        "errors": resolved.get("errors", []),
    }

bold = resolved["input_bold"]

调用 run_spm_realign_subject 时新增：

allow_derivative_input=use_slice_timing_output

并在 result 中加：

result["input_resolution"] = resolved

新增导入：

from backend.app.tools.rsfmri_chain_report import write_st_realign_motion_chain_report

新增 runner：

def run_st_realign_motion_chain_report_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_st_realign_motion_chain_report(
        derivatives_dir=context.derivatives_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"st_realign_motion_chain_report": run_st_realign_motion_chain_report_node,
6. 创建 examples/pipeline_rsfmri_st_realign_motion_qc.yaml

创建文件：

examples/pipeline_rsfmri_st_realign_motion_qc.yaml

内容：

pipeline_id: rsfmri_st_realign_motion_qc_pipeline
version: "0.1.0"
modality: rs-fMRI
description: "Run approved SPM Slice Timing → Realignment → Motion QC chain on synthetic rs-fMRI data."

execution:
  stop_on_failure: true
  run_id: "run_rsfmri_st_realign_motion_qc_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
    matlab_max_workers: 1

nodes:
  - id: create_synthetic_bids
    name: Create Synthetic BIDS Dataset
    agent: data-inspector
    backend: python
    depends_on: []
    inputs: []
    outputs:
      - "./examples/synthetic_bids/rawdata/dataset_description.json"
      - "./examples/synthetic_bids/rawdata/participants.tsv"
    params:
      output_dir: "./examples/synthetic_bids/rawdata"
      subjects:
        - sub-001
        - sub-002
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: data_inspection
    name: Data Inspection
    agent: data-inspector
    backend: python
    depends_on:
      - create_synthetic_bids
    inputs:
      - "./examples/synthetic_bids/rawdata"
    outputs:
      - "./work/dataset_index/dataset_index.json"
      - "./work/dataset_index/data_completeness_report.json"
      - "./work/dataset_index/subject_table.csv"
    params:
      rawdata_dir: "./examples/synthetic_bids/rawdata"
      output_dir: "./work/dataset_index"
      read_nifti_metadata: true
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: environment_check
    name: Environment Check
    agent: system
    backend: matlab
    depends_on: []
    inputs: []
    outputs:
      - "./work/environment_check.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: spm_slice_timing_subject
    name: Approved SPM Slice Timing
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - data_inspection
      - environment_check
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs: []
    params:
      approved: false
      tr: null
      slice_order: null
      reference_slice: null
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: slice_timing_qc_dataset_report
    name: Slice Timing QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - spm_slice_timing_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/slice_timing_qc_summary.json"
      - "./reports/rsfmri/slice_timing_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: spm_realign_subject
    name: Approved SPM Realignment From Slice Timing Output
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - spm_slice_timing_subject
    inputs: []
    outputs: []
    params:
      approved: false
      use_slice_timing_output: true
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: motion_qc_subject
    name: Motion QC
    agent: qc-runner
    backend: python
    depends_on:
      - spm_realign_subject
    inputs: []
    outputs: []
    params:
      fd_threshold: 0.5
      head_radius_mm: 50.0
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: motion_qc_dataset_report
    name: Motion QC Dataset Report
    agent: report-runner
    backend: python
    depends_on:
      - motion_qc_subject
    inputs: []
    outputs:
      - "./reports/rsfmri/motion_qc_summary.json"
      - "./reports/rsfmri/motion_qc_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: st_realign_motion_chain_report
    name: Slice Timing Realignment Motion Chain Report
    agent: report-runner
    backend: python
    depends_on:
      - slice_timing_qc_dataset_report
      - motion_qc_dataset_report
    inputs: []
    outputs:
      - "./reports/rsfmri/st_realign_motion_chain_summary.json"
      - "./reports/rsfmri/st_realign_motion_chain_report.md"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

默认 approved: false，直接运行应该安全失败。
真正执行必须由 CLI/API 显式把两个 SPM 节点都设为 approved: true。

7. 创建 backend/app/tools/run_rsfmri_st_realign_motion_qc_cli.py

创建文件：

backend/app/tools/run_rsfmri_st_realign_motion_qc_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def _make_approved_pipeline_copy(source: Path, target: Path) -> Path:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject", "spm_realign_subject"}:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_rsfmri_st_realign_motion_qc.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/rsfmri/approved_pipeline_st_realign_motion_qc.yaml"),
        )

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
8. 修改 backend/app/api/models.py

新增 request model：

class RsfmriStRealignMotionQcRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_rsfmri_st_realign_motion_qc.yaml")
    approved: bool = Field(default=False)
9. 修改 backend/app/api/routes.py

新增 API：

POST /api/rsfmri/st-realign-motion-qc/run
GET  /api/rsfmri/st-realign-motion-qc

新增导入：

from backend.app.api.models import RsfmriStRealignMotionQcRequest
from backend.app.runtime.pipeline_executor import run_pipeline

新增辅助函数：

def _make_st_realign_motion_approved_copy(source: Path, target: Path) -> Path:
    import yaml

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") in {"spm_slice_timing_subject", "spm_realign_subject"}:
            node.setdefault("params", {})
            node["params"]["approved"] = True

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target

新增路由：

@router.post("/api/rsfmri/st-realign-motion-qc/run")
def api_run_rsfmri_st_realign_motion_qc(
    request: RsfmriStRealignMotionQcRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Slice Timing → Realignment → Motion QC chain requires approved=true.",
        )

    try:
        approved_pipeline = _make_st_realign_motion_approved_copy(
            source=Path(request.pipeline_path),
            target=Path("work/rsfmri/approved_pipeline_st_realign_motion_qc.yaml"),
        )

        summary = run_pipeline(
            request.project_config_path,
            str(approved_pipeline),
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/rsfmri/st-realign-motion-qc")
def api_get_rsfmri_st_realign_motion_qc() -> dict[str, Any]:
    report_base = Path("reports") / "rsfmri"
    derivatives_base = Path("derivatives")

    subject_slice_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/slice_timing_qc.json")):
        subject_slice_qc.append(_read_json_if_exists(path))

    subject_motion_qc = []
    for path in sorted((derivatives_base / "rsfmri_qc").glob("*/motion_qc.json")):
        subject_motion_qc.append(_read_json_if_exists(path))

    return {
        "ok": True,
        "chain_summary": _read_json_if_exists(report_base / "st_realign_motion_chain_summary.json"),
        "chain_report": _read_text_if_exists(report_base / "st_realign_motion_chain_report.md"),
        "slice_timing_qc_summary": _read_json_if_exists(report_base / "slice_timing_qc_summary.json"),
        "motion_qc_summary": _read_json_if_exists(report_base / "motion_qc_summary.json"),
        "subject_slice_timing_qc": subject_slice_qc,
        "subject_motion_qc": subject_motion_qc,
    }
10. 修改 frontend/src/api.ts

新增：

export async function runRsfmriStRealignMotionQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/st-realign-motion-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriStRealignMotionQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/st-realign-motion-qc"
  );
}
11. 创建 frontend/src/components/RsfmriStRealignMotionChainPanel.tsx

创建文件：

frontend/src/components/RsfmriStRealignMotionChainPanel.tsx

内容：

import { useState } from "react";
import {
  getRsfmriStRealignMotionQc,
  runRsfmriStRealignMotionQc
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function RsfmriStRealignMotionChainPanel({ baseUrl }: Props) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loaded, setLoaded] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRun() {
    const confirmed = window.confirm(
      "确认运行 Slice Timing → Realignment → Motion QC 链式 pipeline？这只处理 synthetic BIDS 数据，不会修改 rawdata。"
    );

    if (!confirmed) return;

    setStatus("RUNNING");
    setError("");

    try {
      const response = await runRsfmriStRealignMotionQc(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_rsfmri_st_realign_motion_qc.yaml",
        approved: true
      });
      setResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getRsfmriStRealignMotionQc(baseUrl);
      setLoaded(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const chainSummary = loaded?.chain_summary as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button className="dangerButton" onClick={handleRun}>
          批准并运行 ST → Realign → Motion QC
        </button>
        <button onClick={handleLoad}>加载 Chain 结果</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Subjects</span>
          <strong>{String(chainSummary?.subjects_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(chainSummary?.subjects_pass ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>WARNING</span>
          <strong>{String(chainSummary?.subjects_warning ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>FAIL</span>
          <strong>{String(chainSummary?.subjects_fail ?? "-")}</strong>
        </div>
      </div>

      <h3>Run Summary</h3>
      <JsonBlock value={result} emptyText="尚未运行" />

      <h3>Chain Summary</h3>
      <JsonBlock value={loaded?.chain_summary} emptyText="暂无 chain summary" />

      <h3>Slice Timing Summary</h3>
      <JsonBlock value={loaded?.slice_timing_qc_summary} emptyText="暂无 slice timing summary" />

      <h3>Motion QC Summary</h3>
      <JsonBlock value={loaded?.motion_qc_summary} emptyText="暂无 motion QC summary" />

      <h3>Subject Slice Timing QC</h3>
      <JsonBlock value={loaded?.subject_slice_timing_qc} emptyText="暂无 subject slice timing QC" />

      <h3>Subject Motion QC</h3>
      <JsonBlock value={loaded?.subject_motion_qc} emptyText="暂无 subject motion QC" />

      <h3>Chain Report</h3>
      <TextViewer
        text={
          typeof loaded?.chain_report === "string"
            ? loaded.chain_report
            : null
        }
        emptyText="暂无 chain report"
      />
    </div>
  );
}
12. 修改 frontend/src/App.tsx

新增导入：

import { RsfmriStRealignMotionChainPanel } from "./components/RsfmriStRealignMotionChainPanel";

在 rs-fMRI SPM Slice Timing + Metadata QC 和 rs-fMRI SPM Realignment + Motion QC 后新增 Section：

<Section
  title="rs-fMRI Slice Timing → Realignment → Motion QC"
  description="将 SPM slice timing 输出接入 SPM realignment，并生成链式运动质控报告。"
>
  <RsfmriStRealignMotionChainPanel baseUrl={baseUrl} />
</Section>
13. 新增轻量测试

创建文件：

tests/unit/test_rsfmri_chain_resolver.py

内容：

from __future__ import annotations

from pathlib import Path

from backend.app.tools.rsfmri_chain_resolver import (
    is_safe_slice_timing_derivative,
    resolve_realign_input,
)


def test_resolve_realign_input_prefers_slice_timing_derivative(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    derivative = (
        derivatives
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    )
    derivative.parent.mkdir(parents=True)
    derivative.write_bytes(b"fake nii")

    raw_bold = (
        tmp_path
        / "examples"
        / "synthetic_bids"
        / "rawdata"
        / subject_id
        / "func"
        / f"{subject_id}_task-rest_bold.nii.gz"
    )
    raw_bold.parent.mkdir(parents=True)
    raw_bold.write_bytes(b"fake raw")

    subject_record = {
        "sessions": [
            {
                "func": [
                    {"bold": str(raw_bold)}
                ]
            }
        ]
    }

    result = resolve_realign_input(
        subject_id=subject_id,
        subject_record=subject_record,
        derivatives_dir=str(derivatives),
        use_slice_timing_output=True,
    )

    assert result["ok"] is True
    assert result["input_type"] == "slice_timing_derivative"
    assert result["input_bold"] == str(derivative)


def test_slice_timing_derivative_must_match_expected_path(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    subject_id = "sub-001"

    good = (
        derivatives
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / f"a{subject_id}_bold.nii"
    )
    good.parent.mkdir(parents=True)
    good.write_bytes(b"fake")

    bad = (
        derivatives
        / "rsfmri_preproc"
        / subject_id
        / "func"
        / "some_other_file.nii"
    )
    bad.write_bytes(b"fake")

    assert is_safe_slice_timing_derivative(str(good), subject_id, str(derivatives)) is True
    assert is_safe_slice_timing_derivative(str(bad), subject_id, str(derivatives)) is False
14. 新增轻量测试

创建文件：

tests/unit/test_rsfmri_chain_report.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.rsfmri_chain_report import write_st_realign_motion_chain_report


def test_chain_report_aggregates_subject_status(tmp_path: Path):
    derivatives = tmp_path / "derivatives"
    reports = tmp_path / "reports"
    subject_id = "sub-001"

    qc_dir = derivatives / "rsfmri_qc" / subject_id
    func_dir = derivatives / "rsfmri_preproc" / subject_id / "func"
    qc_dir.mkdir(parents=True)
    func_dir.mkdir(parents=True)

    (qc_dir / "slice_timing_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": subject_id,
            "slice_timing_status": "PASS",
        }),
        encoding="utf-8",
    )

    (func_dir / "spm_realign_result.json").write_text(
        json.dumps({
            "ok": True,
            "realigned_files": [str(func_dir / "rasub-001_bold.nii")],
            "mean_file": str(func_dir / "meanasub-001_bold.nii"),
            "motion_parameter_file": str(func_dir / "rp_asub-001_bold.txt"),
        }),
        encoding="utf-8",
    )

    (qc_dir / "motion_qc.json").write_text(
        json.dumps({
            "ok": True,
            "subject_id": subject_id,
            "motion_qc_status": "PASS",
            "mean_fd": 0.1,
            "max_fd": 0.2,
        }),
        encoding="utf-8",
    )

    result = write_st_realign_motion_chain_report(
        derivatives_dir=str(derivatives),
        report_dir=str(reports),
    )

    assert result["ok"] is True

    summary_path = reports / "rsfmri" / "st_realign_motion_chain_summary.json"
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["subjects_total"] == 1
    assert summary["subjects_pass"] == 1
    assert summary["subjects"][0]["chain_status"] == "PASS"
15. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/rsfmri/st-realign-motion-qc")

不要在 smoke test 中调用 POST run，避免误启动 MATLAB。

16. 更新 README.md

追加第三十七步说明：

## Step 37: Slice Timing → Realignment → Motion QC Chain

This step connects the first two real rs-fMRI preprocessing wrappers.

It supports:

- approved SPM slice timing correction
- approved SPM realignment using slice timing output
- motion QC
- subject-level chain summary
- dataset-level chain report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_st_realign_motion_qc_cli

This should fail safely because approval is missing.

Run with approval
python -m backend.app.tools.run_rsfmri_st_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_st_realign_motion_qc.yaml --approve

Expected outputs:

derivatives/rsfmri_preproc/sub-001/func/asub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/rasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/meanasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/rp_asub-001_bold.txt
derivatives/rsfmri_qc/sub-001/slice_timing_qc.json
derivatives/rsfmri_qc/sub-001/motion_qc.json
reports/rsfmri/st_realign_motion_chain_summary.json
reports/rsfmri/st_realign_motion_chain_report.md
work/pipeline_runs/run_rsfmri_st_realign_motion_qc_001/summary.json
API
curl http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc

Run approved:

curl -X POST http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_st_realign_motion_qc.yaml",
    "approved": true
  }'
Frontend

Use:

rs-fMRI Slice Timing → Realignment → Motion QC
Safety

This step:

requires approved=true
only processes synthetic BIDS-like input
only allows realignment derivative input from expected slice timing output
does not modify rawdata
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not execute full preprocessing

---

## 17. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/rsfmri_st_realign_motion_chain_spec.md
backend/app/tools/rsfmri_chain_resolver.py
backend/app/tools/spm_realign_runner.py
backend/app/tools/rsfmri_chain_report.py
backend/app/runtime/node_registry.py
examples/pipeline_rsfmri_st_realign_motion_qc.yaml
backend/app/tools/run_rsfmri_st_realign_motion_qc_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RsfmriStRealignMotionChainPanel.tsx
frontend/src/App.tsx
tests/unit/test_rsfmri_chain_resolver.py
tests/unit/test_rsfmri_chain_report.py
backend/app/tools/api_smoke_test.py
README.md

先运行不带 approval：

python -m backend.app.tools.run_rsfmri_st_realign_motion_qc_cli

应该安全失败，不应启动 SPM。

然后运行 approved：

python -m backend.app.tools.run_rsfmri_st_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_st_realign_motion_qc.yaml --approve

如果本地 MATLAB + SPM 可用，应生成：

derivatives/rsfmri_preproc/sub-001/func/asub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/rasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/meanasub-001_bold.nii
derivatives/rsfmri_preproc/sub-001/func/rp_asub-001_bold.txt
derivatives/rsfmri_qc/sub-001/slice_timing_qc.json
derivatives/rsfmri_qc/sub-001/motion_qc.json
reports/rsfmri/st_realign_motion_chain_summary.json
reports/rsfmri/st_realign_motion_chain_report.md

chain summary 必须包含：

{
  "node_id": "st_realign_motion_chain_report",
  "subjects_total": 2,
  "subjects": [
    {
      "subject_id": "sub-001",
      "slice_timing_status": "PASS",
      "realign_ok": true,
      "motion_qc_status": "PASS",
      "chain_status": "PASS"
    }
  ],
  "safety": {
    "rawdata_modified": false,
    "dpabi_executed": false,
    "dparsf_run_executed": false,
    "dparsfa_run_executed": false,
    "dpabi_gui_called": false,
    "files_deleted": false
  }
}

运行测试：

python -m pytest tests/unit/test_rsfmri_chain_resolver.py tests/unit/test_rsfmri_chain_report.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc

curl -X POST http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'

未批准 POST 必须返回 403。

批准 POST 可运行：

curl -X POST http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 rs-fMRI Slice Timing → Realignment → Motion QC 区域。
可以点击批准并运行。
点击运行前有 confirm 弹窗。
可以加载 chain 结果。
显示 subject 数量。
显示 PASS / WARNING / FAIL 数量。
显示 chain summary JSON。
显示 slice timing summary。
显示 motion QC summary。
显示 subject-level slice timing QC。
显示 subject-level motion QC。
显示 chain Markdown report。
不修改 rawdata。
不运行 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不执行完整 preprocessing。
18. 重要限制

本步骤只做 Slice Timing → Realignment → Motion QC 链式 pipeline。

不要实现：

coregistration
segmentation
normalization
smoothing
nuisance regression
temporal filtering
ALFF / fALFF / ReHo
真实医学影像处理
DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
rawdata 修改
文件删除

完成后请总结：

新增了哪些文件
修改了哪些文件
realignment 如何使用 slice timing 输出
chain resolver 如何保证输入安全
chain report 聚合哪些信息
输出哪些 derivatives 和 reports
为什么本步骤仍然不是完整 preprocessing
下一步如何实现 Coregistration + Registration QC

'''
这一步做了一件事：把之前两个互相独立的 SPM 步骤串成了一条连续流水线。

之前 slice timing correction 和 realignment 虽然都能单独跑，但 realignment 只能读原始的 synthetic BOLD，不知道 slice timing 已经产出了校正后的 `a*.nii`。这一步改了三个地方把它们连起来：

**写了 chain resolver。** `rsfmri_chain_resolver.py` 决定了 realignment 该用哪个输入文件。当 pipeline 里设了 `use_slice_timing_output: true`，它会去找 `derivatives/rsfmri_preproc/{subject}/func/a{subject}_bold.nii`，并且严格校验这个文件必须在精确的预期路径上——不接受任何其他 derivatives 文件。如果 slice timing 还没跑完、文件不存在，就直接报错，不会静默回退。

**改了 realignment runner。** `spm_realign_runner.py` 新增了 `allow_derivative_input` 参数和两个安全检查函数。当输入是经过校验的 slice timing 输出时，跳过复制步骤直接使用该文件；不是合法输入就拒绝。

**写了 chain report 和 9 节点 pipeline。** `rsfmri_chain_report.py` 把每个 subject 的 slice timing QC、realignment 结果、motion QC 聚合到一起，算出一个 chain_status（三者都 PASS 才是 PASS）。新的 pipeline YAML 把 9 个节点串起来，`spm_realign_subject` 的依赖从 `data_inspection` 改成了 `spm_slice_timing_subject`，这样 pipeline executor 会保证 slice timing 先跑完、realignment 再用它的输出。

前端新增了对应的面板，API 新增了 run 和 get 端点，CLI 的 `--approve` 会同时批准两个 SPM 节点。

简单说，现在 synthetic BOLD → slice timing → realignment → motion QC → chain report 是一条完整的、自动串接的流水线了。
'''