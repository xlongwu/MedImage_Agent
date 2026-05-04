你是我的工程搭建助手。前二十一步已经完成：

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

现在开始第二十二步。

第二十二步目标：实现“DPABI Single-Function Wrapper Sandbox + Contract Test 闭环”。

当前系统已经能够：

- 探测 DPABI 函数是否存在
- 记录 nargin / nargout / help
- 生成 wrapper contracts
- 阻止 DPABI GUI 和 DPARSF_run / DPARSFA_run
- 运行 approved sandbox smoke test

但还没有真正封装任何 DPABI 单函数。

本步骤要实现一个最小、安全、可审计的单函数 wrapper sandbox：

- 读取 dpabi_wrapper_contracts.json
- 选择 allowlisted 单函数候选
- 第一阶段只支持：
  - y_Smooth
  - rest_Smooth
- 必须显式 approved=true 才允许执行 MATLAB 单函数 sandbox
- 只在 work/dpabi/single_function_sandbox/ 下创建 synthetic NIfTI
- 只对 synthetic NIfTI 执行 smoothing wrapper test
- 不读取 rawdata
- 不修改 rawdata
- 不调用 DPABI GUI
- 不调用 DPARSF_run / DPARSFA_run
- 不运行完整 DPABI preprocessing
- 生成 wrapper test result
- 生成 wrapper test audit
- 生成 wrapper test report
- 将 dpabi_single_function_sandbox 作为 project-level pipeline node 接入
- 后端 API 暴露 single-function sandbox run 和结果
- 前端 DPABI Panel 显示 single-function wrapper sandbox 结果

不要实现：
- DPABI 全流程执行
- DPARSF_run / DPARSFA_run 自动执行
- DPABI GUI 自动化
- 真实医学影像处理
- subject-level DPABI 执行
- rawdata 读取或修改
- DPABI 源码修改
- 删除文件
- 并行 DPABI
- GPU DPABI
- WebSocket
- 数据库
- 真实 LLM 自动决策

本步骤只做 synthetic sandbox 下的 DPABI 单函数 wrapper contract test。

---

## 1. 创建 specs/dpabi_single_function_wrapper_spec.md

创建文件：

```text
specs/dpabi_single_function_wrapper_spec.md

内容：

# DPABI Single-Function Wrapper Sandbox Specification

This document defines the MVP DPABI single-function wrapper sandbox.

## Goals

The single-function wrapper sandbox verifies that selected DPABI utility functions can be called safely on synthetic data.

The MVP focuses on:

- y_Smooth
- rest_Smooth
- synthetic NIfTI input
- sandbox-only output
- explicit approval
- execution audit
- wrapper contract validation

## Scope

Supported in this step:

- read dpabi_wrapper_contracts.json
- select allowlisted wrapper candidate
- approved synthetic sandbox execution
- y_Smooth sandbox test
- rest_Smooth sandbox test
- result JSON
- audit JSON
- Markdown report
- API and frontend visibility

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- GUI automation
- real medical image preprocessing
- subject-level DPABI processing
- rawdata modification
- DPABI source modification
- deletion of files

## Inputs

```text
work/dpabi/dpabi_wrapper_contracts.json
examples/project_config_dataset.yaml
Outputs
work/dpabi/single_function_sandbox/input_synthetic.nii
work/dpabi/single_function_sandbox/smoothed_synthetic.nii
work/dpabi/single_function_sandbox/dpabi_single_function_result.json
work/dpabi/audit/dpabi_single_function_wrapper_audit.json
reports/dpabi/dpabi_single_function_wrapper_report.md
logs/dpabi_single_function_stdout.log
logs/dpabi_single_function_stderr.log
Allowlisted Functions

Only the following functions can be executed in this MVP:

y_Smooth
rest_Smooth
Approval Rules
Execution requires approved=true.
Missing approval must fail safely.
Approval must be recorded in the audit.
The wrapper must not execute full DPABI preprocessing.
Safety Rules
Do not read rawdata.
Do not modify rawdata.
Do not call DPABI GUI.
Do not call DPARSF_run.
Do not call DPARSFA_run.
Do not modify DPABI source.
Do not delete files.
Only write under work/dpabi/single_function_sandbox, work/dpabi/audit, reports/dpabi, and logs.

---

## 2. 创建 matlab/dpabi_single_function_sandbox.m

创建文件：

```text
matlab/dpabi_single_function_sandbox.m

功能要求：

接收参数：
dpabi_dir
function_name
sandbox_dir
output_json
只允许 function_name 为：
y_Smooth
rest_Smooth
添加 DPABI 路径：
addpath(genpath(dpabi_dir))
在 sandbox_dir 下创建 synthetic NIfTI：
input_synthetic.nii
根据 function_name 执行对应测试：
如果 y_Smooth 存在：
尝试调用 y_Smooth
如果 rest_Smooth 存在：
尝试调用 rest_Smooth
如果函数不存在：
ok=false
errors 说明函数不存在
如果签名不匹配：
ok=false
errors 说明需要人工 wrapper review
输出：
smoothed_synthetic.nii
dpabi_single_function_result.json
严禁调用：
DPABI
DPARSF
DPARSFA
DPARSF_run
DPARSFA_run
不读取 rawdata。
不修改 DPABI 源码。
不删除文件。

参考实现：

function dpabi_single_function_sandbox(dpabi_dir, function_name, sandbox_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_single_function_sandbox';
    result.backend = 'matlab-dpabi';
    result.function_name = function_name;
    result.dpabi_dir = dpabi_dir;
    result.sandbox_dir = sandbox_dir;
    result.matlab_version = version;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};
    result.warnings = {};

    try
        allowlist = {'y_Smooth', 'rest_Smooth'};
        if ~any(strcmp(function_name, allowlist))
            error(['Function is not allowlisted for sandbox execution: ', function_name]);
        end

        if ~exist(dpabi_dir, 'dir')
            error(['DPABI directory not found: ', dpabi_dir]);
        end

        if ~exist(sandbox_dir, 'dir')
            mkdir(sandbox_dir);
        end

        addpath(genpath(dpabi_dir));

        input_nii = fullfile(sandbox_dir, 'input_synthetic.nii');
        output_nii = fullfile(sandbox_dir, 'smoothed_synthetic.nii');

        fn_path = which(function_name);
        result.metrics.function_found = ~isempty(fn_path);
        result.metrics.function_path = fn_path;

        if isempty(fn_path)
            error(['Function not found on MATLAB path: ', function_name]);
        end

        data = single(randn(16, 16, 16));

        if isempty(which('spm_write_vol'))
            error('spm_write_vol not found. Cannot create synthetic NIfTI.');
        end

        V = struct();
        V.fname = input_nii;
        V.dim = size(data);
        V.dt = [16 0];
        V.mat = eye(4);
        V.pinfo = [1; 0; 0];
        V.descrip = 'Synthetic NIfTI for DPABI single-function wrapper test';

        spm_write_vol(V, data);

        if ~exist(input_nii, 'file')
            error('Failed to create synthetic input NIfTI.');
        end

        result.metrics.input_exists = exist(input_nii, 'file') == 2;
        result.metrics.wrapper_call_attempted = true;
        result.metrics.wrapper_call_success = false;

        fwhm = [4 4 4];

        if strcmp(function_name, 'y_Smooth')
            try
                % Common DPABI style: y_Smooth(InputName, OutputName, FWHM)
                y_Smooth(input_nii, output_nii, fwhm);
                result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                result.metrics.call_pattern = 'y_Smooth(input_nii, output_nii, fwhm)';
            catch ME1
                result.warnings{end+1} = ['First y_Smooth call pattern failed: ', ME1.message];

                try
                    % Some variants may accept cell input.
                    y_Smooth({input_nii}, {output_nii}, fwhm);
                    result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                    result.metrics.call_pattern = 'y_Smooth({input_nii}, {output_nii}, fwhm)';
                catch ME2
                    error(['y_Smooth sandbox wrapper failed. Manual signature review required. Last error: ', ME2.message]);
                end
            end

        elseif strcmp(function_name, 'rest_Smooth')
            try
                % Common REST style. This may vary by version.
                rest_Smooth(input_nii, output_nii, fwhm);
                result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                result.metrics.call_pattern = 'rest_Smooth(input_nii, output_nii, fwhm)';
            catch ME1
                result.warnings{end+1} = ['rest_Smooth call pattern failed: ', ME1.message];
                error('rest_Smooth sandbox wrapper failed. Manual signature review required.');
            end
        end

        if ~exist(output_nii, 'file')
            error('Single-function wrapper did not produce smoothed_synthetic.nii.');
        end

        result.outputs{end+1} = input_nii;
        result.outputs{end+1} = output_nii;
        result.metrics.output_exists = exist(output_nii, 'file') == 2;

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
3. 创建 backend/app/tools/dpabi_single_function_runner.py

创建文件：

backend/app/tools/dpabi_single_function_runner.py

目标：Python 执行 approved DPABI 单函数 sandbox wrapper test。

提供函数：

run_dpabi_single_function_sandbox(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    function_name: str = "y_Smooth",
    approved: bool = False,
    approved_by: str = "local-user",
    matlab_script_dir: str = "./matlab",
) -> dict

要求：

approved=false 时安全失败，不运行 MATLAB。
function_name 只允许：
y_Smooth
rest_Smooth
读取：
work/dpabi/dpabi_wrapper_contracts.json
如果 contract 中该函数不存在或 wrapper_candidate=false：
返回 ok=false
不运行 MATLAB
调用 MATLAB 脚本。
写：
result JSON
audit JSON
Markdown report
不使用 shell=True。
不读取 rawdata。
不调用 full DPABI。

参考实现：

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWLISTED_SINGLE_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_contract(contracts: dict[str, Any], function_name: str) -> dict[str, Any] | None:
    for item in contracts.get("contracts", []):
        if item.get("function_name") == function_name:
            return item
    return None


def run_dpabi_single_function_sandbox(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    function_name: str = "y_Smooth",
    approved: bool = False,
    approved_by: str = "local-user",
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "dpabi_single_function_sandbox",
            "backend": "matlab-dpabi",
            "function_name": function_name,
            "outputs": [],
            "warnings": [],
            "errors": ["DPABI single-function sandbox requires approved=true."],
        }

    if function_name not in ALLOWLISTED_SINGLE_FUNCTIONS:
        return {
            "ok": False,
            "node_id": "dpabi_single_function_sandbox",
            "backend": "matlab-dpabi",
            "function_name": function_name,
            "outputs": [],
            "warnings": [],
            "errors": [f"Function is not allowlisted: {function_name}"],
        }

    dpabi_work = Path(work_dir) / "dpabi"
    sandbox_dir = dpabi_work / "single_function_sandbox"
    audit_dir = dpabi_work / "audit"
    approvals_dir = dpabi_work / "approvals"
    report_dir = Path("reports") / "dpabi"
    log_path = Path(log_dir)

    sandbox_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    log_path.mkdir(parents=True, exist_ok=True)

    contracts_path = dpabi_work / "dpabi_wrapper_contracts.json"
    contracts = _read_json(contracts_path)

    if not contracts:
        return {
            "ok": False,
            "node_id": "dpabi_single_function_sandbox",
            "backend": "matlab-dpabi",
            "function_name": function_name,
            "outputs": [],
            "warnings": [],
            "errors": [f"Missing wrapper contracts: {contracts_path}"],
        }

    contract = _find_contract(contracts, function_name)
    if not contract:
        return {
            "ok": False,
            "node_id": "dpabi_single_function_sandbox",
            "backend": "matlab-dpabi",
            "function_name": function_name,
            "outputs": [],
            "warnings": [],
            "errors": [f"No wrapper contract found for function: {function_name}"],
        }

    if not contract.get("wrapper_candidate"):
        return {
            "ok": False,
            "node_id": "dpabi_single_function_sandbox",
            "backend": "matlab-dpabi",
            "function_name": function_name,
            "outputs": [],
            "warnings": [],
            "errors": [
                f"Function is not marked as wrapper_candidate: {function_name}. "
                f"Reason: {contract.get('blocked_reason')}"
            ],
        }

    approval_record = {
        "approved": True,
        "approved_by": approved_by,
        "approved_at": _now_iso(),
        "execution_type": "dpabi_single_function_sandbox",
        "function_name": function_name,
        "full_dpabi_execution": False,
        "dpabi_gui_called": False,
        "dparsf_run_called": False,
        "rawdata_modified": False,
        "files_deleted": False,
        "contracts_path": str(contracts_path),
    }

    approval_path = approvals_dir / "dpabi_single_function_approval.json"
    approval_path.write_text(
        json.dumps(approval_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result_json = sandbox_dir / "dpabi_single_function_result.json"
    stdout_log = log_path / "dpabi_single_function_stdout.log"
    stderr_log = log_path / "dpabi_single_function_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"dpabi_single_function_sandbox('{_matlab_quote(str(Path(dpabi_dir).resolve()))}', "
        f"'{_matlab_quote(function_name)}', "
        f"'{_matlab_quote(str(sandbox_dir.resolve()))}', "
        f"'{_matlab_quote(str(result_json.resolve()))}'); "
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

    if result_json.exists():
        try:
            data = json.loads(result_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            data = {
                "ok": False,
                "errors": [f"Failed to parse single-function result JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["Single-function sandbox did not produce result JSON."],
        }

    data["node_id"] = "dpabi_single_function_sandbox"
    data["backend"] = "matlab-dpabi"
    data["function_name"] = function_name
    data["returncode"] = completed.returncode
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)
    data["approval_record"] = str(approval_path)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    audit = {
        "ok": bool(data.get("ok")),
        "execution_type": "dpabi_single_function_sandbox",
        "function_name": function_name,
        "full_dpabi_execution": False,
        "dpabi_gui_called": False,
        "dparsf_run_called": False,
        "rawdata_modified": False,
        "files_deleted": False,
        "approval_record": str(approval_path),
        "contracts_path": str(contracts_path),
        "result_json": str(result_json),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "returncode": completed.returncode,
        "contract": contract,
        "errors": data.get("errors", []),
        "warnings": data.get("warnings", []),
        "metrics": data.get("metrics", {}),
    }

    audit_json = audit_dir / "dpabi_single_function_wrapper_audit.json"
    audit_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report_path = report_dir / "dpabi_single_function_wrapper_report.md"
    lines = []
    lines.append("# DPABI Single-Function Wrapper Sandbox Report")
    lines.append("")
    lines.append(f"- OK: {audit['ok']}")
    lines.append(f"- Function: {function_name}")
    lines.append(f"- Full DPABI execution: {audit['full_dpabi_execution']}")
    lines.append(f"- DPABI GUI called: {audit['dpabi_gui_called']}")
    lines.append(f"- DPARSF_run called: {audit['dparsf_run_called']}")
    lines.append(f"- Rawdata modified: {audit['rawdata_modified']}")
    lines.append(f"- Files deleted: {audit['files_deleted']}")
    lines.append(f"- Return code: {audit['returncode']}")
    lines.append("")
    lines.append("## Contract")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(contract, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(audit.get("metrics", {}), ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    if audit["errors"]:
        for item in audit["errors"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This was a synthetic sandbox single-function wrapper test only. It did not run full DPABI preprocessing.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    outputs = list(data.get("outputs", []))
    outputs.extend([str(result_json), str(approval_path), str(audit_json), str(report_path)])

    data["outputs"] = outputs
    data["audit_json"] = str(audit_json)
    data["audit_report"] = str(report_path)

    return data
4. 修改 backend/app/runtime/node_registry.py

新增节点：

dpabi_single_function_sandbox

新增导入：

from backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox

新增 runner：

def run_dpabi_single_function_sandbox_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = run_dpabi_single_function_sandbox(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        function_name=node.params.get("function_name", "y_Smooth"),
        approved=bool(node.params.get("approved", False)),
        approved_by=node.params.get("approved_by", "local-user"),
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_single_function_sandbox": run_dpabi_single_function_sandbox_node,
5. 创建 examples/pipeline_dpabi_single_function_sandbox.yaml

创建文件：

examples/pipeline_dpabi_single_function_sandbox.yaml

内容：

pipeline_id: dpabi_single_function_sandbox_pipeline
version: "0.1.0"
modality: integration-test
description: "Probe DPABI signatures, generate wrapper contracts, and run an approved single-function sandbox wrapper test."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_single_function_sandbox_001"
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

  - id: dpabi_single_function_sandbox
    name: Approved DPABI Single-Function Sandbox
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - dpabi_wrapper_contracts
    inputs:
      - "./work/dpabi/dpabi_wrapper_contracts.json"
    outputs:
      - "./work/dpabi/single_function_sandbox/dpabi_single_function_result.json"
      - "./work/dpabi/audit/dpabi_single_function_wrapper_audit.json"
      - "./reports/dpabi/dpabi_single_function_wrapper_report.md"
    params:
      function_name: "y_Smooth"
      approved: false
      approved_by: "local-user"
    parallel_level: project
    gpu_supported: false
    cache: false

注意：默认 approved: false，直接运行时应该安全失败。真正执行需要 CLI/API 显式 approval。

6. 创建 backend/app/tools/run_dpabi_single_function_sandbox_cli.py

创建文件：

backend/app/tools/run_dpabi_single_function_sandbox_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_dpabi_single_function_sandbox.yaml
默认 function_name：
y_Smooth
默认不 approved。
如果传入 --approve，生成 approved pipeline 副本：
work/dpabi/approved_pipeline_dpabi_single_function_sandbox.yaml

并把：

dpabi_single_function_sandbox.params.approved = true
function_name 改成用户传入的 function_name
调用 run_pipeline。
打印 summary。

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def _make_approved_pipeline_copy(source: Path, target: Path, function_name: str) -> Path:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    for node in data.get("nodes", []):
        if node.get("id") == "dpabi_single_function_sandbox":
            node.setdefault("params", {})
            node["params"]["approved"] = True
            node["params"]["approved_by"] = "local-user"
            node["params"]["function_name"] = function_name

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_dpabi_single_function_sandbox.yaml")
    function_name = args[2] if len(args) > 2 else "y_Smooth"

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("outputs/work/dpabi/approved_pipeline_dpabi_single_function_sandbox.yaml"),
            function_name=function_name,
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
7. 修改 backend/app/api/models.py

新增 request model：

class DpabiSingleFunctionSandboxRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    function_name: str = Field(default="y_Smooth")
    approved: bool = Field(default=False)
    approved_by: str = Field(default="local-user")
8. 修改 backend/app/api/routes.py

新增 API：

POST /api/dpabi/single-function-sandbox
GET  /api/dpabi/single-function-sandbox

新增导入：

from backend.app.api.models import DpabiSingleFunctionSandboxRequest
from backend.app.tools.dpabi_single_function_runner import run_dpabi_single_function_sandbox

新增路由：

@router.post("/api/dpabi/single-function-sandbox")
def api_run_dpabi_single_function_sandbox(
    request: DpabiSingleFunctionSandboxRequest,
) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="DPABI single-function sandbox requires approved=true.",
        )

    if request.function_name not in {"y_Smooth", "rest_Smooth"}:
        raise HTTPException(
            status_code=400,
            detail="Only y_Smooth and rest_Smooth are allowlisted in this MVP.",
        )

    try:
        project_config = _load_project_config(request.project_config_path)
        runtime = project_config.get("runtime", {})
        third_party = project_config.get("third_party", {})

        result = run_dpabi_single_function_sandbox(
            matlab_command=runtime.get("matlab_command", "matlab"),
            dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
            work_dir=runtime.get("work_dir", "./work"),
            log_dir=runtime.get("log_dir", "./logs"),
            function_name=request.function_name,
            approved=request.approved,
            approved_by=request.approved_by,
            matlab_script_dir="./matlab",
        )

        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)

        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/dpabi/single-function-sandbox")
def api_get_dpabi_single_function_sandbox() -> dict[str, Any]:
    base = Path("work") / "dpabi"
    report_base = Path("reports") / "dpabi"

    return {
        "ok": True,
        "single_function_result": _read_json_if_exists(
            base / "single_function_sandbox" / "dpabi_single_function_result.json"
        ),
        "single_function_approval": _read_json_if_exists(
            base / "approvals" / "dpabi_single_function_approval.json"
        ),
        "single_function_audit": _read_json_if_exists(
            base / "audit" / "dpabi_single_function_wrapper_audit.json"
        ),
        "single_function_report": _read_text_if_exists(
            report_base / "dpabi_single_function_wrapper_report.md"
        ),
    }

同时修改已有 /api/dpabi/capabilities，新增返回：

"single_function_result": _read_json_if_exists(base / "single_function_sandbox" / "dpabi_single_function_result.json"),
"single_function_approval": _read_json_if_exists(base / "approvals" / "dpabi_single_function_approval.json"),
"single_function_audit": _read_json_if_exists(base / "audit" / "dpabi_single_function_wrapper_audit.json"),

修改已有 /api/reports/dpabi，新增返回：

"single_function_report": _read_text_if_exists(base / "dpabi_single_function_wrapper_report.md"),
9. 修改 frontend/src/api.ts

新增：

export async function runDpabiSingleFunctionSandbox(
  baseUrl: string,
  payload: {
    project_config_path: string;
    function_name: string;
    approved: boolean;
    approved_by: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/single-function-sandbox",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getDpabiSingleFunctionSandbox(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/single-function-sandbox"
  );
}
10. 修改 frontend/src/components/DpabiPanel.tsx

新增导入：

import {
  runDpabiSingleFunctionSandbox,
  getDpabiSingleFunctionSandbox
} from "../api";

如果已有 getDpabiCapabilities / getDpabiReport 等导入，合并到同一个 import 中，不要重复。

新增 state：

const [singleFunctionName, setSingleFunctionName] = useState("y_Smooth");
const [singleFunctionResult, setSingleFunctionResult] = useState<Record<string, unknown> | null>(null);
const [singleFunctionStatus, setSingleFunctionStatus] = useState("IDLE");

新增函数：

async function handleRunSingleFunctionSandbox() {
  const confirmed = window.confirm(
    `确认运行 DPABI single-function sandbox：${singleFunctionName}？这会启动 MATLAB，但只处理 synthetic NIfTI，不会读取 rawdata。`
  );

  if (!confirmed) return;

  setSingleFunctionStatus("RUNNING");
  setError("");

  try {
    const result = await runDpabiSingleFunctionSandbox(baseUrl, {
      project_config_path: "examples/project_config_dataset.yaml",
      function_name: singleFunctionName,
      approved: true,
      approved_by: "local-user"
    });
    setSingleFunctionResult(result);
    setSingleFunctionStatus(result.ok ? "SUCCESS" : "FAILED");
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
    setSingleFunctionStatus("ERROR");
  }
}

async function handleLoadSingleFunctionSandbox() {
  setError("");

  try {
    const result = await getDpabiSingleFunctionSandbox(baseUrl);
    setSingleFunctionResult(result);
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
  }
}

在 JSX 中增加：

<h3>Approved DPABI Single-Function Sandbox</h3>

<div className="formGrid">
  <label>
    Function
    <select
      value={singleFunctionName}
      onChange={(event) => setSingleFunctionName(event.target.value)}
    >
      <option value="y_Smooth">y_Smooth</option>
      <option value="rest_Smooth">rest_Smooth</option>
    </select>
  </label>
</div>

<div className="row">
  <button className="dangerButton" onClick={handleRunSingleFunctionSandbox}>
    批准并运行 Single-Function Sandbox
  </button>
  <button onClick={handleLoadSingleFunctionSandbox}>
    加载 Single-Function 结果
  </button>
  <StatusBadge status={singleFunctionStatus} />
</div>

<JsonBlock value={singleFunctionResult} emptyText="尚未运行 single-function sandbox" />

<h3>Single-Function Result</h3>
<JsonBlock value={capabilities?.single_function_result} emptyText="暂无 single-function result" />

<h3>Single-Function Approval</h3>
<JsonBlock value={capabilities?.single_function_approval} emptyText="暂无 single-function approval" />

<h3>Single-Function Audit</h3>
<JsonBlock value={capabilities?.single_function_audit} emptyText="暂无 single-function audit" />

<h3>Single-Function Report</h3>
<TextViewer
  text={
    typeof report?.single_function_report === "string"
      ? report.single_function_report
      : null
  }
  emptyText="暂无 single-function wrapper report"
/>

如果 select 样式不好看，在 styles.css 中补：

select {
  border: 1px solid #d2d8e8;
  border-radius: 10px;
  padding: 9px 12px;
  min-width: 280px;
  background: white;
}
11. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/dpabi/single-function-sandbox")

不要在 smoke test 中调用 POST /api/dpabi/single-function-sandbox，避免误启动 MATLAB。

12. 更新 README.md

追加第二十二步说明：

## Step 22: DPABI Single-Function Wrapper Sandbox

This step adds an approved single-function DPABI wrapper sandbox.

It does not run full DPABI preprocessing.

Supported MVP functions:

- y_Smooth
- rest_Smooth

### Run without approval

```bash
python -m backend.app.tools.run_dpabi_single_function_sandbox_cli

This should fail safely because approval is missing.

Run with approval
python -m backend.app.tools.run_dpabi_single_function_sandbox_cli examples/project_config_dataset.yaml examples/pipeline_dpabi_single_function_sandbox.yaml y_Smooth --approve

Expected outputs:

work/dpabi/single_function_sandbox/input_synthetic.nii
work/dpabi/single_function_sandbox/smoothed_synthetic.nii
work/dpabi/single_function_sandbox/dpabi_single_function_result.json
work/dpabi/approvals/dpabi_single_function_approval.json
work/dpabi/audit/dpabi_single_function_wrapper_audit.json
reports/dpabi/dpabi_single_function_wrapper_report.md
logs/dpabi_single_function_stdout.log
logs/dpabi_single_function_stderr.log
API

Run approved single-function sandbox:

curl -X POST http://127.0.0.1:8000/api/dpabi/single-function-sandbox \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "function_name": "y_Smooth",
    "approved": true,
    "approved_by": "local-user"
  }'

Read result:

curl http://127.0.0.1:8000/api/dpabi/single-function-sandbox
Frontend

Use the DPABI panel and choose:

Approved DPABI Single-Function Sandbox
Safety

This step does not:

run DPARSF_run
run DPARSFA_run
call DPABI GUI
read rawdata
modify rawdata
modify DPABI source
delete files
process real medical imaging data

---

## 13. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_single_function_wrapper_spec.md
matlab/dpabi_single_function_sandbox.m
backend/app/tools/dpabi_single_function_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_single_function_sandbox.yaml
backend/app/tools/run_dpabi_single_function_sandbox_cli.py
backend/app/api/models.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/DpabiPanel.tsx
frontend/src/styles.css
README.md

先运行不带 approval：

python -m backend.app.tools.run_dpabi_single_function_sandbox_cli

应该安全失败，不能执行 MATLAB single-function sandbox。

然后运行 signature probe，确保 contracts 存在：

python -m backend.app.tools.run_dpabi_signature_probe_cli

再运行 approved single-function sandbox：

python -m backend.app.tools.run_dpabi_single_function_sandbox_cli examples/project_config_dataset.yaml examples/pipeline_dpabi_single_function_sandbox.yaml y_Smooth --approve

如果本地 DPABI 中存在 y_Smooth 且签名兼容，应生成：

work/dpabi/single_function_sandbox/input_synthetic.nii
work/dpabi/single_function_sandbox/smoothed_synthetic.nii
work/dpabi/single_function_sandbox/dpabi_single_function_result.json
work/dpabi/approvals/dpabi_single_function_approval.json
work/dpabi/audit/dpabi_single_function_wrapper_audit.json
reports/dpabi/dpabi_single_function_wrapper_report.md
logs/dpabi_single_function_stdout.log
logs/dpabi_single_function_stderr.log
work/pipeline_runs/run_dpabi_single_function_sandbox_001/summary.json

其中 approval JSON 应包含：

{
  "approved": true,
  "execution_type": "dpabi_single_function_sandbox",
  "function_name": "y_Smooth",
  "full_dpabi_execution": false,
  "rawdata_modified": false,
  "files_deleted": false
}

其中 audit JSON 应包含：

{
  "full_dpabi_execution": false,
  "dpabi_gui_called": false,
  "dparsf_run_called": false,
  "rawdata_modified": false,
  "files_deleted": false
}

如果 y_Smooth 不存在或 contract 不是 wrapper_candidate：

必须安全失败。
不应读取 rawdata。
不应调用 DPARSF_run。
错误应写入 result / summary / logs。

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/single-function-sandbox

未批准 POST 应失败：

curl -X POST http://127.0.0.1:8000/api/dpabi/single-function-sandbox \
  -H "Content-Type: application/json" \
  -d '{"function_name": "y_Smooth", "approved": false}'

应返回 403 或清晰错误。

批准 POST 可运行：

curl -X POST http://127.0.0.1:8000/api/dpabi/single-function-sandbox \
  -H "Content-Type: application/json" \
  -d '{"function_name": "y_Smooth", "approved": true, "approved_by": "local-user"}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

DPABI Panel 显示 Single-Function Sandbox 区域。
可以选择 y_Smooth 或 rest_Smooth。
点击运行前有 confirm 弹窗。
approved 后调用后端运行 sandbox。
显示 result。
显示 approval。
显示 audit。
显示 wrapper report。
不运行完整 DPABI preprocessing。
不读取或修改 rawdata。
14. 重要限制

本步骤只做 DPABI single-function wrapper sandbox。

不要实现：

DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
subject-level 真实数据处理
rawdata 读取或修改
DPABI 源码修改
删除文件
自动参数优化
并行 DPABI
GPU DPABI

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 signature probe 生成 contracts
如何运行不带 approval 的安全失败测试
如何运行 approved single-function sandbox
sandbox 实际验证了什么
为什么这一步仍然不是完整 DPABI pipeline execution

'''
## Step 22 主要做什么
第二十二步目标：实现"DPABI Single-Function Wrapper Sandbox + Contract Test 闭环"

### 核心目的
在前一步（Step 21）已经能够探测 DPABI 函数签名并生成 wrapper contracts 的基础上， 这一步真正实现对单个 DPABI 函数的封装和测试 。

### 具体做的事情
方面 说明 选择候选函数 从 wrapper contracts 中选择标记为 wrapper_candidate 的函数 Allowlist 限制 第一阶段只允许 y_Smooth 和 rest_Smooth 审批门控 必须显式设置 approved=true 才能执行 合成数据测试 创建 16×16×16 合成 NIfTI，在沙箱中测试函数 合约验证 执行前验证函数在 contracts 中且是 wrapper_candidate 审计记录 生成 approval record、execution audit、Markdown report

### 安全边界
- ✅ 读取 wrapper contracts
- ✅ 在 work/dpabi/single_function_sandbox/ 下创建合成数据
- ✅ 对合成数据执行 smoothing 测试
- ❌ 不读取真实 rawdata
- ❌ 不修改真实 rawdata
- ❌ 不调用 DPABI GUI
- ❌ 不调用 DPARSF_run / DPARSFA_run
- ❌ 不执行完整 DPABI 预处理
### 输出产物
```
work/dpabi/
├── single_function_sandbox/
│   ├── input_synthetic.nii              # 合成输入
│   ├── smoothed_synthetic.nii           # 平滑后输出
│   └── dpabi_single_function_result.json # 测试结果
├── approvals/
│   └── dpabi_single_function_approval.json # 审批记录
└── audit/
    └── dpabi_single_function_wrapper_audit.json # 执行审计

reports/dpabi/
└── dpabi_single_function_wrapper_report.md # 可读报告
```
### 与 Step 21 的区别
Step 21 Step 22 探测函数签名 (nargin/nargout) 实际调用函数执行 生成 wrapper contracts 验证 contracts 并执行 静态分析 动态沙箱测试 不执行任何 DPABI 代码 执行 allowlisted 单函数

简单来说：Step 21 是"看"，Step 22 是"试" —— 在安全的沙箱环境中实际测试选定的 DPABI 单函数是否能被正确封装和调用。
'''