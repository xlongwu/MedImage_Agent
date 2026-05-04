你是我的工程搭建助手。第一步已经完成：项目已经整理成工程骨架，并且可以通过 Python 调用 MATLAB，完成 MATLAB / SPM / DPABI 的环境检查。

现在开始第二步。

第二步目标：实现“单节点执行闭环”。

也就是说，先不要做完整预处理 pipeline，不要做 UI，不要做 Agent Runtime，也不要做多 Agent。现在只实现一个最小可执行节点：

- 读取 pipeline 配置
- 执行一个 SPM smoke test 节点
- 生成节点状态文件
- 生成日志
- 生成 JSON 结果
- 验证输出文件存在
- 为后续 pipeline DAG / Run Monitor / Agent Runtime 打基础

请严格控制范围。

不要实现 UI。
不要实现完整 Agent Runtime。
不要实现多 Agent 协作。
不要实现 DPABI 完整 pipeline。
不要做 GPU。
不要处理真实医学影像数据。
不要修改 SPM / DPABI 源码。
不要写复杂数据库。
不要引入 Celery / Redis / FastAPI 服务。

本步骤只做最小的单节点执行系统。

---

## 1. 新增 specs/pipeline_schema.yaml

创建文件：

```text
specs/pipeline_schema.yaml

内容定义最小 pipeline schema：

pipeline_schema_version: "0.1.0"

required_fields:
  - pipeline_id
  - version
  - modality
  - nodes

node_required_fields:
  - id
  - name
  - agent
  - backend
  - inputs
  - outputs
  - params
  - parallel_level
  - gpu_supported
  - cache

node_status:
  - PENDING
  - READY
  - RUNNING
  - SUCCESS
  - FAILED
  - SKIPPED
  - CACHED
  - RETRYING
  - NEEDS_REVIEW
  - EXCLUDED

example_node:
  id: spm_smoke_test
  name: SPM Smoke Test
  agent: spm-runner
  backend: matlab-spm
  inputs: []
  outputs:
    - work/spm_smoke_test/result.json
    - work/spm_smoke_test/smoothed.nii
  params:
    image_shape: [20, 20, 20]
    smooth_fwhm: [4, 4, 4]
  parallel_level: project
  gpu_supported: false
  cache: false
2. 新增 specs/node_interface.md

创建文件：

specs/node_interface.md

内容：

# Node Interface

A pipeline node is the smallest executable unit in MedImage Agent.

## Responsibilities

Each node must:

1. Receive structured inputs and parameters.
2. Execute one clearly scoped operation.
3. Write outputs to work/, logs/, derivatives/, or reports/.
4. Write a node result JSON.
5. Write a node state JSON.
6. Preserve stdout and stderr logs.
7. Never modify rawdata/.
8. Never modify third_party/.

## Minimal Node Result

```json
{
  "ok": true,
  "node_id": "spm_smoke_test",
  "backend": "matlab-spm",
  "outputs": [
    "work/spm_smoke_test/smoothed.nii"
  ],
  "metrics": {},
  "errors": []
}
Minimal Node State
{
  "run_id": "run_001",
  "subject": "project",
  "node": "spm_smoke_test",
  "status": "SUCCESS",
  "started_at": "2026-05-01T10:00:00",
  "ended_at": "2026-05-01T10:01:00",
  "log_path": "logs/spm_smoke_test_stdout.log",
  "outputs": [
    "work/spm_smoke_test/result.json",
    "work/spm_smoke_test/smoothed.nii"
  ],
  "errors": []
}
Rules
A node with missing required outputs must be FAILED.
A node with MATLAB return code != 0 must be FAILED.
A node that produces expected outputs and valid result JSON can be SUCCESS.
A node must not silently succeed.

---

## 3. 新增 examples/pipeline_spm_smoke.yaml

创建文件：

```text
examples/pipeline_spm_smoke.yaml

内容：

pipeline_id: spm_smoke_pipeline
version: "0.1.0"
modality: test
description: "Minimal SPM smoke test pipeline using synthetic NIfTI data."

nodes:
  - id: spm_smoke_test
    name: SPM Smoke Test
    agent: spm-runner
    backend: matlab-spm
    inputs: []
    outputs:
      - "./work/spm_smoke_test/result.json"
      - "./work/spm_smoke_test/smoothed.nii"
    params:
      image_shape: [20, 20, 20]
      smooth_fwhm: [4, 4, 4]
    parallel_level: project
    gpu_supported: false
    cache: false
4. 新增 MATLAB 脚本 matlab/spm_smoke_test.m

创建文件：

matlab/spm_smoke_test.m

功能：

接收参数：
spm_dir
output_dir
output_json
添加 SPM 路径。
初始化 SPM。
在 output_dir 中生成一个 synthetic NIfTI：
input.nii
尺寸 20 x 20 x 20
float32
调用 SPM 的 spm_smooth：
输入 input.nii
输出 smoothed.nii
FWHM = [4 4 4]
检查 smoothed.nii 是否生成。
将结果写入 output_json。
不读取真实医学影像。
不写 rawdata。
不改 SPM 源码。

请实现为兼容性较好的 MATLAB 函数：

function spm_smoke_test(spm_dir, output_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_smoke_test';
    result.backend = 'matlab-spm';
    result.outputs = {};
    result.errors = {};
    result.metrics = struct();

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end

        addpath(spm_dir);

        try
            spm('defaults', 'fmri');
            spm_jobman('initcfg');
        catch ME
            result.errors{end+1} = ['SPM init warning: ', ME.message];
        end

        input_nii = fullfile(output_dir, 'input.nii');
        smoothed_nii = fullfile(output_dir, 'smoothed.nii');

        data = single(randn(20, 20, 20));

        V = struct();
        V.fname = input_nii;
        V.dim = size(data);
        V.dt = [16 0];
        V.mat = eye(4);
        V.pinfo = [1; 0; 0];
        V.descrip = 'Synthetic NIfTI for SPM smoke test';

        spm_write_vol(V, data);

        if ~exist(input_nii, 'file')
            error('Failed to create synthetic input NIfTI.');
        end

        spm_smooth(input_nii, smoothed_nii, [4 4 4]);

        if ~exist(smoothed_nii, 'file')
            error('SPM smoothing did not produce output NIfTI.');
        end

        result.outputs{end+1} = input_nii;
        result.outputs{end+1} = smoothed_nii;
        result.metrics.input_exists = exist(input_nii, 'file') == 2;
        result.metrics.smoothed_exists = exist(smoothed_nii, 'file') == 2;
        result.metrics.image_shape = [20 20 20];
        result.metrics.smooth_fwhm = [4 4 4];

    catch ME
        result.ok = false;
        result.errors{end+1} = getReport(ME, 'extended', 'hyperlinks', 'off');
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

如果某些 MATLAB 版本不支持 getReport(..., 'hyperlinks', 'off')，请做兼容处理。

5. 新增 backend/app/tools/spm_runner.py

创建文件：

backend/app/tools/spm_runner.py

功能：

提供函数：
run_spm_smoke_test(
    matlab_command: str,
    spm_dir: str,
    work_dir: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict
调用 MATLAB 执行 spm_smoke_test.m。
输出目录：
work/spm_smoke_test/
输出 JSON：
work/spm_smoke_test/result.json
日志：
logs/spm_smoke_test_stdout.log
logs/spm_smoke_test_stderr.log
返回结构化 dict。
如果 MATLAB 返回码非 0，返回 ok=false。
如果 expected outputs 缺失，返回 ok=false。
不要使用 shell=True。
路径使用 pathlib。
注意 MATLAB 字符串单引号转义。

参考实现结构：

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def run_spm_smoke_test(
    matlab_command: str,
    spm_dir: str,
    work_dir: str,
    log_dir: str,
    matlab_script_dir: str = "./matlab",
) -> dict[str, Any]:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    output_dir = Path(work_dir) / "spm_smoke_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    result_json = output_dir / "result.json"
    smoothed_nii = output_dir / "smoothed.nii"

    stdout_log = log_path / "spm_smoke_test_stdout.log"
    stderr_log = log_path / "spm_smoke_test_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())
    spm_abs = str(Path(spm_dir).resolve())
    output_dir_abs = str(output_dir.resolve())
    result_json_abs = str(result_json.resolve())

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_smoke_test('{_matlab_quote(spm_abs)}', "
        f"'{_matlab_quote(output_dir_abs)}', "
        f"'{_matlab_quote(result_json_abs)}'); "
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
                "errors": [f"Failed to parse SPM smoke test JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["SPM smoke test did not produce result.json."],
        }

    data["returncode"] = completed.returncode
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)
    data["expected_outputs"] = [str(smoothed_nii)]

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    if not smoothed_nii.exists():
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"Expected output not found: {smoothed_nii}")

    return data
6. 新增 backend/app/runtime/state_store.py

创建文件：

backend/app/runtime/state_store.py

功能：

提供函数：
now_iso()
write_node_state(...)
determine_status_from_result(...)
将节点状态写入：
work/states/{run_id}/{node_id}.json
状态 JSON 至少包括：
run_id
subject
node
status
started_at
ended_at
log_path
outputs
errors
result_json

参考实现：

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def determine_status_from_result(result: dict[str, Any]) -> str:
    return "SUCCESS" if result.get("ok") else "FAILED"


def write_node_state(
    run_id: str,
    node_id: str,
    subject: str,
    status: str,
    started_at: str,
    ended_at: str,
    result: dict[str, Any],
    work_dir: str,
) -> Path:
    state_dir = Path(work_dir) / "states" / run_id
    state_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "run_id": run_id,
        "subject": subject,
        "node": node_id,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "log_path": result.get("stdout_log"),
        "stderr_log": result.get("stderr_log"),
        "outputs": result.get("outputs", result.get("expected_outputs", [])),
        "errors": result.get("errors", []),
        "result_json": result.get("result_json"),
        "returncode": result.get("returncode"),
    }

    state_path = state_dir / f"{node_id}.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state_path
7. 新增 backend/app/tools/run_spm_smoke_cli.py

创建文件：

backend/app/tools/run_spm_smoke_cli.py

功能：

读取配置文件：
examples/project_config.yaml
调用 run_spm_smoke_test。
写入节点状态文件。
打印结果。
返回码：
成功返回 0
失败返回 2
默认 run_id：
run_spm_smoke_001

参考实现：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.state_store import (
    determine_status_from_result,
    now_iso,
    write_node_state,
)
from backend.app.tools.spm_runner import run_spm_smoke_test


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
    work_dir = config["runtime"]["work_dir"]
    log_dir = config["runtime"]["log_dir"]

    run_id = "run_spm_smoke_001"
    node_id = "spm_smoke_test"

    started_at = now_iso()

    result = run_spm_smoke_test(
        matlab_command=matlab_command,
        spm_dir=spm_dir,
        work_dir=work_dir,
        log_dir=log_dir,
        matlab_script_dir="./matlab",
    )

    ended_at = now_iso()
    status = determine_status_from_result(result)

    state_path = write_node_state(
        run_id=run_id,
        node_id=node_id,
        subject="project",
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        result=result,
        work_dir=work_dir,
    )

    result["state_path"] = str(state_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
8. 更新 README.md

在 README.md 中追加第二步说明：

## Step 2: SPM Smoke Test Node

This step verifies that the project can execute one minimal SPM-backed node.

The smoke test does not use real medical imaging data. It creates a synthetic NIfTI file and runs SPM smoothing.

Run:

```bash
python -m backend.app.tools.run_spm_smoke_cli examples/project_config.yaml

Expected outputs:

work/spm_smoke_test/input.nii
work/spm_smoke_test/smoothed.nii
work/spm_smoke_test/result.json
work/states/run_spm_smoke_001/spm_smoke_test.json
logs/spm_smoke_test_stdout.log
logs/spm_smoke_test_stderr.log

Success criteria:

MATLAB starts successfully.
SPM can be added to MATLAB path.
Synthetic NIfTI is created.
SPM smoothing produces smoothed.nii.
result.json has ok=true.
node state JSON has status=SUCCESS.

---

## 9. 验收标准

完成后，请确认以下文件存在：

```text
specs/pipeline_schema.yaml
specs/node_interface.md
examples/pipeline_spm_smoke.yaml
matlab/spm_smoke_test.m
backend/app/tools/spm_runner.py
backend/app/runtime/state_store.py
backend/app/tools/run_spm_smoke_cli.py

运行：

python -m backend.app.tools.run_spm_smoke_cli examples/project_config.yaml

成功后生成：

work/spm_smoke_test/input.nii
work/spm_smoke_test/smoothed.nii
work/spm_smoke_test/result.json
work/states/run_spm_smoke_001/spm_smoke_test.json
logs/spm_smoke_test_stdout.log
logs/spm_smoke_test_stderr.log

其中：

work/spm_smoke_test/result.json

应该包含：

{
  "ok": true,
  "node_id": "spm_smoke_test",
  "backend": "matlab-spm"
}

其中：

work/states/run_spm_smoke_001/spm_smoke_test.json

应该包含：

{
  "status": "SUCCESS",
  "node": "spm_smoke_test"
}

如果 MATLAB、SPM 或路径有问题，程序必须清晰失败，返回 ok=false，并写入 errors、stdout_log、stderr_log 和 state JSON。

10. 重要限制

本步骤只做单节点执行闭环。

不要扩展到完整 pipeline。
不要实现 Pipeline Executor。
不要实现多节点 DAG。
不要实现 UI。
不要实现 FastAPI 服务。
不要实现 Agent Runtime。
不要实现 DPABI pipeline。
不要实现 GPU。

完成后请给我总结：

新增了哪些文件
如何运行测试
成功输出是什么
如果失败应该看哪些日志