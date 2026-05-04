你是我的工程搭建助手。前十九步已经完成：

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

现在开始第二十步。

第二十步目标：实现“DPABI Approved Sandbox Smoke Run + Execution Audit 闭环”。

当前系统已经能生成 DPABI run plan，但还没有任何受控的 DPABI 执行能力。  
本步骤不要运行完整 DPABI / DPARSF 预处理，而是实现一个安全沙箱 smoke run：

- 必须显式 approved=true 才能运行
- 只在 work/dpabi/sandbox/ 下生成 synthetic NIfTI
- MATLAB 中 addpath(genpath(dpabi_dir))
- 尝试调用 DPABI 的安全 I/O 函数，例如 y_Read / y_Write 或 rest_readfile / rest_writefile
- 如果这些函数不存在，则只记录 capability 缺失，不崩溃
- 不读取 rawdata
- 不修改 rawdata
- 不调用 DPABI GUI
- 不调用 DPARSF_run / DPARSFA_run
- 不运行完整 DPABI preprocessing
- 写 sandbox smoke result
- 写 approval record
- 写 execution audit
- 将 dpabi_sandbox_smoke_run 作为 pipeline node 接入
- 后端 API 支持 approved sandbox run
- 前端 DPABI Panel 增加“Approved Sandbox Smoke Run”区域

不要实现：
- DPABI 全流程执行
- DPARSF_run 自动执行
- DPARSFA_run 自动执行
- DPABI GUI 自动化
- 真实医学影像预处理
- 修改 rawdata
- 修改 DPABI 源码
- 删除文件
- 并行 DPABI
- GPU DPABI
- WebSocket
- 数据库
- 真实 LLM 自动决策

本步骤只做 approved sandbox smoke run，不做完整 DPABI pipeline。

---

## 1. 创建 specs/dpabi_execution_sandbox_spec.md

创建文件：

```text
specs/dpabi_execution_sandbox_spec.md

内容：

# DPABI Execution Sandbox Specification

This document defines the MVP approved DPABI sandbox execution.

## Goals

The sandbox smoke run verifies that MedImage Agent can safely call DPABI-related MATLAB functions without running full preprocessing.

It should validate:

- explicit approval gate
- MATLAB launch
- DPABI path setup
- selected safe DPABI function discovery
- synthetic NIfTI read/write in sandbox
- result JSON
- stdout/stderr logs
- approval record
- execution audit

## Scope

Supported in this step:

- approved sandbox smoke run
- synthetic NIfTI created under work/dpabi/sandbox
- DPABI addpath
- safe function probing
- optional y_Read / y_Write test
- optional rest_readfile / rest_writefile test
- execution audit JSON
- Markdown audit report
- API and frontend visibility

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- GUI automation
- rawdata modification
- DPABI source modification
- deletion of files
- real medical image processing

## Inputs

```text
work/dpabi/dpabi_run_plan.json
work/dpabi/dpabi_capabilities.json
examples/project_config_dataset.yaml
Outputs
work/dpabi/sandbox/input_synthetic.nii
work/dpabi/sandbox/output_synthetic.nii
work/dpabi/sandbox/dpabi_sandbox_smoke_result.json
work/dpabi/approvals/dpabi_sandbox_smoke_approval.json
work/dpabi/audit/dpabi_sandbox_execution_audit.json
reports/dpabi/dpabi_sandbox_execution_audit.md
logs/dpabi_sandbox_smoke_stdout.log
logs/dpabi_sandbox_smoke_stderr.log
Approval Rules
Sandbox run requires approved=true.
Approval must be recorded before MATLAB execution.
Approval record must include timestamp, execution_type, and safety flags.
Missing approval must fail safely.
Safety Rules
Do not read rawdata.
Do not modify rawdata.
Do not call DPABI GUI.
Do not call DPARSF_run.
Do not call DPARSFA_run.
Do not modify DPABI source.
Do not delete files.
Sandbox output must be written only under work/dpabi/sandbox.

---

## 2. 创建 matlab/dpabi_sandbox_smoke_run.m

创建文件：

```text
matlab/dpabi_sandbox_smoke_run.m

功能要求：

接收参数：
dpabi_dir
sandbox_dir
output_json
添加 DPABI 路径：
addpath(genpath(dpabi_dir))
在 sandbox_dir 中创建 synthetic NIfTI：
input_synthetic.nii
size: 8 x 8 x 8
single
affine identity
尝试使用 DPABI / REST 函数读写：
优先尝试 y_Read + y_Write
如果 y_Read / y_Write 不存在，尝试 rest_readfile / rest_writefile
如果都不存在，使用 SPM / MATLAB fallback 或只记录未找到函数
输出：
output_synthetic.nii
dpabi_sandbox_smoke_result.json
记录：
dpabi_dir
sandbox_dir
matlab_version
y_Read_found
y_Write_found
rest_readfile_found
rest_writefile_found
read_write_test_attempted
read_write_test_success
errors
warnings
严禁：
调用 DPARSF_run
调用 DPARSFA_run
调用 DPABI GUI
读取 rawdata
修改 DPABI 源码

参考实现：

function dpabi_sandbox_smoke_run(dpabi_dir, sandbox_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_sandbox_smoke_run';
    result.backend = 'matlab-dpabi';
    result.dpabi_dir = dpabi_dir;
    result.sandbox_dir = sandbox_dir;
    result.matlab_version = version;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};
    result.warnings = {};

    try
        if ~exist(dpabi_dir, 'dir')
            error(['DPABI directory not found: ', dpabi_dir]);
        end

        if ~exist(sandbox_dir, 'dir')
            mkdir(sandbox_dir);
        end

        addpath(genpath(dpabi_dir));

        input_nii = fullfile(sandbox_dir, 'input_synthetic.nii');
        output_nii = fullfile(sandbox_dir, 'output_synthetic.nii');

        y_read_path = which('y_Read');
        y_write_path = which('y_Write');
        rest_read_path = which('rest_readfile');
        rest_write_path = which('rest_writefile');

        result.metrics.y_Read_found = ~isempty(y_read_path);
        result.metrics.y_Write_found = ~isempty(y_write_path);
        result.metrics.rest_readfile_found = ~isempty(rest_read_path);
        result.metrics.rest_writefile_found = ~isempty(rest_write_path);

        data = single(randn(8, 8, 8));

        V = struct();
        V.fname = input_nii;
        V.dim = size(data);
        V.dt = [16 0];
        V.mat = eye(4);
        V.pinfo = [1; 0; 0];
        V.descrip = 'Synthetic NIfTI for DPABI sandbox smoke test';

        spm_found = ~isempty(which('spm_write_vol'));
        result.metrics.spm_write_vol_found = spm_found;

        if spm_found
            spm_write_vol(V, data);
        else
            error('spm_write_vol not found. Cannot create synthetic NIfTI in MATLAB sandbox.');
        end

        if ~exist(input_nii, 'file')
            error('Failed to create synthetic input NIfTI.');
        end

        result.metrics.read_write_test_attempted = false;
        result.metrics.read_write_test_success = false;
        result.metrics.used_function_family = '';

        if ~isempty(y_read_path) && ~isempty(y_write_path)
            result.metrics.read_write_test_attempted = true;
            result.metrics.used_function_family = 'y_Read_y_Write';

            try
                [Data, Header] = y_Read(input_nii);
                y_Write(Data, Header, output_nii);
                result.metrics.read_write_test_success = exist(output_nii, 'file') == 2;
            catch ME
                result.warnings{end+1} = ['y_Read/y_Write smoke test failed: ', ME.message];
            end

        elseif ~isempty(rest_read_path) && ~isempty(rest_write_path)
            result.metrics.read_write_test_attempted = true;
            result.metrics.used_function_family = 'rest_readfile_rest_writefile';

            try
                [Data, Header] = rest_readfile(input_nii);
                rest_writefile(Data, output_nii, Header);
                result.metrics.read_write_test_success = exist(output_nii, 'file') == 2;
            catch ME
                result.warnings{end+1} = ['rest_readfile/rest_writefile smoke test failed: ', ME.message];
            end

        else
            result.warnings{end+1} = 'No supported DPABI/REST read-write function pair found. Smoke run only verified addpath and synthetic NIfTI creation.';
        end

        if ~exist(output_nii, 'file')
            % Safe fallback: copy synthetic input to output using SPM write, so downstream audit can see an output.
            Vout = V;
            Vout.fname = output_nii;
            spm_write_vol(Vout, data);
            result.warnings{end+1} = 'Used SPM fallback to create output_synthetic.nii.';
        end

        if ~exist(output_nii, 'file')
            error('Sandbox output NIfTI was not produced.');
        end

        result.outputs{end+1} = input_nii;
        result.outputs{end+1} = output_nii;
        result.metrics.input_exists = exist(input_nii, 'file') == 2;
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
3. 创建 backend/app/tools/dpabi_sandbox_runner.py

创建文件：

backend/app/tools/dpabi_sandbox_runner.py

目标：实现 approved DPABI sandbox smoke run。

提供函数：

run_dpabi_sandbox_smoke(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool,
    approved_by: str = "local-user",
    matlab_script_dir: str = "./matlab",
) -> dict

要求：

如果 approved=false：
不运行 MATLAB
返回 ok=false
errors 说明需要 approval
检查：
work/dpabi/dpabi_run_plan.json 是否存在
run_plan.requires_approval == true
run_plan.approved == false 可以接受，因为本次 approval 是 sandbox-level approval
run_plan.execution_allowed == false 可以接受，因为本次不是 full DPABI execution
写 approval record：
work/dpabi/approvals/dpabi_sandbox_smoke_approval.json
调用 MATLAB 脚本：
matlab/dpabi_sandbox_smoke_run.m
输出：
work/dpabi/sandbox/dpabi_sandbox_smoke_result.json
logs/dpabi_sandbox_smoke_stdout.log
logs/dpabi_sandbox_smoke_stderr.log
写 audit JSON：
work/dpabi/audit/dpabi_sandbox_execution_audit.json
写 audit Markdown：
reports/dpabi/dpabi_sandbox_execution_audit.md
不使用 shell=True。
不运行 DPARSF_run。
不运行 DPARSFA_run。
不读取 rawdata。

参考实现：

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_dpabi_sandbox_smoke(
    matlab_command: str,
    dpabi_dir: str,
    work_dir: str,
    log_dir: str,
    approved: bool,
    approved_by: str = "local-user",
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    if not approved:
        return {
            "ok": False,
            "node_id": "dpabi_sandbox_smoke_run",
            "backend": "matlab-dpabi",
            "outputs": [],
            "errors": ["DPABI sandbox smoke run requires approved=true."],
            "warnings": [],
        }

    dpabi_work = Path(work_dir) / "dpabi"
    sandbox_dir = dpabi_work / "sandbox"
    approvals_dir = dpabi_work / "approvals"
    audit_dir = dpabi_work / "audit"
    report_dir = Path("reports") / "dpabi"
    log_path = Path(log_dir)

    sandbox_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    log_path.mkdir(parents=True, exist_ok=True)

    run_plan_path = dpabi_work / "dpabi_run_plan.json"
    run_plan = _read_json(run_plan_path)

    if not run_plan:
        return {
            "ok": False,
            "node_id": "dpabi_sandbox_smoke_run",
            "backend": "matlab-dpabi",
            "outputs": [],
            "errors": [f"Missing DPABI run plan: {run_plan_path}"],
            "warnings": [],
        }

    approval_record = {
        "approved": True,
        "approved_by": approved_by,
        "approved_at": _now_iso(),
        "execution_type": "dpabi_sandbox_smoke_run",
        "full_dpabi_execution": False,
        "dpabi_gui_called": False,
        "dparsf_run_called": False,
        "rawdata_modified": False,
        "files_deleted": False,
        "run_plan_path": str(run_plan_path),
    }

    approval_path = approvals_dir / "dpabi_sandbox_smoke_approval.json"
    approval_path.write_text(
        json.dumps(approval_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result_json = sandbox_dir / "dpabi_sandbox_smoke_result.json"
    stdout_log = log_path / "dpabi_sandbox_smoke_stdout.log"
    stderr_log = log_path / "dpabi_sandbox_smoke_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())
    dpabi_abs = str(Path(dpabi_dir).resolve())
    sandbox_abs = str(sandbox_dir.resolve())
    result_abs = str(result_json.resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"dpabi_sandbox_smoke_run('{_matlab_quote(dpabi_abs)}', "
        f"'{_matlab_quote(sandbox_abs)}', "
        f"'{_matlab_quote(result_abs)}'); "
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
                "errors": [f"Failed to parse sandbox smoke result JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["DPABI sandbox smoke run did not produce result JSON."],
        }

    data["node_id"] = "dpabi_sandbox_smoke_run"
    data["backend"] = "matlab-dpabi"
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
        "execution_type": "dpabi_sandbox_smoke_run",
        "full_dpabi_execution": False,
        "dpabi_gui_called": False,
        "dparsf_run_called": False,
        "rawdata_modified": False,
        "files_deleted": False,
        "approval_record": str(approval_path),
        "run_plan_path": str(run_plan_path),
        "result_json": str(result_json),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "returncode": completed.returncode,
        "errors": data.get("errors", []),
        "warnings": data.get("warnings", []),
        "metrics": data.get("metrics", {}),
    }

    audit_json = audit_dir / "dpabi_sandbox_execution_audit.json"
    audit_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    audit_md = report_dir / "dpabi_sandbox_execution_audit.md"
    lines = []
    lines.append("# DPABI Sandbox Execution Audit")
    lines.append("")
    lines.append(f"- OK: {audit['ok']}")
    lines.append(f"- Execution type: {audit['execution_type']}")
    lines.append(f"- Full DPABI execution: {audit['full_dpabi_execution']}")
    lines.append(f"- DPABI GUI called: {audit['dpabi_gui_called']}")
    lines.append(f"- DPARSF_run called: {audit['dparsf_run_called']}")
    lines.append(f"- Rawdata modified: {audit['rawdata_modified']}")
    lines.append(f"- Files deleted: {audit['files_deleted']}")
    lines.append(f"- Return code: {audit['returncode']}")
    lines.append(f"- Result JSON: `{result_json}`")
    lines.append(f"- Approval record: `{approval_path}`")
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
    lines.append("This was a sandbox smoke run only. It did not run full DPABI preprocessing.")

    audit_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    outputs = list(data.get("outputs", []))
    outputs.extend([str(result_json), str(approval_path), str(audit_json), str(audit_md)])

    data["outputs"] = outputs
    data["audit_json"] = str(audit_json)
    data["audit_report"] = str(audit_md)

    return data
4. 修改 backend/app/runtime/node_registry.py

新增节点：

dpabi_sandbox_smoke_run

新增导入：

from backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke

新增 runner：

def run_dpabi_sandbox_smoke_run_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    approved = bool(node.params.get("approved", False))
    approved_by = node.params.get("approved_by", "local-user")

    result = run_dpabi_sandbox_smoke(
        matlab_command=context.matlab_command,
        dpabi_dir=context.dpabi_dir,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        approved=approved,
        approved_by=approved_by,
        matlab_script_dir="./matlab",
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_sandbox_smoke_run": run_dpabi_sandbox_smoke_run_node,
5. 创建 examples/pipeline_dpabi_sandbox_smoke.yaml

创建文件：

examples/pipeline_dpabi_sandbox_smoke.yaml

内容：

pipeline_id: dpabi_sandbox_smoke_pipeline
version: "0.1.0"
modality: integration-test
description: "Generate DPABI run plan and execute an approved DPABI sandbox smoke run without full preprocessing."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_sandbox_smoke_001"
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

  - id: dpabi_sandbox_smoke_run
    name: Approved DPABI Sandbox Smoke Run
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - dpabi_run_plan
    inputs:
      - "./work/dpabi/dpabi_run_plan.json"
    outputs:
      - "./work/dpabi/sandbox/dpabi_sandbox_smoke_result.json"
      - "./work/dpabi/approvals/dpabi_sandbox_smoke_approval.json"
      - "./work/dpabi/audit/dpabi_sandbox_execution_audit.json"
      - "./reports/dpabi/dpabi_sandbox_execution_audit.md"
    params:
      approved: false
      approved_by: "local-user"
    parallel_level: project
    gpu_supported: false
    cache: false

注意：这个 pipeline 默认 approved: false，因此直接运行时应该安全失败。真正 approved run 通过 CLI/API 传入 approved=true，或者复制该 pipeline 并明确改成 approved=true 后再运行。

6. 创建 backend/app/tools/run_dpabi_sandbox_smoke_cli.py

创建文件：

backend/app/tools/run_dpabi_sandbox_smoke_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_dpabi_sandbox_smoke.yaml
默认不 approved。
如果传入 --approve，需要临时生成 approved pipeline 副本：
work/dpabi/approved_pipeline_dpabi_sandbox_smoke.yaml

把 dpabi_sandbox_smoke_run.params.approved 改为 true。

调用 run_pipeline。
打印 summary。
返回码：
SUCCESS 返回 0
INVALID 返回 1
FAILED / PARTIAL 返回 2

参考实现：

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
        if node.get("id") == "dpabi_sandbox_smoke_run":
            node.setdefault("params", {})
            node["params"]["approved"] = True
            node["params"]["approved_by"] = "local-user"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_dpabi_sandbox_smoke.yaml")

    if approved:
        pipeline = _make_approved_pipeline_copy(
            source=pipeline,
            target=Path("work/dpabi/approved_pipeline_dpabi_sandbox_smoke.yaml"),
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

class DpabiSandboxSmokeRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    approved: bool = Field(default=False)
    approved_by: str = Field(default="local-user")
8. 修改 backend/app/api/routes.py

新增 API：

POST /api/dpabi/sandbox-smoke
GET  /api/dpabi/sandbox-smoke

新增导入：

from backend.app.api.models import DpabiSandboxSmokeRequest
from backend.app.runtime.agent_plan import _load_project_config
from backend.app.tools.dpabi_sandbox_runner import run_dpabi_sandbox_smoke

新增路由：

@router.post("/api/dpabi/sandbox-smoke")
def api_run_dpabi_sandbox_smoke(request: DpabiSandboxSmokeRequest) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="DPABI sandbox smoke run requires approved=true.",
        )

    try:
        project_config = _load_project_config(request.project_config_path)
        runtime = project_config.get("runtime", {})
        third_party = project_config.get("third_party", {})

        result = run_dpabi_sandbox_smoke(
            matlab_command=runtime.get("matlab_command", "matlab"),
            dpabi_dir=third_party.get("dpabi_dir", "./third_party/DPABI_V8.2_240510"),
            work_dir=runtime.get("work_dir", "./work"),
            log_dir=runtime.get("log_dir", "./logs"),
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


@router.get("/api/dpabi/sandbox-smoke")
def api_get_dpabi_sandbox_smoke() -> dict[str, Any]:
    base = Path("work") / "dpabi"
    report_base = Path("reports") / "dpabi"

    return {
        "ok": True,
        "sandbox_result": _read_json_if_exists(base / "sandbox" / "dpabi_sandbox_smoke_result.json"),
        "approval_record": _read_json_if_exists(base / "approvals" / "dpabi_sandbox_smoke_approval.json"),
        "execution_audit": _read_json_if_exists(base / "audit" / "dpabi_sandbox_execution_audit.json"),
        "execution_audit_report": _read_text_if_exists(report_base / "dpabi_sandbox_execution_audit.md"),
    }

同时修改已有 /api/dpabi/capabilities 和 /api/reports/dpabi，让它们也返回 sandbox 结果：

/api/dpabi/capabilities 增加：

"sandbox_result": _read_json_if_exists(base / "sandbox" / "dpabi_sandbox_smoke_result.json"),
"sandbox_approval": _read_json_if_exists(base / "approvals" / "dpabi_sandbox_smoke_approval.json"),
"sandbox_audit": _read_json_if_exists(base / "audit" / "dpabi_sandbox_execution_audit.json"),

/api/reports/dpabi 增加：

"sandbox_audit_report": _read_text_if_exists(base / "dpabi_sandbox_execution_audit.md"),
9. 修改 frontend/src/api.ts

新增：

export async function runDpabiSandboxSmoke(
  baseUrl: string,
  payload: {
    project_config_path: string;
    approved: boolean;
    approved_by: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/sandbox-smoke",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getDpabiSandboxSmoke(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/sandbox-smoke"
  );
}
10. 修改 frontend/src/components/DpabiPanel.tsx

在 DPABI Panel 中增加 Approved Sandbox Smoke Run 区域。

新增导入：

import { runDpabiSandboxSmoke, getDpabiSandboxSmoke } from "../api";

新增 state：

const [sandboxResult, setSandboxResult] = useState<Record<string, unknown> | null>(null);
const [sandboxStatus, setSandboxStatus] = useState("IDLE");

新增函数：

async function handleRunSandboxSmoke() {
  const confirmed = window.confirm(
    "确认运行 DPABI sandbox smoke test？这会启动 MATLAB，但不会运行完整 DPABI/DPARSF，不会读取 rawdata。"
  );

  if (!confirmed) return;

  setSandboxStatus("RUNNING");
  setError("");

  try {
    const result = await runDpabiSandboxSmoke(baseUrl, {
      project_config_path: "examples/project_config_dataset.yaml",
      approved: true,
      approved_by: "local-user"
    });
    setSandboxResult(result);
    setSandboxStatus(result.ok ? "SUCCESS" : "FAILED");
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
    setSandboxStatus("ERROR");
  }
}


async function handleLoadSandboxSmoke() {
  setError("");

  try {
    const result = await getDpabiSandboxSmoke(baseUrl);
    setSandboxResult(result);
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
  }
}

在 JSX 中增加：

<h3>Approved DPABI Sandbox Smoke Run</h3>
<div className="row">
  <button className="dangerButton" onClick={handleRunSandboxSmoke}>
    批准并运行 Sandbox Smoke
  </button>
  <button onClick={handleLoadSandboxSmoke}>
    加载 Sandbox Smoke 结果
  </button>
  <StatusBadge status={sandboxStatus} />
</div>

<JsonBlock value={sandboxResult} emptyText="尚未运行 sandbox smoke" />

<h3>Sandbox Result</h3>
<JsonBlock value={capabilities?.sandbox_result} emptyText="暂无 sandbox result" />

<h3>Sandbox Approval</h3>
<JsonBlock value={capabilities?.sandbox_approval} emptyText="暂无 sandbox approval" />

<h3>Sandbox Audit</h3>
<JsonBlock value={capabilities?.sandbox_audit} emptyText="暂无 sandbox audit" />

<h3>Sandbox Audit Report</h3>
<TextViewer
  text={
    typeof report?.sandbox_audit_report === "string"
      ? report.sandbox_audit_report
      : null
  }
  emptyText="暂无 sandbox audit report"
/>

保留原来的 DPABI capability、preflight、run plan 内容。

11. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/dpabi/sandbox-smoke")

不要在 smoke test 中调用 POST /api/dpabi/sandbox-smoke，避免误启动 MATLAB。

12. 更新 README.md

追加第二十步说明：

## Step 20: DPABI Approved Sandbox Smoke Run

This step adds an approved DPABI sandbox smoke run.

It does not run full DPABI preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_dpabi_sandbox_smoke_cli

This should fail safely because approval is missing.

Run with approval
python -m backend.app.tools.run_dpabi_sandbox_smoke_cli --approve

Expected outputs:

work/dpabi/sandbox/input_synthetic.nii
work/dpabi/sandbox/output_synthetic.nii
work/dpabi/sandbox/dpabi_sandbox_smoke_result.json
work/dpabi/approvals/dpabi_sandbox_smoke_approval.json
work/dpabi/audit/dpabi_sandbox_execution_audit.json
reports/dpabi/dpabi_sandbox_execution_audit.md
logs/dpabi_sandbox_smoke_stdout.log
logs/dpabi_sandbox_smoke_stderr.log
API

Run approved sandbox smoke:

curl -X POST http://127.0.0.1:8000/api/dpabi/sandbox-smoke \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "approved": true,
    "approved_by": "local-user"
  }'

Read sandbox result:

curl http://127.0.0.1:8000/api/dpabi/sandbox-smoke
Frontend

Use the DPABI Capability / Wrapper Scaffold panel.

Click:

批准并运行 Sandbox Smoke
Safety

This step does not:

run DPARSF_run
run DPARSFA_run
call DPABI GUI
read rawdata
modify rawdata
modify DPABI source
delete files

---

## 13. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_execution_sandbox_spec.md
matlab/dpabi_sandbox_smoke_run.m
backend/app/tools/dpabi_sandbox_runner.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_sandbox_smoke.yaml
backend/app/tools/run_dpabi_sandbox_smoke_cli.py
backend/app/api/models.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/DpabiPanel.tsx
README.md

先运行不带 approval 的命令：

python -m backend.app.tools.run_dpabi_sandbox_smoke_cli

应该安全失败，不能运行 sandbox smoke。

然后运行：

python -m backend.app.tools.run_dpabi_sandbox_smoke_cli --approve

成功后应生成：

work/dpabi/sandbox/input_synthetic.nii
work/dpabi/sandbox/output_synthetic.nii
work/dpabi/sandbox/dpabi_sandbox_smoke_result.json
work/dpabi/approvals/dpabi_sandbox_smoke_approval.json
work/dpabi/audit/dpabi_sandbox_execution_audit.json
reports/dpabi/dpabi_sandbox_execution_audit.md
logs/dpabi_sandbox_smoke_stdout.log
logs/dpabi_sandbox_smoke_stderr.log
work/pipeline_runs/run_dpabi_sandbox_smoke_001/summary.json

其中：

work/dpabi/approvals/dpabi_sandbox_smoke_approval.json

应包含：

{
  "approved": true,
  "execution_type": "dpabi_sandbox_smoke_run",
  "full_dpabi_execution": false,
  "rawdata_modified": false,
  "files_deleted": false
}

其中：

work/dpabi/audit/dpabi_sandbox_execution_audit.json

应包含：

{
  "full_dpabi_execution": false,
  "dpabi_gui_called": false,
  "dparsf_run_called": false,
  "rawdata_modified": false,
  "files_deleted": false
}

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/sandbox-smoke

未批准 POST 应失败：

curl -X POST http://127.0.0.1:8000/api/dpabi/sandbox-smoke \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'

应返回 403 或清晰错误。

批准 POST 应运行：

curl -X POST http://127.0.0.1:8000/api/dpabi/sandbox-smoke \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "approved_by": "local-user"}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

DPABI Panel 显示 Approved Sandbox Smoke Run 区域。
点击运行前有 confirm 弹窗。
approved 后调用后端运行 sandbox smoke。
显示 sandbox result。
显示 approval record。
显示 execution audit。
显示 sandbox audit report。
不运行完整 DPABI preprocessing。
不调用 DPABI GUI。
不读取或修改 rawdata。
14. 重要限制

本步骤只做 DPABI approved sandbox smoke run。

不要实现：

DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
真实医学影像预处理
修改 rawdata
修改 DPABI 源码
删除文件
并行 DPABI
GPU DPABI
任务取消
WebSocket 实时日志

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行不带 approval 的安全失败测试
如何运行 approved sandbox smoke
sandbox smoke 实际验证了什么
approval record 和 audit 记录了什么
为什么这一步仍然不是完整 DPABI pipeline execution

'''
Step 20：DPABI Approved Sandbox Smoke Run + Execution Audit 闭环

## 核心目标
在真正执行完整 DPABI 预处理之前，建立一个 受控的沙箱环境 来验证系统能够安全调用 DPABI 的 MATLAB 函数，同时不接触真实数据。

## 主要功能
### 1. 审批门控（Approval Gate）
- 必须显式设置 approved=true 才能运行
- 如果 approved=false ，直接返回错误，不执行任何 MATLAB 代码
- 记录审批人、时间戳、执行类型到审批记录文件
### 2. 沙箱环境（Sandbox Environment）
- 在 work/dpabi/sandbox/ 下创建隔离目录
- 生成 合成 NIfTI 数据 （8×8×8 随机数据）用于测试
- 绝不读取或修改真实 rawdata
### 3. DPABI 函数探测与测试
- 将 DPABI 添加到 MATLAB 路径： addpath(genpath(dpabi_dir))
- 探测安全 I/O 函数：
  - 首选： y_Read / y_Write
  - 备选： rest_readfile / rest_writefile
- 如果 DPABI 函数不可用，使用 SPM 作为 fallback
- 尝试读写合成 NIfTI，验证函数可用性
### 4. 执行审计（Execution Audit）
- 生成 JSON 审计文件，记录所有执行细节
- 生成 Markdown 报告，供人工审查
- 记录安全标志：GUI 是否被调用、rawdata 是否被修改等
## 关键输出文件
文件 说明 work/dpabi/sandbox/input_synthetic.nii 合成输入 NIfTI work/dpabi/sandbox/output_synthetic.nii 合成输出 NIfTI work/dpabi/approvals/dpabi_sandbox_smoke_approval.json 审批记录 work/dpabi/audit/dpabi_sandbox_execution_audit.json 执行审计 reports/dpabi/dpabi_sandbox_execution_audit.md 审计报告 logs/dpabi_sandbox_smoke_*.log MATLAB 日志

## 安全约束
- ✅ 需要显式审批
- ❌ 不读取真实 rawdata
- ❌ 不修改真实 rawdata
- ❌ 不调用 DPABI GUI
- ❌ 不调用 DPARSF_run / DPARSFA_run
- ❌ 不修改 DPABI 源码
- ❌ 不删除文件
## 这一步不做的事
- ❌ 不运行完整 DPABI 预处理
- ❌ 不处理真实医学影像数据
- ❌ 不生成实际的预处理结果
## 意义
这是 DPABI 执行链的 最后安全验证步骤 ，确保：

1. MATLAB 能正常启动
2. DPABI 路径配置正确
3. 核心 I/O 函数可用
4. 审批和审计机制正常工作
通过 sandbox smoke run 验证后，系统才能安全地进入下一步： 完整 DPABI 预处理执行 。
'''