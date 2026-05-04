你是我的工程搭建助手。前四步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环，可以执行 environment_check → spm_smoke_test。
Step 4：完成数据集导入、扫描与索引闭环，可以创建 synthetic BIDS-like 数据集，并生成 dataset_index.json、data_completeness_report.json、subject_table.csv。

现在开始第五步。

第五步目标：实现“最小 subject-level 预处理与 QC 闭环”。

也就是说，本步骤要在 synthetic BIDS-like 数据集上，实现一个最小的 subject-level pipeline：

- 读取 dataset_index.json
- 找到 COMPLETE subjects
- 对每个 subject 的 BOLD 文件执行一个最小 SPM smoothing 预处理节点
- 将输出写入 derivatives/
- 为每个 subject 写 node state
- 生成 subject-level QC metrics
- 生成 subject_preprocess_summary.json
- 让 pipeline executor 支持 sequential subject-level execution

不要实现 UI。
不要实现 FastAPI 服务。
不要实现完整 Agent Runtime。
不要实现多 Agent 协作。
不要做并行调度。
不要做 GPU。
不要做 DPABI pipeline。
不要处理真实医学影像数据。
不要修改 SPM / DPABI 源码。
不要引入数据库。
不要引入 Celery / Redis。
不要过度抽象。

本步骤只做 synthetic 数据上的最小 subject-level SPM smoothing + QC 闭环。

---

## 1. 创建 specs/subject_execution_spec.md

创建文件：

```text
specs/subject_execution_spec.md

内容：

# Subject-Level Execution Specification

This document defines the MVP subject-level execution behavior.

## Scope

The MVP supports sequential subject-level execution only.

Supported subject-level nodes:

- spm_smooth_subject
- subject_qc

Unsupported in this step:

- parallel execution
- GPU execution
- Slurm execution
- DPABI preprocessing
- real medical imaging data
- UI
- database

## Subject Selection

Subject-level nodes should run only on subjects whose dataset_index status is:

```text
COMPLETE

Subjects with these statuses are skipped:

MISSING_T1W
MISSING_BOLD
INCOMPLETE
WARNING
State Files

Project-level node state:

work/states/{run_id}/{node_id}.json

Subject-level node state:

work/states/{run_id}/{subject_id}/{node_id}.json

Example:

work/states/run_subject_preprocess_001/sub-001/spm_smooth_subject.json
work/states/run_subject_preprocess_001/sub-001/subject_qc.json
Derivatives Layout

SPM smoothing outputs should be written to:

derivatives/spm_smooth/{subject_id}/func/

Example:

derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smoothed.nii
Minimal Subject QC

For each smoothed BOLD output, compute:

shape
dtype
mean
std
min
max
nan_count
finite_voxel_count
Safety Rules
Do not modify rawdata.
Do not delete files.
Do not modify third_party.
Write intermediate files only to work/.
Write outputs only to derivatives/.
Write logs only to logs/.

---

## 2. 更新 examples/project_config_dataset.yaml

请在已有 `examples/project_config_dataset.yaml` 中新增 derivatives_dir。

修改 runtime 部分为：

```yaml
runtime:
  matlab_command: "matlab"
  work_dir: "./work"
  log_dir: "./logs"
  report_dir: "./reports"
  derivatives_dir: "./derivatives"

不要删除已有字段。

3. 创建 matlab/spm_smooth_4d.m

创建文件：

matlab/spm_smooth_4d.m

功能：

接收参数：
spm_dir
input_nii
output_nii
output_json
fwhm
添加 SPM 路径。
初始化 SPM。
读取 input_nii。
支持 3D 或 4D NIfTI。
对每个 volume 执行 smoothing。
写入 output_nii。
检查 output_nii 是否存在。
写 result JSON。
不修改 rawdata。
不修改 SPM 源码。

请实现为兼容性较好的 MATLAB 函数：

function spm_smooth_4d(spm_dir, input_nii, output_nii, output_json, fwhm)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_smooth_subject';
    result.backend = 'matlab-spm';
    result.input = input_nii;
    result.output = output_nii;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input NIfTI not found: ', input_nii]);
        end

        output_dir = fileparts(output_nii);
        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end

        if exist(output_nii, 'file')
            delete(output_nii);
        end

        addpath(spm_dir);

        try
            spm('defaults', 'fmri');
            spm_jobman('initcfg');
        catch ME
            result.errors{end+1} = ['SPM init warning: ', ME.message];
        end

        V = spm_vol(input_nii);
        n_volumes = numel(V);

        for i = 1:n_volumes
            Y = spm_read_vols(V(i));
            Ys = zeros(size(Y), 'single');

            try
                spm_smooth(Y, Ys, fwhm);
            catch
                % Fallback: use temporary files if matrix-based smoothing fails
                tmp_in = fullfile(output_dir, ['tmp_vol_', num2str(i), '.nii']);
                tmp_out = fullfile(output_dir, ['tmp_smooth_', num2str(i), '.nii']);

                Vtmp = V(i);
                Vtmp.fname = tmp_in;
                Vtmp.n = [1 1];
                spm_write_vol(Vtmp, Y);

                spm_smooth(tmp_in, tmp_out, fwhm);

                Vsm = spm_vol(tmp_out);
                Ys = spm_read_vols(Vsm);

                if exist(tmp_in, 'file')
                    delete(tmp_in);
                end
                if exist(tmp_out, 'file')
                    delete(tmp_out);
                end
            end

            Vout = V(i);
            Vout.fname = output_nii;
            Vout.dt = [16 0];
            Vout.pinfo = [1; 0; 0];
            Vout.descrip = 'SPM smoothed synthetic BOLD';
            Vout.n = [i 1];

            spm_write_vol(Vout, Ys);
        end

        if ~exist(output_nii, 'file')
            error('SPM smoothing did not produce output NIfTI.');
        end

        result.outputs{end+1} = output_nii;
        result.metrics.n_volumes = n_volumes;
        result.metrics.fwhm = fwhm;
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
4. 创建 backend/app/tools/nifti_utils.py

创建文件：

backend/app/tools/nifti_utils.py

目标：为 SPM 准备 NIfTI 输入。SPM 对 .nii 支持更稳定，因此如果输入是 .nii.gz，先复制/转换成 .nii 到 work 目录。

功能要求：

提供函数：
prepare_nifti_for_spm(
    input_path: str,
    output_dir: str,
    output_name: str | None = None,
) -> dict
如果 input_path 是 .nii：
复制到 output_dir
如果 input_path 是 .nii.gz：
用 nibabel 读取并保存成 .nii
返回：
{
  "ok": true,
  "prepared_path": "outputs/work/spm_inputs/sub-001/sub-001_task-rest_bold.nii",
  "errors": []
}
如果 nibabel 不存在，返回清晰错误。
不要修改原始 rawdata。
不要删除原始文件。

参考实现方向：

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def prepare_nifti_for_spm(
    input_path: str,
    output_dir: str,
    output_name: str | None = None,
) -> dict[str, Any]:
    src = Path(input_path)
    dst_dir = Path(output_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        return {
            "ok": False,
            "prepared_path": None,
            "errors": [f"Input NIfTI not found: {src}"],
        }

    if output_name is None:
        if src.name.endswith(".nii.gz"):
            output_name = src.name.replace(".nii.gz", ".nii")
        else:
            output_name = src.name

    dst = dst_dir / output_name

    try:
        if src.name.endswith(".nii.gz"):
            try:
                import nibabel as nib
            except ImportError:
                return {
                    "ok": False,
                    "prepared_path": None,
                    "errors": ["Missing dependency: nibabel. Install with: pip install nibabel"],
                }

            img = nib.load(str(src))
            nib.save(img, str(dst))
        else:
            shutil.copy2(src, dst)

        return {
            "ok": True,
            "prepared_path": str(dst),
            "errors": [],
        }
    except Exception as exc:
        return {
            "ok": False,
            "prepared_path": None,
            "errors": [f"Failed to prepare NIfTI for SPM: {exc}"],
        }
5. 创建 backend/app/tools/spm_subject_runner.py

创建文件：

backend/app/tools/spm_subject_runner.py

功能：对单个 subject 的 BOLD 文件执行 SPM smoothing。

提供函数：

run_spm_smooth_subject(
    matlab_command: str,
    spm_dir: str,
    subject_record: dict,
    subject_id: str,
    work_dir: str,
    log_dir: str,
    derivatives_dir: str,
    matlab_script_dir: str = "./matlab",
    fwhm: list[int] | None = None,
) -> dict

要求：

从 subject_record 中找到第一个 BOLD 文件。
用 prepare_nifti_for_spm 将 .nii.gz 转成 .nii 到：
work/spm_inputs/{subject_id}/
输出目录：
derivatives/spm_smooth/{subject_id}/func/
输出文件名：
{subject_id}_task-rest_bold_smoothed.nii
输出 JSON：
derivatives/spm_smooth/{subject_id}/func/spm_smooth_result.json
日志：
logs/{subject_id}_spm_smooth_stdout.log
logs/{subject_id}_spm_smooth_stderr.log
调用 MATLAB 的 spm_smooth_4d.m。
返回结构化 dict。
如果找不到 BOLD，ok=false。
如果 MATLAB 返回码非 0，ok=false。
如果 output_nii 不存在，ok=false。
不要修改 rawdata。

参考实现结构：

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from backend.app.tools.nifti_utils import prepare_nifti_for_spm


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def _find_first_bold(subject_record: dict[str, Any]) -> str | None:
    sessions = subject_record.get("sessions", [])
    for session in sessions:
        for func in session.get("func", []):
            bold = func.get("bold")
            if bold:
                return bold
    return None


def run_spm_smooth_subject(
    matlab_command: str,
    spm_dir: str,
    subject_record: dict[str, Any],
    subject_id: str,
    work_dir: str,
    log_dir: str,
    derivatives_dir: str,
    matlab_script_dir: str = "./matlab",
    fwhm: list[int] | None = None,
) -> dict[str, Any]:
    fwhm = fwhm or [4, 4, 4]

    bold_path = _find_first_bold(subject_record)
    if not bold_path:
        return {
            "ok": False,
            "node_id": "spm_smooth_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"No BOLD file found for subject: {subject_id}"],
        }

    prepared = prepare_nifti_for_spm(
        input_path=bold_path,
        output_dir=str(Path(work_dir) / "spm_inputs" / subject_id),
    )
    if not prepared.get("ok"):
        return {
            "ok": False,
            "node_id": "spm_smooth_subject",
            "backend": "matlab-spm",
            "subject_id": subject_id,
            "outputs": [],
            "errors": prepared.get("errors", []),
        }

    input_nii = prepared["prepared_path"]

    output_dir = Path(derivatives_dir) / "spm_smooth" / subject_id / "func"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_nii = output_dir / f"{subject_id}_task-rest_bold_smoothed.nii"
    result_json = output_dir / "spm_smooth_result.json"

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    stdout_log = log_path / f"{subject_id}_spm_smooth_stdout.log"
    stderr_log = log_path / f"{subject_id}_spm_smooth_stderr.log"

    matlab_script_path = str(Path(matlab_script_dir).resolve())
    spm_abs = str(Path(spm_dir).resolve())

    fwhm_expr = "[" + " ".join(str(x) for x in fwhm) + "]"

    matlab_code = (
        "try, "
        f"addpath('{_matlab_quote(matlab_script_path)}'); "
        f"spm_smooth_4d('{_matlab_quote(spm_abs)}', "
        f"'{_matlab_quote(str(Path(input_nii).resolve()))}', "
        f"'{_matlab_quote(str(output_nii.resolve()))}', "
        f"'{_matlab_quote(str(result_json.resolve()))}', "
        f"{fwhm_expr}); "
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
                "errors": [f"Failed to parse SPM smooth result JSON: {exc}"],
            }
    else:
        data = {
            "ok": False,
            "errors": ["SPM smooth did not produce result JSON."],
        }

    data["node_id"] = "spm_smooth_subject"
    data["backend"] = "matlab-spm"
    data["subject_id"] = subject_id
    data["input_bold"] = bold_path
    data["prepared_input"] = input_nii
    data["returncode"] = completed.returncode
    data["stdout_log"] = str(stdout_log)
    data["stderr_log"] = str(stderr_log)
    data["result_json"] = str(result_json)
    data["outputs"] = [str(output_nii)]

    if completed.returncode != 0:
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"MATLAB exited with return code {completed.returncode}.")

    if not output_nii.exists():
        data["ok"] = False
        data.setdefault("errors", [])
        data["errors"].append(f"Expected smoothed output not found: {output_nii}")

    return data
6. 创建 backend/app/tools/qc_metrics.py

创建文件：

backend/app/tools/qc_metrics.py

功能：对单个 subject 的 smoothed NIfTI 输出计算基础 QC metrics。

提供函数：

compute_subject_qc(
    subject_id: str,
    input_nii: str,
    output_dir: str,
) -> dict

要求：

使用 nibabel + numpy。
如果依赖缺失，返回清晰错误。
计算：
shape
dtype
mean
std
min
max
nan_count
finite_voxel_count
输出 JSON：
derivatives/qc/{subject_id}/subject_qc.json
返回结构化 dict：
{
  "ok": true,
  "node_id": "subject_qc",
  "backend": "python",
  "subject_id": "sub-001",
  "outputs": ["outputs/derivatives/qc/sub-001/subject_qc.json"],
  "metrics": {
    "shape": [16, 16, 16, 10],
    "mean": 0.01,
    "std": 0.95,
    "nan_count": 0
  },
  "errors": []
}

参考实现方向：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compute_subject_qc(
    subject_id: str,
    input_nii: str,
    output_dir: str,
) -> dict[str, Any]:
    try:
        import numpy as np
        import nibabel as nib
    except ImportError as exc:
        return {
            "ok": False,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"Missing dependency: {exc.name}. Install with: pip install numpy nibabel"],
        }

    path = Path(input_nii)
    if not path.exists():
        return {
            "ok": False,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"QC input not found: {path}"],
        }

    out_dir = Path(output_dir) / subject_id
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_json = out_dir / "subject_qc.json"

    try:
        img = nib.load(str(path))
        data = img.get_fdata(dtype="float32")

        finite_mask = np.isfinite(data)
        finite_values = data[finite_mask]

        metrics = {
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "mean": float(np.mean(finite_values)) if finite_values.size else None,
            "std": float(np.std(finite_values)) if finite_values.size else None,
            "min": float(np.min(finite_values)) if finite_values.size else None,
            "max": float(np.max(finite_values)) if finite_values.size else None,
            "nan_count": int(np.isnan(data).sum()),
            "finite_voxel_count": int(finite_mask.sum()),
        }

        payload = {
            "ok": True,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "input": str(path),
            "outputs": [str(qc_json)],
            "metrics": metrics,
            "errors": [],
        }

        qc_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    except Exception as exc:
        return {
            "ok": False,
            "node_id": "subject_qc",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "errors": [f"Failed to compute QC metrics: {exc}"],
        }
7. 新增 examples/pipeline_subject_preprocess.yaml

创建文件：

examples/pipeline_subject_preprocess.yaml

内容：

pipeline_id: subject_preprocess_pipeline
version: "0.1.0"
modality: synthetic-rsfmri
description: "Synthetic BIDS-like subject-level preprocessing pipeline using SPM smoothing and basic QC."

execution:
  stop_on_failure: true
  run_id: "run_subject_preprocess_001"

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

  - id: spm_smooth_subject
    name: SPM Smooth Subject BOLD
    agent: spm-runner
    backend: matlab-spm
    depends_on:
      - data_inspection
    inputs:
      - "./work/dataset_index/dataset_index.json"
    outputs: []
    params:
      dataset_index: "./work/dataset_index/dataset_index.json"
      fwhm: [4, 4, 4]
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: subject_qc
    name: Subject QC
    agent: qc-agent
    backend: python
    depends_on:
      - spm_smooth_subject
    inputs: []
    outputs: []
    params:
      qc_output_dir: "./derivatives/qc"
    parallel_level: subject
    gpu_supported: false
    cache: false
8. 修改 backend/app/runtime/node_registry.py

在现有 node registry 中新增两个 subject-level 节点：

spm_smooth_subject
subject_qc

要求：

不破坏已有 environment_check、spm_smoke_test、create_synthetic_bids、data_inspection。
NodeExecutionContext 需要新增可选字段：
subject_id
subject_record
derivatives_dir
previous_subject_results

参考修改：

@dataclass
class NodeExecutionContext:
    run_id: str
    project_config: dict[str, Any]
    work_dir: str
    log_dir: str
    matlab_command: str
    spm_dir: str
    dpabi_dir: str
    derivatives_dir: str = "./derivatives"
    subject_id: str | None = None
    subject_record: dict[str, Any] | None = None
    previous_subject_results: dict[str, dict[str, Any]] | None = None

新增导入：

from backend.app.tools.spm_subject_runner import run_spm_smooth_subject
from backend.app.tools.qc_metrics import compute_subject_qc

新增 runner：

def run_spm_smooth_subject_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    if not context.subject_id or not context.subject_record:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "matlab-spm",
            "outputs": [],
            "errors": ["Missing subject_id or subject_record in context."],
        }

    fwhm = node.params.get("fwhm", [4, 4, 4])

    result = run_spm_smooth_subject(
        matlab_command=context.matlab_command,
        spm_dir=context.spm_dir,
        subject_record=context.subject_record,
        subject_id=context.subject_id,
        work_dir=context.work_dir,
        log_dir=context.log_dir,
        derivatives_dir=context.derivatives_dir,
        matlab_script_dir="./matlab",
        fwhm=fwhm,
    )
    result["node_id"] = node.id
    return result


def run_subject_qc_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    if not context.subject_id:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "errors": ["Missing subject_id in context."],
        }

    previous = context.previous_subject_results or {}
    smooth_result = previous.get("spm_smooth_subject", {})
    outputs = smooth_result.get("outputs", [])

    if not outputs:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "subject_id": context.subject_id,
            "outputs": [],
            "errors": ["No smoothed output found from spm_smooth_subject."],
        }

    smoothed_nii = outputs[0]
    qc_output_dir = node.params.get("qc_output_dir", f"{context.derivatives_dir}/qc")

    result = compute_subject_qc(
        subject_id=context.subject_id,
        input_nii=smoothed_nii,
        output_dir=qc_output_dir,
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

NODE_REGISTRY = {
    "environment_check": run_environment_check_node,
    "spm_smoke_test": run_spm_smoke_test_node,
    "create_synthetic_bids": run_create_synthetic_bids_node,
    "data_inspection": run_data_inspection_node,
    "spm_smooth_subject": run_spm_smooth_subject_node,
    "subject_qc": run_subject_qc_node,
}
9. 修改 backend/app/runtime/state_store.py

扩展 write_node_state，支持 subject-level 状态路径。

要求：

如果 subject == "project"：
路径保持：
work/states/{run_id}/{node_id}.json
如果 subject 是 sub-xxx：
路径改为：
work/states/{run_id}/{subject}/{node_id}.json
状态 JSON 保留：
run_id
subject
node
status
started_at
ended_at
outputs
metrics
warnings
errors
result_json
stdout_log
stderr_log
returncode
不破坏已有调用。
10. 修改 backend/app/runtime/pipeline_executor.py

这是第五步核心。请在现有 pipeline executor 基础上扩展，支持 sequential subject-level execution。

要求：

保持已有 project-level pipeline 行为不变。
如果 node.parallel_level == "project"：
按原逻辑执行一次。
如果 node.parallel_level == "subject"：
从 work/dataset_index/dataset_index.json 读取 dataset index。
只选择 status == "COMPLETE" 的 subjects。
对每个 subject sequential 执行该 node。
为每个 subject 写独立 state。
subject-level dependency 规则：
如果 subject 的前置 subject-level 节点失败，则当前 subject 的后续节点跳过或失败。
MVP 中建议：当前 subject 后续节点标记为 FAILED，并记录依赖失败原因。
如果某个 subject 失败：
pipeline 可以继续处理其他 subjects。
但是最终 pipeline summary 应显示 PARTIAL 或 FAILED。
如果所有 project nodes 和所有 subject nodes 成功：
summary status = SUCCESS。
summary 中新增：
subjects_total
subjects_processed
subjects_success
subjects_failed
subject_results
不要实现并行。
不要引入数据库。

建议实现辅助函数：

def load_dataset_index(path: str | Path) -> dict[str, Any]:
    ...

def get_complete_subjects(dataset_index: dict[str, Any]) -> list[dict[str, Any]]:
    ...

def default_dataset_index_path(work_dir: str) -> Path:
    return Path(work_dir) / "dataset_index" / "dataset_index.json"

summary 示例：

{
  "run_id": "run_subject_preprocess_001",
  "pipeline_id": "subject_preprocess_pipeline",
  "status": "SUCCESS",
  "nodes_total": 4,
  "subjects_total": 2,
  "subjects_processed": 2,
  "subjects_success": 2,
  "subjects_failed": 0,
  "node_states": [
    "outputs/work/states/run_subject_preprocess_001/create_synthetic_bids.json",
    "outputs/work/states/run_subject_preprocess_001/data_inspection.json",
    "outputs/work/states/run_subject_preprocess_001/sub-001/spm_smooth_subject.json",
    "outputs/work/states/run_subject_preprocess_001/sub-001/subject_qc.json",
    "outputs/work/states/run_subject_preprocess_001/sub-002/spm_smooth_subject.json",
    "outputs/work/states/run_subject_preprocess_001/sub-002/subject_qc.json"
  ],
  "errors": []
}
11. 修改 backend/app/runtime/state_store.py 的 write_pipeline_summary

扩展 summary，使其可以保存：

subjects_total
subjects_processed
subjects_success
subjects_failed
subject_results
node_results
node_states

保持向后兼容。

12. 新增 backend/app/tools/run_subject_preprocess_cli.py

创建文件：

backend/app/tools/run_subject_preprocess_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_subject_preprocess.yaml
调用 run_pipeline。
打印 summary JSON。
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


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_subject_preprocess.yaml")

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
13. 更新 README.md

追加第五步说明：

## Step 5: Subject-Level SPM Smoothing and QC

This step runs a minimal subject-level preprocessing pipeline on the synthetic BIDS-like dataset.

It performs:

1. synthetic BIDS dataset creation
2. data inspection
3. SPM smoothing for each COMPLETE subject
4. subject-level QC metrics

Install dependencies:

```bash
pip install numpy nibabel pyyaml

Run:

python -m backend.app.tools.run_subject_preprocess_cli

Or explicitly:

python -m backend.app.tools.run_subject_preprocess_cli examples/project_config_dataset.yaml examples/pipeline_subject_preprocess.yaml

Expected outputs:

derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smoothed.nii
derivatives/spm_smooth/sub-001/func/spm_smooth_result.json
derivatives/spm_smooth/sub-002/func/sub-002_task-rest_bold_smoothed.nii
derivatives/spm_smooth/sub-002/func/spm_smooth_result.json

derivatives/qc/sub-001/subject_qc.json
derivatives/qc/sub-002/subject_qc.json

work/states/run_subject_preprocess_001/sub-001/spm_smooth_subject.json
work/states/run_subject_preprocess_001/sub-001/subject_qc.json
work/states/run_subject_preprocess_001/sub-002/spm_smooth_subject.json
work/states/run_subject_preprocess_001/sub-002/subject_qc.json

work/pipeline_runs/run_subject_preprocess_001/summary.json

Success criteria:

summary.json has status=SUCCESS.
subjects_processed=2.
subjects_success=2.
each subject has a smoothed NIfTI output.
each subject has subject_qc.json.

---

## 14. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/subject_execution_spec.md
examples/project_config_dataset.yaml
matlab/spm_smooth_4d.m
backend/app/tools/nifti_utils.py
backend/app/tools/spm_subject_runner.py
backend/app/tools/qc_metrics.py
examples/pipeline_subject_preprocess.yaml
backend/app/runtime/node_registry.py
backend/app/runtime/state_store.py
backend/app/runtime/pipeline_executor.py
backend/app/tools/run_subject_preprocess_cli.py
README.md

运行：

pip install numpy nibabel pyyaml
python -m backend.app.tools.run_subject_preprocess_cli

成功后应该生成：

derivatives/spm_smooth/sub-001/func/sub-001_task-rest_bold_smoothed.nii
derivatives/spm_smooth/sub-001/func/spm_smooth_result.json
derivatives/spm_smooth/sub-002/func/sub-002_task-rest_bold_smoothed.nii
derivatives/spm_smooth/sub-002/func/spm_smooth_result.json

derivatives/qc/sub-001/subject_qc.json
derivatives/qc/sub-002/subject_qc.json

work/states/run_subject_preprocess_001/sub-001/spm_smooth_subject.json
work/states/run_subject_preprocess_001/sub-001/subject_qc.json
work/states/run_subject_preprocess_001/sub-002/spm_smooth_subject.json
work/states/run_subject_preprocess_001/sub-002/subject_qc.json

work/pipeline_runs/run_subject_preprocess_001/summary.json

其中：

work/pipeline_runs/run_subject_preprocess_001/summary.json

应该包含：

{
  "run_id": "run_subject_preprocess_001",
  "pipeline_id": "subject_preprocess_pipeline",
  "status": "SUCCESS",
  "subjects_processed": 2,
  "subjects_success": 2,
  "subjects_failed": 0
}

其中：

derivatives/qc/sub-001/subject_qc.json

应该包含：

{
  "ok": true,
  "node_id": "subject_qc",
  "subject_id": "sub-001",
  "metrics": {
    "shape": [16, 16, 16, 10],
    "nan_count": 0
  }
}

如果 MATLAB 或 SPM 失败：

对应 subject 的 spm_smooth_subject state 应为 FAILED。
pipeline summary 应为 PARTIAL 或 FAILED。
stderr_log 和 stdout_log 路径必须写入 state JSON。
其他 subject 可以继续执行。

如果 nibabel 缺失：

程序应该清晰提示 pip install nibabel。
不要崩溃成未捕获异常。
15. 重要限制

本步骤只做 synthetic subject-level SPM smoothing + QC。

不要实现：

UI
FastAPI 服务
Agent Runtime
多 Agent
并行调度
GPU
DPABI pipeline
真实医学影像预处理
数据库
复杂缓存系统
报告 PDF

完成后请总结：

新增了哪些文件
修改了哪些文件
如何运行 subject-level preprocessing
成功输出是什么
如果失败应该看哪些日志或 JSON

'''
这一步主要做的是：

## 第五步：最小 subject-level 预处理与 QC 闭环
这是在 synthetic BIDS-like 数据集上实现一个最小的 subject-level pipeline，为后续真实医学影像预处理做准备。

### 核心目标
1. 读取 dataset_index.json
   
   - 找到状态为 COMPLETE 的被试
   - 跳过 MISSING_T1W 、 MISSING_BOLD 、 INCOMPLETE 、 WARNING 状态的被试
2. Subject-level SPM smoothing
   
   - 对每个被试的 BOLD 文件执行 SPM 平滑预处理
   - 将输出写入 derivatives/spm_smooth/{subject_id}/func/
   - 支持 3D/4D NIfTI 文件
3. Subject-level QC 计算
   
   - 对平滑后的输出计算基础 QC 指标：
     - shape, dtype
     - mean, std, min, max
     - nan_count, finite_voxel_count
4. Sequential subject-level execution
   
   - Pipeline Executor 支持按被试顺序执行
   - 为每个被试写独立的 node state 文件
   - 生成 subject_preprocess_summary.json
### 关键组件
组件 功能 matlab/spm_smooth_4d.m MATLAB 脚本，执行 SPM 4D 平滑 backend/app/tools/nifti_utils.py NIfTI 文件准备（.nii.gz → .nii） backend/app/tools/spm_subject_runner.py 单被试 SPM 平滑执行器 backend/app/tools/qc_metrics.py QC 指标计算 backend/app/runtime/pipeline_executor.py 支持 subject-level 执行逻辑

### 执行流程
```
create_synthetic_bids → data_inspection → spm_smooth_subject → 
subject_qc
                         (project-level)    (subject-level)      
                         (subject-level)
```
### 明确不做的事情
- ❌ 并行执行（只做 sequential）
- ❌ GPU 计算
- ❌ DPABI pipeline
- ❌ 真实医学影像数据
- ❌ UI / FastAPI
- ❌ 数据库 / Celery / Redis
这一步已经 全部完成 并验证通过。成功在 2 个合成被试上执行了 SPM 平滑和 QC 计算，所有节点状态为 SUCCESS。
'''