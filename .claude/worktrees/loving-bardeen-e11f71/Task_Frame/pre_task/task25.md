你是我的工程搭建助手。前二十四步已经完成：

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

现在开始第二十五步。

第二十五步目标：实现“DPABI Pipeline Template Library + Promotable Wrapper 模板化闭环”。

当前系统已经可以生成：

- dpabi_function_signatures.json
- dpabi_wrapper_contracts.json
- dpabi_single_function_result.json
- dpabi_subject_wrapper_summary.json
- dpabi_wrapper_compatibility_matrix.json

其中 compatibility matrix 会把通过 sandbox test 和 subject-level synthetic test 的函数标记为：

```text
PROMOTABLE_TO_TEMPLATE

本步骤要把这些 promotable wrappers 转化成可复用 pipeline templates：

读取 dpabi_wrapper_compatibility_matrix.json
找出 readiness == PROMOTABLE_TO_TEMPLATE 的函数
为每个 promotable function 生成 pipeline template
生成 template index
生成 template manifest
生成 Markdown template report
template 默认 approved=false
template 只处理 synthetic BIDS-like 数据
template 不自动执行
template 明确标记 safety gates
后端 API 暴露 template library
前端 DPABI Panel 显示 template index、manifest、report
validation suite 增加 template library 轻量测试

本步骤不要运行完整 DPABI pipeline。
本步骤不要调用 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。
本步骤只生成模板，不执行模板。

1. 创建 specs/dpabi_template_library_spec.md

创建文件：

specs/dpabi_template_library_spec.md

内容：

# DPABI Pipeline Template Library Specification

This document defines the MVP DPABI pipeline template library.

## Goals

The template library converts validated DPABI wrapper functions into reusable pipeline templates.

It should:

- read the wrapper compatibility matrix
- find promotable wrappers
- generate pipeline templates
- generate a template index
- generate a template manifest
- generate a Markdown report
- preserve approval requirements
- prevent accidental full DPABI execution

## Scope

Supported in this step:

- template generation from PROMOTABLE_TO_TEMPLATE wrappers
- subject-level DPABI single-function wrapper templates
- synthetic BIDS-like data only
- approved=false by default
- template index JSON
- template manifest YAML
- Markdown report
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
- automatic template execution

## Inputs

```text
work/dpabi/dpabi_wrapper_compatibility_matrix.json
Outputs
work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/dpabi_template_manifest.yaml
work/dpabi/templates/pipelines/{template_id}.yaml
reports/dpabi/dpabi_template_library_report.md
Template Rules

Every generated pipeline template must:

use approved=false by default
require explicit future approval
only allow synthetic BIDS-like data
only use allowlisted wrapper functions
include environment_check
include data_inspection
include dpabi_signature_probe
include dpabi_wrapper_contracts
include dpabi_subject_smooth
include dpabi_subject_wrapper_report
not include DPARSF_run
not include DPARSFA_run
not include DPABI GUI calls
Safety Rules
Do not execute generated templates.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Do not promote blocked functions.
Do not promote GUI entrypoints.
Do not promote full pipeline runners.

---

## 2. 创建 backend/app/tools/dpabi_template_library.py

创建文件：

```text
backend/app/tools/dpabi_template_library.py

目标：根据 compatibility matrix 生成 DPABI pipeline template library。

提供函数：

write_dpabi_template_library(
    work_dir: str,
    report_dir: str,
    matrix_path: str = "./work/dpabi/dpabi_wrapper_compatibility_matrix.json",
) -> dict

输出：

work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/dpabi_template_manifest.yaml
work/dpabi/templates/pipelines/{template_id}.yaml
reports/dpabi/dpabi_template_library_report.md

实现要求：

读取 compatibility matrix。
只选择：
readiness == PROMOTABLE_TO_TEMPLATE
只允许函数：
y_Smooth
rest_Smooth
为每个函数生成一个 pipeline template。
template 中 dpabi_subject_smooth.params.approved 必须是 false。
template 中必须包含 safety metadata。
不执行 template。
不调用 MATLAB。
不读取 rawdata。
不修改 rawdata。

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWLISTED_TEMPLATE_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


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


def _render_subject_wrapper_template(function_name: str, template_id: str) -> str:
    return f"""pipeline_id: {template_id}
version: "0.1.0"
modality: synthetic-rsfmri
description: "Generated DPABI subject-level single-function wrapper template for {function_name}. Synthetic data only."

template_metadata:
  generated_by: "dpabi_template_library"
  function_name: "{function_name}"
  template_type: "dpabi_subject_single_function_wrapper"
  synthetic_only: true
  requires_approval: true
  approved_by_default: false
  full_dpabi_execution: false
  dparsf_run_allowed: false
  dparsfa_run_allowed: false
  dpabi_gui_allowed: false

execution:
  stop_on_failure: true
  run_id: "run_{template_id}_001"
  scheduler:
    mode: "local_parallel"
    max_workers: 2
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
    params: {{}}
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
    params: {{}}
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

  - id: dpabi_subject_smooth
    name: Approved DPABI Subject Smooth
    agent: dpabi-runner
    backend: matlab-dpabi
    depends_on:
      - data_inspection
      - dpabi_wrapper_contracts
    inputs:
      - "./work/dataset_index/dataset_index.json"
      - "./work/dpabi/dpabi_wrapper_contracts.json"
    outputs: []
    params:
      function_name: "{function_name}"
      fwhm: [4, 4, 4]
      approved: false
      synthetic_only: true
    parallel_level: subject
    gpu_supported: false
    cache: false

  - id: dpabi_subject_wrapper_report
    name: DPABI Subject Wrapper Report
    agent: dpabi-runner
    backend: python
    depends_on:
      - dpabi_subject_smooth
    inputs: []
    outputs:
      - "./reports/dpabi/dpabi_subject_wrapper_summary.json"
      - "./reports/dpabi/dpabi_subject_wrapper_report.md"
    params: {{}}
    parallel_level: project
    gpu_supported: false
    cache: false
"""


def write_dpabi_template_library(
    work_dir: str,
    report_dir: str,
    matrix_path: str = "./work/dpabi/dpabi_wrapper_compatibility_matrix.json",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    matrix_file = Path(matrix_path)
    matrix = _read_json(matrix_file)

    if not matrix:
        return {
            "ok": False,
            "node_id": "dpabi_template_library",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid compatibility matrix: {matrix_file}"],
        }

    template_root = Path(work_dir) / "dpabi" / "templates"
    pipeline_dir = template_root / "pipelines"
    report_out = Path(report_dir) / "dpabi"

    pipeline_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    generated_templates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in matrix.get("rows", []):
        function_name = row.get("function_name")
        readiness = row.get("readiness")

        if readiness != "PROMOTABLE_TO_TEMPLATE":
            skipped.append({
                "function_name": function_name,
                "reason": f"readiness={readiness}",
            })
            continue

        if function_name not in ALLOWLISTED_TEMPLATE_FUNCTIONS:
            skipped.append({
                "function_name": function_name,
                "reason": "not_allowlisted_for_template_generation",
            })
            continue

        template_id = f"dpabi_{function_name.lower()}_subject_wrapper_template"
        template_path = pipeline_dir / f"{template_id}.yaml"

        template_path.write_text(
            _render_subject_wrapper_template(function_name, template_id),
            encoding="utf-8",
        )

        generated_templates.append({
            "template_id": template_id,
            "function_name": function_name,
            "template_path": str(template_path),
            "template_type": "dpabi_subject_single_function_wrapper",
            "synthetic_only": True,
            "requires_approval": True,
            "approved_by_default": False,
            "readiness_source": readiness,
        })

    index = {
        "ok": True,
        "node_id": "dpabi_template_library",
        "backend": "python",
        "matrix_path": str(matrix_file),
        "templates_total": len(generated_templates),
        "templates": generated_templates,
        "skipped": skipped,
        "safety": {
            "templates_executed": False,
            "full_dpabi_execution": False,
            "dparsf_run_allowed": False,
            "dpabi_gui_allowed": False,
            "rawdata_modified": False,
            "files_deleted": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    index_path = template_root / "dpabi_template_index.json"
    manifest_path = template_root / "dpabi_template_manifest.yaml"
    report_path = report_out / "dpabi_template_library_report.md"

    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest_lines = []
    manifest_lines.append('version: "0.1.0"')
    manifest_lines.append("templates:")
    for item in generated_templates:
        manifest_lines.append(f"  - template_id: {_yaml_scalar(item['template_id'])}")
        manifest_lines.append(f"    function_name: {_yaml_scalar(item['function_name'])}")
        manifest_lines.append(f"    template_path: {_yaml_scalar(item['template_path'])}")
        manifest_lines.append(f"    synthetic_only: {_yaml_scalar(item['synthetic_only'])}")
        manifest_lines.append(f"    requires_approval: {_yaml_scalar(item['requires_approval'])}")
        manifest_lines.append(f"    approved_by_default: {_yaml_scalar(item['approved_by_default'])}")
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    lines = []
    lines.append("# DPABI Template Library Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Matrix: `{matrix_file}`")
    lines.append(f"- Templates generated: {len(generated_templates)}")
    lines.append(f"- Skipped functions: {len(skipped)}")
    lines.append("")
    lines.append("## Generated Templates")
    lines.append("")
    if generated_templates:
        lines.append("| Template ID | Function | Path | Requires Approval |")
        lines.append("|---|---|---|---:|")
        for item in generated_templates:
            lines.append(
                f"| {item['template_id']} | {item['function_name']} | "
                f"`{item['template_path']}` | {item['requires_approval']} |"
            )
    else:
        lines.append("No templates were generated.")
    lines.append("")
    lines.append("## Skipped")
    lines.append("")
    if skipped:
        for item in skipped:
            lines.append(f"- {item.get('function_name')}: {item.get('reason')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("Generated templates are not executed automatically. Each generated template defaults to approved=false.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_template_library",
        "backend": "python",
        "outputs": [str(index_path), str(manifest_path), str(report_path)]
        + [item["template_path"] for item in generated_templates],
        "metrics": {
            "templates_total": len(generated_templates),
            "skipped_total": len(skipped),
        },
        "warnings": warnings,
        "errors": errors,
    }
3. 修改 backend/app/runtime/node_registry.py

新增节点：

dpabi_template_library

新增导入：

from backend.app.tools.dpabi_template_library import write_dpabi_template_library

新增 runner：

def run_dpabi_template_library_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_template_library(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        matrix_path=node.params.get(
            "matrix_path",
            f"{context.work_dir}/dpabi/dpabi_wrapper_compatibility_matrix.json",
        ),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_template_library": run_dpabi_template_library_node,
4. 创建 examples/pipeline_dpabi_template_library.yaml

创建文件：

examples/pipeline_dpabi_template_library.yaml

内容：

pipeline_id: dpabi_template_library_pipeline
version: "0.1.0"
modality: integration-test
description: "Generate DPABI pipeline template library from wrapper compatibility matrix."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_template_library_001"
  scheduler:
    mode: "sequential"
    max_workers: 1
    matlab_max_workers: 1

nodes:
  - id: dpabi_template_library
    name: DPABI Template Library
    agent: dpabi-runner
    backend: python
    depends_on: []
    inputs:
      - "./work/dpabi/dpabi_wrapper_compatibility_matrix.json"
    outputs:
      - "./work/dpabi/templates/dpabi_template_index.json"
      - "./work/dpabi/templates/dpabi_template_manifest.yaml"
      - "./reports/dpabi/dpabi_template_library_report.md"
    params:
      matrix_path: "./work/dpabi/dpabi_wrapper_compatibility_matrix.json"
    parallel_level: project
    gpu_supported: false
    cache: false
5. 创建 backend/app/tools/run_dpabi_template_library_cli.py

创建文件：

backend/app/tools/run_dpabi_template_library_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dpabi_template_library.yaml")

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
6. 修改 backend/app/api/routes.py

修改已有：

GET /api/dpabi/capabilities
GET /api/reports/dpabi

让 /api/dpabi/capabilities 新增返回：

"template_index": _read_json_if_exists(base / "templates" / "dpabi_template_index.json"),
"template_manifest": _read_text_if_exists(base / "templates" / "dpabi_template_manifest.yaml"),

让 /api/reports/dpabi 新增返回：

"template_library_report": _read_text_if_exists(base / "dpabi_template_library_report.md"),

新增 API：

GET /api/dpabi/templates

路由：

@router.get("/api/dpabi/templates")
def api_get_dpabi_templates() -> dict[str, Any]:
    work_base = Path("work") / "dpabi" / "templates"
    report_base = Path("reports") / "dpabi"

    return {
        "ok": True,
        "template_index": _read_json_if_exists(work_base / "dpabi_template_index.json"),
        "template_manifest": _read_text_if_exists(work_base / "dpabi_template_manifest.yaml"),
        "template_library_report": _read_text_if_exists(report_base / "dpabi_template_library_report.md"),
    }
7. 修改 frontend/src/api.ts

新增：

export async function getDpabiTemplates(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/templates"
  );
}
8. 修改 frontend/src/components/DpabiPanel.tsx

新增导入：

import { getDpabiTemplates } from "../api";

如果已有 DPABI API import，请合并到同一个 import 中。

新增 state：

const [dpabiTemplates, setDpabiTemplates] = useState<Record<string, unknown> | null>(null);

新增函数：

async function handleLoadDpabiTemplates() {
  setError("");

  try {
    const result = await getDpabiTemplates(baseUrl);
    setDpabiTemplates(result);
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
  }
}

在 JSX 中新增：

<h3>DPABI Pipeline Template Library</h3>

<div className="row">
  <button onClick={handleLoadDpabiTemplates}>
    加载 DPABI Template Library
  </button>
</div>

<h3>Template Index</h3>
<JsonBlock
  value={dpabiTemplates?.template_index || capabilities?.template_index}
  emptyText="暂无 template index"
/>

<h3>Template Manifest</h3>
<TextViewer
  text={
    typeof dpabiTemplates?.template_manifest === "string"
      ? dpabiTemplates.template_manifest
      : typeof capabilities?.template_manifest === "string"
        ? capabilities.template_manifest
        : null
  }
  emptyText="暂无 template manifest"
/>

<h3>Template Library Report</h3>
<TextViewer
  text={
    typeof dpabiTemplates?.template_library_report === "string"
      ? dpabiTemplates.template_library_report
      : typeof report?.template_library_report === "string"
        ? report.template_library_report
        : null
  }
  emptyText="暂无 template library report"
/>
9. 新增轻量测试

创建文件：

tests/unit/test_dpabi_template_library.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.dpabi_template_library import write_dpabi_template_library


def test_dpabi_template_library_generates_template_for_promotable_wrapper(tmp_path: Path):
    work = tmp_path / "work"
    reports = tmp_path / "reports"
    dpabi = work / "dpabi"
    dpabi.mkdir(parents=True)

    matrix_path = dpabi / "dpabi_wrapper_compatibility_matrix.json"
    matrix_path.write_text(
        json.dumps({
            "rows": [
                {
                    "function_name": "y_Smooth",
                    "readiness": "PROMOTABLE_TO_TEMPLATE",
                    "wrapper_candidate": True,
                    "safety_classification": "SAFE_SINGLE_FUNCTION_CANDIDATE",
                },
                {
                    "function_name": "DPARSF_run",
                    "readiness": "BLOCKED",
                    "wrapper_candidate": False,
                    "safety_classification": "FULL_PIPELINE_BLOCKED",
                },
            ]
        }),
        encoding="utf-8",
    )

    result = write_dpabi_template_library(
        work_dir=str(work),
        report_dir=str(reports),
        matrix_path=str(matrix_path),
    )

    assert result["ok"] is True
    assert result["metrics"]["templates_total"] == 1

    index_path = work / "dpabi" / "templates" / "dpabi_template_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))

    assert index["templates_total"] == 1
    assert index["templates"][0]["function_name"] == "y_Smooth"

    template_path = Path(index["templates"][0]["template_path"])
    template_text = template_path.read_text(encoding="utf-8")

    assert "approved: false" in template_text
    assert "DPARSF_run" not in template_text
    assert "DPARSFA_run" not in template_text
10. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/dpabi/templates")

不要在 smoke test 中自动运行 template generation pipeline。

11. 更新 README.md

追加第二十五步说明：

## Step 25: DPABI Pipeline Template Library

This step generates reusable DPABI pipeline templates from validated wrapper compatibility evidence.

It does not execute DPABI.

### Run

```bash
python -m backend.app.tools.run_dpabi_template_library_cli

Expected outputs:

work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/dpabi_template_manifest.yaml
work/dpabi/templates/pipelines/dpabi_y_smooth_subject_wrapper_template.yaml
reports/dpabi/dpabi_template_library_report.md
work/pipeline_runs/run_dpabi_template_library_001/summary.json
API
curl http://127.0.0.1:8000/api/dpabi/templates
Frontend

Use the DPABI panel and load:

DPABI Pipeline Template Library
Safety

Generated templates:

are not executed automatically
default to approved=false
only target synthetic BIDS-like data
do not call DPARSF_run
do not call DPARSFA_run
do not call DPABI GUI
do not modify rawdata

---

## 12. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/dpabi_template_library_spec.md
backend/app/tools/dpabi_template_library.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_template_library.yaml
backend/app/tools/run_dpabi_template_library_cli.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/DpabiPanel.tsx
tests/unit/test_dpabi_template_library.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有 compatibility matrix：

python -m backend.app.tools.run_dpabi_wrapper_validation_cli

然后运行：

python -m backend.app.tools.run_dpabi_template_library_cli

成功后应生成：

work/dpabi/templates/dpabi_template_index.json
work/dpabi/templates/dpabi_template_manifest.yaml
work/dpabi/templates/pipelines/dpabi_y_smooth_subject_wrapper_template.yaml
reports/dpabi/dpabi_template_library_report.md
work/pipeline_runs/run_dpabi_template_library_001/summary.json

其中 template index 应包含：

{
  "templates_total": 1,
  "safety": {
    "templates_executed": false,
    "full_dpabi_execution": false,
    "dparsf_run_allowed": false,
    "dpabi_gui_allowed": false,
    "rawdata_modified": false,
    "files_deleted": false
  }
}

生成的 pipeline template 中必须包含：

approved: false
synthetic_only: true

并且不能包含：

DPARSF_run
DPARSFA_run

运行测试：

python -m pytest tests/unit/test_dpabi_template_library.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/templates

启动前端：

cd frontend
npm run dev

页面应该能完成：

DPABI Panel 显示 Pipeline Template Library 区域。
可以加载 template index。
可以显示 template manifest。
可以显示 template library report。
不自动执行任何 template。
template 默认 approved=false。
不运行完整 DPABI preprocessing。
不调用 DPARSF_run / DPARSFA_run。
不调用 DPABI GUI。
不修改 rawdata。
13. 重要限制

本步骤只做 DPABI pipeline template library。

不要实现：

自动执行 template
DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
真实医学影像处理
自动参数优化
修改 rawdata
修改 DPABI 源码
删除文件
生产级 template registry

完成后请总结：

新增了哪些文件
修改了哪些文件
template library 从哪些证据生成
哪些函数可以生成 template
为什么 template 必须 approved=false
如何从前端查看 template library
下一步如何做 template instantiation / approved execution

'''
Step 25 的主要目标是实现 DPABI Pipeline Template Library + Promotable Wrapper 模板化闭环 ，即将已验证的 DPABI 包装器函数转换为可复用的 Pipeline 模板。

## 这一步主要做什么
### 核心功能
1. 读取兼容性矩阵
   
   - 读取 work/dpabi/dpabi_wrapper_compatibility_matrix.json
   - 找出 readiness == PROMOTABLE_TO_TEMPLATE 的函数
2. 生成 Pipeline 模板
   
   - 为每个可提升的函数生成完整的 Pipeline 模板
   - 目前只允许： y_Smooth , rest_Smooth
   - 每个模板包含 7 个节点：
     - 创建合成 BIDS 数据集
     - 数据检查
     - 环境检查
     - DPABI 函数签名探测
     - 包装器合约生成
     - 主题级平滑（approved=false）
     - 报告生成
3. 模板安全元数据
   
   - synthetic_only: true - 只处理合成数据
   - requires_approval: true - 需要显式审批
   - approved_by_default: false - 默认为未审批
   - full_dpabi_execution: false - 不是完整 DPABI 执行
   - dparsf_run_allowed: false - 不调用 DPARSF_run
   - dpabi_gui_allowed: false - 不调用 DPABI GUI
### 解决的问题
这一步解决了以下问题：

- 如何将验证通过的包装器转化为可复用模板？ - 自动生成完整的 Pipeline 配置
- 如何确保模板安全性？ - 内置安全元数据，默认不执行，只处理合成数据
- 如何管理多个模板？ - 生成模板索引和清单文件
### 推广条件
一个函数会被提升为模板的条件：

- 就绪级别为 PROMOTABLE_TO_TEMPLATE
- 函数在白名单中（y_Smooth, rest_Smooth）
- 通过所有安全检查
### 安全规则
- 不执行生成的模板
- 不修改 rawdata
- 不修改 DPABI 源码
- 不删除文件
- 不推广被阻塞的函数
- 不推广 GUI 入口点
- 不推广完整 Pipeline 运行器
- 模板默认为 approved=false
- 模板只处理合成 BIDS-like 数据
这一步是 DPABI 集成的 最终模板化阶段 ，将前面所有验证工作的成果转化为可复用、可管理的 Pipeline 模板库。
'''