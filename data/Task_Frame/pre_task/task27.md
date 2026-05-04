你是我的工程搭建助手。前二十六步已经完成：

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
Step 26：完成 DPABI Template Instantiation + Approved Synthetic Execution 闭环。

现在开始第二十七步。

第二十七步目标：实现“DPABI Parameterized Pipeline Wizard + Review UI 闭环”。

当前系统已经可以：

- 生成 DPABI template library
- 生成 template instance
- approved 后执行 synthetic-only template instance
- 记录 approval 和 execution summary

但当前实例化主要通过 CLI/API 参数完成，缺少一个可视化、可审查的 pipeline wizard。

本步骤要实现：

- 后端生成 wizard options
- 后端校验 wizard 参数
- 后端生成 wizard preview
- 后端创建 template instance
- 前端提供参数化 UI
- 用户可以选择 template_id
- 用户可以选择 function_name
- 用户可以设置 subjects
- 用户可以设置 fwhm
- 用户可以设置 scheduler
- 用户可以先 preview，不执行
- 用户可以 create instance，不执行
- 用户可以显式 approval 后 execute instance
- 页面显示 safety gates、manifest、review、execution summary
- validation suite 增加 wizard 参数校验轻量测试

本步骤不要运行完整 DPABI pipeline。
本步骤不要调用 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤只允许 synthetic BIDS-like 数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。
本步骤默认只 preview/create，不 execute；execute 必须 approved=true。

---

## 1. 创建 specs/dpabi_pipeline_wizard_spec.md

创建文件：

```text
specs/dpabi_pipeline_wizard_spec.md

内容：

# DPABI Pipeline Wizard Specification

This document defines the MVP DPABI parameterized pipeline wizard.

## Goals

The wizard helps users create reviewable DPABI template instances through a structured UI.

It should:

- load available DPABI templates
- expose only safe parameters
- validate template_id, function_name, fwhm, subjects, and scheduler
- generate a preview without execution
- create a template instance without execution
- require explicit approval before execution
- display safety gates and review artifacts

## Scope

Supported in this step:

- wizard options
- parameter validation
- preview generation
- template instance creation
- approved instance execution via existing executor
- frontend wizard panel
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
- production workflow builder

## Inputs

```text
work/dpabi/templates/dpabi_template_index.json
work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/template_instances/{instance_id}/...
Outputs
work/dpabi/template_wizard/latest_preview.json
work/dpabi/template_wizard/latest_preview.md
work/dpabi/template_instances/{instance_id}/pipeline.yaml
work/dpabi/template_instances/{instance_id}/instance_manifest.json
work/dpabi/template_instances/{instance_id}/instance_review.md
Allowed Parameters
template_id
instance_id
run_id
function_name
fwhm
subjects
scheduler.mode
scheduler.max_workers
scheduler.matlab_max_workers
Safety Rules
Do not execute on preview.
Do not execute on create.
Execute only with approved=true.
Only allow y_Smooth and rest_Smooth.
Only allow synthetic subject IDs such as sub-001.
Default approved=false.
Do not run DPARSF_run.
Do not run DPARSFA_run.
Do not call DPABI GUI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.

---

## 2. 创建 backend/app/tools/dpabi_template_wizard.py

创建文件：

```text
backend/app/tools/dpabi_template_wizard.py

目标：提供 wizard options、参数校验和 preview。

提供函数：

get_dpabi_template_wizard_options(work_dir: str = "./work") -> dict
validate_dpabi_template_wizard_payload(payload: dict, work_dir: str = "./work") -> dict
preview_dpabi_template_instance(payload: dict, work_dir: str = "./work") -> dict
create_dpabi_template_instance_from_wizard(payload: dict, work_dir: str = "./work") -> dict

要求：

读取：
work/dpabi/templates/dpabi_template_index.json
work/dpabi/dpabi_wrapper_compatibility_matrix.json
只允许 function_name：
y_Smooth
rest_Smooth
subjects 只允许 sub- 开头。
fwhm 必须是 3 个正数。
scheduler.mode 只允许：
sequential
local_parallel
scheduler.max_workers 范围 1 到 8。
scheduler.matlab_max_workers 范围 1 到 max_workers。
preview 只写：
latest_preview.json
latest_preview.md
preview 不调用 instantiate。
create 调用已有 instantiate_dpabi_template。
create 不执行。
所有返回必须结构化。

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.tools.dpabi_template_instantiator import (
    instantiate_dpabi_template,
    list_dpabi_templates,
)


ALLOWLISTED_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _wizard_dir(work_dir: str) -> Path:
    return Path(work_dir) / "dpabi" / "template_wizard"


def _matrix_path(work_dir: str) -> Path:
    return Path(work_dir) / "dpabi" / "dpabi_wrapper_compatibility_matrix.json"


def get_dpabi_template_wizard_options(work_dir: str = "./work") -> dict[str, Any]:
    templates = list_dpabi_templates(work_dir)
    matrix = _read_json(_matrix_path(work_dir))

    promotable_functions: list[str] = []
    if matrix:
        for row in matrix.get("rows", []):
            if row.get("readiness") == "PROMOTABLE_TO_TEMPLATE":
                fn = row.get("function_name")
                if fn in ALLOWLISTED_FUNCTIONS:
                    promotable_functions.append(fn)

    return {
        "ok": templates.get("ok", False),
        "templates": templates.get("templates", []),
        "functions": sorted(set(promotable_functions) or ALLOWLISTED_FUNCTIONS),
        "default_subjects": ["sub-001", "sub-002"],
        "default_fwhm": [4, 4, 4],
        "default_scheduler": {
            "mode": "local_parallel",
            "max_workers": 2,
            "matlab_max_workers": 1,
        },
        "safety": {
            "synthetic_only": True,
            "requires_approval": True,
            "approved_by_default": False,
            "full_dpabi_execution": False,
            "dparsf_run_allowed": False,
            "dparsfa_run_allowed": False,
            "dpabi_gui_allowed": False,
        },
        "warnings": templates.get("warnings", []),
        "errors": templates.get("errors", []),
    }


def validate_dpabi_template_wizard_payload(
    payload: dict[str, Any],
    work_dir: str = "./work",
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    template_id = str(payload.get("template_id", "")).strip()
    instance_id = str(payload.get("instance_id", "")).strip()
    function_name = str(payload.get("function_name", "")).strip()
    fwhm = payload.get("fwhm", [4, 4, 4])
    subjects = payload.get("subjects", ["sub-001", "sub-002"])
    scheduler = payload.get("scheduler", {}) or {}

    if not template_id or "/" in template_id or "\\" in template_id or ".." in template_id:
        errors.append("Invalid template_id.")

    if instance_id and ("/" in instance_id or "\\" in instance_id or ".." in instance_id):
        errors.append("Invalid instance_id.")

    options = get_dpabi_template_wizard_options(work_dir)
    available_template_ids = {
        item.get("template_id") for item in options.get("templates", [])
    }

    if template_id not in available_template_ids:
        errors.append(f"Template is not available: {template_id}")

    if function_name not in ALLOWLISTED_FUNCTIONS:
        errors.append(f"Function is not allowlisted: {function_name}")

    if not isinstance(fwhm, list) or len(fwhm) != 3:
        errors.append("fwhm must be a list of length 3.")
    else:
        for value in fwhm:
            try:
                if float(value) <= 0:
                    errors.append("fwhm values must be positive.")
            except Exception:
                errors.append("fwhm values must be numeric.")

    if not isinstance(subjects, list) or not subjects:
        errors.append("subjects must be a non-empty list.")
    else:
        for subject in subjects:
            if not isinstance(subject, str) or not subject.startswith("sub-"):
                errors.append(f"Invalid synthetic subject id: {subject}")

    mode = scheduler.get("mode", "local_parallel")
    if mode not in {"sequential", "local_parallel"}:
        errors.append(f"Invalid scheduler.mode: {mode}")

    try:
        max_workers = int(scheduler.get("max_workers", 2))
    except Exception:
        max_workers = 2
        errors.append("scheduler.max_workers must be an integer.")

    try:
        matlab_max_workers = int(scheduler.get("matlab_max_workers", 1))
    except Exception:
        matlab_max_workers = 1
        errors.append("scheduler.matlab_max_workers must be an integer.")

    if max_workers < 1 or max_workers > 8:
        errors.append("scheduler.max_workers must be between 1 and 8.")

    if matlab_max_workers < 1 or matlab_max_workers > max_workers:
        errors.append("scheduler.matlab_max_workers must be between 1 and max_workers.")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "normalized": {
            "template_id": template_id,
            "instance_id": instance_id or None,
            "run_id": payload.get("run_id"),
            "function_name": function_name,
            "fwhm": [float(x) for x in fwhm] if isinstance(fwhm, list) and len(fwhm) == 3 else fwhm,
            "subjects": subjects,
            "scheduler": {
                "mode": mode,
                "max_workers": max_workers,
                "matlab_max_workers": matlab_max_workers,
            },
        },
    }


def preview_dpabi_template_instance(
    payload: dict[str, Any],
    work_dir: str = "./work",
) -> dict[str, Any]:
    validation = validate_dpabi_template_wizard_payload(payload, work_dir)
    out_dir = _wizard_dir(work_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    preview_json = out_dir / "latest_preview.json"
    preview_md = out_dir / "latest_preview.md"

    if not validation.get("ok"):
        preview = {
            "ok": False,
            "mode": "PREVIEW",
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
            "normalized": validation.get("normalized"),
        }
    else:
        normalized = validation["normalized"]
        preview = {
            "ok": True,
            "mode": "PREVIEW",
            "will_execute": False,
            "template_id": normalized["template_id"],
            "instance_id": normalized["instance_id"],
            "run_id": normalized["run_id"],
            "function_name": normalized["function_name"],
            "fwhm": normalized["fwhm"],
            "subjects": normalized["subjects"],
            "scheduler": normalized["scheduler"],
            "safety": {
                "requires_approval": True,
                "approved": False,
                "execution_allowed": False,
                "synthetic_only": True,
                "full_dpabi_execution": False,
                "dparsf_run_allowed": False,
                "dparsfa_run_allowed": False,
                "dpabi_gui_allowed": False,
                "rawdata_modified": False,
                "files_deleted": False,
            },
            "warnings": validation.get("warnings", []),
            "errors": [],
        }

    preview_json.write_text(
        json.dumps(preview, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Template Wizard Preview")
    lines.append("")
    lines.append(f"- OK: {preview.get('ok')}")
    lines.append(f"- Template ID: {preview.get('template_id')}")
    lines.append(f"- Instance ID: {preview.get('instance_id')}")
    lines.append(f"- Function: {preview.get('function_name')}")
    lines.append(f"- Subjects: {preview.get('subjects')}")
    lines.append(f"- Will execute: {preview.get('will_execute')}")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("- Requires approval: true")
    lines.append("- Approved: false")
    lines.append("- Execution allowed: false")
    lines.append("- Synthetic only: true")
    lines.append("- Full DPABI execution: false")
    lines.append("- DPARSF_run allowed: false")
    lines.append("- DPARSFA_run allowed: false")
    lines.append("- DPABI GUI allowed: false")

    preview_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    preview["outputs"] = [str(preview_json), str(preview_md)]
    return preview


def create_dpabi_template_instance_from_wizard(
    payload: dict[str, Any],
    work_dir: str = "./work",
) -> dict[str, Any]:
    validation = validate_dpabi_template_wizard_payload(payload, work_dir)
    if not validation.get("ok"):
        return {
            "ok": False,
            "mode": "CREATE_INSTANCE",
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
        }

    normalized = validation["normalized"]

    result = instantiate_dpabi_template(
        template_id=normalized["template_id"],
        instance_id=normalized["instance_id"],
        run_id=normalized["run_id"],
        function_name=normalized["function_name"],
        fwhm=normalized["fwhm"],
        subjects=normalized["subjects"],
        scheduler=normalized["scheduler"],
        work_dir=work_dir,
    )

    result["mode"] = "CREATE_INSTANCE"
    result["created_by"] = "dpabi_template_wizard"
    return result
3. 修改 backend/app/api/models.py

新增 request model：

class DpabiTemplateWizardRequest(BaseModel):
    template_id: str = Field(default="dpabi_y_smooth_subject_wrapper_template")
    instance_id: str | None = Field(default="instance_dpabi_y_smooth_001")
    run_id: str | None = Field(default=None)
    function_name: str = Field(default="y_Smooth")
    fwhm: list[float] = Field(default=[4, 4, 4])
    subjects: list[str] = Field(default=["sub-001", "sub-002"])
    scheduler: dict[str, Any] = Field(
        default={
            "mode": "local_parallel",
            "max_workers": 2,
            "matlab_max_workers": 1,
        }
    )

如果 models.py 顶部还没有 Any：

from typing import Any
4. 修改 backend/app/api/routes.py

新增 API：

GET  /api/dpabi/template-wizard/options
POST /api/dpabi/template-wizard/preview
POST /api/dpabi/template-wizard/create
GET  /api/dpabi/template-wizard/latest

新增导入：

from backend.app.api.models import DpabiTemplateWizardRequest
from backend.app.tools.dpabi_template_wizard import (
    create_dpabi_template_instance_from_wizard,
    get_dpabi_template_wizard_options,
    preview_dpabi_template_instance,
)

新增路由：

@router.get("/api/dpabi/template-wizard/options")
def api_dpabi_template_wizard_options() -> dict[str, Any]:
    result = get_dpabi_template_wizard_options("./work")
    if not result.get("ok"):
        return result
    return result


@router.post("/api/dpabi/template-wizard/preview")
def api_dpabi_template_wizard_preview(
    request: DpabiTemplateWizardRequest,
) -> dict[str, Any]:
    result = preview_dpabi_template_instance(
        payload=request.model_dump(),
        work_dir="./work",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/dpabi/template-wizard/create")
def api_dpabi_template_wizard_create(
    request: DpabiTemplateWizardRequest,
) -> dict[str, Any]:
    result = create_dpabi_template_instance_from_wizard(
        payload=request.model_dump(),
        work_dir="./work",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/dpabi/template-wizard/latest")
def api_dpabi_template_wizard_latest() -> dict[str, Any]:
    base = Path("work") / "dpabi" / "template_wizard"

    return {
        "ok": True,
        "latest_preview": _read_json_if_exists(base / "latest_preview.json"),
        "latest_preview_markdown": _read_text_if_exists(base / "latest_preview.md"),
    }
5. 修改 frontend/src/api.ts

新增：

export async function getDpabiTemplateWizardOptions(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/options"
  );
}

export async function previewDpabiTemplateWizard(
  baseUrl: string,
  payload: {
    template_id: string;
    instance_id?: string | null;
    run_id?: string | null;
    function_name: string;
    fwhm: number[];
    subjects: string[];
    scheduler: Record<string, unknown>;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/preview",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function createDpabiTemplateWizardInstance(
  baseUrl: string,
  payload: {
    template_id: string;
    instance_id?: string | null;
    run_id?: string | null;
    function_name: string;
    fwhm: number[];
    subjects: string[];
    scheduler: Record<string, unknown>;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/create",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getDpabiTemplateWizardLatest(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/latest"
  );
}
6. 创建 frontend/src/components/DpabiTemplateWizard.tsx

创建文件：

frontend/src/components/DpabiTemplateWizard.tsx

内容：

import { useEffect, useState } from "react";
import {
  createDpabiTemplateWizardInstance,
  executeDpabiTemplate,
  getDpabiTemplateWizardLatest,
  getDpabiTemplateWizardOptions,
  previewDpabiTemplateWizard
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

function parseList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseFwhm(value: string) {
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item));
}

export function DpabiTemplateWizard({ baseUrl }: Props) {
  const [options, setOptions] = useState<Record<string, unknown> | null>(null);
  const [templateId, setTemplateId] = useState("dpabi_y_smooth_subject_wrapper_template");
  const [instanceId, setInstanceId] = useState("instance_dpabi_y_smooth_001");
  const [runId, setRunId] = useState("");
  const [functionName, setFunctionName] = useState("y_Smooth");
  const [subjectsText, setSubjectsText] = useState("sub-001, sub-002");
  const [fwhmText, setFwhmText] = useState("4, 4, 4");
  const [schedulerMode, setSchedulerMode] = useState("local_parallel");
  const [maxWorkers, setMaxWorkers] = useState(2);
  const [matlabMaxWorkers, setMatlabMaxWorkers] = useState(1);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [created, setCreated] = useState<Record<string, unknown> | null>(null);
  const [executed, setExecuted] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function loadOptions() {
    setError("");
    try {
      const result = await getDpabiTemplateWizardOptions(baseUrl);
      setOptions(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  function payload() {
    return {
      template_id: templateId,
      instance_id: instanceId || null,
      run_id: runId || null,
      function_name: functionName,
      fwhm: parseFwhm(fwhmText),
      subjects: parseList(subjectsText),
      scheduler: {
        mode: schedulerMode,
        max_workers: maxWorkers,
        matlab_max_workers: matlabMaxWorkers
      }
    };
  }

  async function handlePreview() {
    setStatus("PREVIEWING");
    setError("");

    try {
      const result = await previewDpabiTemplateWizard(baseUrl, payload());
      setPreview(result);
      setStatus("PREVIEW_READY");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleCreate() {
    setStatus("CREATING_INSTANCE");
    setError("");

    try {
      const result = await createDpabiTemplateWizardInstance(baseUrl, payload());
      setCreated(result);
      setStatus("INSTANCE_CREATED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleExecute() {
    const confirmed = window.confirm(
      `确认执行 template instance：${instanceId}？这只处理 synthetic BIDS 数据，不会运行完整 DPABI/DPARSF。`
    );

    if (!confirmed) return;

    setStatus("EXECUTING");
    setError("");

    try {
      const result = await executeDpabiTemplate(baseUrl, {
        instance_id: instanceId,
        project_config_path: "examples/project_config_dataset.yaml",
        approved: true,
        approved_by: "local-user"
      });
      setExecuted(result);
      setStatus("EXECUTED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadLatest() {
    setError("");

    try {
      const result = await getDpabiTemplateWizardLatest(baseUrl);
      setLatest(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const templateOptions = Array.isArray(options?.templates) ? options.templates : [];
  const functionOptions = Array.isArray(options?.functions) ? options.functions : ["y_Smooth", "rest_Smooth"];

  return (
    <div>
      <div className="row">
        <button onClick={loadOptions}>刷新 Wizard Options</button>
        <button onClick={handleLoadLatest}>加载最新 Preview</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="formGrid">
        <label>
          Template ID
          <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
            {templateOptions.map((item: any) => (
              <option key={item.template_id} value={item.template_id}>
                {item.template_id}
              </option>
            ))}
            {templateOptions.length === 0 ? (
              <option value={templateId}>{templateId}</option>
            ) : null}
          </select>
        </label>

        <label>
          Instance ID
          <input value={instanceId} onChange={(event) => setInstanceId(event.target.value)} />
        </label>

        <label>
          Run ID
          <input
            value={runId}
            placeholder="留空自动生成"
            onChange={(event) => setRunId(event.target.value)}
          />
        </label>

        <label>
          Function
          <select value={functionName} onChange={(event) => setFunctionName(event.target.value)}>
            {functionOptions.map((item: any) => (
              <option key={String(item)} value={String(item)}>
                {String(item)}
              </option>
            ))}
          </select>
        </label>

        <label>
          Subjects
          <input value={subjectsText} onChange={(event) => setSubjectsText(event.target.value)} />
        </label>

        <label>
          FWHM
          <input value={fwhmText} onChange={(event) => setFwhmText(event.target.value)} />
        </label>

        <label>
          Scheduler Mode
          <select value={schedulerMode} onChange={(event) => setSchedulerMode(event.target.value)}>
            <option value="sequential">sequential</option>
            <option value="local_parallel">local_parallel</option>
          </select>
        </label>

        <label>
          Max Workers
          <input
            type="number"
            min={1}
            max={8}
            value={maxWorkers}
            onChange={(event) => setMaxWorkers(Number(event.target.value))}
          />
        </label>

        <label>
          MATLAB Max Workers
          <input
            type="number"
            min={1}
            max={8}
            value={matlabMaxWorkers}
            onChange={(event) => setMatlabMaxWorkers(Number(event.target.value))}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={handlePreview}>Preview</button>
        <button onClick={handleCreate}>Create Instance</button>
        <button className="dangerButton" onClick={handleExecute}>
          批准并执行 Instance
        </button>
      </div>

      <h3>Wizard Options</h3>
      <JsonBlock value={options} emptyText="尚未加载 options" />

      <h3>Preview</h3>
      <JsonBlock value={preview || latest?.latest_preview} emptyText="尚未 preview" />

      <h3>Preview Markdown</h3>
      <TextViewer
        text={
          typeof latest?.latest_preview_markdown === "string"
            ? latest.latest_preview_markdown
            : null
        }
        emptyText="暂无 preview markdown"
      />

      <h3>Created Instance</h3>
      <JsonBlock value={created} emptyText="尚未 create instance" />

      <h3>Execution Result</h3>
      <JsonBlock value={executed} emptyText="尚未 execute" />
    </div>
  );
}
7. 修改 frontend/src/components/DpabiPanel.tsx

新增导入：

import { DpabiTemplateWizard } from "./DpabiTemplateWizard";

在 DPABI Panel 靠近 Template Library / Template Instance 区域后新增：

<h3>DPABI Parameterized Pipeline Wizard</h3>
<DpabiTemplateWizard baseUrl={baseUrl} />
8. 新增轻量测试

创建文件：

tests/unit/test_dpabi_template_wizard.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.dpabi_template_wizard import (
    preview_dpabi_template_instance,
    validate_dpabi_template_wizard_payload,
)


def test_dpabi_template_wizard_rejects_invalid_fwhm(tmp_path: Path):
    work = tmp_path / "work"
    templates = work / "dpabi" / "templates"
    templates.mkdir(parents=True)

    (templates / "dpabi_template_index.json").write_text(
        json.dumps({
            "templates": [
                {
                    "template_id": "dpabi_y_smooth_subject_wrapper_template",
                    "function_name": "y_Smooth",
                    "template_path": str(templates / "pipelines" / "x.yaml"),
                }
            ]
        }),
        encoding="utf-8",
    )

    result = validate_dpabi_template_wizard_payload(
        {
            "template_id": "dpabi_y_smooth_subject_wrapper_template",
            "instance_id": "instance_test",
            "function_name": "y_Smooth",
            "fwhm": [4, 4],
            "subjects": ["sub-001"],
            "scheduler": {
                "mode": "local_parallel",
                "max_workers": 2,
                "matlab_max_workers": 1,
            },
        },
        work_dir=str(work),
    )

    assert result["ok"] is False
    assert any("fwhm" in err for err in result["errors"])


def test_dpabi_template_wizard_preview_does_not_execute(tmp_path: Path):
    work = tmp_path / "work"
    templates = work / "dpabi" / "templates"
    templates.mkdir(parents=True)

    (templates / "dpabi_template_index.json").write_text(
        json.dumps({
            "templates": [
                {
                    "template_id": "dpabi_y_smooth_subject_wrapper_template",
                    "function_name": "y_Smooth",
                    "template_path": str(templates / "pipelines" / "x.yaml"),
                }
            ]
        }),
        encoding="utf-8",
    )

    result = preview_dpabi_template_instance(
        {
            "template_id": "dpabi_y_smooth_subject_wrapper_template",
            "instance_id": "instance_test",
            "function_name": "y_Smooth",
            "fwhm": [4, 4, 4],
            "subjects": ["sub-001"],
            "scheduler": {
                "mode": "local_parallel",
                "max_workers": 2,
                "matlab_max_workers": 1,
            },
        },
        work_dir=str(work),
    )

    assert result["ok"] is True
    assert result["will_execute"] is False
    assert result["safety"]["execution_allowed"] is False
9. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/dpabi/template-wizard/options")
call("GET", "/api/dpabi/template-wizard/latest")

不要在 smoke test 中调用 execute。

10. 更新 README.md

追加第二十七步说明：

## Step 27: DPABI Parameterized Pipeline Wizard

This step adds a parameterized wizard for DPABI template instances.

It supports:

- loading template options
- validating wizard parameters
- previewing an instance
- creating an instance
- approved execution through the existing template executor

It does not run full DPABI preprocessing.

### API

Options:

```bash
curl http://127.0.0.1:8000/api/dpabi/template-wizard/options

Preview:

curl -X POST http://127.0.0.1:8000/api/dpabi/template-wizard/preview \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "dpabi_y_smooth_subject_wrapper_template",
    "instance_id": "instance_dpabi_y_smooth_001",
    "function_name": "y_Smooth",
    "fwhm": [4, 4, 4],
    "subjects": ["sub-001", "sub-002"],
    "scheduler": {
      "mode": "local_parallel",
      "max_workers": 2,
      "matlab_max_workers": 1
    }
  }'

Create instance:

curl -X POST http://127.0.0.1:8000/api/dpabi/template-wizard/create \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "dpabi_y_smooth_subject_wrapper_template",
    "instance_id": "instance_dpabi_y_smooth_001",
    "function_name": "y_Smooth",
    "fwhm": [4, 4, 4],
    "subjects": ["sub-001", "sub-002"],
    "scheduler": {
      "mode": "local_parallel",
      "max_workers": 2,
      "matlab_max_workers": 1
    }
  }'

Expected outputs:

work/dpabi/template_wizard/latest_preview.json
work/dpabi/template_wizard/latest_preview.md
work/dpabi/template_instances/{instance_id}/pipeline.yaml
work/dpabi/template_instances/{instance_id}/instance_manifest.json
work/dpabi/template_instances/{instance_id}/instance_review.md
Frontend

Use:

DPABI Parameterized Pipeline Wizard
Safety

The wizard:

does not execute on preview
does not execute on create
requires approval before execution
only allows synthetic BIDS-like subjects
does not run DPARSF_run
does not run DPARSFA_run
does not call DPABI GUI
does not modify rawdata

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_pipeline_wizard_spec.md
backend/app/tools/dpabi_template_wizard.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/DpabiTemplateWizard.tsx
frontend/src/components/DpabiPanel.tsx
tests/unit/test_dpabi_template_wizard.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有 template library：

python -m backend.app.tools.run_dpabi_template_library_cli

运行测试：

python -m pytest tests/unit/test_dpabi_template_wizard.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 options：

curl http://127.0.0.1:8000/api/dpabi/template-wizard/options

测试 preview：

curl -X POST http://127.0.0.1:8000/api/dpabi/template-wizard/preview \
  -H "Content-Type: application/json" \
  -d '{"template_id":"dpabi_y_smooth_subject_wrapper_template","instance_id":"instance_dpabi_y_smooth_001","function_name":"y_Smooth","fwhm":[4,4,4],"subjects":["sub-001","sub-002"],"scheduler":{"mode":"local_parallel","max_workers":2,"matlab_max_workers":1}}'

preview 应生成：

work/dpabi/template_wizard/latest_preview.json
work/dpabi/template_wizard/latest_preview.md

并且 JSON 必须包含：

{
  "will_execute": false,
  "safety": {
    "requires_approval": true,
    "approved": false,
    "execution_allowed": false,
    "synthetic_only": true
  }
}

测试 create：

curl -X POST http://127.0.0.1:8000/api/dpabi/template-wizard/create \
  -H "Content-Type: application/json" \
  -d '{"template_id":"dpabi_y_smooth_subject_wrapper_template","instance_id":"instance_dpabi_y_smooth_001","function_name":"y_Smooth","fwhm":[4,4,4],"subjects":["sub-001","sub-002"],"scheduler":{"mode":"local_parallel","max_workers":2,"matlab_max_workers":1}}'

create 应生成：

work/dpabi/template_instances/instance_dpabi_y_smooth_001/pipeline.yaml
work/dpabi/template_instances/instance_dpabi_y_smooth_001/instance_manifest.json
work/dpabi/template_instances/instance_dpabi_y_smooth_001/instance_review.md

启动前端：

cd frontend
npm run dev

页面应该能完成：

DPABI Panel 显示 Parameterized Pipeline Wizard。
可以加载 template options。
可以选择 template_id。
可以设置 instance_id。
可以选择 y_Smooth / rest_Smooth。
可以设置 subjects。
可以设置 fwhm。
可以设置 scheduler。
点击 Preview 只生成 preview，不执行。
点击 Create Instance 只生成 instance，不执行。
点击批准并执行前有 confirm 弹窗。
approved 后才执行 synthetic-only instance。
不运行完整 DPABI preprocessing。
不调用 DPARSF_run / DPARSFA_run。
不调用 DPABI GUI。
不读取或修改真实 rawdata。
12. 重要限制

本步骤只做 DPABI parameterized pipeline wizard。

不要实现：

自动执行
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
拖拽式 workflow builder

完成后请总结：

新增了哪些文件
修改了哪些文件
wizard options 从哪里来
preview 和 create 的区别
execute 为什么必须 approval
wizard UI 支持哪些参数
下一步如何做 run comparison dashboard / multi-run experiment tracking

'''
根据 task27.md 的内容， Step 27 主要实现的是：

## DPABI Parameterized Pipeline Wizard + Review UI 闭环
### 核心目标
提供一个可视化的参数化 Pipeline 向导，帮助用户通过结构化 UI 创建可审查的 DPABI 模板实例。

### 主要功能
1. Wizard 选项加载
   
   - 从 dpabi_template_index.json 加载可用模板
   - 从兼容性矩阵加载可提升为模板的函数
   - 提供所有参数的默认值
   - 显示安全门和限制
2. 参数验证
   
   - 验证 template_id 是否存在于可用模板中
   - 验证 function_name 是否在白名单中（ y_Smooth , rest_Smooth ）
   - 验证 fwhm 为 3 个正数
   - 验证 subjects 为 synthetic IDs（必须以 sub- 开头）
   - 验证 scheduler.mode （ sequential 或 local_parallel ）
   - 验证 scheduler.max_workers （1-8）
   - 验证 scheduler.matlab_max_workers （1 到 max_workers）
3. 预览生成
   
   - 不执行的情况下生成预览
   - 显示将要创建的内容
   - 显示安全状态
   - 保存预览到 work/dpabi/template_wizard/latest_preview.json
   - 生成 Markdown 预览文档
4. 模板实例创建
   
   - 根据 wizard 参数创建实例
   - 调用现有的 instantiate_dpabi_template 函数
   - 不执行
   - 返回实例元数据和文件路径
5. 前端 Wizard 面板
   
   - 模板选择下拉框
   - 函数名选择
   - FWHM 参数输入（X, Y, Z）
   - 受试者输入（逗号分隔）
   - 调度器配置
   - 安全门显示
   - 预览按钮
   - 创建实例按钮
   - 执行（已批准）按钮
### 安全规则
- 预览不执行
- 创建不执行
- 执行需要 approved=true
- 仅允许白名单中的函数
- 仅允许 synthetic subject IDs（sub-xxx）
- FWHM 必须是 3 个正数
- 最大 workers 限制为 1-8
- MATLAB workers 限制为 max_workers
- 阻止完整的 DPABI 执行
- 阻止 DPARSF_run
- 阻止 DPABI GUI
### 工作流程
1. 配置 - 选择模板、函数、设置参数
2. 预览 - 验证并预览，无副作用
3. 审查 - 检查安全门和预览输出
4. 创建 - 生成模板实例文件
5. 批准 - 明确批准执行
6. 执行 - 运行已批准的实例
'''