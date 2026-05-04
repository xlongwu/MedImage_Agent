你是我的工程搭建助手。前二十三步已经完成：

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

现在开始第二十四步。

第二十四步目标：实现“DPABI Wrapper Validation Suite + Function Compatibility Matrix 闭环”。

当前系统已经可以：

- 探测 DPABI 函数签名
- 生成 wrapper contracts
- 对 y_Smooth / rest_Smooth 做 sandbox 测试
- 对 synthetic subject 数据做 subject-level wrapper
- 生成 DPABI subject wrapper report

但还缺少一个关键工程能力：  
在不同 DPABI 版本、MATLAB 版本、函数签名变化的情况下，系统需要有一个稳定的 wrapper validation matrix，用来判断：

- 哪些 DPABI 函数被发现
- 哪些函数是 wrapper_candidate
- 哪些函数已经通过 sandbox test
- 哪些函数已经通过 subject-level synthetic test
- 哪些函数仍然 blocked
- 哪些函数需要人工 review
- 哪些函数可进入下一步 pipeline template

本步骤要实现：

- DPABI wrapper validation spec
- wrapper compatibility matrix 生成器
- 聚合 signature probe / contracts / sandbox result / subject wrapper result
- 生成 dpabi_wrapper_compatibility_matrix.json
- 生成 dpabi_wrapper_compatibility_matrix.csv
- 生成 dpabi_wrapper_validation_report.md
- 将 dpabi_wrapper_validation_matrix 作为 project-level pipeline node 接入
- 后端 API 暴露 wrapper validation matrix
- 前端 DPABI Panel 显示 compatibility matrix 和 validation report
- validation suite 增加 DPABI wrapper matrix 轻量测试

本步骤不要运行完整 DPABI pipeline。
本步骤不要调用 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。

---

## 1. 创建 specs/dpabi_wrapper_validation_spec.md

创建文件：

```text
specs/dpabi_wrapper_validation_spec.md

内容：

# DPABI Wrapper Validation Specification

This document defines the MVP DPABI wrapper validation matrix.

## Goals

The validation matrix summarizes the compatibility and readiness of DPABI wrapper functions.

It should answer:

- Which functions exist?
- Which functions are blocked?
- Which functions are wrapper candidates?
- Which functions passed sandbox testing?
- Which functions passed subject-level synthetic testing?
- Which functions need manual review?
- Which functions can be promoted to pipeline templates?

## Scope

Supported in this step:

- aggregate signature probe output
- aggregate wrapper contracts
- aggregate sandbox wrapper result
- aggregate subject-level wrapper result
- generate JSON matrix
- generate CSV matrix
- generate Markdown validation report
- API and frontend visibility
- lightweight validation test

Unsupported in this step:

- full DPABI preprocessing
- DPARSF_run execution
- DPARSFA_run execution
- GUI automation
- real medical image preprocessing
- rawdata modification
- DPABI source modification
- deletion of files

## Inputs

```text
work/dpabi/dpabi_function_signatures.json
work/dpabi/dpabi_wrapper_contracts.json
work/dpabi/single_function_sandbox/dpabi_single_function_result.json
reports/dpabi/dpabi_subject_wrapper_summary.json
Outputs
work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/dpabi_wrapper_compatibility_matrix.csv
reports/dpabi/dpabi_wrapper_validation_report.md
Readiness Levels
BLOCKED
MISSING
CONTRACT_ONLY
SANDBOX_PASSED
SUBJECT_SYNTHETIC_PASSED
MANUAL_REVIEW_REQUIRED
PROMOTABLE_TO_TEMPLATE
Promotion Rules

A function can be PROMOTABLE_TO_TEMPLATE only if:

it exists
it is a wrapper_candidate
it is not GUI_BLOCKED
it is not FULL_PIPELINE_BLOCKED
sandbox test passed
subject-level synthetic test passed, if subject-level test applies
Safety Rules
Do not execute DPABI.
Do not call DPARSF_run.
Do not call DPARSFA_run.
Do not call DPABI GUI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.

---

## 2. 创建 backend/app/tools/dpabi_wrapper_validation.py

创建文件：

```text
backend/app/tools/dpabi_wrapper_validation.py

目标：聚合 DPABI wrapper 相关输出，生成 compatibility matrix。

提供函数：

write_dpabi_wrapper_validation_matrix(
    work_dir: str,
    report_dir: str,
    signatures_path: str = "./work/dpabi/dpabi_function_signatures.json",
    contracts_path: str = "./work/dpabi/dpabi_wrapper_contracts.json",
    sandbox_result_path: str = "./work/dpabi/single_function_sandbox/dpabi_single_function_result.json",
    subject_wrapper_summary_path: str = "./reports/dpabi/dpabi_subject_wrapper_summary.json",
) -> dict

输出：

work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/dpabi_wrapper_compatibility_matrix.csv
reports/dpabi/dpabi_wrapper_validation_report.md

矩阵每行字段：

{
  "function_name": "y_Smooth",
  "category": "y_tools",
  "exists": true,
  "nargin": 3,
  "nargout": 0,
  "safety_classification": "SAFE_SINGLE_FUNCTION_CANDIDATE",
  "wrapper_candidate": true,
  "blocked_reason": "",
  "sandbox_tested": true,
  "sandbox_passed": true,
  "subject_tested": true,
  "subject_passed": true,
  "readiness": "PROMOTABLE_TO_TEMPLATE",
  "recommended_next_step": "add_to_pipeline_template_library"
}

实现要求：

如果某些输入文件不存在，不失败，记录 warnings。
contracts 是主数据源。
signatures 用来补充 nargin / nargout / help 信息。
sandbox result 只代表一个 function_name 的 sandbox 结果。
subject wrapper summary 可代表一个或多个 function_name 的 subject-level 结果。
如果函数是 GUI_BLOCKED 或 FULL_PIPELINE_BLOCKED，readiness 必须是 BLOCKED。
如果函数不存在，readiness 必须是 MISSING。
如果 wrapper_candidate=true 但没有 sandbox test，readiness 是 CONTRACT_ONLY。
如果 sandbox passed 但没有 subject-level test，readiness 是 SANDBOX_PASSED。
如果 subject-level test passed，且安全分类允许，readiness 是 PROMOTABLE_TO_TEMPLATE。
不执行 MATLAB。
不读取 rawdata。

参考实现：

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


BLOCKED_CLASSES = {"GUI_BLOCKED", "FULL_PIPELINE_BLOCKED"}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _signature_by_name(signatures: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not signatures:
        return {}
    return {
        item.get("name"): item
        for item in signatures.get("functions", [])
        if item.get("name")
    }


def _sandbox_status_by_function(sandbox: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not sandbox:
        return {}

    function_name = sandbox.get("function_name")
    if not function_name:
        return {}

    return {
        function_name: {
            "tested": True,
            "passed": bool(sandbox.get("ok")),
            "errors": sandbox.get("errors", []),
            "warnings": sandbox.get("warnings", []),
        }
    }


def _subject_status_by_function(summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not summary:
        return {}

    out: dict[str, dict[str, Any]] = {}

    for subject in summary.get("subjects", []):
        fn = subject.get("function_name", "unknown")
        item = out.setdefault(
            fn,
            {
                "tested": True,
                "subjects_total": 0,
                "subjects_success": 0,
                "subjects_failed": 0,
            },
        )

        item["subjects_total"] += 1
        if subject.get("ok"):
            item["subjects_success"] += 1
        else:
            item["subjects_failed"] += 1

    for fn, item in out.items():
        item["passed"] = item["subjects_total"] > 0 and item["subjects_failed"] == 0

    return out


def _determine_readiness(
    exists: bool,
    safety_classification: str,
    wrapper_candidate: bool,
    sandbox_tested: bool,
    sandbox_passed: bool,
    subject_tested: bool,
    subject_passed: bool,
) -> tuple[str, str]:
    if safety_classification in BLOCKED_CLASSES:
        return "BLOCKED", "do_not_execute"

    if not exists:
        return "MISSING", "skip_until_function_available"

    if not wrapper_candidate:
        return "MANUAL_REVIEW_REQUIRED", "manual_contract_review"

    if not sandbox_tested:
        return "CONTRACT_ONLY", "run_single_function_sandbox"

    if sandbox_tested and not sandbox_passed:
        return "MANUAL_REVIEW_REQUIRED", "review_sandbox_failure"

    if sandbox_passed and not subject_tested:
        return "SANDBOX_PASSED", "run_subject_level_synthetic_test"

    if subject_tested and not subject_passed:
        return "MANUAL_REVIEW_REQUIRED", "review_subject_level_failure"

    if subject_passed:
        return "PROMOTABLE_TO_TEMPLATE", "add_to_pipeline_template_library"

    return "MANUAL_REVIEW_REQUIRED", "manual_review"


def write_dpabi_wrapper_validation_matrix(
    work_dir: str,
    report_dir: str,
    signatures_path: str = "./work/dpabi/dpabi_function_signatures.json",
    contracts_path: str = "./work/dpabi/dpabi_wrapper_contracts.json",
    sandbox_result_path: str = "./work/dpabi/single_function_sandbox/dpabi_single_function_result.json",
    subject_wrapper_summary_path: str = "./reports/dpabi/dpabi_subject_wrapper_summary.json",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    sig_path = Path(signatures_path)
    con_path = Path(contracts_path)
    sandbox_path = Path(sandbox_result_path)
    subject_path = Path(subject_wrapper_summary_path)

    signatures = _read_json(sig_path)
    contracts = _read_json(con_path)
    sandbox = _read_json(sandbox_path)
    subject_summary = _read_json(subject_path)

    if not signatures:
        warnings.append(f"Missing or invalid signatures JSON: {sig_path}")

    if not contracts:
        return {
            "ok": False,
            "node_id": "dpabi_wrapper_validation_matrix",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid wrapper contracts JSON: {con_path}"],
        }

    if not sandbox:
        warnings.append(f"Missing sandbox result: {sandbox_path}")

    if not subject_summary:
        warnings.append(f"Missing subject wrapper summary: {subject_path}")

    sig_map = _signature_by_name(signatures)
    sandbox_map = _sandbox_status_by_function(sandbox)
    subject_map = _subject_status_by_function(subject_summary)

    rows: list[dict[str, Any]] = []

    for contract in contracts.get("contracts", []):
        function_name = contract.get("function_name")
        signature = sig_map.get(function_name, {})
        sandbox_status = sandbox_map.get(function_name, {"tested": False, "passed": False})
        subject_status = subject_map.get(function_name, {"tested": False, "passed": False})

        exists = bool(contract.get("exists"))
        safety_classification = str(contract.get("safety_classification", "UNKNOWN_REVIEW_REQUIRED"))
        wrapper_candidate = bool(contract.get("wrapper_candidate"))

        readiness, recommended_next_step = _determine_readiness(
            exists=exists,
            safety_classification=safety_classification,
            wrapper_candidate=wrapper_candidate,
            sandbox_tested=bool(sandbox_status.get("tested")),
            sandbox_passed=bool(sandbox_status.get("passed")),
            subject_tested=bool(subject_status.get("tested")),
            subject_passed=bool(subject_status.get("passed")),
        )

        rows.append({
            "function_name": function_name,
            "category": contract.get("category"),
            "exists": exists,
            "which_path": contract.get("which_path"),
            "nargin": contract.get("nargin", signature.get("nargin")),
            "nargout": contract.get("nargout", signature.get("nargout")),
            "safety_classification": safety_classification,
            "wrapper_candidate": wrapper_candidate,
            "blocked_reason": contract.get("blocked_reason", ""),
            "sandbox_tested": bool(sandbox_status.get("tested")),
            "sandbox_passed": bool(sandbox_status.get("passed")),
            "subject_tested": bool(subject_status.get("tested")),
            "subject_passed": bool(subject_status.get("passed")),
            "subjects_total": subject_status.get("subjects_total"),
            "subjects_success": subject_status.get("subjects_success"),
            "subjects_failed": subject_status.get("subjects_failed"),
            "readiness": readiness,
            "recommended_next_step": recommended_next_step,
        })

    out_dir = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "dpabi_wrapper_compatibility_matrix.json"
    csv_path = out_dir / "dpabi_wrapper_compatibility_matrix.csv"
    report_path = report_out / "dpabi_wrapper_validation_report.md"

    payload = {
        "ok": True,
        "node_id": "dpabi_wrapper_validation_matrix",
        "backend": "python",
        "matrix_total": len(rows),
        "promotable_total": sum(1 for row in rows if row["readiness"] == "PROMOTABLE_TO_TEMPLATE"),
        "blocked_total": sum(1 for row in rows if row["readiness"] == "BLOCKED"),
        "manual_review_total": sum(1 for row in rows if row["readiness"] == "MANUAL_REVIEW_REQUIRED"),
        "rows": rows,
        "warnings": warnings,
        "errors": errors,
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "function_name",
        "category",
        "exists",
        "nargin",
        "nargout",
        "safety_classification",
        "wrapper_candidate",
        "blocked_reason",
        "sandbox_tested",
        "sandbox_passed",
        "subject_tested",
        "subject_passed",
        "subjects_total",
        "subjects_success",
        "subjects_failed",
        "readiness",
        "recommended_next_step",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    lines = []
    lines.append("# DPABI Wrapper Validation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Matrix total: {payload['matrix_total']}")
    lines.append(f"- Promotable total: {payload['promotable_total']}")
    lines.append(f"- Blocked total: {payload['blocked_total']}")
    lines.append(f"- Manual review total: {payload['manual_review_total']}")
    lines.append("")
    lines.append("## Compatibility Matrix")
    lines.append("")
    lines.append("| Function | Exists | Candidate | Sandbox | Subject | Readiness | Next Step |")
    lines.append("|---|---:|---:|---:|---:|---|---|")

    for row in rows:
        lines.append(
            f"| {row['function_name']} | {row['exists']} | {row['wrapper_candidate']} | "
            f"{row['sandbox_passed']} | {row['subject_passed']} | "
            f"{row['readiness']} | {row['recommended_next_step']} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This validation matrix does not execute DPABI. It only summarizes existing wrapper evidence.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_wrapper_validation_matrix",
        "backend": "python",
        "outputs": [str(json_path), str(csv_path), str(report_path)],
        "metrics": {
            "matrix_total": payload["matrix_total"],
            "promotable_total": payload["promotable_total"],
            "blocked_total": payload["blocked_total"],
            "manual_review_total": payload["manual_review_total"],
        },
        "warnings": warnings,
        "errors": errors,
    }
3. 修改 backend/app/runtime/node_registry.py

新增节点：

dpabi_wrapper_validation_matrix

新增导入：

from backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix

新增 runner：

def run_dpabi_wrapper_validation_matrix_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = write_dpabi_wrapper_validation_matrix(
        work_dir=context.work_dir,
        report_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        signatures_path=node.params.get("signatures_path", f"{context.work_dir}/dpabi/dpabi_function_signatures.json"),
        contracts_path=node.params.get("contracts_path", f"{context.work_dir}/dpabi/dpabi_wrapper_contracts.json"),
        sandbox_result_path=node.params.get("sandbox_result_path", f"{context.work_dir}/dpabi/single_function_sandbox/dpabi_single_function_result.json"),
        subject_wrapper_summary_path=node.params.get("subject_wrapper_summary_path", "./reports/dpabi/dpabi_subject_wrapper_summary.json"),
    )
    result["node_id"] = node.id
    return result

更新 NODE_REGISTRY：

"dpabi_wrapper_validation_matrix": run_dpabi_wrapper_validation_matrix_node,
4. 创建 examples/pipeline_dpabi_wrapper_validation.yaml

创建文件：

examples/pipeline_dpabi_wrapper_validation.yaml

内容：

pipeline_id: dpabi_wrapper_validation_pipeline
version: "0.1.0"
modality: integration-test
description: "Generate DPABI wrapper compatibility matrix from signatures, contracts, sandbox tests, and subject wrapper results."

execution:
  stop_on_failure: true
  run_id: "run_dpabi_wrapper_validation_001"
  scheduler:
    mode: "sequential"
    max_workers: 1
    matlab_max_workers: 1

nodes:
  - id: dpabi_wrapper_validation_matrix
    name: DPABI Wrapper Validation Matrix
    agent: dpabi-runner
    backend: python
    depends_on: []
    inputs:
      - "./work/dpabi/dpabi_function_signatures.json"
      - "./work/dpabi/dpabi_wrapper_contracts.json"
      - "./work/dpabi/single_function_sandbox/dpabi_single_function_result.json"
      - "./reports/dpabi/dpabi_subject_wrapper_summary.json"
    outputs:
      - "./work/dpabi/dpabi_wrapper_compatibility_matrix.json"
      - "./work/dpabi/dpabi_wrapper_compatibility_matrix.csv"
      - "./reports/dpabi/dpabi_wrapper_validation_report.md"
    params:
      signatures_path: "./work/dpabi/dpabi_function_signatures.json"
      contracts_path: "./work/dpabi/dpabi_wrapper_contracts.json"
      sandbox_result_path: "./work/dpabi/single_function_sandbox/dpabi_single_function_result.json"
      subject_wrapper_summary_path: "./reports/dpabi/dpabi_subject_wrapper_summary.json"
    parallel_level: project
    gpu_supported: false
    cache: false
5. 创建 backend/app/tools/run_dpabi_wrapper_validation_cli.py

创建文件：

backend/app/tools/run_dpabi_wrapper_validation_cli.py

内容：

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_dpabi_wrapper_validation.yaml")

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

"wrapper_compatibility_matrix": _read_json_if_exists(base / "dpabi_wrapper_compatibility_matrix.json"),
"wrapper_compatibility_csv": _read_text_if_exists(base / "dpabi_wrapper_compatibility_matrix.csv"),

让 /api/reports/dpabi 新增返回：

"wrapper_validation_report": _read_text_if_exists(base / "dpabi_wrapper_validation_report.md"),

新增 API：

GET /api/dpabi/wrapper-validation

路由：

@router.get("/api/dpabi/wrapper-validation")
def api_get_dpabi_wrapper_validation() -> dict[str, Any]:
    work_base = Path("work") / "dpabi"
    report_base = Path("reports") / "dpabi"

    return {
        "ok": True,
        "matrix": _read_json_if_exists(work_base / "dpabi_wrapper_compatibility_matrix.json"),
        "csv": _read_text_if_exists(work_base / "dpabi_wrapper_compatibility_matrix.csv"),
        "report": _read_text_if_exists(report_base / "dpabi_wrapper_validation_report.md"),
    }
7. 修改 frontend/src/api.ts

新增：

export async function getDpabiWrapperValidation(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/wrapper-validation"
  );
}
8. 修改 frontend/src/components/DpabiPanel.tsx

新增导入：

import { getDpabiWrapperValidation } from "../api";

如果已有 DPABI API import，请合并到同一个 import 中。

新增 state：

const [wrapperValidation, setWrapperValidation] = useState<Record<string, unknown> | null>(null);

新增函数：

async function handleLoadWrapperValidation() {
  setError("");

  try {
    const result = await getDpabiWrapperValidation(baseUrl);
    setWrapperValidation(result);
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
  }
}

在 JSX 中新增：

<h3>DPABI Wrapper Compatibility Matrix</h3>

<div className="row">
  <button onClick={handleLoadWrapperValidation}>
    加载 Wrapper Validation Matrix
  </button>
</div>

<JsonBlock
  value={wrapperValidation?.matrix || capabilities?.wrapper_compatibility_matrix}
  emptyText="暂无 wrapper compatibility matrix"
/>

<h3>DPABI Wrapper Compatibility CSV</h3>
<TextViewer
  text={
    typeof wrapperValidation?.csv === "string"
      ? wrapperValidation.csv
      : typeof capabilities?.wrapper_compatibility_csv === "string"
        ? capabilities.wrapper_compatibility_csv
        : null
  }
  emptyText="暂无 wrapper compatibility CSV"
/>

<h3>DPABI Wrapper Validation Report</h3>
<TextViewer
  text={
    typeof wrapperValidation?.report === "string"
      ? wrapperValidation.report
      : typeof report?.wrapper_validation_report === "string"
        ? report.wrapper_validation_report
        : null
  }
  emptyText="暂无 wrapper validation report"
/>
9. 修改 tests/unit/test_memory_store.py 之外新增轻量测试

创建文件：

tests/unit/test_dpabi_wrapper_validation.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.dpabi_wrapper_validation import write_dpabi_wrapper_validation_matrix


def test_dpabi_wrapper_validation_matrix_promotes_passed_wrapper(tmp_path: Path):
    work = tmp_path / "work"
    reports = tmp_path / "reports"
    dpabi = work / "dpabi"
    report_dpabi = reports / "dpabi"
    dpabi.mkdir(parents=True)
    report_dpabi.mkdir(parents=True)

    signatures_path = dpabi / "dpabi_function_signatures.json"
    contracts_path = dpabi / "dpabi_wrapper_contracts.json"
    sandbox_path = dpabi / "single_function_sandbox" / "dpabi_single_function_result.json"
    sandbox_path.parent.mkdir(parents=True)
    subject_summary_path = report_dpabi / "dpabi_subject_wrapper_summary.json"

    signatures_path.write_text(
        json.dumps({
            "functions": [
                {
                    "name": "y_Smooth",
                    "category": "y_tools",
                    "exists": True,
                    "nargin": 3,
                    "nargout": 0,
                }
            ]
        }),
        encoding="utf-8",
    )

    contracts_path.write_text(
        json.dumps({
            "contracts": [
                {
                    "function_name": "y_Smooth",
                    "category": "y_tools",
                    "exists": True,
                    "which_path": "/fake/y_Smooth.m",
                    "nargin": 3,
                    "nargout": 0,
                    "safety_classification": "SAFE_SINGLE_FUNCTION_CANDIDATE",
                    "wrapper_candidate": True,
                    "blocked_reason": "",
                }
            ]
        }),
        encoding="utf-8",
    )

    sandbox_path.write_text(
        json.dumps({
            "ok": True,
            "function_name": "y_Smooth",
        }),
        encoding="utf-8",
    )

    subject_summary_path.write_text(
        json.dumps({
            "subjects": [
                {"subject_id": "sub-001", "ok": True, "function_name": "y_Smooth"},
                {"subject_id": "sub-002", "ok": True, "function_name": "y_Smooth"},
            ]
        }),
        encoding="utf-8",
    )

    result = write_dpabi_wrapper_validation_matrix(
        work_dir=str(work),
        report_dir=str(reports),
        signatures_path=str(signatures_path),
        contracts_path=str(contracts_path),
        sandbox_result_path=str(sandbox_path),
        subject_wrapper_summary_path=str(subject_summary_path),
    )

    assert result["ok"] is True

    matrix = json.loads(
        (dpabi / "dpabi_wrapper_compatibility_matrix.json").read_text(encoding="utf-8")
    )

    assert matrix["promotable_total"] == 1
    assert matrix["rows"][0]["readiness"] == "PROMOTABLE_TO_TEMPLATE"
10. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/dpabi/wrapper-validation")

不要在 smoke test 中自动运行 wrapper validation pipeline。

11. 更新 README.md

追加第二十四步说明：

## Step 24: DPABI Wrapper Validation Matrix

This step aggregates DPABI wrapper evidence into a compatibility matrix.

It does not run DPABI.

### Run

```bash
python -m backend.app.tools.run_dpabi_wrapper_validation_cli

Expected outputs:

work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/dpabi_wrapper_compatibility_matrix.csv
reports/dpabi/dpabi_wrapper_validation_report.md
work/pipeline_runs/run_dpabi_wrapper_validation_001/summary.json
API
curl http://127.0.0.1:8000/api/dpabi/wrapper-validation
Frontend

Use the DPABI panel and load:

DPABI Wrapper Compatibility Matrix
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
specs/dpabi_wrapper_validation_spec.md
backend/app/tools/dpabi_wrapper_validation.py
backend/app/runtime/node_registry.py
examples/pipeline_dpabi_wrapper_validation.yaml
backend/app/tools/run_dpabi_wrapper_validation_cli.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/DpabiPanel.tsx
tests/unit/test_dpabi_wrapper_validation.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有 wrapper evidence：

python -m backend.app.tools.run_dpabi_signature_probe_cli
python -m backend.app.tools.run_dpabi_single_function_sandbox_cli examples/project_config_dataset.yaml examples/pipeline_dpabi_single_function_sandbox.yaml y_Smooth --approve
python -m backend.app.tools.run_dpabi_subject_wrapper_cli examples/project_config_dataset.yaml examples/pipeline_dpabi_subject_wrapper.yaml y_Smooth --approve

然后运行：

python -m backend.app.tools.run_dpabi_wrapper_validation_cli

成功后应生成：

work/dpabi/dpabi_wrapper_compatibility_matrix.json
work/dpabi/dpabi_wrapper_compatibility_matrix.csv
reports/dpabi/dpabi_wrapper_validation_report.md
work/pipeline_runs/run_dpabi_wrapper_validation_001/summary.json

其中 JSON 应包含：

{
  "node_id": "dpabi_wrapper_validation_matrix",
  "matrix_total": 1,
  "promotable_total": 1,
  "rows": []
}

如果 y_Smooth sandbox 和 subject-level test 都通过，则 y_Smooth 的 readiness 应为：

PROMOTABLE_TO_TEMPLATE

如果函数是 DPARSF_run 或 DPARSFA_run，readiness 必须是：

BLOCKED

运行测试：

python -m pytest tests/unit/test_dpabi_wrapper_validation.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/dpabi/wrapper-validation

启动前端：

cd frontend
npm run dev

页面应该能完成：

DPABI Panel 显示 Wrapper Compatibility Matrix。
可以加载 matrix JSON。
可以显示 CSV。
可以显示 validation report。
不运行完整 DPABI preprocessing。
不调用 DPARSF_run / DPARSFA_run。
不调用 DPABI GUI。
不读取或修改真实 rawdata。
13. 重要限制

本步骤只做 DPABI wrapper validation matrix。

不要实现：

DPABI 全流程执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
DPABI GUI 自动化
新 DPABI 函数执行
真实医学影像处理
自动参数优化
修改 rawdata
修改 DPABI 源码
删除文件

完成后请总结：

新增了哪些文件
修改了哪些文件
compatibility matrix 聚合了哪些证据
readiness 如何判断
什么情况下函数可以 PROMOTABLE_TO_TEMPLATE
为什么 DPARSF_run / DPARSFA_run 仍然必须 BLOCKED
下一步如何把 promotable wrapper 加入 pipeline template library

'''
Step 24 的主要目标是实现 DPABI Wrapper Validation Suite + Function Compatibility Matrix 闭环 ，即 DPABI 包装器验证套件 + 函数兼容性矩阵闭环。

## 这一步主要做什么
### 核心功能
1. 聚合所有 DPABI 包装器证据
   
   - 读取函数签名探测结果（Step 21）
   - 读取包装器合约（Step 21）
   - 读取单函数沙盒测试结果（Step 22）
   - 读取主题级包装器结果（Step 23）
2. 确定函数就绪级别 为每个 DPABI 函数判定以下状态之一：
   
   - BLOCKED - 被阻塞（GUI 或完整 Pipeline）
   - MISSING - 函数不存在
   - CONTRACT_ONLY - 只有合约，未测试
   - SANDBOX_PASSED - 沙盒测试通过
   - SUBJECT_SYNTHETIC_PASSED - 主题级测试通过
   - MANUAL_REVIEW_REQUIRED - 需要人工审核
   - PROMOTABLE_TO_TEMPLATE - 可提升到 Pipeline 模板库
3. 生成兼容性矩阵
   
   - JSON 格式： work/dpabi/dpabi_wrapper_compatibility_matrix.json
   - CSV 格式： work/dpabi/dpabi_wrapper_compatibility_matrix.csv
   - Markdown 报告： reports/dpabi/dpabi_wrapper_validation_report.md
### 推广规则
一个函数可以被标记为 PROMOTABLE_TO_TEMPLATE （可提升到模板库）的条件：

- 函数存在
- 是 wrapper_candidate（包装候选）
- 不是 GUI_BLOCKED
- 不是 FULL_PIPELINE_BLOCKED
- 沙盒测试通过
- 主题级合成测试通过（如适用）
### 解决的问题
这一步解决了以下问题：

- 哪些函数可以安全地包装？ - 通过就绪级别一目了然
- 下一步应该做什么？ - 每个函数都有推荐的下一步操作
- 哪些函数可以加入 Pipeline 模板？ - PROMOTABLE_TO_TEMPLATE 状态的函数
### 安全规则
- 不执行 DPABI
- 不调用 DPARSF_run 或 DPARSFA_run
- 不调用 DPABI GUI
- 不修改 rawdata
- 不修改 DPABI 源码
- 不删除文件
- 只聚合现有的包装器证据
这一步是整个 DPABI 集成工作的 总结和验收 ，通过兼容性矩阵可以清晰地看到所有函数的验证状态和下一步行动计划。
'''