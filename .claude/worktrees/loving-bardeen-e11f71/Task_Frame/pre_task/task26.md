你是我的工程搭建助手。前二十五步已经完成：

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
Step 19：完成 DPABI 参数审查 + Approved Run Plan 闭环。
Step 20：完成 DPABI Approved Sandbox Smoke Run + Execution Audit 闭环。
Step 21：完成 DPABI Function Signature Probe + Wrapper Contract Registry 闭环。
Step 22：完成 DPABI Single-Function Wrapper Sandbox + Contract Test 闭环。
Step 23：完成 DPABI Single-Function Subject Wrapper + SPM Baseline Comparison 闭环。
Step 24：完成 DPABI Wrapper Validation Suite + Function Compatibility Matrix 闭环。
Step 25：完成 DPABI Pipeline Template Library + Promotable Wrapper 模板化闭环。

现在开始第二十六步。

第二十六步目标：实现“DPABI Template Instantiation + Approved Synthetic Execution 闭环”。

当前系统已经可以根据 compatibility matrix 生成 template library：

- work/dpabi/templates/dpabi_template_index.json
- work/dpabi/templates/dpabi_template_manifest.yaml
- work/dpabi/templates/pipelines/{template_id}.yaml

这些 template 默认：

- approved=false
- synthetic_only=true
- 不自动执行
- 不调用 DPARSF_run / DPARSFA_run
- 不调用 DPABI GUI

本步骤要实现：

- 读取 template index
- 选择一个 template_id
- 生成 template instance
- 允许设置 run_id、function_name、fwhm、subjects、scheduler
- 默认只做 dry-run instantiation，不执行
- 生成 instantiated pipeline YAML
- 生成 instance manifest JSON
- 生成 instance review Markdown
- approved=false 时不能执行
- approved=true 时可以执行 synthetic-only subject wrapper pipeline
- 写 approval record
- 写 execution summary
- 后端 API 暴露 instantiate / execute / list instances
- 前端 DPABI Panel 增加 Template Instance / Approved Execution 区域
- validation suite 增加 template instantiation 轻量测试

本步骤仍然不要运行完整 DPABI pipeline。
本步骤不要调用 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤只允许 synthetic BIDS-like 数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。

---

## 1. 创建 specs/dpabi_template_instantiation_spec.md

创建文件：

```text
specs/dpabi_template_instantiation_spec.md

内容：

# DPABI Template Instantiation Specification

This document defines the MVP DPABI template instantiation and approved synthetic execution stage.

## Goals

The template instantiator turns a validated DPABI pipeline template into a concrete, reviewable pipeline instance.

It should:

- read the DPABI template index
- select a template by template_id
- create an instantiated pipeline YAML
- create an instance manifest JSON
- create a review Markdown file
- keep approved=false by default
- require explicit approved=true before execution
- execute only synthetic BIDS-like pipelines
- record approval and execution summary

## Scope

Supported in this step:

- template selection
- safe template path validation
- run_id override
- function_name override if allowlisted
- fwhm override
- subject list override
- scheduler override
- dry-run instantiation
- approved synthetic execution
- API and frontend visibility
- lightweight unit test

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- real medical image preprocessing
- rawdata modification
- DPABI source modification
- deletion of files
- production template registry

## Inputs

```text
work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/pipelines/{template_id}.yaml
examples/project_config_dataset.yaml
Outputs
work/dpabi/template_instances/{instance_id}/pipeline.yaml
work/dpabi/template_instances/{instance_id}/instance_manifest.json
work/dpabi/template_instances/{instance_id}/instance_review.md
work/dpabi/template_instances/{instance_id}/approval.json
work/dpabi/template_instances/{instance_id}/execution_summary.json
reports/dpabi/dpabi_template_instance_report.md
Approval Rules
Instantiation does not require approval.
Execution requires approved=true.
The instantiated pipeline must default to approved=false.
The executor may set approved=true only after explicit request.
Full DPABI execution remains disallowed.
Safety Rules
Do not execute generated instances automatically.
Do not execute without approved=true.
Do not run DPARSF_run.
Do not run DPARSFA_run.
Do not call DPABI GUI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Only synthetic BIDS-like templates may be instantiated.

---

## 2. 创建 backend/app/tools/dpabi_template_instantiator.py

创建文件：

```text
backend/app/tools/dpabi_template_instantiator.py

目标：实现 template instance 生成与 approved execution。

提供函数：

list_dpabi_templates(work_dir: str = "./work") -> dict
instantiate_dpabi_template(
    template_id: str,
    instance_id: str | None = None,
    run_id: str | None = None,
    function_name: str | None = None,
    fwhm: list[float] | None = None,
    subjects: list[str] | None = None,
    scheduler: dict | None = None,
    work_dir: str = "./work",
) -> dict
execute_dpabi_template_instance(
    instance_id: str,
    project_config_path: str = "examples/project_config_dataset.yaml",
    approved: bool = False,
    approved_by: str = "local-user",
    work_dir: str = "./work",
) -> dict

实现要求：

读取：
work/dpabi/templates/dpabi_template_index.json
template path 必须位于：
work/dpabi/templates/pipelines/
禁止路径穿越。
只允许 template metadata：
synthetic_only: true
full_dpabi_execution: false
dparsf_run_allowed: false
dparsfa_run_allowed: false
dpabi_gui_allowed: false
function_name 只允许：
y_Smooth
rest_Smooth
实例化输出：
work/dpabi/template_instances/{instance_id}/pipeline.yaml
work/dpabi/template_instances/{instance_id}/instance_manifest.json
work/dpabi/template_instances/{instance_id}/instance_review.md
实例化后的 pipeline 中：
execution.run_id 使用传入 run_id 或自动生成。
dpabi_subject_smooth.params.approved 必须保持 false。
dpabi_subject_smooth.params.function_name 可以被 override。
dpabi_subject_smooth.params.fwhm 可以被 override。
create_synthetic_bids.params.subjects 可以被 override。
execution.scheduler 可以被 override。
execute 时：
approved=false 必须失败。
approved=true 时复制 pipeline 并将 dpabi_subject_smooth.params.approved=true。
写 approval.json。
调用 run_pipeline。
写 execution_summary.json。
不执行完整 DPABI。
不调用 DPARSF_run / DPARSFA_run。
不调用 DPABI GUI。

参考实现：

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWLISTED_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _safe_id(value: str) -> bool:
    if not value:
        return False
    return "/" not in value and "\\" not in value and ".." not in value


def _template_index_path(work_dir: str) -> Path:
    return Path(work_dir) / "dpabi" / "templates" / "dpabi_template_index.json"


def _template_pipeline_root(work_dir: str) -> Path:
    return (Path(work_dir) / "dpabi" / "templates" / "pipelines").resolve()


def _instance_root(work_dir: str, instance_id: str) -> Path:
    return Path(work_dir) / "dpabi" / "template_instances" / instance_id


def _find_template(index: dict[str, Any], template_id: str) -> dict[str, Any] | None:
    for item in index.get("templates", []):
        if item.get("template_id") == template_id:
            return item
    return None


def _validate_template_path(template_path: Path, work_dir: str) -> None:
    root = _template_pipeline_root(work_dir)
    resolved = template_path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Template path escapes template root: {template_path}") from exc


def _validate_template_metadata(pipeline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metadata = pipeline.get("template_metadata", {}) or {}

    if metadata.get("synthetic_only") is not True:
        errors.append("template_metadata.synthetic_only must be true.")

    if metadata.get("full_dpabi_execution") is not False:
        errors.append("template_metadata.full_dpabi_execution must be false.")

    if metadata.get("dparsf_run_allowed") is not False:
        errors.append("template_metadata.dparsf_run_allowed must be false.")

    if metadata.get("dparsfa_run_allowed") is not False:
        errors.append("template_metadata.dparsfa_run_allowed must be false.")

    if metadata.get("dpabi_gui_allowed") is not False:
        errors.append("template_metadata.dpabi_gui_allowed must be false.")

    return errors


def _update_nodes(
    pipeline: dict[str, Any],
    function_name: str | None,
    fwhm: list[float] | None,
    subjects: list[str] | None,
    approved: bool,
) -> None:
    for node in pipeline.get("nodes", []):
        if node.get("id") == "dpabi_subject_smooth":
            node.setdefault("params", {})
            if function_name:
                node["params"]["function_name"] = function_name
            if fwhm:
                node["params"]["fwhm"] = fwhm
            node["params"]["approved"] = approved
            node["params"]["synthetic_only"] = True

        if node.get("id") == "create_synthetic_bids" and subjects:
            node.setdefault("params", {})
            node["params"]["subjects"] = subjects


def list_dpabi_templates(work_dir: str = "./work") -> dict[str, Any]:
    index_path = _template_index_path(work_dir)
    index = _read_json(index_path)

    if not index:
        return {
            "ok": False,
            "templates": [],
            "errors": [f"Missing or invalid template index: {index_path}"],
            "warnings": [],
        }

    return {
        "ok": True,
        "template_index_path": str(index_path),
        "templates": index.get("templates", []),
        "warnings": index.get("warnings", []),
        "errors": [],
    }


def instantiate_dpabi_template(
    template_id: str,
    instance_id: str | None = None,
    run_id: str | None = None,
    function_name: str | None = None,
    fwhm: list[float] | None = None,
    subjects: list[str] | None = None,
    scheduler: dict[str, Any] | None = None,
    work_dir: str = "./work",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if not _safe_id(template_id):
        return {
            "ok": False,
            "errors": ["Invalid template_id."],
            "warnings": warnings,
        }

    instance_id = instance_id or f"instance_{template_id}_001"

    if not _safe_id(instance_id):
        return {
            "ok": False,
            "errors": ["Invalid instance_id."],
            "warnings": warnings,
        }

    if function_name and function_name not in ALLOWLISTED_FUNCTIONS:
        return {
            "ok": False,
            "errors": [f"Function is not allowlisted: {function_name}"],
            "warnings": warnings,
        }

    index = _read_json(_template_index_path(work_dir))
    if not index:
        return {
            "ok": False,
            "errors": [f"Missing template index: {_template_index_path(work_dir)}"],
            "warnings": warnings,
        }

    template = _find_template(index, template_id)
    if not template:
        return {
            "ok": False,
            "errors": [f"Template not found: {template_id}"],
            "warnings": warnings,
        }

    template_path = Path(template.get("template_path", ""))
    try:
        _validate_template_path(template_path, work_dir)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "warnings": warnings,
        }

    try:
        pipeline = _load_yaml(template_path)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Failed to load template YAML: {exc}"],
            "warnings": warnings,
        }

    metadata_errors = _validate_template_metadata(pipeline)
    if metadata_errors:
        return {
            "ok": False,
            "errors": metadata_errors,
            "warnings": warnings,
        }

    final_run_id = run_id or f"run_{instance_id}"

    pipeline.setdefault("execution", {})
    pipeline["execution"]["run_id"] = final_run_id

    if scheduler:
        pipeline["execution"]["scheduler"] = scheduler

    _update_nodes(
        pipeline=pipeline,
        function_name=function_name,
        fwhm=fwhm,
        subjects=subjects,
        approved=False,
    )

    instance_dir = _instance_root(work_dir, instance_id)
    instance_dir.mkdir(parents=True, exist_ok=True)

    pipeline_out = instance_dir / "pipeline.yaml"
    manifest_out = instance_dir / "instance_manifest.json"
    review_out = instance_dir / "instance_review.md"

    _write_yaml(pipeline_out, pipeline)

    manifest = {
        "ok": True,
        "template_id": template_id,
        "instance_id": instance_id,
        "run_id": final_run_id,
        "template_path": str(template_path),
        "pipeline_path": str(pipeline_out),
        "function_name": function_name or template.get("function_name"),
        "fwhm": fwhm,
        "subjects": subjects,
        "scheduler": pipeline.get("execution", {}).get("scheduler", {}),
        "requires_approval": True,
        "approved": False,
        "execution_allowed": False,
        "synthetic_only": True,
        "full_dpabi_execution": False,
        "dparsf_run_allowed": False,
        "dparsfa_run_allowed": False,
        "dpabi_gui_allowed": False,
        "created_at": _now_iso(),
        "warnings": warnings,
        "errors": errors,
    }

    manifest_out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Template Instance Review")
    lines.append("")
    lines.append(f"- Template ID: {template_id}")
    lines.append(f"- Instance ID: {instance_id}")
    lines.append(f"- Run ID: {final_run_id}")
    lines.append(f"- Pipeline: `{pipeline_out}`")
    lines.append(f"- Requires approval: true")
    lines.append(f"- Approved: false")
    lines.append(f"- Execution allowed: false")
    lines.append(f"- Synthetic only: true")
    lines.append("")
    lines.append("## Safety Gates")
    lines.append("")
    lines.append("- Full DPABI execution: false")
    lines.append("- DPARSF_run allowed: false")
    lines.append("- DPARSFA_run allowed: false")
    lines.append("- DPABI GUI allowed: false")
    lines.append("- Rawdata modification: false")
    lines.append("")
    lines.append("This instance is review-only until explicitly approved.")

    review_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "mode": "INSTANTIATE_ONLY",
        "template_id": template_id,
        "instance_id": instance_id,
        "run_id": final_run_id,
        "outputs": [str(pipeline_out), str(manifest_out), str(review_out)],
        "pipeline_path": str(pipeline_out),
        "manifest_path": str(manifest_out),
        "review_path": str(review_out),
        "warnings": warnings,
        "errors": errors,
    }


def execute_dpabi_template_instance(
    instance_id: str,
    project_config_path: str = "examples/project_config_dataset.yaml",
    approved: bool = False,
    approved_by: str = "local-user",
    work_dir: str = "./work",
) -> dict[str, Any]:
    if not _safe_id(instance_id):
        return {
            "ok": False,
            "errors": ["Invalid instance_id."],
            "warnings": [],
        }

    if not approved:
        return {
            "ok": False,
            "mode": "EXECUTE",
            "instance_id": instance_id,
            "errors": ["Template instance execution requires approved=true."],
            "warnings": [],
        }

    instance_dir = _instance_root(work_dir, instance_id)
    pipeline_path = instance_dir / "pipeline.yaml"
    manifest_path = instance_dir / "instance_manifest.json"

    if not pipeline_path.exists():
        return {
            "ok": False,
            "errors": [f"Instance pipeline not found: {pipeline_path}"],
            "warnings": [],
        }

    manifest = _read_json(manifest_path)
    if not manifest:
        return {
            "ok": False,
            "errors": [f"Instance manifest missing or invalid: {manifest_path}"],
            "warnings": [],
        }

    if manifest.get("synthetic_only") is not True:
        return {
            "ok": False,
            "errors": ["Refusing to execute non-synthetic template instance."],
            "warnings": [],
        }

    try:
        pipeline = _load_yaml(pipeline_path)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Failed to load instance pipeline: {exc}"],
            "warnings": [],
        }

    metadata_errors = _validate_template_metadata(pipeline)
    if metadata_errors:
        return {
            "ok": False,
            "errors": metadata_errors,
            "warnings": [],
        }

    _update_nodes(
        pipeline=pipeline,
        function_name=None,
        fwhm=None,
        subjects=None,
        approved=True,
    )

    approved_pipeline = instance_dir / "approved_pipeline.yaml"
    _write_yaml(approved_pipeline, pipeline)

    approval = {
        "approved": True,
        "approved_by": approved_by,
        "approved_at": _now_iso(),
        "execution_type": "dpabi_template_instance_execution",
        "instance_id": instance_id,
        "pipeline_path": str(approved_pipeline),
        "synthetic_only": True,
        "full_dpabi_execution": False,
        "dparsf_run_allowed": False,
        "dparsfa_run_allowed": False,
        "dpabi_gui_allowed": False,
        "rawdata_modified": False,
        "files_deleted": False,
    }

    approval_path = instance_dir / "approval.json"
    approval_path.write_text(
        json.dumps(approval, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    from backend.app.runtime.pipeline_executor import run_pipeline

    summary = run_pipeline(project_config_path, approved_pipeline)

    execution_summary = {
        "ok": summary.get("status") in {"SUCCESS", "PARTIAL"},
        "mode": "EXECUTE",
        "instance_id": instance_id,
        "approved": True,
        "approval_path": str(approval_path),
        "approved_pipeline": str(approved_pipeline),
        "pipeline_summary": summary,
        "safety": {
            "synthetic_only": True,
            "full_dpabi_execution": False,
            "dparsf_run_allowed": False,
            "dparsfa_run_allowed": False,
            "dpabi_gui_allowed": False,
            "rawdata_modified": False,
            "files_deleted": False,
        },
    }

    execution_path = instance_dir / "execution_summary.json"
    execution_path.write_text(
        json.dumps(execution_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report_dir = Path("reports") / "dpabi"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "dpabi_template_instance_report.md"

    lines = []
    lines.append("# DPABI Template Instance Execution Report")
    lines.append("")
    lines.append(f"- Instance ID: {instance_id}")
    lines.append(f"- Approved: true")
    lines.append(f"- Pipeline status: {summary.get('status')}")
    lines.append(f"- Approved pipeline: `{approved_pipeline}`")
    lines.append(f"- Approval record: `{approval_path}`")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("- Synthetic only: true")
    lines.append("- Full DPABI execution: false")
    lines.append("- DPARSF_run allowed: false")
    lines.append("- DPARSFA_run allowed: false")
    lines.append("- DPABI GUI allowed: false")
    lines.append("- Rawdata modified: false")
    lines.append("- Files deleted: false")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    execution_summary["outputs"] = [
        str(approved_pipeline),
        str(approval_path),
        str(execution_path),
        str(report_path),
    ]

    return execution_summary
3. 创建 backend/app/tools/run_dpabi_template_instance_cli.py

创建文件：

backend/app/tools/run_dpabi_template_instance_cli.py

功能：

默认 template_id：
dpabi_y_smooth_subject_wrapper_template
默认 instance_id：
instance_dpabi_y_smooth_001
默认只 instantiate，不 execute。
传入 --approve 才执行。
打印 JSON。
返回码：
ok=true 返回 0
ok=false 返回 2

内容：

from __future__ import annotations

import json
import sys

from backend.app.tools.dpabi_template_instantiator import (
    execute_dpabi_template_instance,
    instantiate_dpabi_template,
)


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    template_id = args[0] if len(args) > 0 else "dpabi_y_smooth_subject_wrapper_template"
    instance_id = args[1] if len(args) > 1 else "instance_dpabi_y_smooth_001"
    function_name = args[2] if len(args) > 2 else "y_Smooth"

    result = instantiate_dpabi_template(
        template_id=template_id,
        instance_id=instance_id,
        function_name=function_name,
        fwhm=[4, 4, 4],
        subjects=["sub-001", "sub-002"],
    )

    if result.get("ok") and approved:
        result = execute_dpabi_template_instance(
            instance_id=instance_id,
            approved=True,
            approved_by="local-user",
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
4. 修改 backend/app/api/models.py

新增 request models：

class DpabiTemplateInstantiateRequest(BaseModel):
    template_id: str = Field(default="dpabi_y_smooth_subject_wrapper_template")
    instance_id: str | None = Field(default=None)
    run_id: str | None = Field(default=None)
    function_name: str | None = Field(default="y_Smooth")
    fwhm: list[float] | None = Field(default=[4, 4, 4])
    subjects: list[str] | None = Field(default=["sub-001", "sub-002"])
    scheduler: dict[str, Any] | None = Field(default=None)


class DpabiTemplateExecuteRequest(BaseModel):
    instance_id: str = Field(default="instance_dpabi_y_smooth_001")
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    approved: bool = Field(default=False)
    approved_by: str = Field(default="local-user")

如果 Any 还没有导入，在 models.py 顶部加入：

from typing import Any
5. 修改 backend/app/api/routes.py

新增 API：

GET  /api/dpabi/template-instances
POST /api/dpabi/templates/instantiate
POST /api/dpabi/templates/execute

新增导入：

from backend.app.api.models import (
    DpabiTemplateExecuteRequest,
    DpabiTemplateInstantiateRequest,
)
from backend.app.tools.dpabi_template_instantiator import (
    execute_dpabi_template_instance,
    instantiate_dpabi_template,
    list_dpabi_templates,
)

新增路由：

@router.get("/api/dpabi/template-instances")
def api_list_dpabi_template_instances() -> dict[str, Any]:
    base = Path("work") / "dpabi" / "template_instances"
    instances = []

    if base.exists():
        for item in sorted(base.iterdir()):
            if not item.is_dir():
                continue
            instances.append({
                "instance_id": item.name,
                "manifest": _read_json_if_exists(item / "instance_manifest.json"),
                "execution_summary": _read_json_if_exists(item / "execution_summary.json"),
                "approval": _read_json_if_exists(item / "approval.json"),
            })

    return {
        "ok": True,
        "templates": list_dpabi_templates("./work"),
        "instances": instances,
    }


@router.post("/api/dpabi/templates/instantiate")
def api_instantiate_dpabi_template(
    request: DpabiTemplateInstantiateRequest,
) -> dict[str, Any]:
    result = instantiate_dpabi_template(
        template_id=request.template_id,
        instance_id=request.instance_id,
        run_id=request.run_id,
        function_name=request.function_name,
        fwhm=request.fwhm,
        subjects=request.subjects,
        scheduler=request.scheduler,
        work_dir="./work",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/api/dpabi/templates/execute")
def api_execute_dpabi_template(
    request: DpabiTemplateExecuteRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="DPABI template instance execution requires approved=true.",
        )

    result = execute_dpabi_template_instance(
        instance_id=request.instance_id,
        project_config_path=request.project_config_path,
        approved=request.approved,
        approved_by=request.approved_by,
        work_dir="./work",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result

同时修改已有 /api/dpabi/templates，让它也返回 instances：

"instances": api_list_dpabi_template_instances().get("instances", []),
6. 修改 frontend/src/api.ts

新增：

export async function listDpabiTemplateInstances(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-instances"
  );
}

export async function instantiateDpabiTemplate(
  baseUrl: string,
  payload: {
    template_id: string;
    instance_id?: string | null;
    run_id?: string | null;
    function_name?: string | null;
    fwhm?: number[] | null;
    subjects?: string[] | null;
    scheduler?: Record<string, unknown> | null;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/templates/instantiate",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function executeDpabiTemplate(
  baseUrl: string,
  payload: {
    instance_id: string;
    project_config_path: string;
    approved: boolean;
    approved_by: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/templates/execute",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}
7. 修改 frontend/src/components/DpabiPanel.tsx

新增导入：

import {
  executeDpabiTemplate,
  instantiateDpabiTemplate,
  listDpabiTemplateInstances
} from "../api";

如果已有 DPABI API import，请合并。

新增 state：

const [templateId, setTemplateId] = useState("dpabi_y_smooth_subject_wrapper_template");
const [templateInstanceId, setTemplateInstanceId] = useState("instance_dpabi_y_smooth_001");
const [templateFunctionName, setTemplateFunctionName] = useState("y_Smooth");
const [templateInstanceResult, setTemplateInstanceResult] = useState<Record<string, unknown> | null>(null);
const [templateExecutionResult, setTemplateExecutionResult] = useState<Record<string, unknown> | null>(null);
const [templateInstanceStatus, setTemplateInstanceStatus] = useState("IDLE");

新增函数：

async function handleInstantiateTemplate() {
  setTemplateInstanceStatus("INSTANTIATING");
  setError("");

  try {
    const result = await instantiateDpabiTemplate(baseUrl, {
      template_id: templateId,
      instance_id: templateInstanceId,
      function_name: templateFunctionName,
      fwhm: [4, 4, 4],
      subjects: ["sub-001", "sub-002"],
      scheduler: {
        mode: "local_parallel",
        max_workers: 2,
        matlab_max_workers: 1
      }
    });
    setTemplateInstanceResult(result);
    setTemplateInstanceStatus("INSTANTIATED");
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
    setTemplateInstanceStatus("ERROR");
  }
}

async function handleExecuteTemplate() {
  const confirmed = window.confirm(
    `确认执行 DPABI template instance：${templateInstanceId}？这只处理 synthetic BIDS 数据，不会运行完整 DPABI/DPARSF。`
  );

  if (!confirmed) return;

  setTemplateInstanceStatus("EXECUTING");
  setError("");

  try {
    const result = await executeDpabiTemplate(baseUrl, {
      instance_id: templateInstanceId,
      project_config_path: "examples/project_config_dataset.yaml",
      approved: true,
      approved_by: "local-user"
    });
    setTemplateExecutionResult(result);
    setTemplateInstanceStatus("EXECUTED");
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
    setTemplateInstanceStatus("ERROR");
  }
}

async function handleLoadTemplateInstances() {
  setError("");

  try {
    const result = await listDpabiTemplateInstances(baseUrl);
    setTemplateInstanceResult(result);
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
  }
}

在 JSX 中新增：

<h3>DPABI Template Instance / Approved Execution</h3>

<div className="formGrid">
  <label>
    Template ID
    <input
      value={templateId}
      onChange={(event) => setTemplateId(event.target.value)}
    />
  </label>

  <label>
    Instance ID
    <input
      value={templateInstanceId}
      onChange={(event) => setTemplateInstanceId(event.target.value)}
    />
  </label>

  <label>
    Function
    <select
      value={templateFunctionName}
      onChange={(event) => setTemplateFunctionName(event.target.value)}
    >
      <option value="y_Smooth">y_Smooth</option>
      <option value="rest_Smooth">rest_Smooth</option>
    </select>
  </label>
</div>

<div className="row">
  <button onClick={handleInstantiateTemplate}>
    生成 Template Instance
  </button>
  <button className="dangerButton" onClick={handleExecuteTemplate}>
    批准并执行 Template Instance
  </button>
  <button onClick={handleLoadTemplateInstances}>
    加载 Template Instances
  </button>
  <StatusBadge status={templateInstanceStatus} />
</div>

<h3>Template Instance Result</h3>
<JsonBlock value={templateInstanceResult} emptyText="尚未生成 template instance" />

<h3>Template Execution Result</h3>
<JsonBlock value={templateExecutionResult} emptyText="尚未执行 template instance" />
8. 新增轻量测试

创建文件：

tests/unit/test_dpabi_template_instantiator.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.dpabi_template_instantiator import instantiate_dpabi_template


def test_dpabi_template_instantiation_keeps_approved_false(tmp_path: Path):
    work = tmp_path / "work"
    templates = work / "dpabi" / "templates"
    pipelines = templates / "pipelines"
    pipelines.mkdir(parents=True)

    template_id = "dpabi_y_smooth_subject_wrapper_template"
    template_path = pipelines / f"{template_id}.yaml"

    template_path.write_text(
        """
pipeline_id: dpabi_y_smooth_subject_wrapper_template
version: "0.1.0"
modality: synthetic-rsfmri
template_metadata:
  synthetic_only: true
  full_dpabi_execution: false
  dparsf_run_allowed: false
  dparsfa_run_allowed: false
  dpabi_gui_allowed: false
execution:
  run_id: run_template
nodes:
  - id: create_synthetic_bids
    params:
      subjects:
        - sub-001
  - id: dpabi_subject_smooth
    params:
      function_name: y_Smooth
      fwhm: [4, 4, 4]
      approved: false
""",
        encoding="utf-8",
    )

    index_path = templates / "dpabi_template_index.json"
    index_path.write_text(
        json.dumps({
            "templates": [
                {
                    "template_id": template_id,
                    "function_name": "y_Smooth",
                    "template_path": str(template_path),
                    "requires_approval": True,
                    "approved_by_default": False,
                    "synthetic_only": True,
                }
            ]
        }),
        encoding="utf-8",
    )

    result = instantiate_dpabi_template(
        template_id=template_id,
        instance_id="instance_test",
        function_name="y_Smooth",
        subjects=["sub-001", "sub-002"],
        work_dir=str(work),
    )

    assert result["ok"] is True

    pipeline_text = Path(result["pipeline_path"]).read_text(encoding="utf-8")
    assert "approved: false" in pipeline_text
    assert "sub-002" in pipeline_text

    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["approved"] is False
    assert manifest["execution_allowed"] is False
    assert manifest["synthetic_only"] is True
9. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/dpabi/template-instances")

不要在 smoke test 中调用 POST execute，避免误启动 MATLAB。

10. 更新 README.md

追加第二十六步说明：

## Step 26: DPABI Template Instantiation and Approved Synthetic Execution

This step instantiates generated DPABI pipeline templates.

It supports:

- template selection
- instance generation
- review manifest
- approved synthetic execution
- approval record
- execution summary

It does not run full DPABI preprocessing.

### Instantiate only

```bash
python -m backend.app.tools.run_dpabi_template_instance_cli

Expected outputs:

work/dpabi/template_instances/instance_dpabi_y_smooth_001/pipeline.yaml
work/dpabi/template_instances/instance_dpabi_y_smooth_001/instance_manifest.json
work/dpabi/template_instances/instance_dpabi_y_smooth_001/instance_review.md
Approved execution
python -m backend.app.tools.run_dpabi_template_instance_cli dpabi_y_smooth_subject_wrapper_template instance_dpabi_y_smooth_001 y_Smooth --approve

Expected outputs:

work/dpabi/template_instances/instance_dpabi_y_smooth_001/approved_pipeline.yaml
work/dpabi/template_instances/instance_dpabi_y_smooth_001/approval.json
work/dpabi/template_instances/instance_dpabi_y_smooth_001/execution_summary.json
reports/dpabi/dpabi_template_instance_report.md
API
curl http://127.0.0.1:8000/api/dpabi/template-instances

Instantiate:

curl -X POST http://127.0.0.1:8000/api/dpabi/templates/instantiate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "dpabi_y_smooth_subject_wrapper_template",
    "instance_id": "instance_dpabi_y_smooth_001",
    "function_name": "y_Smooth"
  }'

Execute with approval:

curl -X POST http://127.0.0.1:8000/api/dpabi/templates/execute \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "instance_dpabi_y_smooth_001",
    "approved": true,
    "approved_by": "local-user"
  }'
Safety

Template instances:

default to approved=false
require approved=true before execution
only target synthetic BIDS-like data
do not run DPARSF_run
do not run DPARSFA_run
do not call DPABI GUI
do not modify rawdata

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_template_instantiation_spec.md
backend/app/tools/dpabi_template_instantiator.py
backend/app/tools/run_dpabi_template_instance_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/DpabiPanel.tsx
tests/unit/test_dpabi_template_instantiator.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有 template library：

python -m backend.app.tools.run_dpabi_template_library_cli

然后只生成 instance：

python -m backend.app.tools.run_dpabi_template_instance_cli

应该生成：

work/dpabi/template_instances/instance_dpabi_y_smooth_001/pipeline.yaml
work/dpabi/template_instances/instance_dpabi_y_smooth_001/instance_manifest.json
work/dpabi/template_instances/instance_dpabi_y_smooth_001/instance_review.md

其中 manifest 必须包含：

{
  "requires_approval": true,
  "approved": false,
  "execution_allowed": false,
  "synthetic_only": true,
  "full_dpabi_execution": false
}

运行 approved execution：

python -m backend.app.tools.run_dpabi_template_instance_cli dpabi_y_smooth_subject_wrapper_template instance_dpabi_y_smooth_001 y_Smooth --approve

如果本地 DPABI 中 y_Smooth 可用，应该生成：

work/dpabi/template_instances/instance_dpabi_y_smooth_001/approved_pipeline.yaml
work/dpabi/template_instances/instance_dpabi_y_smooth_001/approval.json
work/dpabi/template_instances/instance_dpabi_y_smooth_001/execution_summary.json
reports/dpabi/dpabi_template_instance_report.md

其中 approval.json 必须包含：

{
  "approved": true,
  "execution_type": "dpabi_template_instance_execution",
  "synthetic_only": true,
  "full_dpabi_execution": false,
  "dparsf_run_allowed": false,
  "dpabi_gui_allowed": false,
  "rawdata_modified": false,
  "files_deleted": false
}

运行测试：

python -m pytest tests/unit/test_dpabi_template_instantiator.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/template-instances

未批准 execute 应失败：

curl -X POST http://127.0.0.1:8000/api/dpabi/templates/execute \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "instance_dpabi_y_smooth_001", "approved": false}'

批准 execute 可运行：

curl -X POST http://127.0.0.1:8000/api/dpabi/templates/execute \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "instance_dpabi_y_smooth_001", "approved": true}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

DPABI Panel 显示 Template Instance / Approved Execution 区域。
可以输入 template_id。
可以输入 instance_id。
可以选择 y_Smooth 或 rest_Smooth。
点击生成 Template Instance 后只生成实例，不执行。
点击批准并执行前有 confirm 弹窗。
approved 后执行 synthetic-only pipeline。
显示 instance result。
显示 execution result。
不运行完整 DPABI preprocessing。
不调用 DPARSF_run / DPARSFA_run。
不调用 DPABI GUI。
不读取或修改真实 rawdata。
12. 重要限制

本步骤只做 template instantiation 和 approved synthetic execution。

不要实现：

自动执行 template
无 approval 执行
DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
真实医学影像处理
自动参数优化
修改 rawdata
修改 DPABI 源码
删除文件
生产级模板市场

完成后请总结：

新增了哪些文件
修改了哪些文件
如何生成 template instance
如何 approved execute template instance
instance manifest 记录了哪些 safety gates
为什么 approved execution 仍然不是完整 DPABI pipeline
下一步如何做参数化 UI / pipeline wizard

'''
Step 26: DPABI Template Instantiation + Approved Synthetic Execution 闭环 主要完成以下工作：

## 核心目标
将验证通过的 DPABI Pipeline Template 转换为 可审查、可批准、可执行 的具体 Pipeline 实例，形成完整的"模板→实例→执行"闭环。

## 主要功能
### 1. Template Instantiation（模板实例化）
- 读取 DPABI 模板索引 ( dpabi_template_index.json )
- 根据 template_id 选择模板
- 创建实例化的 Pipeline YAML（支持参数覆盖）
- 生成实例清单 ( instance_manifest.json )
- 生成人工审查文档 ( instance_review.md )
- 默认 approved=false （未批准状态）
### 2. 参数覆盖支持
- run_id - 执行运行ID
- function_name - 覆盖DPABI函数（仅白名单函数）
- fwhm - 平滑核参数
- subjects - 被试列表
- scheduler - 调度器配置
### 3. Approved Execution（批准执行）
- 必须 显式设置 approved=true 才能执行
- 记录批准时间戳和批准人身份
- 仅执行合成BIDS-like Pipeline
- 执行前验证安全元数据
### 4. 安全规则
- 实例化无需批准，执行需要批准
- 仅允许白名单函数 ( y_Smooth , rest_Smooth )
- 仅允许合成数据模板
- 禁止完整DPABI执行、DPARSF_run、DPABI GUI
- 禁止修改rawdata和DPABI源码
## 输出文件结构
```
work/dpabi/template_instances/{instance_id}/
├── pipeline.yaml              # 实例化的Pipeline
├── instance_manifest.json     # 实例元数据
├── instance_review.md         # 人工审查文档
├── approval.json              # 批准记录
└── execution_summary.json     # 执行结果摘要
```
## 批准流程
1. Instantiate → 选择模板、配置参数、生成实例（无需批准）
2. Review → 人工审查 instance_review.md 和安全元数据
3. Approve → 显式批准，记录批准人，生成 approval.json
4. Execute → 验证批准后执行Pipeline，生成执行摘要
这一步完成了从"可提升为模板的函数"到"可安全执行的Pipeline实例"的最后一环，确保所有执行都经过人工审查和显式批准。
'''