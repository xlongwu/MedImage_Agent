你是我的工程搭建助手。前十六步已经完成：

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

现在开始第十七步。

第十七步目标：实现“DPABI Capability Inspector + Wrapper Scaffold 闭环”。

当前系统已经检查了 DPABI 路径，但还没有真正把 DPABI 接入工具层。  
本步骤不要直接跑完整 DPABI 预处理。先实现一个安全的 DPABI 能力探测与 wrapper scaffold：

- MATLAB 中添加 DPABI 路径
- 探测 DPABI 入口函数是否存在
- 探测常见 DPABI / REST / y_ 工具函数是否存在
- 生成 dpabi_capabilities.json
- 生成 DPABI wrapper config 模板
- 生成 DPABI dry-run plan
- 将 dpabi_capability_inspection 作为 project-level pipeline node 接入
- 后端 API 暴露 DPABI capability
- 前端增加 DPABI Capability 区域
- 不运行完整 DPABI pipeline
- 不调用 DPABI GUI
- 不修改 DPABI 源码
- 不修改 rawdata
- 不删除文件

不要实现：
- 完整 DPABI 预处理
- DPARSF 批处理执行
- 真实医学影像数据处理
- 自动修改 DPABI 参数
- 修改 DPABI 源码
- 大规模 MATLAB 任务
- 并行 DPABI
- GPU DPABI
- WebSocket
- 数据库
- 真实 LLM

本步骤只做 DPABI capability inspection 和 wrapper scaffold。

---

## 1. 创建 specs/dpabi_runtime_spec.md

创建文件：

```text
specs/dpabi_runtime_spec.md

内容：

# DPABI Runtime Specification

This document defines the MVP DPABI integration layer for MedImage Agent.

## Goals

The DPABI runtime should safely inspect and prepare DPABI integration without running full preprocessing.

The MVP supports:

- DPABI path validation
- MATLAB addpath(genpath(dpabi_dir))
- function discovery
- capability summary
- dry-run wrapper plan
- config template generation
- pipeline node integration
- API and frontend visibility

## Scope

Supported in this step:

- DPABI capability inspection
- common function discovery
- dry-run plan generation
- wrapper config template
- JSON output
- Markdown report

Unsupported in this step:

- full DPABI preprocessing
- DPARSF batch execution
- GUI automation
- real medical image preprocessing
- modifying DPABI source code
- modifying rawdata
- deleting files
- parallel DPABI execution
- GPU DPABI execution

## Outputs

```text
work/dpabi/dpabi_capabilities.json
work/dpabi/dpabi_wrapper_config_template.yaml
work/dpabi/dpabi_dry_run_plan.json
reports/dpabi/dpabi_capability_report.md
Capability Categories
dpabi_entrypoint
rest_tools
y_tools
nifti_io
preprocessing_wrappers
gui_entrypoints
unknown
Safety Rules
Do not run full DPABI preprocessing.
Do not call DPABI GUI automatically.
Do not modify DPABI source.
Do not modify rawdata.
Do not delete files.
Treat this as a dry-run integration scaffold.

---

## 2. 创建 matlab/dpabi_capability_inspection.m

创建文件：

```text
matlab/dpabi_capability_inspection.m

功能要求：

接收参数：
dpabi_dir
output_json
添加 DPABI 路径：
addpath(genpath(dpabi_dir))
探测函数是否存在：
DPABI
DPARSF
DPARSFA
DPARSF_run
DPARSFA_run
y_Read
y_Write
y_Reslice
y_Smooth
y_RegressOutImgCovariates
y_bandpass
y_ALFF
y_fALFF
y_ReHo
y_CalcALFF
y_CalcReHo
rest_readfile
rest_writefile
rest_Smooth
rest_RegressOutCovariates
对每个函数记录：
name
exists
which_path
category
记录 MATLAB version。
记录 dpabi_dir 是否存在。
写 JSON 到 output_json。
不调用完整 DPABI pipeline。
不调用 GUI。
不读写 rawdata。

参考实现：

function dpabi_capability_inspection(dpabi_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_capability_inspection';
    result.backend = 'matlab-dpabi';
    result.matlab_version = version;
    result.dpabi_dir = dpabi_dir;
    result.functions = {};
    result.summary = struct();
    result.errors = {};
    result.warnings = {};

    try
        if ~exist(dpabi_dir, 'dir')
            result.ok = false;
            result.errors{end+1} = ['DPABI directory not found: ', dpabi_dir];
        else
            addpath(genpath(dpabi_dir));
        end

        candidates = {
            'DPABI', 'dpabi_entrypoint';
            'DPARSF', 'gui_entrypoints';
            'DPARSFA', 'gui_entrypoints';
            'DPARSF_run', 'preprocessing_wrappers';
            'DPARSFA_run', 'preprocessing_wrappers';
            'y_Read', 'nifti_io';
            'y_Write', 'nifti_io';
            'y_Reslice', 'y_tools';
            'y_Smooth', 'y_tools';
            'y_RegressOutImgCovariates', 'y_tools';
            'y_bandpass', 'y_tools';
            'y_ALFF', 'y_tools';
            'y_fALFF', 'y_tools';
            'y_ReHo', 'y_tools';
            'y_CalcALFF', 'y_tools';
            'y_CalcReHo', 'y_tools';
            'rest_readfile', 'rest_tools';
            'rest_writefile', 'rest_tools';
            'rest_Smooth', 'rest_tools';
            'rest_RegressOutCovariates', 'rest_tools'
        };

        found_count = 0;
        missing_count = 0;

        for i = 1:size(candidates, 1)
            fn = candidates{i, 1};
            category = candidates{i, 2};

            item = struct();
            item.name = fn;
            item.category = category;

            try
                fn_path = which(fn);
                item.which_path = fn_path;
                item.exists = ~isempty(fn_path);

                if item.exists
                    found_count = found_count + 1;
                else
                    missing_count = missing_count + 1;
                end
            catch ME
                item.which_path = '';
                item.exists = false;
                item.error = ME.message;
                missing_count = missing_count + 1;
            end

            result.functions{end+1} = item;
        end

        result.summary.found_count = found_count;
        result.summary.missing_count = missing_count;
        result.summary.total_checked = size(candidates, 1);

        dpabi_entry = which('DPABI');
        result.summary.dpabi_entrypoint_found = ~isempty(dpabi_entry);
        result.summary.dpabi_entrypoint_path = dpabi_entry;

        if isempty(dpabi_entry)
            result.warnings{end+1} = 'DPABI entrypoint was not found. DPABI may use a different entry function or path setup may be incomplete.';
        end

    catch ME
        result.ok = false;
        try
            result.errors{end+1} = getReport(ME, 'extended', 'hyperlinks', 'off');
        catch
            result.errors{end+1} = ME.message;
        end
    end

    fid = fopen(output_json, 'w');
    if fid == -1
        error(['Cannot open output JSON for writing: ', output_json]);
    end

    fwrite(fid, jsonencode(result), 'char');
    fclose(fid);

    if ~result.ok
        exit(1);
    end
end
3. 创建 backend/app/tools/dpabi_runner.py

创建文件：

backend/app/tools/dpabi_runner.py

目标：通过 Python 调用 MATLAB 的 DPABI capability inspection。

提供函数：

run_dpabi_capability_inspection(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict

要求：

调用 matlab/dpabi_capability_inspection.m。
输出目录：
work/dpabi/
输出 JSON：
work/dpabi/dpabi_capabilities.json
日志：
logs/dpabi_capability_stdout.log
logs/dpabi_capability_stderr.log
返回结构化 dict。
如果 MATLAB returncode 非 0，ok=false。
如果 JSON 不存在，ok=false。
不使用 shell=True。
不运行完整 DPABI pipeline。

参考实现：

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def run_dpabi_capability_inspection(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    output_dir = Path(work_dir) / "dpabi"
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    output_json = output_dir / "dpabi_capabilities.json"
    stdout_log = log_path / "dpabi_capability_stdout.log"
    stderr_log = log_path / "dpabi_capability_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())
    dpabi_abs = str(Path(dpabi_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"dpabi_capability_inspection('{_matlab_quote(dpabi_abs)}', "
        f"'{_matlab_quote(str(output_json.resolve()))}'); "
        "catch ME, disp(getReport(ME)); exit(1); end; exit(0);"
    )

    cmd = [
        matlab_command,
        "-nodisplay",
        "-nosplash",
        "-r",
        matlab_code,
    ]

    with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open("w", encoding="utf-8") as err:
        completed = subprocess.run(cmd, stdout=out, stderr=err, check=False)

    if output_json.exists():
        try:
            data = json.loads(output_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            data = {
                "ok": False,
                "errors": [f"Failed to parse DPABI capabilities JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["DPABI capability inspection did not produce output JSON."],
        }

    data["returncode"] = completed.returncode
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(output_json)
    data["outputs"] = [str(output_json)]

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    return data
4. 创建 backend/app/tools/dpabi_config.py

创建文件：

backend/app/tools/dpabi_config.py

目标：根据 capability inspection 结果生成 DPABI wrapper 配置模板和 dry-run plan。

提供函数：

write_dpabi_wrapper_scaffold(
    capabilities_path: str,
    work_dir: str,
    report_dir: str,
) -> dict

输出：

work/dpabi/dpabi_wrapper_config_template.yaml
work/dpabi/dpabi_dry_run_plan.json
reports/dpabi/dpabi_capability_report.md

要求：

读取 dpabi_capabilities.json。
生成 YAML 配置模板。
生成 dry-run plan。
生成 Markdown 报告。
不运行 DPABI。
不修改 rawdata。
如果 PyYAML 不存在，可以手写 YAML 字符串，不要强制依赖。

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


def _find_function(capabilities: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in capabilities.get("functions", []):
        if item.get("name") == name:
            return item
    return None


def write_dpabi_wrapper_scaffold(
    capabilities_path: str,
    work_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    cap_path = Path(capabilities_path)
    capabilities = _read_json(cap_path)

    if not capabilities:
        return {
            "ok": False,
            "node_id": "dpabi_wrapper_scaffold",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid capabilities JSON: {cap_path}"],
        }

    out_dir = Path(work_dir) / "dpabi"
    report_out_dir = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out_dir.mkdir(parents=True, exist_ok=True)

    config_path = out_dir / "dpabi_wrapper_config_template.yaml"
    dry_run_path = out_dir / "dpabi_dry_run_plan.json"
    report_path = report_out_dir / "dpabi_capability_report.md"

    functions = capabilities.get("functions", [])
    found = [item for item in functions if item.get("exists")]
    missing = [item for item in functions if not item.get("exists")]

    dpabi_entry = _find_function(capabilities, "DPABI")
    dparsf_run = _find_function(capabilities, "DPARSF_run")
    dparsfa_run = _find_function(capabilities, "DPARSFA_run")

    config_text = f"""# DPABI Wrapper Config Template
# This is a scaffold only. It does not execute DPABI automatically.

dpabi:
  capabilities_json: "{cap_path}"
  entrypoint_found: {str(bool(dpabi_entry and dpabi_entry.get("exists"))).lower()}
  entrypoint: "DPABI"
  dry_run_only: true

input:
  rawdata_dir: "./examples/synthetic_bids/rawdata"
  dataset_index: "./work/dataset_index/dataset_index.json"

output:
  work_dir: "./work/dpabi"
  derivatives_dir: "./derivatives/dpabi"
  report_dir: "./reports/dpabi"

execution:
  mode: "dry_run"
  require_manual_review: true
  allow_gui: false
  allow_full_preprocessing: false

candidate_wrappers:
  DPARSF_run:
    available: {str(bool(dparsf_run and dparsf_run.get("exists"))).lower()}
  DPARSFA_run:
    available: {str(bool(dparsfa_run and dparsfa_run.get("exists"))).lower()}

safety:
  modify_rawdata: false
  modify_dpabi_source: false
  delete_files: false
"""
    config_path.write_text(config_text, encoding="utf-8")

    dry_run_plan = {
        "ok": True,
        "mode": "DRY_RUN",
        "capabilities_json": str(cap_path),
        "entrypoint_found": bool(dpabi_entry and dpabi_entry.get("exists")),
        "candidate_wrappers": {
            "DPARSF_run": bool(dparsf_run and dparsf_run.get("exists")),
            "DPARSFA_run": bool(dparsfa_run and dparsfa_run.get("exists")),
        },
        "steps": [
            {
                "step_id": "dpabi_001",
                "action": "validate_dpabi_path",
                "status": "planned",
            },
            {
                "step_id": "dpabi_002",
                "action": "review_wrapper_config_template",
                "status": "requires_human_review",
            },
            {
                "step_id": "dpabi_003",
                "action": "map_dataset_index_to_dpabi_expected_layout",
                "status": "future_work",
            },
            {
                "step_id": "dpabi_004",
                "action": "prepare_dpabi_batch_config",
                "status": "future_work",
            },
        ],
        "safety": {
            "full_preprocessing_executed": False,
            "rawdata_modified": False,
            "dpabi_source_modified": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    dry_run_path.write_text(
        json.dumps(dry_run_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Capability Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Capability JSON: `{cap_path}`")
    lines.append(f"- Total checked: {len(functions)}")
    lines.append(f"- Found: {len(found)}")
    lines.append(f"- Missing: {len(missing)}")
    lines.append(f"- DPABI entrypoint found: {bool(dpabi_entry and dpabi_entry.get('exists'))}")
    lines.append("")
    lines.append("## Found Functions")
    lines.append("")
    if found:
        lines.append("| Function | Category | Path |")
        lines.append("|---|---|---|")
        for item in found:
            lines.append(
                f"| {item.get('name')} | {item.get('category')} | `{item.get('which_path')}` |"
            )
    else:
        lines.append("No known DPABI functions found.")
    lines.append("")
    lines.append("## Missing Functions")
    lines.append("")
    if missing:
        for item in missing:
            lines.append(f"- {item.get('name')} ({item.get('category')})")
    else:
        lines.append("No missing functions from the candidate list.")
    lines.append("")
    lines.append("## Dry-run Plan")
    lines.append("")
    lines.append(f"- Dry-run plan: `{dry_run_path}`")
    lines.append(f"- Config template: `{config_path}`")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This step did not run full DPABI preprocessing and did not modify rawdata or DPABI source code.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_wrapper_scaffold",
        "backend": "python",
        "outputs": [str(config_path), str(dry_run_path), str(report_path)],
        "metrics": {
            "functions_total": len(functions),
            "functions_found": len(found),
            "functions_missing": len(missing),
            "dpabi_entrypoint_found": bool(dpabi_entry and dpabi_entry.get("exists")),
        },
        "warnings": warnings,
        "errors": errors,
    }
5. 修改 backend/app/runtime/node_registry.py

新增两个节点：

dpabi_capability_inspection
dpabi_wrapper_scaffold

新增导入：

from backend.app.tools.dpabi_runner import run_dpabi_capability_inspection
from backend.app.tools.dpabi_config import write_dpabi_wrapper_scaffold

新增 runner：

def run_dpabi_capability_inspection_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_dpabi_capability_inspection(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_dpabi_wrapper_scaffold_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    capabilities_path = node.params.get(
        "capabilities_path",
        f"{context.work_dir}/dpabi/dpabi_capabilities.json",
    )

    result = write_dpabi_wrapper_scaffold(
        capabilities_path=capabilities_path,
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_capability_inspection": run_dpabi_capability_inspection_node,
"dpabi_wrapper_scaffold": run_dpabi_wrapper_scaffold_node,
6. 创建 examples/pipeline_dpabi_capability.yaml

创建文件：

examples/pipeline_dpabi_capability.yaml

内容：

pipeline_id: dpabi_capability_pipeline
version: "0.1.0"
modality: integration-test
description: "Inspect DPABI capabilities and generate wrapper scaffold without running full preprocessing."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_capability_001"
  scheduler:
    mode: "sequential"
    max_workers: 1
    matlab_max_workers: 1

nodes:
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
7. 创建 backend/app/tools/run_dpabi_capability_cli.py

创建文件：

backend/app/tools/run_dpabi_capability_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dpabi_capability.yaml")

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
8. 修改 backend/app/api/routes.py

新增 API：

GET /api/dpabi/capabilities
GET /api/reports/dpabi

新增路由：

@router.get("/api/dpabi/capabilities")
def get_dpabi_capabilities() -> dict[str, Any]:
    base = Path("work") / "dpabi"

    return {
        "ok": True,
        "capabilities": _read_json_if_exists(base / "dpabi_capabilities.json"),
        "dry_run_plan": _read_json_if_exists(base / "dpabi_dry_run_plan.json"),
        "wrapper_config_template": _read_text_if_exists(base / "dpabi_wrapper_config_template.yaml"),
    }


@router.get("/api/reports/dpabi")
def get_dpabi_report() -> dict[str, Any]:
    base = Path("reports") / "dpabi"

    return {
        "ok": True,
        "capability_report": _read_text_if_exists(base / "dpabi_capability_report.md"),
    }
9. 修改 frontend/src/api.ts

新增：

export async function getDpabiCapabilities(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/capabilities"
  );
}

export async function getDpabiReport(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/reports/dpabi"
  );
}
10. 创建 frontend/src/components/DpabiPanel.tsx

创建文件：

frontend/src/components/DpabiPanel.tsx

内容：

import { useState } from "react";
import { getDpabiCapabilities, getDpabiReport } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function DpabiPanel({ baseUrl }: Props) {
  const [capabilities, setCapabilities] = useState<Record<string, unknown> | null>(null);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoadCapabilities() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getDpabiCapabilities(baseUrl);
      setCapabilities(result);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadReport() {
    setError("");

    try {
      const result = await getDpabiReport(baseUrl);
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="row">
        <button onClick={handleLoadCapabilities}>加载 DPABI Capabilities</button>
        <button onClick={handleLoadReport}>加载 DPABI Report</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <h3>DPABI Capabilities</h3>
      <JsonBlock value={capabilities?.capabilities} emptyText="尚未生成 DPABI capabilities" />

      <h3>DPABI Dry-run Plan</h3>
      <JsonBlock value={capabilities?.dry_run_plan} emptyText="尚未生成 dry-run plan" />

      <h3>DPABI Wrapper Config Template</h3>
      <TextViewer
        text={
          typeof capabilities?.wrapper_config_template === "string"
            ? capabilities.wrapper_config_template
            : null
        }
        emptyText="尚未生成 wrapper config template"
      />

      <h3>DPABI Capability Report</h3>
      <TextViewer
        text={
          typeof report?.capability_report === "string"
            ? report.capability_report
            : null
        }
        emptyText="尚未生成 DPABI capability report"
      />
    </div>
  );
}
11. 修改 frontend/src/App.tsx

新增导入：

import { DpabiPanel } from "./components/DpabiPanel";

在 GPU Panel 后面新增 Section：

<Section
  title="DPABI Capability / Wrapper Scaffold"
  description="探测 DPABI 可用函数，生成 wrapper config 模板和 dry-run plan。"
>
  <DpabiPanel baseUrl={baseUrl} />
</Section>
12. 修改 backend/app/tools/api_smoke_test.py

新增测试：

call("GET", "/api/dpabi/capabilities")
call("GET", "/api/reports/dpabi")

不要在 smoke test 中自动运行 DPABI pipeline。

13. 更新 README.md

追加第十七步说明：

## Step 17: DPABI Capability Inspector and Wrapper Scaffold

This step adds a safe DPABI integration scaffold.

It does not run full DPABI preprocessing.

### Run DPABI Capability Pipeline

```bash
python -m backend.app.tools.run_dpabi_capability_cli

Expected outputs:

work/dpabi/dpabi_capabilities.json
work/dpabi/dpabi_wrapper_config_template.yaml
work/dpabi/dpabi_dry_run_plan.json
reports/dpabi/dpabi_capability_report.md
API
curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi
Frontend

Use the DPABI Capability / Wrapper Scaffold panel.

Safety

This step does not:

run full DPABI preprocessing
call DPABI GUI
modify rawdata
modify DPABI source
delete files

---

## 14. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_runtime_spec.md
matlab/dpabi_capability_inspection.m
backend/app/tools/dpabi_runner.py
backend/app/tools/dpabi_config.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_capability.yaml
backend/app/tools/run_dpabi_capability_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/DpabiPanel.tsx
frontend/src/App.tsx
README.md

运行：

python -m backend.app.tools.run_dpabi_capability_cli

成功后应生成：

work/dpabi/dpabi_capabilities.json
work/dpabi/dpabi_wrapper_config_template.yaml
work/dpabi/dpabi_dry_run_plan.json
reports/dpabi/dpabi_capability_report.md
work/pipeline_runs/run_dpabi_capability_001/summary.json

其中：

work/dpabi/dpabi_capabilities.json

应包含：

{
  "ok": true,
  "node_id": "dpabi_capability_inspection",
  "backend": "matlab-dpabi",
  "functions": [],
  "summary": {
    "found_count": 0,
    "missing_count": 0,
    "total_checked": 0
  }
}

实际 found_count 根据本地 DPABI 代码不同可能不同。

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 DPABI Capability / Wrapper Scaffold 区域。
加载 dpabi_capabilities.json。
显示 dry-run plan。
显示 wrapper config template。
显示 capability report。
不运行完整 DPABI preprocessing。
不调用 DPABI GUI。
不修改 rawdata。
15. 重要限制

本步骤只做 DPABI capability inspection 和 wrapper scaffold。

不要实现：

DPABI 全流程预处理
DPARSF 批处理运行
DPABI GUI 自动化
真实医学影像处理
DPABI 并行化
DPABI GPU 加速
修改 DPABI 源码
删除文件
自动修改参数

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 DPABI capability inspection
输出文件在哪里
前端如何查看 DPABI capability
为什么本步骤只做 dry-run scaffold
下一步如果要真正接 DPABI pipeline，需要补哪些信息

'''
## Step 17: DPABI Capability Inspector + Wrapper Scaffold 闭环
### 核心目标
实现一个安全的 DPABI 集成层，能够在 不运行完整预处理 的情况下检查 DPABI 的能力，并生成包装器脚手架。

### 主要功能
1. DPABI 能力检查
   
   - 通过 MATLAB 脚本检查 DPABI 安装
   - 发现常用的 DPABI 函数（DPABI、DPARSF、y_* 函数、rest_* 函数等）
   - 生成能力报告 JSON
2. 包装器脚手架生成
   
   - 生成 DPABI 包装器配置模板
   - 生成 dry-run 执行计划
   - 生成 Markdown 能力报告
3. 流水线集成
   
   - 在节点注册表中注册 DPABI 相关节点
   - 提供 API 端点供前端调用
   - 前端面板展示 DPABI 能力检查结果
### 输出文件
```
work/dpabi/dpabi_capabilities.json          # 能力检查结果
work/dpabi/dpabi_wrapper_config_template.yaml  # 配置模板
work/dpabi/dpabi_dry_run_plan.json          # Dry-run 计划
reports/dpabi/dpabi_capability_report.md    # Markdown 报告
```
### 安全规则
- ✅ 允许：路径验证、函数发现、配置生成
- ❌ 禁止：运行完整 DPABI 预处理、自动调用 GUI、修改源代码、修改原始数据、删除文件
这是一个 dry-run 集成脚手架 ，为后续可能的 DPABI 预处理集成做准备，但本身不执行任何实际的图像处理操作。
'''