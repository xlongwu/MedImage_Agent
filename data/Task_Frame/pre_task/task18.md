你是我的工程搭建助手。前十七步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。
Step 9：完成最小 FastAPI 后端服务闭环。
Step 10：完成最小 React 前端闭环。
Step 11：完成 Run Monitor + State / Log Viewer 闭环。
Step 12：完成 Error Diagnosis + Retry Plan 闭环。
Step 13：完成 Checkpoint / Cache / Approved Retry 闭环。
Step 14：完成本地 subject-level 并行调度与资源限制闭环。
Step 15：完成 GPU ALFF / fALFF 原型与 CPU fallback 闭环。
Step 16：完成 Validation / Benchmark / Regression Suite 闭环。
Step 17：完成 DPABI Capability Inspector + Wrapper Scaffold 闭环。

现在开始第十八步。

第十八步目标：实现“DPABI Dataset Adapter + Batch Config Preflight 闭环”。

当前系统已经能探测 DPABI 能力，并生成 wrapper scaffold，但还没有把 BIDS-like 数据集映射成 DPABI wrapper 可理解的输入结构，也没有做真正执行前的参数预检。

本步骤只做 DPABI 执行前准备，不运行完整 DPABI pipeline。

本步骤要实现：

- 读取 dataset_index.json
- 读取 dpabi_capabilities.json
- 读取 dpabi_wrapper_config_template.yaml
- 生成 DPABI input manifest
- 生成 DPABI workspace scaffold
- 生成 DPABI batch config draft
- 生成 DPABI preflight report
- 检查 T1w / BOLD / metadata / TR
- 检查 DPABI candidate wrapper 是否可用
- 检查输出目录是否可写
- 检查 rawdata 是否只读
- 将 dpabi_preflight 作为 pipeline node 接入
- 后端 API 暴露 DPABI preflight
- 前端 DPABI Panel 显示 preflight 结果

不要实现：
- 完整 DPABI 预处理
- DPARSF 批处理执行
- DPABI GUI 自动化
- 真实医学影像数据处理
- 修改 DPABI 源码
- 修改 rawdata
- 删除文件
- 自动重排真实数据目录
- 并行 DPABI
- GPU DPABI
- WebSocket
- 数据库
- 真实 LLM

本步骤只做 DPABI 执行前 adapter、config draft 和 preflight validator。

---

## 1. 创建 specs/dpabi_preflight_spec.md

创建文件：

```text
specs/dpabi_preflight_spec.md

内容：

# DPABI Preflight Specification

This document defines the MVP DPABI dataset adapter and preflight validator.

## Goals

Before running any DPABI / DPARSF preprocessing, the system should verify:

- DPABI path and capabilities
- dataset completeness
- BIDS-like subject mapping
- T1w and BOLD availability
- functional metadata such as TR
- output workspace safety
- wrapper configuration readiness

## Scope

Supported in this step:

- read dataset_index.json
- read dpabi_capabilities.json
- read dpabi_wrapper_config_template.yaml
- generate dpabi_input_manifest.json
- generate dpabi_batch_config_draft.yaml
- generate dpabi_preflight_report.json
- generate dpabi_preflight_report.md
- create a safe DPABI workspace scaffold

Unsupported in this step:

- full DPABI preprocessing
- DPARSF batch execution
- GUI automation
- rawdata modification
- DPABI source modification
- deletion of files
- real clinical interpretation

## Outputs

```text
work/dpabi/dpabi_input_manifest.json
work/dpabi/dpabi_workspace/
work/dpabi/dpabi_batch_config_draft.yaml
work/dpabi/dpabi_preflight_report.json
reports/dpabi/dpabi_preflight_report.md
Subject Status
READY_FOR_DPABI_DRY_RUN
MISSING_T1W
MISSING_BOLD
MISSING_TR
INCOMPLETE
SKIPPED
Preflight Status
PASS: all required checks passed
WARNING: non-blocking warnings exist
FAIL: blocking errors exist
Safety Rules
Do not run DPABI.
Do not call DPABI GUI.
Do not modify rawdata.
Do not delete files.
Do not modify DPABI source.
Create workspace scaffold only under work/dpabi.

---

## 2. 创建 backend/app/tools/dpabi_adapter.py

创建文件：

```text
backend/app/tools/dpabi_adapter.py

目标：把 dataset_index.json 转换成 DPABI input manifest。

提供函数：

build_dpabi_input_manifest(
    dataset_index_path: str,
    work_dir: str,
) -> dict

输出：

work/dpabi/dpabi_input_manifest.json
work/dpabi/dpabi_workspace/

manifest 结构示例：

{
  "ok": true,
  "dataset_index": "outputs/work/dataset_index/dataset_index.json",
  "workspace_dir": "outputs/work/dpabi/dpabi_workspace",
  "subjects_total": 2,
  "subjects_ready": 2,
  "subjects": [
    {
      "subject_id": "sub-001",
      "status": "READY_FOR_DPABI_DRY_RUN",
      "t1w": ".../sub-001_T1w.nii.gz",
      "bold": ".../sub-001_task-rest_bold.nii.gz",
      "bold_json": ".../sub-001_task-rest_bold.json",
      "tr": 2.0,
      "issues": []
    }
  ],
  "errors": [],
  "warnings": []
}

实现要求：

读取 dataset_index.json。
对每个 subject 找第一个 T1w 和第一个 BOLD。
读取 BOLD metadata 中的 RepetitionTime。
对 subject 标记状态。
创建 workspace scaffold：
work/dpabi/dpabi_workspace/
├── rawdata_links/
├── configs/
├── logs/
└── outputs/
不要复制真实 NIfTI。
不要移动 rawdata。
不要创建 symlink，先只在 manifest 中记录路径。
不要修改 rawdata。

参考实现方向：

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


def _first_t1w(subject: dict[str, Any]) -> str | None:
    for session in subject.get("sessions", []):
        anat = session.get("anat", {})
        t1w = anat.get("t1w")
        if t1w:
            return t1w
    return None


def _first_bold_record(subject: dict[str, Any]) -> dict[str, Any] | None:
    for session in subject.get("sessions", []):
        for func in session.get("func", []):
            if func.get("bold"):
                return func
    return None


def build_dpabi_input_manifest(
    dataset_index_path: str,
    work_dir: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    dataset_path = Path(dataset_index_path)
    dataset_index = _read_json(dataset_path)

    if not dataset_index:
        return {
            "ok": False,
            "node_id": "dpabi_input_manifest",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid dataset index: {dataset_path}"],
        }

    dpabi_dir = Path(work_dir) / "dpabi"
    workspace_dir = dpabi_dir / "dpabi_workspace"

    for subdir in ["rawdata_links", "configs", "logs", "outputs"]:
        (workspace_dir / subdir).mkdir(parents=True, exist_ok=True)

    subjects_out: list[dict[str, Any]] = []

    for subject in dataset_index.get("subjects", []):
        subject_id = subject.get("subject_id")
        dataset_status = subject.get("status", "UNKNOWN")
        issues: list[str] = []

        t1w = _first_t1w(subject)
        bold_record = _first_bold_record(subject)
        bold = bold_record.get("bold") if bold_record else None
        bold_json = bold_record.get("json") if bold_record else None
        metadata = bold_record.get("metadata", {}) if bold_record else {}
        tr = metadata.get("RepetitionTime")

        if dataset_status != "COMPLETE":
            issues.append(f"dataset_status={dataset_status}")

        if not t1w:
            issues.append("missing T1w")

        if not bold:
            issues.append("missing BOLD")

        if tr is None:
            issues.append("missing RepetitionTime")

        if not t1w:
            status = "MISSING_T1W"
        elif not bold:
            status = "MISSING_BOLD"
        elif tr is None:
            status = "MISSING_TR"
        elif dataset_status != "COMPLETE":
            status = "INCOMPLETE"
        else:
            status = "READY_FOR_DPABI_DRY_RUN"

        subjects_out.append({
            "subject_id": subject_id,
            "dataset_status": dataset_status,
            "status": status,
            "t1w": t1w,
            "bold": bold,
            "bold_json": bold_json,
            "tr": tr,
            "issues": issues,
        })

    subjects_ready = sum(
        1 for item in subjects_out
        if item["status"] == "READY_FOR_DPABI_DRY_RUN"
    )

    manifest = {
        "ok": True,
        "node_id": "dpabi_input_manifest",
        "backend": "python",
        "dataset_index": str(dataset_path),
        "workspace_dir": str(workspace_dir),
        "subjects_total": len(subjects_out),
        "subjects_ready": subjects_ready,
        "subjects": subjects_out,
        "warnings": warnings,
        "errors": errors,
    }

    manifest_path = dpabi_dir / "dpabi_input_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "node_id": "dpabi_input_manifest",
        "backend": "python",
        "outputs": [str(manifest_path), str(workspace_dir)],
        "metrics": {
            "subjects_total": len(subjects_out),
            "subjects_ready": subjects_ready,
        },
        "warnings": warnings,
        "errors": errors,
        "manifest_path": str(manifest_path),
    }
3. 创建 backend/app/tools/dpabi_preflight.py

创建文件：

backend/app/tools/dpabi_preflight.py

目标：生成 DPABI batch config draft 和 preflight report。

提供函数：

run_dpabi_preflight(
    work_dir: str,
    report_dir: str,
    capabilities_path: str = "./work/dpabi/dpabi_capabilities.json",
    manifest_path: str = "./work/dpabi/dpabi_input_manifest.json",
    wrapper_config_template_path: str = "./work/dpabi/dpabi_wrapper_config_template.yaml",
) -> dict

输出：

work/dpabi/dpabi_batch_config_draft.yaml
work/dpabi/dpabi_preflight_report.json
reports/dpabi/dpabi_preflight_report.md

检查项：

capabilities JSON 是否存在。
DPABI entrypoint 是否存在。
candidate wrapper 是否存在。
input manifest 是否存在。
至少一个 subject ready。
每个 ready subject 的 T1w / BOLD 路径是否存在。
每个 ready subject 是否有 TR。
workspace 输出目录是否存在。
wrapper config template 是否存在。
不运行 DPABI。

参考实现方向：

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


def _function_exists(capabilities: dict[str, Any], name: str) -> bool:
    for item in capabilities.get("functions", []):
        if item.get("name") == name:
            return bool(item.get("exists"))
    return False


def run_dpabi_preflight(
    work_dir: str,
    report_dir: str,
    capabilities_path: str = "./work/dpabi/dpabi_capabilities.json",
    manifest_path: str = "./work/dpabi/dpabi_input_manifest.json",
    wrapper_config_template_path: str = "./work/dpabi/dpabi_wrapper_config_template.yaml",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    dpabi_work = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    dpabi_work.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    cap_path = Path(capabilities_path)
    man_path = Path(manifest_path)
    wrapper_path = Path(wrapper_config_template_path)

    capabilities = _read_json(cap_path)
    manifest = _read_json(man_path)

    def add_check(name: str, ok: bool, message: str, blocking: bool = True):
        checks.append({
            "name": name,
            "ok": ok,
            "message": message,
            "blocking": blocking,
        })
        if not ok and blocking:
            errors.append(message)
        elif not ok:
            warnings.append(message)

    add_check(
        "capabilities_json_exists",
        capabilities is not None,
        f"Capabilities JSON missing or invalid: {cap_path}",
    )

    add_check(
        "input_manifest_exists",
        manifest is not None,
        f"Input manifest missing or invalid: {man_path}",
    )

    add_check(
        "wrapper_config_template_exists",
        wrapper_path.exists(),
        f"Wrapper config template missing: {wrapper_path}",
        blocking=False,
    )

    dpabi_entry_found = False
    candidate_wrapper_found = False

    if capabilities:
        dpabi_entry_found = bool(
            capabilities.get("summary", {}).get("dpabi_entrypoint_found")
        ) or _function_exists(capabilities, "DPABI")

        candidate_wrapper_found = (
            _function_exists(capabilities, "DPARSF_run")
            or _function_exists(capabilities, "DPARSFA_run")
        )

    add_check(
        "dpabi_entrypoint_found",
        dpabi_entry_found,
        "DPABI entrypoint was not found.",
        blocking=False,
    )

    add_check(
        "candidate_wrapper_found",
        candidate_wrapper_found,
        "No candidate DPARSF_run or DPARSFA_run wrapper found. Full execution should not proceed without manual mapping.",
        blocking=False,
    )

    subjects_ready = 0
    ready_subjects: list[dict[str, Any]] = []

    if manifest:
        ready_subjects = [
            item for item in manifest.get("subjects", [])
            if item.get("status") == "READY_FOR_DPABI_DRY_RUN"
        ]
        subjects_ready = len(ready_subjects)

    add_check(
        "subjects_ready",
        subjects_ready > 0,
        "No subjects are ready for DPABI dry-run mapping.",
    )

    subject_checks: list[dict[str, Any]] = []

    for subject in ready_subjects:
        subject_id = subject.get("subject_id")
        t1w = subject.get("t1w")
        bold = subject.get("bold")
        tr = subject.get("tr")

        t1w_exists = bool(t1w and Path(t1w).exists())
        bold_exists = bool(bold and Path(bold).exists())
        has_tr = tr is not None

        item = {
            "subject_id": subject_id,
            "t1w_exists": t1w_exists,
            "bold_exists": bold_exists,
            "has_tr": has_tr,
            "tr": tr,
        }
        subject_checks.append(item)

        if not t1w_exists:
            errors.append(f"{subject_id}: T1w path missing: {t1w}")
        if not bold_exists:
            errors.append(f"{subject_id}: BOLD path missing: {bold}")
        if not has_tr:
            errors.append(f"{subject_id}: RepetitionTime missing.")

    workspace_dir = Path(work_dir) / "dpabi" / "dpabi_workspace"
    add_check(
        "workspace_exists",
        workspace_dir.exists(),
        f"DPABI workspace missing: {workspace_dir}",
    )

    batch_config_path = dpabi_work / "dpabi_batch_config_draft.yaml"

    batch_config = f"""# DPABI Batch Config Draft
# This file is generated by DPABI preflight.
# It is a draft only and must be reviewed before execution.

mode: "dry_run"
allow_full_preprocessing: false
require_manual_review: true

inputs:
  manifest: "{man_path}"
  subjects_ready: {subjects_ready}

dpabi:
  capabilities_json: "{cap_path}"
  dpabi_entrypoint_found: {str(dpabi_entry_found).lower()}
  candidate_wrapper_found: {str(candidate_wrapper_found).lower()}

workspace:
  root: "{workspace_dir}"
  outputs: "{workspace_dir / "outputs"}"
  logs: "{workspace_dir / "logs"}"

preprocessing:
  # Draft only. Do not execute without manual review.
  slice_timing: false
  realign: true
  normalize: true
  smooth: true
  nuisance_regression: false
  filter: false
  alff: false
  falff: false

safety:
  modify_rawdata: false
  delete_files: false
  modify_dpabi_source: false
"""
    batch_config_path.write_text(batch_config, encoding="utf-8")

    status = "PASS"
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARNING"

    report_json_path = dpabi_work / "dpabi_preflight_report.json"
    report_md_path = report_out / "dpabi_preflight_report.md"

    report = {
        "ok": status in {"PASS", "WARNING"},
        "node_id": "dpabi_preflight",
        "backend": "python",
        "status": status,
        "capabilities_path": str(cap_path),
        "manifest_path": str(man_path),
        "batch_config_draft": str(batch_config_path),
        "subjects_ready": subjects_ready,
        "checks": checks,
        "subject_checks": subject_checks,
        "warnings": warnings,
        "errors": errors,
    }

    report_json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Preflight Report")
    lines.append("")
    lines.append(f"- Status: {status}")
    lines.append(f"- Subjects ready: {subjects_ready}")
    lines.append(f"- Capabilities: `{cap_path}`")
    lines.append(f"- Manifest: `{man_path}`")
    lines.append(f"- Batch config draft: `{batch_config_path}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | OK | Blocking | Message |")
    lines.append("|---|---:|---:|---|")
    for check in checks:
        lines.append(
            f"| {check['name']} | {check['ok']} | {check['blocking']} | {check['message']} |"
        )
    lines.append("")
    lines.append("## Subject Checks")
    lines.append("")
    if subject_checks:
        lines.append("| Subject | T1w exists | BOLD exists | Has TR | TR |")
        lines.append("|---|---:|---:|---:|---:|")
        for item in subject_checks:
            lines.append(
                f"| {item['subject_id']} | {item['t1w_exists']} | {item['bold_exists']} | {item['has_tr']} | {item['tr']} |"
            )
    else:
        lines.append("No subjects ready for DPABI dry-run mapping.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This preflight did not run DPABI preprocessing and did not modify rawdata or DPABI source code.")

    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": report["ok"],
        "node_id": "dpabi_preflight",
        "backend": "python",
        "outputs": [
            str(batch_config_path),
            str(report_json_path),
            str(report_md_path),
        ],
        "metrics": {
            "status": status,
            "subjects_ready": subjects_ready,
            "checks_total": len(checks),
            "errors_count": len(errors),
            "warnings_count": len(warnings),
        },
        "warnings": warnings,
        "errors": errors,
    }
4. 修改 backend/app/runtime/node_registry.py

新增两个节点：

dpabi_input_manifest
dpabi_preflight

新增导入：

from backend.app.tools.dpabi_adapter import build_dpabi_input_manifest
from backend.app.tools.dpabi_preflight import run_dpabi_preflight

新增 runner：

def run_dpabi_input_manifest_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    dataset_index_path = node.params.get(
        "dataset_index",
        f"{context.work_dir}/dataset_index/dataset_index.json",
    )

    result = build_dpabi_input_manifest(
        dataset_index_path=dataset_index_path,
        work_dir=context.work_dir,
    )
    result["node_id"] = node.id
    return result


def run_dpabi_preflight_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_dpabi_preflight(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        capabilities_path=node.params.get("capabilities_path", f"{context.work_dir}/dpabi/dpabi_capabilities.json"),
        manifest_path=node.params.get("manifest_path", f"{context.work_dir}/dpabi/dpabi_input_manifest.json"),
        wrapper_config_template_path=node.params.get("wrapper_config_template_path", f"{context.work_dir}/dpabi/dpabi_wrapper_config_template.yaml"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_input_manifest": run_dpabi_input_manifest_node,
"dpabi_preflight": run_dpabi_preflight_node,
5. 创建 examples/pipeline_dpabi_preflight.yaml

创建文件：

examples/pipeline_dpabi_preflight.yaml

内容：

pipeline_id: dpabi_preflight_pipeline
version: "0.1.0"
modality: integration-test
description: "Create synthetic data, inspect DPABI capabilities, build DPABI input manifest, and run preflight without full preprocessing."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_preflight_001"
  scheduler:
    mode: "sequential"
    max_workers: 1
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

  - id: dpabi_capability_inspection
    name: DPABI Capability Inspection
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - environment_check
    inputs: []
    outputs:
      - "./work/dpabi/dpabi_capabilities.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_wrapper_scaffold
    name: DPABI Wrapper Scaffold
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_capability_inspection
    inputs:
      - "./work/dpabi/dpabi_capabilities.json"
    outputs:
      - "./work/dpabi/dpabi_wrapper_config_template.yaml"
      - "./work/dpabi/dpabi_dry_run_plan.json"
      - "./reports/dpabi/dpabi_capability_report.md"
    params:
      capabilities_path: "./work/dpabi/dpabi_capabilities.json"
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_input_manifest
    name: DPABI Input Manifest
    agent: dpabi-runner
    backend: python
    depends_on:
      - data_inspection
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs:
      - "./work/dpabi/dpabi_input_manifest.json"
      - "./work/dpabi/dpabi_workspace"
    params:
      dataset_index: "./work/dataset_index/dataset_index.json"
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_preflight
    name: DPABI Preflight
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_wrapper_scaffold
      - dpabi_input_manifest
    inputs:
      - "./work/dpabi/dpabi_capabilities.json"
      - "./work/dpabi/dpabi_input_manifest.json"
      - "./work/dpabi/dpabi_wrapper_config_template.yaml"
    outputs:
      - "./work/dpabi/dpabi_batch_config_draft.yaml"
      - "./work/dpabi/dpabi_preflight_report.json"
      - "./reports/dpabi/dpabi_preflight_report.md"
    params:
      capabilities_path: "./work/dpabi/dpabi_capabilities.json"
      manifest_path: "./work/dpabi/dpabi_input_manifest.json"
      wrapper_config_template_path: "./work/dpabi/dpabi_wrapper_config_template.yaml"
    parallel_level: project
    gpu_supported: false
    cache: false
6. 创建 backend/app/tools/run_dpabi_preflight_cli.py

创建文件：

backend/app/tools/run_dpabi_preflight_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dpabi_preflight.yaml")

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
7. 修改 backend/app/api/routes.py

修改已有：

GET /api/dpabi/capabilities
GET /api/reports/dpabi

让它们也返回 preflight 文件。

/api/dpabi/capabilities 返回新增：

"input_manifest": _read_json_if_exists(base / "dpabi_input_manifest.json"),
"batch_config_draft": _read_text_if_exists(base / "dpabi_batch_config_draft.yaml"),
"preflight_report": _read_json_if_exists(base / "dpabi_preflight_report.json"),

/api/reports/dpabi 返回新增：

"preflight_report": _read_text_if_exists(base / "dpabi_preflight_report.md"),
8. 修改 frontend/src/components/DpabiPanel.tsx

在现有 DPABI Panel 中增加显示：

input manifest
batch config draft
preflight report JSON
preflight report Markdown

增加内容：

<h3>DPABI Input Manifest</h3>
<JsonBlock value={capabilities?.input_manifest} emptyText="尚未生成 input manifest" />

<h3>DPABI Batch Config Draft</h3>
<TextViewer
  text={
    typeof capabilities?.batch_config_draft === "string"
      ? capabilities.batch_config_draft
      : null
  }
  emptyText="尚未生成 batch config draft"
/>

<h3>DPABI Preflight JSON</h3>
<JsonBlock value={capabilities?.preflight_report} emptyText="尚未生成 preflight report JSON" />

<h3>DPABI Preflight Report</h3>
<TextViewer
  text={
    typeof report?.preflight_report === "string"
      ? report.preflight_report
      : null
  }
  emptyText="尚未生成 DPABI preflight report"
/>

保留原来的 capability report、dry-run plan、wrapper config template。

9. 修改 backend/app/tools/api_smoke_test.py

新增测试：

call("GET", "/api/dpabi/capabilities")
call("GET", "/api/reports/dpabi")

如果已经存在，不要重复添加。

不要在 smoke test 中自动运行 DPABI preflight pipeline。

10. 更新 README.md

追加第十八步说明：

## Step 18: DPABI Dataset Adapter and Preflight

This step adds a DPABI pre-execution adapter and preflight validator.

It does not run full DPABI preprocessing.

### Run DPABI Preflight Pipeline

```bash
python -m backend.app.tools.run_dpabi_preflight_cli

Expected outputs:

work/dpabi/dpabi_input_manifest.json
work/dpabi/dpabi_workspace/
work/dpabi/dpabi_batch_config_draft.yaml
work/dpabi/dpabi_preflight_report.json
reports/dpabi/dpabi_preflight_report.md
work/pipeline_runs/run_dpabi_preflight_001/summary.json
API
curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi
Frontend

Use the DPABI Capability / Wrapper Scaffold panel.

It now shows:

DPABI capabilities
dry-run plan
wrapper config template
input manifest
batch config draft
preflight JSON
preflight Markdown report
Safety

This step does not:

run full DPABI preprocessing
call DPABI GUI
modify rawdata
modify DPABI source
delete files

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_preflight_spec.md
backend/app/tools/dpabi_adapter.py
backend/app/tools/dpabi_preflight.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_preflight.yaml
backend/app/tools/run_dpabi_preflight_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/components/DpabiPanel.tsx
README.md

运行：

python -m backend.app.tools.run_dpabi_preflight_cli

成功后应生成：

work/dpabi/dpabi_input_manifest.json
work/dpabi/dpabi_workspace/
work/dpabi/dpabi_batch_config_draft.yaml
work/dpabi/dpabi_preflight_report.json
reports/dpabi/dpabi_preflight_report.md
work/pipeline_runs/run_dpabi_preflight_001/summary.json

其中：

work/dpabi/dpabi_input_manifest.json

应包含：

{
  "ok": true,
  "subjects_total": 2,
  "subjects_ready": 2
}

其中：

work/dpabi/dpabi_preflight_report.json

应包含：

{
  "node_id": "dpabi_preflight",
  "status": "PASS"
}

如果 DPABI entrypoint 或 candidate wrapper 找不到，可以是 WARNING，但不应运行 DPABI。

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 DPABI capabilities。
显示 wrapper config template。
显示 input manifest。
显示 batch config draft。
显示 preflight JSON。
显示 preflight Markdown report。
不运行完整 DPABI preprocessing。
不修改 rawdata。
不修改 DPABI 源码。
12. 重要限制

本步骤只做 DPABI adapter 和 preflight。

不要实现：

DPABI 全流程执行
DPARSF_run 自动运行
DPABI GUI 自动化
真实医学影像预处理
参数自动优化
并行 DPABI
GPU DPABI
删除旧输出
修改 rawdata
修改 DPABI 源码

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 DPABI preflight
input manifest 记录什么
batch config draft 为什么不能直接执行
preflight PASS / WARNING / FAIL 如何判断
下一步真正执行 DPABI 前还需要人工确认哪些内容

'''
## Step 18: DPABI Dataset Adapter + Batch Config Preflight 闭环
### 核心目标
在真正执行 DPABI 预处理之前，完成 数据集适配 和 执行前预检 ，确保所有准备工作就绪。

### 主要功能
1. DPABI Input Manifest（数据集适配）
   
   - 读取 dataset_index.json
   - 将 BIDS-like 数据集映射成 DPABI 可理解的输入结构
   - 检查每个 subject 的 T1w 和 BOLD 可用性
   - 从 BOLD metadata 中提取 TR（RepetitionTime）
   - 标记 subject 状态（READY_FOR_DPABI_DRY_RUN、MISSING_T1W、MISSING_BOLD 等）
   - 生成 work/dpabi/dpabi_input_manifest.json
2. DPABI Preflight（执行前预检）
   
   - 验证 DPABI capabilities JSON 是否存在
   - 验证 input manifest 是否存在
   - 检查 DPABI entrypoint 和 candidate wrapper（DPARSF_run/DPARSFA_run）是否可用
   - 验证每个 ready subject 的 T1w/BOLD 路径是否真实存在
   - 验证 workspace 输出目录是否可写
   - 生成 batch config draft（ dpabi_batch_config_draft.yaml ）
   - 生成 preflight report（JSON 和 Markdown）
3. Workspace Scaffold（工作空间脚手架）
   
   - 创建安全的工作目录结构： work/dpabi/dpabi_workspace/
   - 子目录：rawdata_links/、configs/、logs/、outputs/
   - 不复制真实 NIfTI 文件，不创建 symlink，只记录路径
### 输出文件
```
work/dpabi/
├── dpabi_input_manifest.json          # 输入清单
├── dpabi_workspace/                   # 工作空间
│   ├── rawdata_links/
│   ├── configs/
│   ├── logs/
│   └── outputs/
├── dpabi_batch_config_draft.yaml      # 批处理配置草稿
└── dpabi_preflight_report.json        # 预检报告

reports/dpabi/
└── dpabi_preflight_report.md          # Markdown 报告
```
### Subject 状态
- READY_FOR_DPABI_DRY_RUN - 所有必需数据齐全
- MISSING_T1W - 缺少 T1w 图像
- MISSING_BOLD - 缺少 BOLD 图像
- MISSING_TR - 缺少 RepetitionTime 元数据
- INCOMPLETE - 数据集状态不完整
- SKIPPED - 跳过该 subject
### Preflight 状态
- PASS - 所有必需检查通过
- WARNING - 存在非阻塞性警告
- FAIL - 存在阻塞性错误
### 安全规则
- ✅ 允许：读取 dataset_index、生成 manifest、验证路径、创建配置草稿
- ❌ 禁止：运行 DPABI 预处理、调用 DPABI GUI、修改 rawdata、删除文件、修改 DPABI 源码
这是一个 执行前准备步骤 ，为下一步真正执行 DPABI 预处理做全面的检查和准备工作。
'''