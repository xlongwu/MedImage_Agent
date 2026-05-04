你是我的工程搭建助手。前二十步已经完成：

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

现在开始第二十一步。

第二十一步目标：实现“DPABI Function Signature Probe + Wrapper Contract Registry 闭环”。

当前系统已经可以：

- 探测 DPABI capability
- 生成 preflight
- 生成 run plan
- 做 approved sandbox smoke run
- 验证 MATLAB + DPABI addpath + NIfTI sandbox I/O

但还不能安全封装 DPABI 单函数，因为不同 DPABI / REST / y_ 函数的调用签名可能随版本不同而变化。

本步骤要实现：

- MATLAB 中探测候选 DPABI 函数的 nargin / nargout / help / which path
- 生成 dpabi_function_signatures.json
- 生成 dpabi_wrapper_contracts.json
- 生成 dpabi_wrapper_contracts.yaml
- 生成 dpabi_signature_probe_report.md
- 根据函数签名判断哪些函数可以进入下一步 wrapper 候选
- 将 dpabi_signature_probe 作为 project-level pipeline node 接入
- 后端 API 暴露 function signatures 和 wrapper contracts
- 前端 DPABI Panel 显示 signature probe 和 wrapper contracts

本步骤不要执行完整 DPABI pipeline。
本步骤不要调用 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。

---

## 1. 创建 specs/dpabi_signature_probe_spec.md

创建文件：

```text
specs/dpabi_signature_probe_spec.md

内容：

# DPABI Function Signature Probe Specification

This document defines the MVP DPABI function signature probing and wrapper contract registry.

## Goals

Before wrapping DPABI functions, the system should inspect function signatures and documentation.

The probe should collect:

- function name
- function category
- existence
- which path
- nargin
- nargout
- help excerpt
- wrapper readiness
- safety classification

## Scope

Supported in this step:

- MATLAB function discovery
- nargin / nargout probing
- help text extraction
- wrapper contract generation
- JSON / YAML registry output
- Markdown report
- API and frontend visibility

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- DPABI GUI automation
- real medical image preprocessing
- rawdata modification
- DPABI source modification
- deletion of files

## Outputs

```text
work/dpabi/dpabi_function_signatures.json
work/dpabi/dpabi_wrapper_contracts.json
work/dpabi/dpabi_wrapper_contracts.yaml
reports/dpabi/dpabi_signature_probe_report.md
Wrapper Readiness

A function can be marked as wrapper_candidate if:

it exists
it has a resolvable path
nargin and nargout can be inspected
it is not a GUI entrypoint
it is not a full pipeline runner
it is not explicitly blocked
Function Safety Classification
SAFE_IO_PROBE: simple read/write utilities such as y_Read, y_Write
SAFE_SINGLE_FUNCTION_CANDIDATE: possible single-function wrappers such as y_Smooth, y_ALFF, y_fALFF
FULL_PIPELINE_BLOCKED: DPARSF_run, DPARSFA_run
GUI_BLOCKED: DPABI, DPARSF, DPARSFA
UNKNOWN_REVIEW_REQUIRED: insufficient signature information
Safety Rules
Do not execute DPABI preprocessing.
Do not call GUI entrypoints.
Do not call DPARSF_run or DPARSFA_run.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.

---

## 2. 创建 matlab/dpabi_signature_probe.m

创建文件：

```text
matlab/dpabi_signature_probe.m

功能要求：

接收参数：
dpabi_dir
output_json
添加 DPABI 路径：
addpath(genpath(dpabi_dir))
探测候选函数：
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
category
exists
which_path
nargin
nargout
help_excerpt
probe_errors
不调用这些函数。
不调用 DPARSF_run。
不调用 DPABI GUI。
不读写 rawdata。
写 JSON 到 output_json。

参考实现：

function dpabi_signature_probe(dpabi_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_signature_probe';
    result.backend = 'matlab-dpabi';
    result.dpabi_dir = dpabi_dir;
    result.matlab_version = version;
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
            'DPABI', 'gui_entrypoints';
            'DPARSF', 'gui_entrypoints';
            'DPARSFA', 'gui_entrypoints';
            'DPARSF_run', 'full_pipeline_runner';
            'DPARSFA_run', 'full_pipeline_runner';
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
        signature_count = 0;

        for i = 1:size(candidates, 1)
            fn = candidates{i, 1};
            category = candidates{i, 2};

            item = struct();
            item.name = fn;
            item.category = category;
            item.exists = false;
            item.which_path = '';
            item.nargin = [];
            item.nargout = [];
            item.help_excerpt = '';
            item.probe_errors = {};

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
                item.probe_errors{end+1} = ['which failed: ', ME.message];
                missing_count = missing_count + 1;
            end

            if item.exists
                try
                    item.nargin = nargin(fn);
                    signature_count = signature_count + 1;
                catch ME
                    item.probe_errors{end+1} = ['nargin failed: ', ME.message];
                end

                try
                    item.nargout = nargout(fn);
                catch ME
                    item.probe_errors{end+1} = ['nargout failed: ', ME.message];
                end

                try
                    h = help(fn);
                    if length(h) > 2000
                        h = h(1:2000);
                    end
                    item.help_excerpt = h;
                catch ME
                    item.probe_errors{end+1} = ['help failed: ', ME.message];
                end
            end

            result.functions{end+1} = item;
        end

        result.summary.found_count = found_count;
        result.summary.missing_count = missing_count;
        result.summary.signature_count = signature_count;
        result.summary.total_checked = size(candidates, 1);

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
3. 创建 backend/app/tools/dpabi_signature_runner.py

创建文件：

backend/app/tools/dpabi_signature_runner.py

目标：Python 调用 MATLAB signature probe。

提供函数：

run_dpabi_signature_probe(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict

输出：

work/dpabi/dpabi_function_signatures.json
logs/dpabi_signature_probe_stdout.log
logs/dpabi_signature_probe_stderr.log

参考实现：

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def run_dpabi_signature_probe(
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

    output_json = output_dir / "dpabi_function_signatures.json"
    stdout_log = log_path / "dpabi_signature_probe_stdout.log"
    stderr_log = log_path / "dpabi_signature_probe_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())
    dpabi_abs = str(Path(dpabi_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"dpabi_signature_probe('{_matlab_quote(dpabi_abs)}', "
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
                "errors": [f"Failed to parse DPABI signature JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["DPABI signature probe did not produce output JSON."],
        }

    data["node_id"] = "dpabi_signature_probe"
    data["backend"] = "matlab-dpabi"
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
4. 创建 backend/app/tools/dpabi_contract_registry.py

创建文件：

backend/app/tools/dpabi_contract_registry.py

目标：根据 signature probe 结果生成 wrapper contract registry。

提供函数：

write_dpabi_wrapper_contracts(
    signatures_path: str,
    work_dir: str,
    report_dir: str,
) -> dict

输出：

work/dpabi/dpabi_wrapper_contracts.json
work/dpabi/dpabi_wrapper_contracts.yaml
reports/dpabi/dpabi_signature_probe_report.md

contract 应包含：

function_name
category
exists
nargin
nargout
safety_classification
wrapper_candidate
blocked_reason
recommended_next_step

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GUI_ENTRYPOINTS = {"DPABI", "DPARSF", "DPARSFA"}
FULL_PIPELINE_RUNNERS = {"DPARSF_run", "DPARSFA_run"}
SAFE_IO = {"y_Read", "y_Write", "rest_readfile", "rest_writefile"}
SINGLE_FUNCTION_CANDIDATES = {
    "y_Smooth",
    "y_Reslice",
    "y_ALFF",
    "y_fALFF",
    "y_ReHo",
    "y_CalcALFF",
    "y_CalcReHo",
    "rest_Smooth",
    "rest_RegressOutCovariates",
    "y_RegressOutImgCovariates",
    "y_bandpass",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace('"', '\\"') + '"'


def _classify_function(item: dict[str, Any]) -> dict[str, Any]:
    name = item.get("name")
    exists = bool(item.get("exists"))
    nargin_value = item.get("nargin")
    nargout_value = item.get("nargout")
    probe_errors = item.get("probe_errors", []) or []

    wrapper_candidate = False
    blocked_reason = ""
    recommended_next_step = "manual_review"
    safety_classification = "UNKNOWN_REVIEW_REQUIRED"

    if not exists:
        blocked_reason = "function_missing"
        recommended_next_step = "skip"
    elif name in GUI_ENTRYPOINTS:
        safety_classification = "GUI_BLOCKED"
        blocked_reason = "gui_entrypoint_blocked"
        recommended_next_step = "do_not_wrap"
    elif name in FULL_PIPELINE_RUNNERS:
        safety_classification = "FULL_PIPELINE_BLOCKED"
        blocked_reason = "full_pipeline_runner_blocked"
        recommended_next_step = "requires_separate_approved_execution_design"
    elif name in SAFE_IO:
        safety_classification = "SAFE_IO_PROBE"
        wrapper_candidate = True
        recommended_next_step = "keep_for_io_smoke_tests"
    elif name in SINGLE_FUNCTION_CANDIDATES:
        safety_classification = "SAFE_SINGLE_FUNCTION_CANDIDATE"
        wrapper_candidate = True
        recommended_next_step = "create_sandbox_contract_test_before_subject_execution"
    elif probe_errors:
        safety_classification = "UNKNOWN_REVIEW_REQUIRED"
        blocked_reason = "signature_probe_errors"
        recommended_next_step = "manual_review"
    else:
        safety_classification = "UNKNOWN_REVIEW_REQUIRED"
        recommended_next_step = "manual_review"

    if wrapper_candidate and (nargin_value is None or nargout_value is None):
        wrapper_candidate = False
        blocked_reason = "missing_nargin_or_nargout"
        recommended_next_step = "manual_signature_review"

    return {
        "function_name": name,
        "category": item.get("category"),
        "exists": exists,
        "which_path": item.get("which_path"),
        "nargin": nargin_value,
        "nargout": nargout_value,
        "safety_classification": safety_classification,
        "wrapper_candidate": wrapper_candidate,
        "blocked_reason": blocked_reason,
        "recommended_next_step": recommended_next_step,
        "probe_errors": probe_errors,
    }


def write_dpabi_wrapper_contracts(
    signatures_path: str,
    work_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    sig_path = Path(signatures_path)
    signatures = _read_json(sig_path)

    if not signatures:
        return {
            "ok": False,
            "node_id": "dpabi_wrapper_contracts",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid signatures JSON: {sig_path}"],
        }

    out_dir = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    contracts = [
        _classify_function(item)
        for item in signatures.get("functions", [])
    ]

    candidates = [item for item in contracts if item["wrapper_candidate"]]
    blocked = [item for item in contracts if item["blocked_reason"]]

    payload = {
        "ok": True,
        "node_id": "dpabi_wrapper_contracts",
        "backend": "python",
        "signatures_path": str(sig_path),
        "contracts_total": len(contracts),
        "wrapper_candidates": len(candidates),
        "blocked_total": len(blocked),
        "contracts": contracts,
        "warnings": warnings,
        "errors": errors,
    }

    json_path = out_dir / "dpabi_wrapper_contracts.json"
    yaml_path = out_dir / "dpabi_wrapper_contracts.yaml"
    report_path = report_out / "dpabi_signature_probe_report.md"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    yaml_lines = []
    yaml_lines.append("version: \"0.1.0\"")
    yaml_lines.append("contracts:")
    for item in contracts:
        yaml_lines.append(f"  - function_name: {_yaml_scalar(item['function_name'])}")
        yaml_lines.append(f"    category: {_yaml_scalar(item['category'])}")
        yaml_lines.append(f"    exists: {_yaml_scalar(item['exists'])}")
        yaml_lines.append(f"    nargin: {_yaml_scalar(item['nargin'])}")
        yaml_lines.append(f"    nargout: {_yaml_scalar(item['nargout'])}")
        yaml_lines.append(f"    safety_classification: {_yaml_scalar(item['safety_classification'])}")
        yaml_lines.append(f"    wrapper_candidate: {_yaml_scalar(item['wrapper_candidate'])}")
        yaml_lines.append(f"    blocked_reason: {_yaml_scalar(item['blocked_reason'])}")
        yaml_lines.append(f"    recommended_next_step: {_yaml_scalar(item['recommended_next_step'])}")
    yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    lines = []
    lines.append("# DPABI Signature Probe Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Signatures: `{sig_path}`")
    lines.append(f"- Contracts total: {len(contracts)}")
    lines.append(f"- Wrapper candidates: {len(candidates)}")
    lines.append(f"- Blocked total: {len(blocked)}")
    lines.append("")
    lines.append("## Wrapper Candidates")
    lines.append("")
    if candidates:
        lines.append("| Function | Category | nargin | nargout | Classification |")
        lines.append("|---|---|---:|---:|---|")
        for item in candidates:
            lines.append(
                f"| {item['function_name']} | {item['category']} | {item['nargin']} | "
                f"{item['nargout']} | {item['safety_classification']} |"
            )
    else:
        lines.append("No wrapper candidates found.")
    lines.append("")
    lines.append("## Blocked Functions")
    lines.append("")
    if blocked:
        lines.append("| Function | Reason | Classification |")
        lines.append("|---|---|---|")
        for item in blocked:
            lines.append(
                f"| {item['function_name']} | {item['blocked_reason']} | "
                f"{item['safety_classification']} |"
            )
    else:
        lines.append("No blocked functions.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This probe did not execute full DPABI preprocessing, did not call DPARSF_run, and did not call DPABI GUI.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_wrapper_contracts",
        "backend": "python",
        "outputs": [str(json_path), str(yaml_path), str(report_path)],
        "metrics": {
            "contracts_total": len(contracts),
            "wrapper_candidates": len(candidates),
            "blocked_total": len(blocked),
        },
        "warnings": warnings,
        "errors": errors,
    }
5. 修改 backend/app/runtime/node_registry.py

新增两个节点：

dpabi_signature_probe
dpabi_wrapper_contracts

新增导入：

from backend.app.tools.dpabi_signature_runner import run_dpabi_signature_probe
from backend.app.tools.dpabi_contract_registry import write_dpabi_wrapper_contracts

新增 runner：

def run_dpabi_signature_probe_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_dpabi_signature_probe(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result


def run_dpabi_wrapper_contracts_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    signatures_path = node.params.get(
        "signatures_path",
        f"{context.work_dir}/dpabi/dpabi_function_signatures.json",
    )

    result = write_dpabi_wrapper_contracts(
        signatures_path=signatures_path,
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_signature_probe": run_dpabi_signature_probe_node,
"dpabi_wrapper_contracts": run_dpabi_wrapper_contracts_node,
6. 创建 examples/pipeline_dpabi_signature_probe.yaml

创建文件：

examples/pipeline_dpabi_signature_probe.yaml

内容：

pipeline_id: dpabi_signature_probe_pipeline
version: "0.1.0"
modality: integration-test
description: "Probe DPABI function signatures and generate wrapper contracts without executing full preprocessing."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_signature_probe_001"
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

  - id: dpabi_signature_probe
    name: DPABI Signature Probe
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - environment_check
    inputs: []
    outputs:
      - "./work/dpabi/dpabi_function_signatures.json"
    params: {}
    parallel_level: project
    gpu_supported: false
    cache: false

  - id: dpabi_wrapper_contracts
    name: DPABI Wrapper Contracts
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_signature_probe
    inputs:
      - "./work/dpabi/dpabi_function_signatures.json"
    outputs:
      - "./work/dpabi/dpabi_wrapper_contracts.json"
      - "./work/dpabi/dpabi_wrapper_contracts.yaml"
      - "./reports/dpabi/dpabi_signature_probe_report.md"
    params:
      signatures_path: "./work/dpabi/dpabi_function_signatures.json"
    parallel_level: project
    gpu_supported: false
    cache: false
7. 创建 backend/app/tools/run_dpabi_signature_probe_cli.py

创建文件：

backend/app/tools/run_dpabi_signature_probe_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dpabi_signature_probe.yaml")

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

修改已有：

GET /api/dpabi/capabilities
GET /api/reports/dpabi

让 /api/dpabi/capabilities 新增返回：

"function_signatures": _read_json_if_exists(base / "dpabi_function_signatures.json"),
"wrapper_contracts": _read_json_if_exists(base / "dpabi_wrapper_contracts.json"),
"wrapper_contracts_yaml": _read_text_if_exists(base / "dpabi_wrapper_contracts.yaml"),

让 /api/reports/dpabi 新增返回：

"signature_probe_report": _read_text_if_exists(base / "dpabi_signature_probe_report.md"),
9. 修改 frontend/src/components/DpabiPanel.tsx

在现有 DPABI Panel 中增加显示：

<h3>DPABI Function Signatures</h3>
<JsonBlock value={capabilities?.function_signatures} emptyText="尚未生成 function signatures" />

<h3>DPABI Wrapper Contracts JSON</h3>
<JsonBlock value={capabilities?.wrapper_contracts} emptyText="尚未生成 wrapper contracts" />

<h3>DPABI Wrapper Contracts YAML</h3>
<TextViewer
  text={
    typeof capabilities?.wrapper_contracts_yaml === "string"
      ? capabilities.wrapper_contracts_yaml
      : null
  }
  emptyText="尚未生成 wrapper contracts YAML"
/>

<h3>DPABI Signature Probe Report</h3>
<TextViewer
  text={
    typeof report?.signature_probe_report === "string"
      ? report.signature_probe_report
      : null
  }
  emptyText="尚未生成 signature probe report"
/>

保留原来的 DPABI capability、preflight、run plan、sandbox smoke 内容。

10. 修改 backend/app/tools/api_smoke_test.py

确保已有 DPABI API 只读测试：

call("GET", "/api/dpabi/capabilities")
call("GET", "/api/reports/dpabi")

不要在 smoke test 中自动运行 signature probe pipeline，避免误启动 MATLAB。

11. 更新 README.md

追加第二十一步说明：

## Step 21: DPABI Function Signature Probe and Wrapper Contracts

This step probes DPABI function signatures and generates wrapper contracts.

It does not run full DPABI preprocessing.

### Run

```bash
python -m backend.app.tools.run_dpabi_signature_probe_cli

Expected outputs:

work/dpabi/dpabi_function_signatures.json
work/dpabi/dpabi_wrapper_contracts.json
work/dpabi/dpabi_wrapper_contracts.yaml
reports/dpabi/dpabi_signature_probe_report.md
work/pipeline_runs/run_dpabi_signature_probe_001/summary.json
API
curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi
Frontend

Use the DPABI Capability / Wrapper Scaffold panel.

It now shows:

function signatures
wrapper contracts JSON
wrapper contracts YAML
signature probe report
Safety

This step does not:

run DPARSF_run
run DPARSFA_run
call DPABI GUI
process real medical imaging data
modify rawdata
modify DPABI source
delete files

---

## 12. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_signature_probe_spec.md
matlab/dpabi_signature_probe.m
backend/app/tools/dpabi_signature_runner.py
backend/app/tools/dpabi_contract_registry.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_signature_probe.yaml
backend/app/tools/run_dpabi_signature_probe_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/components/DpabiPanel.tsx
README.md

运行：

python -m backend.app.tools.run_dpabi_signature_probe_cli

成功后应生成：

work/dpabi/dpabi_function_signatures.json
work/dpabi/dpabi_wrapper_contracts.json
work/dpabi/dpabi_wrapper_contracts.yaml
reports/dpabi/dpabi_signature_probe_report.md
work/pipeline_runs/run_dpabi_signature_probe_001/summary.json

其中：

work/dpabi/dpabi_function_signatures.json

应包含：

{
  "node_id": "dpabi_signature_probe",
  "backend": "matlab-dpabi",
  "functions": [],
  "summary": {
    "found_count": 0,
    "missing_count": 0,
    "signature_count": 0,
    "total_checked": 0
  }
}

实际 found_count / signature_count 根据本地 DPABI 版本不同可能不同。

其中：

work/dpabi/dpabi_wrapper_contracts.json

应包含：

{
  "node_id": "dpabi_wrapper_contracts",
  "contracts_total": 0,
  "wrapper_candidates": 0,
  "contracts": []
}

如果发现 DPARSF_run 或 DPARSFA_run，必须标记为：

FULL_PIPELINE_BLOCKED

如果发现 DPABI / DPARSF / DPARSFA，必须标记为：

GUI_BLOCKED

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/capabilities
curl http://127.0.0.1:8000/api/reports/dpabi

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 DPABI Function Signatures。
显示 DPABI Wrapper Contracts JSON。
显示 DPABI Wrapper Contracts YAML。
显示 DPABI Signature Probe Report。
不运行完整 DPABI preprocessing。
不调用 DPARSF_run / DPARSFA_run。
不调用 DPABI GUI。
不修改 rawdata。
不修改 DPABI 源码。
13. 重要限制

本步骤只做 DPABI function signature probe 和 wrapper contract registry。

不要实现：

DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
单函数 subject-level execution
真实医学影像处理
自动参数优化
修改 rawdata
修改 DPABI 源码
删除文件

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 DPABI signature probe
signature probe 记录哪些字段
wrapper contracts 如何分类函数安全性
为什么 DPARSF_run / DPARSFA_run 仍然被 block
下一步如果要封装 DPABI 单函数，应该优先选择哪些 wrapper_candidate

'''
Step 21：DPABI Function Signature Probe + Wrapper Contract Registry 闭环

## 核心目标
在封装 DPABI 单函数之前，系统需要 了解每个函数的调用签名 （输入/输出参数数量），以便安全地构建 wrapper。这一步通过 MATLAB 探测 DPABI 函数的签名信息，并生成分类和 contract registry。

## 主要功能
### 1. 函数签名探测
- 探测 nargin ：函数的输入参数数量
- 探测 nargout ：函数的输出参数数量
- 提取 which 路径 ：函数在文件系统中的位置
- 捕获 help 文本 ：函数文档的前 2000 字符
- 记录探测错误 ：如果某个函数探测失败
### 2. 候选函数列表
函数 类别 用途 y_Read / y_Write NIfTI I/O 读写 NIfTI 文件 y_Smooth 预处理 图像平滑 y_ALFF / y_fALFF 指标计算 ALFF/fALFF 计算 y_ReHo 指标计算 区域同质性 y_Reslice 预处理 重采样 y_bandpass 预处理 带通滤波 rest_readfile / rest_writefile REST I/O REST 工具包 I/O rest_Smooth 预处理 REST 平滑

### 3. 被阻止的函数
函数 阻止原因 DPABI GUI 入口点 DPARSF GUI 入口点 DPARSFA GUI 入口点 DPARSF_run 完整 pipeline runner DPARSFA_run 完整 pipeline runner

### 4. 函数安全分类
- SAFE_IO_PROBE : 简单的读写工具（y_Read, y_Write）
- SAFE_SINGLE_FUNCTION_CANDIDATE : 安全的单函数 wrapper 候选（y_Smooth, y_ALFF, y_fALFF）
- FULL_PIPELINE_BLOCKED : 完整 pipeline runner（DPARSF_run, DPARSFA_run）
- GUI_BLOCKED : GUI 入口点（DPABI, DPARSF, DPARSFA）
- UNKNOWN_REVIEW_REQUIRED : 信息不足，需要人工审查
## 生成的文件
```
work/dpabi/
├── dpabi_function_signatures.json    # 函数签名
├── dpabi_wrapper_contracts.json      # Wrapper contracts (JSON)
└── dpabi_wrapper_contracts.yaml      # Wrapper contracts (YAML)

reports/dpabi/
└── dpabi_signature_probe_report.md   # 人工可读报告
```
## 这一步不做的事
- ❌ 不执行 DPABI 预处理
- ❌ 不调用 DPARSF_run / DPARSFA_run
- ❌ 不调用 DPABI GUI
- ❌ 不处理真实医学影像数据
- ❌ 不修改 rawdata
- ❌ 不修改 DPABI 源码
- ❌ 不删除文件
## 意义
这是 DPABI 执行链的 函数级安全分析步骤 ，确保：

1. 了解每个函数的参数签名
2. 识别哪些函数可以安全封装
3. 阻止危险的 GUI 和 pipeline runner
4. 为下一步的单函数 wrapper 开发提供 contract
通过 signature probe 后，系统可以安全地进入下一步： 基于 contracts 创建单函数 wrapper 。
'''