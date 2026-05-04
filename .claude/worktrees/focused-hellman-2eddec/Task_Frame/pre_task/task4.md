你是我的工程搭建助手。前三步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环，可以执行 environment_check → spm_smoke_test，并生成 pipeline summary。

现在开始第四步。

第四步目标：实现“数据集导入、扫描与索引闭环”。

也就是说，现在开始为后续真实医学影像预处理做准备，但本步骤仍然不做真实预处理。只实现 Data Inspector 能力：

- 创建一个最小 synthetic BIDS-like 测试数据集
- 扫描 BIDS-like rawdata 目录
- 识别 subject / session / anat / func
- 检查 T1w 和 BOLD 是否存在
- 读取 sidecar JSON，例如 TR / SliceTiming
- 可选读取 NIfTI 基础 metadata，例如 shape / affine / dtype
- 生成 dataset_index.json
- 生成 data_completeness_report.json
- 生成 subject_table.csv
- 将 data_inspection 作为 pipeline node 接入现有 Pipeline Executor
- 为每个节点写 state JSON
- 为整个 pipeline 写 summary JSON

不要实现 UI。
不要实现 FastAPI 服务。
不要实现完整 Agent Runtime。
不要实现多 Agent 协作。
不要做真实预处理。
不要调用 SPM / DPABI 做预处理。
不要做 GPU。
不要修改 SPM / DPABI 源码。
不要引入数据库。
不要引入 Celery / Redis。
不要过度抽象。

本步骤只做 Data Inspector 和 synthetic BIDS-like 数据集扫描。

---

## 1. 创建 specs/dataset_index_spec.md

创建文件：

```text
specs/dataset_index_spec.md

内容：

# Dataset Index Specification

This document defines the dataset indexing format for MedImage Agent.

## Scope

The dataset index is a project-level summary of BIDS-like medical imaging data.

The MVP supports:

- subject-level folders: sub-xxx
- optional session folders: ses-xxx
- anatomical images: anat/*T1w.nii or anat/*T1w.nii.gz
- functional images: func/*bold.nii or func/*bold.nii.gz
- functional sidecar JSON files
- participants.tsv

The MVP does not perform preprocessing.

## Output Files

The Data Inspector node writes:

```text
work/dataset_index/dataset_index.json
work/dataset_index/data_completeness_report.json
work/dataset_index/subject_table.csv
dataset_index.json

Minimal structure:

{
  "dataset_root": "examples/synthetic_bids/rawdata",
  "subjects_total": 2,
  "subjects": [
    {
      "subject_id": "sub-001",
      "sessions": [
        {
          "session_id": null,
          "anat": {
            "t1w": "examples/synthetic_bids/rawdata/sub-001/anat/sub-001_T1w.nii.gz",
            "exists": true
          },
          "func": [
            {
              "bold": "examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.nii.gz",
              "json": "examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.json",
              "exists": true,
              "metadata": {
                "RepetitionTime": 2.0
              }
            }
          ]
        }
      ],
      "status": "COMPLETE",
      "issues": []
    }
  ]
}
data_completeness_report.json

Minimal structure:

{
  "subjects_total": 2,
  "subjects_complete": 2,
  "subjects_missing_t1w": 0,
  "subjects_missing_bold": 0,
  "subjects_with_issues": 0,
  "issues": []
}
Subject Status
COMPLETE: required T1w and BOLD files exist
MISSING_T1W: no T1w file found
MISSING_BOLD: no BOLD file found
INCOMPLETE: multiple required files or metadata are missing
WARNING: files exist but metadata or naming may be questionable
Safety Rules
The Data Inspector must not modify rawdata.
The Data Inspector must not delete files.
The Data Inspector may write only to work/, logs/, and reports/.

---

## 2. 创建 backend/app/tools/synthetic_bids.py

创建文件：

```text
backend/app/tools/synthetic_bids.py

目标：创建一个最小 synthetic BIDS-like 数据集，用于测试 Data Inspector。

功能要求：

提供函数：
create_synthetic_bids_dataset(
    output_dir: str,
    subjects: list[str] | None = None,
) -> dict
默认创建：
examples/synthetic_bids/rawdata/
├── dataset_description.json
├── participants.tsv
├── sub-001/
│   ├── anat/sub-001_T1w.nii.gz
│   └── func/
│       ├── sub-001_task-rest_bold.nii.gz
│       └── sub-001_task-rest_bold.json
└── sub-002/
    ├── anat/sub-002_T1w.nii.gz
    └── func/
        ├── sub-002_task-rest_bold.nii.gz
        └── sub-002_task-rest_bold.json
使用 numpy + nibabel 生成小型 NIfTI：
T1w shape: 16 x 16 x 16
BOLD shape: 16 x 16 x 16 x 10
affine: identity
dtype: float32
如果 nibabel 或 numpy 没安装，返回清晰错误，不要崩溃。提示：
pip install numpy nibabel
不要覆盖已有数据，除非 output_dir 是 synthetic_bids 测试目录。
不要删除任何文件。

参考实现方向：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def create_synthetic_bids_dataset(
    output_dir: str,
    subjects: list[str] | None = None,
) -> dict[str, Any]:
    try:
        import numpy as np
        import nibabel as nib
    except ImportError as exc:
        return {
            "ok": False,
            "errors": [
                f"Missing dependency: {exc.name}. Install with: pip install numpy nibabel"
            ],
        }

    subjects = subjects or ["sub-001", "sub-002"]
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    dataset_description = {
        "Name": "Synthetic BIDS-like dataset for MedImage Agent",
        "BIDSVersion": "1.8.0",
        "DatasetType": "raw",
    }
    (root / "dataset_description.json").write_text(
        json.dumps(dataset_description, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    participants_lines = ["participant_id\tage\tsex\tgroup"]
    for idx, subject in enumerate(subjects, start=1):
        participants_lines.append(f"{subject}\t{20 + idx}\tM\tcontrol")
    (root / "participants.tsv").write_text(
        "\n".join(participants_lines) + "\n",
        encoding="utf-8",
    )

    created_files: list[str] = []

    for subject in subjects:
        anat_dir = root / subject / "anat"
        func_dir = root / subject / "func"
        anat_dir.mkdir(parents=True, exist_ok=True)
        func_dir.mkdir(parents=True, exist_ok=True)

        t1_data = np.random.randn(16, 16, 16).astype("float32")
        bold_data = np.random.randn(16, 16, 16, 10).astype("float32")
        affine = np.eye(4)

        t1_path = anat_dir / f"{subject}_T1w.nii.gz"
        bold_path = func_dir / f"{subject}_task-rest_bold.nii.gz"
        bold_json_path = func_dir / f"{subject}_task-rest_bold.json"

        nib.save(nib.Nifti1Image(t1_data, affine), str(t1_path))
        nib.save(nib.Nifti1Image(bold_data, affine), str(bold_path))

        bold_metadata = {
            "TaskName": "rest",
            "RepetitionTime": 2.0,
            "SliceTiming": [0.0, 1.0],
            "Manufacturer": "Synthetic",
        }
        bold_json_path.write_text(
            json.dumps(bold_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        created_files.extend([
            str(t1_path),
            str(bold_path),
            str(bold_json_path),
        ])

    return {
        "ok": True,
        "dataset_root": str(root),
        "subjects": subjects,
        "created_files": created_files,
        "errors": [],
    }
3. 创建 backend/app/tools/data_inspector.py

创建文件：

backend/app/tools/data_inspector.py

目标：扫描 BIDS-like 数据集，生成 dataset_index 和 completeness report。

功能要求：

提供函数：
inspect_dataset(
    rawdata_dir: str,
    output_dir: str,
    read_nifti_metadata: bool = True,
) -> dict
扫描：
sub-* subject
ses-* session，可选
anat/*T1w.nii 或 anat/*T1w.nii.gz
func/*bold.nii 或 func/*bold.nii.gz
func/*bold.json
participants.tsv
输出：
dataset_index.json
data_completeness_report.json
subject_table.csv
如果 nibabel 不存在：
仍然可以扫描文件路径
read_nifti_metadata 自动降级为 false
在 warnings 中记录
不要修改 rawdata。
不要删除任何文件。
使用 pathlib、json、csv 标准库。
返回结构化 dict：
{
  "ok": true,
  "node_id": "data_inspection",
  "backend": "python",
  "outputs": [
    "work/dataset_index/dataset_index.json",
    "work/dataset_index/data_completeness_report.json",
    "work/dataset_index/subject_table.csv"
  ],
  "metrics": {
    "subjects_total": 2,
    "subjects_complete": 2
  },
  "warnings": [],
  "errors": []
}

请实现以下辅助函数：

_find_subject_dirs(rawdata_path: Path) -> list[Path]
_find_session_dirs(subject_dir: Path) -> list[Path]
_find_t1w(anat_dir: Path) -> str | None
_find_bold_files(func_dir: Path) -> list[Path]
_read_json(path: Path) -> dict
_read_nifti_metadata(path: Path) -> dict
_determine_subject_status(...)

subject_table.csv 至少包含：

subject_id,status,t1w_exists,bold_count,issues
4. 新增 examples/project_config_dataset.yaml

创建文件：

examples/project_config_dataset.yaml

内容：

project:
  name: medimage_agent_dataset_mvp
  root_dir: "."

third_party:
  spm_dir: "./third_party/spm12"
  dpabi_dir: "./third_party/DPABI_V8.2_240510"

data:
  rawdata_dir: "./examples/synthetic_bids/rawdata"

runtime:
  matlab_command: "matlab"
  work_dir: "./work"
  log_dir: "./logs"
  report_dir: "./reports"

safety:
  rawdata_readonly: true
  allow_overwrite_derivatives: false
  require_confirmation_for_matlab_run: true
5. 新增 examples/pipeline_dataset_inspection.yaml

创建文件：

examples/pipeline_dataset_inspection.yaml

内容：

pipeline_id: dataset_inspection_pipeline
version: "0.1.0"
modality: test
description: "Create a synthetic BIDS-like dataset and inspect its structure."

execution:
  stop_on_failure: true
  run_id: "run_dataset_inspection_001"

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
6. 修改 backend/app/runtime/node_registry.py

在现有 node registry 中新增两个节点：

create_synthetic_bids
data_inspection

要求：

不破坏已有 environment_check 和 spm_smoke_test。
runner 从 node.params 读取参数。
runner 返回结构化 dict。
对输出路径进行基本检查。

新增导入：

from backend.app.tools.synthetic_bids import create_synthetic_bids_dataset
from backend.app.tools.data_inspector import inspect_dataset

新增 runner：

def run_create_synthetic_bids_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    output_dir = node.params.get("output_dir", "./examples/synthetic_bids/rawdata")
    subjects = node.params.get("subjects")
    result = create_synthetic_bids_dataset(
        output_dir=output_dir,
        subjects=subjects,
    )
    result["node_id"] = node.id
    result["backend"] = "python"
    return result


def run_data_inspection_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    rawdata_dir = node.params.get("rawdata_dir")
    output_dir = node.params.get("output_dir", f"{context.work_dir}/dataset_index")
    read_nifti_metadata = bool(node.params.get("read_nifti_metadata", True))

    if not rawdata_dir:
        return {
            "ok": False,
            "node_id": node.id,
            "backend": "python",
            "outputs": [],
            "errors": ["Missing required param: rawdata_dir"],
        }

    result = inspect_dataset(
        rawdata_dir=rawdata_dir,
        output_dir=output_dir,
        read_nifti_metadata=read_nifti_metadata,
    )
    result["node_id"] = node.id
    result["backend"] = "python"
    return result

更新 NODE_REGISTRY：

NODE_REGISTRY = {
    "environment_check": run_environment_check_node,
    "spm_smoke_test": run_spm_smoke_test_node,
    "create_synthetic_bids": run_create_synthetic_bids_node,
    "data_inspection": run_data_inspection_node,
}
7. 修改 backend/app/runtime/pipeline_executor.py

请检查现有 pipeline executor 是否满足以下要求：

node.params 可以传入 runner。
node outputs 不应该强制在 executor 中统一检查，因为每个 runner 已经负责检查。
pipeline summary 应该包含每个 node 的 metrics、warnings、errors。
如果 node result 里有 warnings，不应导致失败。
如果 result.ok=false，节点状态为 FAILED。
如果依赖失败，后续节点不要执行。

如果已有实现满足，则不要大改。

8. 修改 backend/app/runtime/state_store.py

请确保 write_node_state 能保存：

metrics
warnings
result_json
outputs
returncode
errors

如果当前没有 metrics 和 warnings，请添加。

状态 JSON 示例：

{
  "run_id": "run_dataset_inspection_001",
  "subject": "project",
  "node": "data_inspection",
  "status": "SUCCESS",
  "started_at": "...",
  "ended_at": "...",
  "outputs": [
    "work/dataset_index/dataset_index.json",
    "work/dataset_index/data_completeness_report.json",
    "work/dataset_index/subject_table.csv"
  ],
  "metrics": {
    "subjects_total": 2,
    "subjects_complete": 2
  },
  "warnings": [],
  "errors": []
}
9. 新增 backend/app/tools/run_dataset_inspection_cli.py

创建文件：

backend/app/tools/run_dataset_inspection_cli.py

功能：

默认 project config：
examples/project_config_dataset.yaml
默认 pipeline：
examples/pipeline_dataset_inspection.yaml
调用现有 run_pipeline。
打印 summary JSON。
返回码：
SUCCESS 返回 0
INVALID 返回 1
FAILED / PARTIAL 返回 2

参考结构：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dataset_inspection.yaml")

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
10. 更新 README.md

追加第四步说明：

## Step 4: Dataset Inspection

This step creates a synthetic BIDS-like dataset and scans it with the Data Inspector node.

Install optional dependencies:

```bash
pip install numpy nibabel pyyaml

Run:

python -m backend.app.tools.run_dataset_inspection_cli

Or explicitly:

python -m backend.app.tools.run_dataset_inspection_cli examples/project_config_dataset.yaml examples/pipeline_dataset_inspection.yaml

Expected synthetic dataset:

examples/synthetic_bids/rawdata/
├── dataset_description.json
├── participants.tsv
├── sub-001/
│   ├── anat/sub-001_T1w.nii.gz
│   └── func/
│       ├── sub-001_task-rest_bold.nii.gz
│       └── sub-001_task-rest_bold.json
└── sub-002/
    ├── anat/sub-002_T1w.nii.gz
    └── func/
        ├── sub-002_task-rest_bold.nii.gz
        └── sub-002_task-rest_bold.json

Expected outputs:

work/dataset_index/dataset_index.json
work/dataset_index/data_completeness_report.json
work/dataset_index/subject_table.csv
work/states/run_dataset_inspection_001/create_synthetic_bids.json
work/states/run_dataset_inspection_001/data_inspection.json
work/pipeline_runs/run_dataset_inspection_001/summary.json

Success criteria:

summary.json has status=SUCCESS.
dataset_index.json contains 2 subjects.
data_completeness_report.json reports subjects_complete=2.
subject_table.csv contains sub-001 and sub-002.

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dataset_index_spec.md
backend/app/tools/synthetic_bids.py
backend/app/tools/data_inspector.py
examples/project_config_dataset.yaml
examples/pipeline_dataset_inspection.yaml
backend/app/runtime/node_registry.py
backend/app/runtime/pipeline_executor.py
backend/app/runtime/state_store.py
backend/app/tools/run_dataset_inspection_cli.py
README.md

运行：

pip install numpy nibabel pyyaml
python -m backend.app.tools.run_dataset_inspection_cli

成功后应该生成：

examples/synthetic_bids/rawdata/dataset_description.json
examples/synthetic_bids/rawdata/participants.tsv
examples/synthetic_bids/rawdata/sub-001/anat/sub-001_T1w.nii.gz
examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.nii.gz
examples/synthetic_bids/rawdata/sub-001/func/sub-001_task-rest_bold.json
examples/synthetic_bids/rawdata/sub-002/anat/sub-002_T1w.nii.gz
examples/synthetic_bids/rawdata/sub-002/func/sub-002_task-rest_bold.nii.gz
examples/synthetic_bids/rawdata/sub-002/func/sub-002_task-rest_bold.json
work/dataset_index/dataset_index.json
work/dataset_index/data_completeness_report.json
work/dataset_index/subject_table.csv
work/states/run_dataset_inspection_001/create_synthetic_bids.json
work/states/run_dataset_inspection_001/data_inspection.json
work/pipeline_runs/run_dataset_inspection_001/summary.json

其中：

work/pipeline_runs/run_dataset_inspection_001/summary.json

应该包含：

{
  "run_id": "run_dataset_inspection_001",
  "pipeline_id": "dataset_inspection_pipeline",
  "status": "SUCCESS"
}

其中：

work/dataset_index/data_completeness_report.json

应该包含：

{
  "subjects_total": 2,
  "subjects_complete": 2,
  "subjects_missing_t1w": 0,
  "subjects_missing_bold": 0
}

如果 numpy 或 nibabel 缺失，程序应该清晰提示安装依赖，而不是崩溃。

如果 synthetic dataset 中某个 subject 缺少 T1w 或 BOLD，Data Inspector 应该将该 subject 标记为 MISSING_T1W、MISSING_BOLD 或 INCOMPLETE。

12. 重要限制

本步骤只做数据集扫描与索引闭环。

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
如何运行 dataset inspection
成功输出是什么
如果失败应该看哪些日志或 JSON


'''
这一步主要做的是：

## 第四步：数据集导入、扫描与索引闭环
这是为后续真实医学影像预处理做准备的关键步骤，但本步骤 不做真实预处理 ，只实现 Data Inspector（数据检查器） 能力。

### 核心目标
1. 创建合成BIDS数据集
   
   - 生成最小的 synthetic BIDS-like 测试数据集
   - 包含 T1w 结构像和 BOLD 功能像
   - 包含 sidecar JSON 元数据文件
2. 实现数据扫描能力
   
   - 扫描 BIDS-like rawdata 目录结构
   - 识别 subject / session / anat / func 层级
   - 检查 T1w 和 BOLD 文件是否存在
3. 元数据提取
   
   - 读取 sidecar JSON（如 TR、SliceTiming）
   - 可选读取 NIfTI 基础元数据（shape、affine、dtype）
4. 生成索引报告
   
   - dataset_index.json - 完整数据集索引
   - data_completeness_report.json - 数据完整性报告
   - subject_table.csv - 被试信息表
5. 接入Pipeline执行器
   
   - 将 data_inspection 作为 pipeline node
   - 复用现有的 Pipeline Executor 执行逻辑
   - 生成节点 state JSON 和 pipeline summary JSON
### 明确不做的事情
- ❌ 实现 UI
- ❌ 实现 FastAPI 服务
- ❌ 实现完整 Agent Runtime
- ❌ 实现多 Agent 协作
- ❌ 做真实预处理
- ❌ 调用 SPM / DPABI 做预处理
- ❌ 做 GPU 计算
- ❌ 修改 SPM / DPABI 源码
- ❌ 引入数据库
- ❌ 引入 Celery / Redis
这一步已经 全部完成 并验证通过。生成的合成数据集包含 2 个被试（sub-001、sub-002），每个被试都有完整的 T1w 和 BOLD 数据，数据检查器成功扫描并生成了所有索引文件。
'''