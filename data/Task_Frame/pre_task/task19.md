你是我的工程搭建助手。前十八步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环。
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
Step 18：完成 DPABI Dataset Adapter + Batch Config Preflight 闭环。

现在开始第十九步。

第十九步目标：实现“DPABI 参数审查 + Approved Run Plan 闭环”。

当前系统已经能够：

- 探测 DPABI capability
- 生成 wrapper scaffold
- 生成 input manifest
- 生成 batch config draft
- 运行 preflight

但在真正执行 DPABI 前，还缺少一个关键环节：

- 把 DPABI 参数变成结构化 schema
- 生成可人工审查的参数文件
- 校验参数范围和安全性
- 生成 approved run plan
- 明确标记 requires_approval=true
- 默认 approved=false
- 不执行 DPABI
- 不调用 DPABI GUI
- 不修改 rawdata
- 不修改 DPABI 源码

本步骤只做 DPABI 参数审查和执行计划生成，不运行完整 DPABI pipeline。

不要实现：
- DPABI 全流程执行
- DPARSF_run 自动执行
- DPABI GUI 自动化
- 真实医学影像预处理
- 参数自动优化
- 修改 rawdata
- 修改 DPABI 源码
- 删除文件
- 并行 DPABI
- GPU DPABI
- WebSocket
- 数据库
- 真实 LLM

---

## 1. 创建 specs/dpabi_run_plan_spec.md

创建文件：

```text
specs/dpabi_run_plan_spec.md

内容：

# DPABI Run Plan Specification

This document defines the MVP DPABI parameter review and approved run plan stage.

## Goals

Before any DPABI execution, the system must generate a human-reviewable run plan.

The run plan should combine:

- DPABI capabilities
- input manifest
- preflight results
- parameter schema
- parameter review YAML
- safety checks
- approval status

## Scope

Supported in this step:

- DPABI parameter schema
- default parameter review YAML
- parameter validation
- approved run plan JSON
- run plan Markdown report
- API and frontend visibility

Unsupported in this step:

- full DPABI execution
- DPARSF_run execution
- DPABI GUI automation
- rawdata modification
- DPABI source modification
- deletion of files
- real clinical interpretation

## Outputs

```text
work/dpabi/dpabi_parameter_schema.json
work/dpabi/dpabi_params_review.yaml
work/dpabi/dpabi_params_validation.json
work/dpabi/dpabi_run_plan.json
reports/dpabi/dpabi_run_plan_report.md
Run Plan Status
READY_FOR_REVIEW: all inputs exist, but human approval is required
BLOCKED: blocking error exists
WARNING: non-blocking issue exists
APPROVED: future state only; not set automatically in this step
Safety Rules
Do not execute DPABI.
Do not call DPABI GUI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Run plan must default to approved=false.
Run plan must require explicit future approval before execution.

---

## 2. 创建 backend/app/tools/dpabi_param_schema.py

创建文件：

```text
backend/app/tools/dpabi_param_schema.py

目标：定义 DPABI 参数 schema，生成默认 review YAML，并校验参数。

提供函数：

write_dpabi_parameter_schema(work_dir: str) -> dict
write_dpabi_params_review_template(work_dir: str) -> dict
validate_dpabi_params(params_path: str, work_dir: str) -> dict

输出：

work/dpabi/dpabi_parameter_schema.json
work/dpabi/dpabi_params_review.yaml
work/dpabi/dpabi_params_validation.json

参数 schema 至少包含这些部分：

basic:
  tr
  slice_timing_enabled
  realign_enabled
  normalize_enabled
  smooth_enabled
  smooth_fwhm

nuisance:
  regress_motion
  regress_wm
  regress_csf
  regress_global_signal

filtering:
  bandpass_enabled
  low_freq
  high_freq

metrics:
  alff
  falff
  reho

safety:
  allow_full_dpabi_execution
  require_manual_review
  modify_rawdata
  delete_files

默认参数必须安全：

basic:
  tr: 2.0
  slice_timing_enabled: false
  realign_enabled: true
  normalize_enabled: true
  smooth_enabled: true
  smooth_fwhm: [6, 6, 6]

nuisance:
  regress_motion: true
  regress_wm: false
  regress_csf: false
  regress_global_signal: false

filtering:
  bandpass_enabled: false
  low_freq: 0.01
  high_freq: 0.08

metrics:
  alff: false
  falff: false
  reho: false

safety:
  allow_full_dpabi_execution: false
  require_manual_review: true
  modify_rawdata: false
  delete_files: false

校验规则：

tr 必须 > 0。
smooth_fwhm 必须是长度为 3 的数字数组。
low_freq 必须 >= 0。
high_freq 必须 > low_freq。
modify_rawdata 必须 false。
delete_files 必须 false。
require_manual_review 必须 true。
allow_full_dpabi_execution 默认必须 false。
如果 allow_full_dpabi_execution=true，本步骤仍然不执行，只在 validation 中标记需要人工确认。

参考实现方向：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PARAMS = {
    "basic": {
        "tr": 2.0,
        "slice_timing_enabled": False,
        "realign_enabled": True,
        "normalize_enabled": True,
        "smooth_enabled": True,
        "smooth_fwhm": [6, 6, 6],
    },
    "nuisance": {
        "regress_motion": True,
        "regress_wm": False,
        "regress_csf": False,
        "regress_global_signal": False,
    },
    "filtering": {
        "bandpass_enabled": False,
        "low_freq": 0.01,
        "high_freq": 0.08,
    },
    "metrics": {
        "alff": False,
        "falff": False,
        "reho": False,
    },
    "safety": {
        "allow_full_dpabi_execution": False,
        "require_manual_review": True,
        "modify_rawdata": False,
        "delete_files": False,
    },
}


def _yaml_dump_fallback(data: dict[str, Any]) -> str:
    lines = []
    for section, values in data.items():
        lines.append(f"{section}:")
        for key, value in values.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, list):
                rendered = "[" + ", ".join(str(x) for x in value) + "]"
            elif isinstance(value, str):
                rendered = f'"{value}"'
            else:
                rendered = str(value)
            lines.append(f"  {key}: {rendered}")
        lines.append("")
    return "\n".join(lines)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_dpabi_parameter_schema(work_dir: str) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "version": "0.1.0",
        "sections": {
            "basic": {
                "tr": {"type": "float", "min": 0.001, "required": True},
                "slice_timing_enabled": {"type": "bool"},
                "realign_enabled": {"type": "bool"},
                "normalize_enabled": {"type": "bool"},
                "smooth_enabled": {"type": "bool"},
                "smooth_fwhm": {"type": "list[float]", "length": 3},
            },
            "nuisance": {
                "regress_motion": {"type": "bool"},
                "regress_wm": {"type": "bool"},
                "regress_csf": {"type": "bool"},
                "regress_global_signal": {"type": "bool"},
            },
            "filtering": {
                "bandpass_enabled": {"type": "bool"},
                "low_freq": {"type": "float", "min": 0.0},
                "high_freq": {"type": "float", "min": 0.0},
            },
            "metrics": {
                "alff": {"type": "bool"},
                "falff": {"type": "bool"},
                "reho": {"type": "bool"},
            },
            "safety": {
                "allow_full_dpabi_execution": {"type": "bool", "default": False},
                "require_manual_review": {"type": "bool", "must_be": True},
                "modify_rawdata": {"type": "bool", "must_be": False},
                "delete_files": {"type": "bool", "must_be": False},
            },
        },
        "default_params": DEFAULT_PARAMS,
    }

    schema_path = out_dir / "dpabi_parameter_schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "outputs": [str(schema_path)],
        "schema_path": str(schema_path),
        "errors": [],
        "warnings": [],
    }


def write_dpabi_params_review_template(work_dir: str) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)

    params_path = out_dir / "dpabi_params_review.yaml"

    header = """# DPABI Parameter Review Template
# Human review is required before any DPABI execution.
# This file does not execute DPABI.

"""
    params_path.write_text(header + _yaml_dump_fallback(DEFAULT_PARAMS), encoding="utf-8")

    return {
        "ok": True,
        "outputs": [str(params_path)],
        "params_path": str(params_path),
        "errors": [],
        "warnings": [],
    }


def validate_dpabi_params(params_path: str, work_dir: str) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    path = Path(params_path)
    if not path.exists():
        errors.append(f"DPABI params review YAML not found: {path}")
        params = {}
    else:
        try:
            params = _load_yaml(path)
        except Exception as exc:
            errors.append(f"Failed to load params YAML: {exc}")
            params = {}

    basic = params.get("basic", {})
    filtering = params.get("filtering", {})
    safety = params.get("safety", {})

    tr = basic.get("tr")
    try:
        if tr is None or float(tr) <= 0:
            errors.append("basic.tr must be > 0.")
    except Exception:
        errors.append("basic.tr must be numeric.")

    fwhm = basic.get("smooth_fwhm")
    if not isinstance(fwhm, list) or len(fwhm) != 3:
        errors.append("basic.smooth_fwhm must be a list of length 3.")
    else:
        try:
            [float(x) for x in fwhm]
        except Exception:
            errors.append("basic.smooth_fwhm must contain numeric values.")

    low = filtering.get("low_freq", 0.01)
    high = filtering.get("high_freq", 0.08)

    try:
        low_f = float(low)
        high_f = float(high)
        if low_f < 0:
            errors.append("filtering.low_freq must be >= 0.")
        if high_f <= low_f:
            errors.append("filtering.high_freq must be greater than low_freq.")
    except Exception:
        errors.append("filtering.low_freq and high_freq must be numeric.")

    if safety.get("modify_rawdata") is not False:
        errors.append("safety.modify_rawdata must be false.")

    if safety.get("delete_files") is not False:
        errors.append("safety.delete_files must be false.")

    if safety.get("require_manual_review") is not True:
        errors.append("safety.require_manual_review must be true.")

    if safety.get("allow_full_dpabi_execution") is True:
        warnings.append(
            "allow_full_dpabi_execution=true was found. This step still does not execute DPABI; future execution must require explicit approval."
        )

    validation = {
        "ok": len(errors) == 0,
        "params_path": str(path),
        "errors": errors,
        "warnings": warnings,
        "params": params,
    }

    out_dir = Path(work_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)

    validation_path = out_dir / "dpabi_params_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    validation["outputs"] = [str(validation_path)]
    validation["validation_path"] = str(validation_path)
    return validation
3. 创建 backend/app/tools/dpabi_run_plan.py

创建文件：

backend/app/tools/dpabi_run_plan.py

目标：基于 capability、manifest、preflight、params validation 生成 DPABI approved run plan。

提供函数：

create_dpabi_run_plan(
    work_dir: str,
    report_dir: str,
    capabilities_path: str = "./work/dpabi/dpabi_capabilities.json",
    manifest_path: str = "./work/dpabi/dpabi_input_manifest.json",
    preflight_path: str = "./work/dpabi/dpabi_preflight_report.json",
    params_path: str = "./work/dpabi/dpabi_params_review.yaml",
) -> dict

输出：

work/dpabi/dpabi_run_plan.json
reports/dpabi/dpabi_run_plan_report.md

run plan 必须包含：

{
  "ok": true,
  "mode": "PLAN_ONLY",
  "requires_approval": true,
  "approved": false,
  "execution_allowed": false,
  "status": "READY_FOR_REVIEW",
  "subjects_ready": 2,
  "blocking_errors": [],
  "warnings": [],
  "planned_steps": []
}

状态规则：

如果 capabilities 缺失：BLOCKED。
如果 manifest 缺失：BLOCKED。
如果 preflight status=FAIL：BLOCKED。
如果 params validation 失败：BLOCKED。
如果 subjects_ready=0：BLOCKED。
如果只有非阻塞 warning：WARNING。
否则 READY_FOR_REVIEW。
本步骤永远不要把 approved 设置为 true。
本步骤永远不要把 execution_allowed 设置为 true。

参考实现方向：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.tools.dpabi_param_schema import (
    validate_dpabi_params,
    write_dpabi_parameter_schema,
    write_dpabi_params_review_template,
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def create_dpabi_run_plan(
    work_dir: str,
    report_dir: str,
    capabilities_path: str = "./work/dpabi/dpabi_capabilities.json",
    manifest_path: str = "./work/dpabi/dpabi_input_manifest.json",
    preflight_path: str = "./work/dpabi/dpabi_preflight_report.json",
    params_path: str = "./work/dpabi/dpabi_params_review.yaml",
) -> dict[str, Any]:
    warnings: list[str] = []
    blocking_errors: list[str] = []

    out_dir = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    schema_result = write_dpabi_parameter_schema(work_dir)

    params_file = Path(params_path)
    if not params_file.exists():
        template_result = write_dpabi_params_review_template(work_dir)
        params_path = template_result["params_path"]

    params_validation = validate_dpabi_params(params_path=params_path, work_dir=work_dir)

    capabilities = _read_json(Path(capabilities_path))
    manifest = _read_json(Path(manifest_path))
    preflight = _read_json(Path(preflight_path))

    if not capabilities:
        blocking_errors.append(f"Missing capabilities JSON: {capabilities_path}")

    if not manifest:
        blocking_errors.append(f"Missing input manifest: {manifest_path}")

    if not preflight:
        blocking_errors.append(f"Missing preflight report: {preflight_path}")

    if preflight and preflight.get("status") == "FAIL":
        blocking_errors.append("DPABI preflight status is FAIL.")

    if not params_validation.get("ok"):
        blocking_errors.extend(params_validation.get("errors", []))

    warnings.extend(params_validation.get("warnings", []))

    subjects_ready = 0
    if manifest:
        subjects_ready = int(manifest.get("subjects_ready", 0) or 0)

    if subjects_ready <= 0:
        blocking_errors.append("No subjects are ready for DPABI run plan.")

    capability_summary = capabilities.get("summary", {}) if capabilities else {}
    dpabi_entrypoint_found = bool(capability_summary.get("dpabi_entrypoint_found"))

    if not dpabi_entrypoint_found:
        warnings.append("DPABI entrypoint was not found. Future execution may be blocked.")

    status = "READY_FOR_REVIEW"
    if blocking_errors:
        status = "BLOCKED"
    elif warnings:
        status = "WARNING"

    planned_steps = [
        {
            "step_id": "dpabi_plan_001",
            "action": "review_params",
            "status": "required",
            "input": params_path,
        },
        {
            "step_id": "dpabi_plan_002",
            "action": "review_preflight",
            "status": "required",
            "input": preflight_path,
        },
        {
            "step_id": "dpabi_plan_003",
            "action": "review_subject_manifest",
            "status": "required",
            "input": manifest_path,
        },
        {
            "step_id": "dpabi_plan_004",
            "action": "future_approved_dpabi_execution",
            "status": "not_executed",
            "requires_approval": True,
        },
    ]

    run_plan = {
        "ok": status in {"READY_FOR_REVIEW", "WARNING"},
        "node_id": "dpabi_run_plan",
        "backend": "python",
        "mode": "PLAN_ONLY",
        "status": status,
        "requires_approval": True,
        "approved": False,
        "execution_allowed": False,
        "capabilities_path": capabilities_path,
        "manifest_path": manifest_path,
        "preflight_path": preflight_path,
        "params_path": params_path,
        "params_validation_path": params_validation.get("validation_path"),
        "schema_path": schema_result.get("schema_path"),
        "subjects_ready": subjects_ready,
        "dpabi_entrypoint_found": dpabi_entrypoint_found,
        "planned_steps": planned_steps,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "errors": blocking_errors,
        "safety": {
            "full_dpabi_executed": False,
            "rawdata_modified": False,
            "dpabi_source_modified": False,
            "files_deleted": False,
        },
    }

    run_plan_path = out_dir / "dpabi_run_plan.json"
    report_path = report_out / "dpabi_run_plan_report.md"

    run_plan.write_text if False else None
    run_plan_path.write_text(json.dumps(run_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# DPABI Run Plan Report")
    lines.append("")
    lines.append(f"- Status: {status}")
    lines.append(f"- Subjects ready: {subjects_ready}")
    lines.append(f"- Requires approval: {run_plan['requires_approval']}")
    lines.append(f"- Approved: {run_plan['approved']}")
    lines.append(f"- Execution allowed: {run_plan['execution_allowed']}")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Capabilities: `{capabilities_path}`")
    lines.append(f"- Manifest: `{manifest_path}`")
    lines.append(f"- Preflight: `{preflight_path}`")
    lines.append(f"- Params: `{params_path}`")
    lines.append("")
    lines.append("## Planned Steps")
    lines.append("")
    for step in planned_steps:
        lines.append(f"- {step['step_id']}: {step['action']} — {step['status']}")
    lines.append("")
    lines.append("## Blocking Errors")
    lines.append("")
    if blocking_errors:
        for item in blocking_errors:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This step did not run DPABI. Future execution must require explicit approval.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": run_plan["ok"],
        "node_id": "dpabi_run_plan",
        "backend": "python",
        "outputs": [
            str(run_plan_path),
            str(report_path),
            str(schema_result.get("schema_path")),
            str(params_validation.get("validation_path")),
        ],
        "metrics": {
            "status": status,
            "subjects_ready": subjects_ready,
            "blocking_errors_count": len(blocking_errors),
            "warnings_count": len(warnings),
        },
        "warnings": warnings,
        "errors": blocking_errors,
    }

注意：请删除示例中的无意义行 run_plan.write_text if False else None，不要保留。

4. 修改 backend/app/runtime/node_registry.py

新增节点：

dpabi_run_plan

新增导入：

from backend.app.tools.dpabi_run_plan import create_dpabi_run_plan

新增 runner：

def run_dpabi_run_plan_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = create_dpabi_run_plan(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        capabilities_path=node.params.get("capabilities_path", f"{context.work_dir}/dpabi/dpabi_capabilities.json"),
        manifest_path=node.params.get("manifest_path", f"{context.work_dir}/dpabi/dpabi_input_manifest.json"),
        preflight_path=node.params.get("preflight_path", f"{context.work_dir}/dpabi/dpabi_preflight_report.json"),
        params_path=node.params.get("params_path", f"{context.work_dir}/dpabi/dpabi_params_review.yaml"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_run_plan": run_dpabi_run_plan_node,
5. 创建 examples/pipeline_dpabi_run_plan.yaml

创建文件：

examples/pipeline_dpabi_run_plan.yaml

内容基于 pipeline_dpabi_preflight.yaml，在最后增加 dpabi_run_plan 节点：

pipeline_id: dpabi_run_plan_pipeline
version: "0.1.0"
modality: integration-test
description: "Generate DPABI parameter schema, review template, validation, and approved run plan without executing DPABI."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_run_plan_001"
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

  - id: dpabi_run_plan
    name: DPABI Approved Run Plan
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_preflight
    inputs:
      - "./work/dpabi/dpabi_capabilities.json"
      - "./work/dpabi/dpabi_input_manifest.json"
      - "./work/dpabi/dpabi_preflight_report.json"
      - "./work/dpabi/dpabi_params_review.yaml"
    outputs:
      - "./work/dpabi/dpabi_parameter_schema.json"
      - "./work/dpabi/dpabi_params_review.yaml"
      - "./work/dpabi/dpabi_params_validation.json"
      - "./work/dpabi/dpabi_run_plan.json"
      - "./reports/dpabi/dpabi_run_plan_report.md"
    params:
      capabilities_path: "./work/dpabi/dpabi_capabilities.json"
      manifest_path: "./work/dpabi/dpabi_input_manifest.json"
      preflight_path: "./work/dpabi/dpabi_preflight_report.json"
      params_path: "./work/dpabi/dpabi_params_review.yaml"
    parallel_level: project
    gpu_supported: false
    cache: false
6. 创建 backend/app/tools/run_dpabi_run_plan_cli.py

创建文件：

backend/app/tools/run_dpabi_run_plan_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dpabi_run_plan.yaml")

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

让 /api/dpabi/capabilities 新增返回：

"parameter_schema": _read_json_if_exists(base / "dpabi_parameter_schema.json"),
"params_review": _read_text_if_exists(base / "dpabi_params_review.yaml"),
"params_validation": _read_json_if_exists(base / "dpabi_params_validation.json"),
"run_plan": _read_json_if_exists(base / "dpabi_run_plan.json"),

让 /api/reports/dpabi 新增返回：

"run_plan_report": _read_text_if_exists(base / "dpabi_run_plan_report.md"),
8. 修改 frontend/src/components/DpabiPanel.tsx

在现有 DPABI Panel 中增加显示：

<h3>DPABI Parameter Schema</h3>
<JsonBlock value={capabilities?.parameter_schema} emptyText="尚未生成 parameter schema" />

<h3>DPABI Params Review YAML</h3>
<TextViewer
  text={
    typeof capabilities?.params_review === "string"
      ? capabilities.params_review
      : null
  }
  emptyText="尚未生成 params review YAML"
/>

<h3>DPABI Params Validation</h3>
<JsonBlock value={capabilities?.params_validation} emptyText="尚未生成 params validation" />

<h3>DPABI Run Plan</h3>
<JsonBlock value={capabilities?.run_plan} emptyText="尚未生成 run plan" />

<h3>DPABI Run Plan Report</h3>
<TextViewer
  text={
    typeof report?.run_plan_report === "string"
      ? report.run_plan_report
      : null
  }
  emptyText="尚未生成 run plan report"
/>

保留原来的 capability、preflight、batch config 内容。

9. 修改 backend/app/tools/api_smoke_test.py

如果已有 DPABI API 测试，不要重复添加。确保包含：

call("GET", "/api/dpabi/capabilities")
call("GET", "/api/reports/dpabi")

不要在 smoke test 中自动运行 DPABI run plan pipeline。

10. 更新 README.md

追加第十九步说明：

## Step 19: DPABI Parameter Review and Approved Run Plan

This step creates a human-reviewable DPABI run plan.

It does not execute DPABI.

### Run DPABI Run Plan Pipeline

```bash
python -m backend.app.tools.run_dpabi_run_plan_cli

Expected outputs:

work/dpabi/dpabi_parameter_schema.json
work/dpabi/dpabi_params_review.yaml
work/dpabi/dpabi_params_validation.json
work/dpabi/dpabi_run_plan.json
reports/dpabi/dpabi_run_plan_report.md
work/pipeline_runs/run_dpabi_run_plan_001/summary.json
API
curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi
Frontend

Use the DPABI Capability / Wrapper Scaffold panel.

It now shows:

parameter schema
params review YAML
params validation
approved run plan
run plan report
Safety

This step does not:

execute DPABI
call DPABI GUI
modify rawdata
modify DPABI source
delete files

The run plan defaults to:

{
  "requires_approval": true,
  "approved": false,
  "execution_allowed": false
}

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_run_plan_spec.md
backend/app/tools/dpabi_param_schema.py
backend/app/tools/dpabi_run_plan.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_run_plan.yaml
backend/app/tools/run_dpabi_run_plan_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/components/DpabiPanel.tsx
README.md

运行：

python -m backend.app.tools.run_dpabi_run_plan_cli

成功后应生成：

work/dpabi/dpabi_parameter_schema.json
work/dpabi/dpabi_params_review.yaml
work/dpabi/dpabi_params_validation.json
work/dpabi/dpabi_run_plan.json
reports/dpabi/dpabi_run_plan_report.md
work/pipeline_runs/run_dpabi_run_plan_001/summary.json

其中：

work/dpabi/dpabi_run_plan.json

应包含：

{
  "mode": "PLAN_ONLY",
  "requires_approval": true,
  "approved": false,
  "execution_allowed": false
}

其中：

work/dpabi/dpabi_params_validation.json

应包含：

{
  "ok": true
}

如果参数不合法，例如：

safety:
  modify_rawdata: true

则 validation 必须失败，run_plan 状态必须是 BLOCKED。

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 DPABI parameter schema。
显示 params review YAML。
显示 params validation。
显示 run plan。
显示 run plan report。
run plan 明确显示 requires_approval=true。
run plan 明确显示 approved=false。
run plan 明确显示 execution_allowed=false。
不执行 DPABI。
不修改 rawdata。
12. 重要限制

本步骤只做 DPABI 参数审查和 run plan。

不要实现：

DPABI 全流程执行
DPARSF_run 自动执行
DPABI GUI 自动化
真实医学影像预处理
自动批准
自动修改参数
删除文件
修改 rawdata
修改 DPABI 源码
并行 DPABI
GPU DPABI

完成后请总结：

新增了哪些文件
修改了哪些文件
如何生成 DPABI run plan
参数 schema 检查哪些内容
run plan 为什么默认不能执行
前端如何查看参数和 run plan
下一步如果要执行 DPABI，必须增加哪些 approval 和 sandbox 机制

'''
Step 19：DPABI 参数审查 + Approved Run Plan 闭环

## 核心目标
在真正执行 DPABI 预处理之前，建立一个 人工可审查的参数审批机制 ，确保所有参数都经过验证和人工确认。

## 主要功能
### 1. DPABI 参数 Schema 定义
- 定义结构化参数分类：basic（基础）、nuisance（噪声回归）、filtering（滤波）、metrics（指标计算）、safety（安全）
- 包含参数类型、范围、是否必填等验证规则
- 输出： work/dpabi/dpabi_parameter_schema.json
### 2. 默认参数审查模板
- 生成可人工编辑的 YAML 文件
- 安全默认值：不执行 DPABI、不修改 rawdata、需要人工审查
- 输出： work/dpabi/dpabi_params_review.yaml
### 3. 参数校验
- 验证 TR > 0
- 验证 smooth_fwhm 是长度为 3 的数组
- 验证 low_freq < high_freq
- 强制安全检查 ：modify_rawdata=false、delete_files=false、require_manual_review=true
- 输出： work/dpabi/dpabi_params_validation.json
### 4. Approved Run Plan 生成
- 整合 capabilities、manifest、preflight、params 四个输入
- 评估状态：
  - READY_FOR_REVIEW - 所有输入有效，等待人工审批
  - WARNING - 存在非阻塞警告
  - BLOCKED - 存在阻塞错误
- 关键安全机制 ：
  - requires_approval=true - 标记需要审批
  - approved=false - 默认不批准
  - execution_allowed=false - 默认不允许执行
- 输出： work/dpabi/dpabi_run_plan.json 、 reports/dpabi/dpabi_run_plan_report.md
## 安全约束
约束 值 说明 allow_full_dpabi_execution false 默认不允许执行 require_manual_review true 必须人工审查 modify_rawdata false 禁止修改 rawdata delete_files false 禁止删除文件

## 本步骤不做的事
- ❌ 不执行 DPABI 预处理
- ❌ 不调用 DPABI GUI
- ❌ 不修改 rawdata
- ❌ 不修改 DPABI 源码
- ❌ 不删除文件
- ❌ 不自动设置 approved=true
'''