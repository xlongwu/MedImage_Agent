你是我的工程搭建助手。当前项目是一个医学影像预处理 Agent 平台，目标是后续基于 Hermes Agent 和 Claude Code Agent 的思想，构建可视化、可复现、可并行、可 GPU 扩展的医学影像预处理与数据集评估系统。

当前根目录中已有这些内容：

- DPABI_V8.2_240510/
- spm12/
- Claude Code 源码解读（二）.pdf
- Hermes Agent 架构解析.pdf
- MedImage_Agent.md

现在只完成第一步：把项目从“资料堆”整理成“可运行工程骨架”，并打通 MATLAB / SPM / DPABI 环境检查闭环。

不要实现 UI。
不要实现完整 Agent Runtime。
不要实现预处理 pipeline。
不要修改 SPM 或 DPABI 源码。
不要做 GPU。
不要做多 Agent 协作。
不要引入复杂依赖。

请按以下要求执行。

---

## 1. 整理目录结构

请创建如下目录：

```text
third_party/
docs/
specs/
backend/app/tools/
backend/app/runtime/
backend/app/agents/
backend/app/schemas/
matlab/
examples/
work/
logs/
reports/

然后移动文件：

DPABI_V8.2_240510/                 -> third_party/DPABI_V8.2_240510/
spm12/                             -> third_party/spm12/
Claude Code 源码解读（二）.pdf       -> docs/
Hermes Agent 架构解析.pdf           -> docs/
MedImage_Agent.md                  -> docs/

如果移动可能导致问题，可以先复制，但最终项目根目录不要混放第三方源码和项目代码。

2. 创建 examples/project_config.yaml

内容如下：

project:
  name: medimage_agent_mvp
  root_dir: "."

third_party:
  spm_dir: "./third_party/spm12"
  dpabi_dir: "./third_party/DPABI_V8.2_240510"

runtime:
  matlab_command: "matlab"
  work_dir: "./work"
  log_dir: "./logs"
  report_dir: "./reports"

safety:
  rawdata_readonly: true
  allow_overwrite_derivatives: false
  require_confirmation_for_matlab_run: true

注意：后续所有路径都应从这个配置读取，不要在代码里硬编码 SPM/DPABI 路径。

3. 创建 matlab/check_environment.m

请创建 MATLAB 脚本：

matlab/check_environment.m

功能要求：

接收三个参数：
spm_dir
dpabi_dir
output_json
检查：
MATLAB version
spm_dir 是否存在
dpabi_dir 是否存在
addpath(spm_dir) 后 which('spm') 是否可用
addpath(genpath(dpabi_dir)) 后 which('DPABI') 是否可用
将检查结果写入 output_json，格式为 JSON。
输出字段至少包含：
ok: true/false
matlab_version
spm_path
dpabi_path
errors: string array
不要运行任何预处理。
不要修改 SPM / DPABI 源码。
不要写入 rawdata 或 derivatives。

建议实现如下，但可以根据 MATLAB 版本兼容性做小调整：

function check_environment(spm_dir, dpabi_dir, output_json)
    result = struct();
    result.ok = true;
    result.errors = {};
    result.matlab_version = version;
    result.spm_path = '';
    result.dpabi_path = '';

    if ~exist(spm_dir, 'dir')
        result.ok = false;
        result.errors{end+1} = ['SPM directory not found: ', spm_dir];
    else
        addpath(spm_dir);
        try
            spm_path = which('spm');
            result.spm_path = spm_path;
            if isempty(spm_path)
                result.ok = false;
                result.errors{end+1} = 'SPM function not found after addpath.';
            end
        catch ME
            result.ok = false;
            result.errors{end+1} = ['SPM check failed: ', ME.message];
        end
    end

    if ~exist(dpabi_dir, 'dir')
        result.ok = false;
        result.errors{end+1} = ['DPABI directory not found: ', dpabi_dir];
    else
        addpath(genpath(dpabi_dir));
        try
            dpabi_main = which('DPABI');
            result.dpabi_path = dpabi_main;
            if isempty(dpabi_main)
                result.errors{end+1} = 'DPABI function not found after addpath. This may be acceptable if DPABI entry file has a different name.';
            end
        catch ME
            result.ok = false;
            result.errors{end+1} = ['DPABI check failed: ', ME.message];
        end
    end

    fid = fopen(output_json, 'w');
    if fid == -1
        error(['Cannot open output JSON for writing: ', output_json]);
    end
    fwrite(fid, jsonencode(result), 'char');
    fclose(fid);
end
4. 创建 backend/app/tools/matlab_runner.py

请创建 Python 文件：

backend/app/tools/matlab_runner.py

功能要求：

提供函数：
run_matlab_check(
    matlab_command: str,
    spm_dir: str,
    dpabi_dir: str,
    output_json: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict
使用 subprocess 调用 MATLAB：
matlab -nodisplay -nosplash -r "..."
执行 MATLAB 函数 check_environment。
保存 stdout 到：
logs/matlab_check_stdout.log
保存 stderr 到：
logs/matlab_check_stderr.log
读取 output_json 并返回结构化 dict。
如果 output_json 不存在，也要返回结构化错误。
不要用 shell=True。
注意路径中的反斜杠和单引号转义。
代码应尽量健壮、简洁，有类型标注。

参考实现：

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def run_matlab_check(
    matlab_command: str,
    spm_dir: str,
    dpabi_dir: str,
    output_json: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / "matlab_check_stdout.log"
    stderr_log = log_path / "matlab_check_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())
    spm_abs = str(Path(spm_dir).resolve())
    dpabi_abs = str(Path(dpabi_dir).resolve())
    output_abs = str(output_path.resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"check_environment('{_matlab_quote(spm_abs)}', "
        f"'{_matlab_quote(dpabi_abs)}', "
        f"'{_matlab_quote(output_abs)}'); "
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

    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            data = {
                "ok": False,
                "errors": [f"Failed to parse MATLAB output JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["MATLAB did not produce output JSON."],
        }

    data["returncode"] = completed.returncode
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["output_json"] = str(output_path)

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    return data
5. 创建 backend/app/tools/check_env_cli.py

请创建一个最小 CLI，方便我测试环境：

backend/app/tools/check_env_cli.py

功能：

读取 YAML 配置文件，默认路径：
examples/project_config.yaml
调用 run_matlab_check。
输出检查结果到终端。
同时生成：
work/environment_check.json
logs/matlab_check_stdout.log
logs/matlab_check_stderr.log

可以使用 PyYAML。如果没有 PyYAML，请在报错中提示安装：

pip install pyyaml

参考结构：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.tools.matlab_runner import run_matlab_check


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("Missing dependency: PyYAML. Install with: pip install pyyaml")
        return 1

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config.yaml")
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    matlab_command = config["runtime"]["matlab_command"]
    spm_dir = config["third_party"]["spm_dir"]
    dpabi_dir = config["third_party"]["dpabi_dir"]
    work_dir = config["runtime"]["work_dir"]
    log_dir = config["runtime"]["log_dir"]

    output_json = str(Path(work_dir) / "environment_check.json")

    result = run_matlab_check(
        matlab_command=matlab_command,
        spm_dir=spm_dir,
        dpabi_dir=dpabi_dir,
        output_json=output_json,
        log_dir=log_dir,
        matlab_script_dir="./matlab",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
6. 创建 specs/run_state_machine.md

内容：

# Run State Machine

This document defines the minimal execution state model for MedImage Agent.

## Node Status

- PENDING: node is created but not ready
- READY: all inputs are available
- RUNNING: node is executing
- SUCCESS: node completed and outputs validated
- FAILED: node failed
- SKIPPED: node skipped by rule or user
- CACHED: outputs reused from previous run
- RETRYING: node is being retried
- NEEDS_REVIEW: automatic QC is uncertain
- EXCLUDED: subject or node is excluded from downstream analysis

## Minimal State Record

```json
{
  "run_id": "run_001",
  "subject": "project",
  "node": "environment_check",
  "status": "SUCCESS",
  "started_at": "2026-05-01T10:00:00",
  "ended_at": "2026-05-01T10:01:00",
  "log_path": "outputs/logs/matlab_check_stdout.log",
  "outputs": ["outputs/work/environment_check.json"],
  "errors": []
}
Rules
Every executable step must create a state record.
FAILED nodes must preserve logs.
SUCCESS nodes must validate required outputs.
CACHED nodes must record the source cache entry.
NEEDS_REVIEW must not be treated as SUCCESS automatically.

---

## 7. 创建 specs/tool_permission_spec.md

内容：

```markdown
# Tool Permission Spec

Every tool must declare its permission and safety attributes.

## Required Fields

- name
- read_only
- writes_files
- destructive
- requires_confirmation
- parallel_safe
- allowed_read_paths
- allowed_write_paths

## Risk Principles

Risk is determined by:

1. Reversibility: can the action be undone?
2. Blast radius: does the action affect only local workspace or shared systems?

## Example

```yaml
name: matlab.check_environment
read_only: false
writes_files: true
destructive: false
requires_confirmation: false
parallel_safe: false
allowed_read_paths:
  - third_party/
  - matlab/
  - examples/
allowed_write_paths:
  - work/
  - logs/
Default Safety Rules
rawdata/ is read-only.
sourcedata/ is read-only.
derivatives/ is writable only with explicit configuration.
work/, logs/, reports/ are writable.
Deleting files requires confirmation.
Overwriting derivatives requires confirmation.
Uploading medical imaging data to external services is forbidden unless explicitly approved and de-identified.

---

## 8. 创建 README.md

README 写明当前项目的第一步目标和测试方法：

```markdown
# MedImage Agent

A visual and agent-based medical imaging preprocessing framework.

## Current Stage

MVP Step 1: environment check loop.

This stage only verifies that MATLAB, SPM, and DPABI can be located and called from the project.

## Directory Layout

- third_party/: SPM and DPABI source code
- docs/: architecture documents
- specs/: system specifications
- backend/: Python backend code
- matlab/: MATLAB helper scripts
- examples/: example configs
- work/: generated intermediate files
- logs/: execution logs
- reports/: generated reports

## Environment Check

Install Python dependency:

```bash
pip install pyyaml

Run:

python -m backend.app.tools.check_env_cli examples/project_config.yaml

Expected outputs:

work/environment_check.json
logs/matlab_check_stdout.log
logs/matlab_check_stderr.log
Notes

This step does not run preprocessing.
This step does not modify SPM or DPABI.
This step does not implement UI or Agent Runtime.


---

## 9. 验收标准

完成后，请确认：

1. 根目录不再直接混放 SPM/DPABI 源码。
2. 存在：

```text
third_party/spm12/
third_party/DPABI_V8.2_240510/
docs/MedImage_Agent.md
examples/project_config.yaml
matlab/check_environment.m
backend/app/tools/matlab_runner.py
backend/app/tools/check_env_cli.py
specs/run_state_machine.md
specs/tool_permission_spec.md
README.md
可以运行：
python -m backend.app.tools.check_env_cli examples/project_config.yaml
运行后生成：
work/environment_check.json
logs/matlab_check_stdout.log
logs/matlab_check_stderr.log
如果 MATLAB 不在 PATH 中，程序应该返回清晰错误，而不是崩溃。
如果 SPM 或 DPABI 路径错误，environment_check.json 中应该有 ok=false 和 errors 字段。

请现在执行这个第一步，只做上述内容。不要扩展其它功能。



'''
这一步主要完成的是 将项目从"资料堆"整理成"可运行工程骨架" ，并打通 MATLAB / SPM / DPABI 环境检查闭环 。

具体来说，完成了以下工作：

## 1. 目录结构规范化
把原来混放在根目录的第三方源码（SPM、DPABI）和文档，整理到规范的目录结构中：

- third_party/ - 存放 SPM12 和 DPABI_V8.2 源码
- docs/ - 存放架构文档和 PDF
- backend/ - Python 后端代码
- matlab/ - MATLAB 辅助脚本
- 其他标准目录（examples/, work/, logs/, reports/, specs/）
## 2. 打通环境检查闭环
构建了从 Python 调用 MATLAB 检查环境的完整链路：

```
┌─────────────────────────────────────────────────────────────┐
│  Python CLI                                                  │
│  backend/app/tools/check_env_cli.py                         │
│     ↓ 读取配置                                                │
│  examples/project_config.yaml                               │
│     ↓ 调用                                                    │
│  backend/app/tools/matlab_runner.py                         │
│     ↓ subprocess 调用 MATLAB                                  │
│  matlab -batch "check_environment(...)"                     │
│     ↓                                                         │
│  matlab/check_environment.m                                  │
│     ↓ 检查并写入结果                                          │
│  work/environment_check.json                                 │
└─────────────────────────────────────────────────────────────┘
```
## 3. 核心交付物
组件 作用 check_env_cli.py 命令行入口，读取配置并执行检查 matlab_runner.py 封装 MATLAB 调用，处理跨平台差异（Windows 用 -batch ，Linux/Mac 用 -r ） check_environment.m MATLAB 脚本，检查 SPM/DPABI 是否能正常加载 project_config.yaml 统一配置，所有路径从这里读取，不硬编码

## 4. 验收标准达成
✅ 根目录不再混放第三方源码
 ✅ 可以运行 python -m backend.app.tools.check_env_cli examples/project_config.yaml
 ✅ 生成 work/environment_check.json 、 logs/matlab_check_stdout.log 、 logs/matlab_check_stderr.log
 ✅ 如果 MATLAB 不在 PATH 或路径错误，会返回清晰的错误信息（ ok: false + errors 数组）

这一步 不做 的事情：

- 不实现 UI
- 不实现完整 Agent Runtime
- 不实现预处理 pipeline
- 不修改 SPM/DPABI 源码
- 不做 GPU 支持
- 不做多 Agent 协作
这只是 第一步：环境检查 ，为后续的可视化预处理流程和 Agent 系统打下基础。
'''