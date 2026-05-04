你是我的工程搭建助手。前三十一步已经完成：

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
Step 15：完成 GPU ALFF / fALFF CPU fallback + Benchmark 闭环。
Step 16：完成 Validation / Benchmark / Regression Suite 闭环。
Step 17：完成 DPABI Capability Inspector + Wrapper Scaffold 闭环。
Step 18：完成 DPABI Dataset Adapter + Batch Config Preflight 闭环。
Step 19：完成 DPABI 参数审查 + Approved Run Plan 闭环。
Step 20：完成 DPABI Approved Sandbox Smoke Run + Execution Audit 闭环。
Step 21：完成 DPABI Function Signature Probe + Wrapper Contract Registry 闭环。
Step 22：完成 DPABI Single-Function Wrapper Sandbox + Contract Test 闭环。
Step 23：完成 DPABI Single-Function Subject Wrapper + SPM Baseline Comparison 闭环。
Step 24：完成 DPABI Wrapper Validation Suite + Function Compatibility Matrix 闭环。
Step 25：完成 DPABI Pipeline Template Library + Promotable Wrapper 模板化闭环。
Step 26：完成 DPABI Template Instantiation + Approved Synthetic Execution 闭环。
Step 27：完成 DPABI Parameterized Pipeline Wizard + Review UI 闭环。
Step 28：完成 Multi-Run Experiment Tracking + Comparison Dashboard 闭环。
Step 29：完成 Experiment Dashboard 图表化 + 趋势分析闭环。
Step 30：完成 Run Artifact Browser + File Preview 闭环。
Step 31：完成 Project Packaging + Reproducibility Bundle 闭环。

现在开始第三十二步。

第三十二步目标：实现“Release Checklist + Deployment Readiness 闭环”。

当前系统已经具备完整的：

- pipeline runtime
- DPABI wrapper safety gates
- template library
- template wizard
- experiment tracking
- artifact browser
- reproducibility bundle

但还缺少部署前的统一审查能力。  
本步骤要新增一个 release readiness 层，用来回答：

- 项目核心文件是否齐全？
- specs 是否齐全？
- README 是否覆盖关键功能？
- 后端 API 是否有 smoke test 覆盖？
- 前端关键面板是否存在？
- DPABI safety gates 是否仍然有效？
- generated templates 是否默认 approved=false？
- bundle 是否排除了 rawdata / third_party？
- artifact browser 是否禁止任意路径？
- 是否存在明显的 deployment blocker？
- 当前项目是否适合演示、交付或进入下一阶段真实数据适配？

本步骤要实现：

- release readiness spec
- release checklist YAML
- deployment readiness scanner
- safety gate audit
- API surface checklist
- frontend surface checklist
- reproducibility checklist
- release readiness JSON
- release readiness Markdown report
- 后端 API 暴露 release readiness
- 前端新增 Release Readiness Panel
- validation suite 增加 release readiness 轻量测试

本步骤只做读取、扫描、校验和报告。
本步骤不要执行新的 pipeline。
本步骤不要启动 MATLAB。
本步骤不要运行 DPABI。
本步骤不要运行 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。
本步骤不要自动部署。
本步骤不要上传云端。

---

## 1. 创建 specs/release_readiness_spec.md

创建文件：

```text
specs/release_readiness_spec.md

内容：

# Release Readiness Specification

This document defines the MVP release checklist and deployment readiness scanner.

## Goals

The release readiness scanner should verify that MedImage Agent is ready for demo, handoff, or deployment preparation.

It should check:

- required project structure
- required specs
- backend tools
- API routes
- frontend panels
- unit tests
- reproducibility bundle
- artifact browser
- experiment dashboard
- DPABI safety gates
- template approval defaults
- blocked DPABI full-pipeline execution paths

## Scope

Supported in this step:

- static release checklist
- file existence checks
- safety string scan
- generated template safety check
- reproducibility bundle check
- artifact index check
- experiment dashboard check
- API and frontend visibility
- Markdown readiness report
- lightweight unit test

Unsupported in this step:

- automatic deployment
- cloud upload
- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- real medical image processing
- rawdata modification
- file deletion

## Outputs

```text
work/release/release_checklist.yaml
work/release/release_readiness.json
reports/release/release_readiness_report.md
Readiness Status
READY: no blockers and only minor warnings
WARNING: no blockers but meaningful warnings exist
BLOCKED: at least one deployment blocker exists
Required Safety Guarantees

The scanner should verify:

generated templates default to approved=false
DPARSF_run / DPARSFA_run are blocked in wrapper contracts
template library does not promote full pipeline runners
artifact browser rejects path traversal
bundles exclude rawdata and third_party
release scanner itself does not execute pipelines or MATLAB
Safety Rules
Do not execute pipelines.
Do not launch MATLAB.
Do not run DPABI.
Do not call DPABI GUI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Do not deploy automatically.

---

## 2. 创建 backend/app/tools/release_readiness.py

创建文件：

```text
backend/app/tools/release_readiness.py

目标：扫描项目结构、关键功能、safety gates 和 release blocker。

提供函数：

build_release_readiness(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    frontend_dir: str = "./frontend",
) -> dict

输出：

work/release/release_checklist.yaml
work/release/release_readiness.json
reports/release/release_readiness_report.md

实现要求：

不执行 pipeline。
不启动 MATLAB。
不运行 DPABI。
不删除文件。
检查核心目录：
backend/app
frontend/src
matlab
specs
examples
tests/unit
检查关键文件：
README.md
backend/app/main.py
backend/app/api/routes.py
frontend/src/App.tsx
examples/project_config_dataset.yaml
检查关键 specs 是否存在。
检查关键 tools 是否存在。
检查关键前端面板是否存在。
检查关键测试文件是否存在。
检查 DPABI safety：
dpabi_wrapper_contracts.json 中 DPARSF_run / DPARSFA_run 如果存在，必须 FULL_PIPELINE_BLOCKED。
template YAML 中 dpabi_subject_smooth.params.approved 必须 false。
template YAML 不应该包含 DPARSF_run / DPARSFA_run。
检查 artifact browser：
artifact_browser.py 存在。
test_artifact_browser.py 存在。
检查 reproducibility bundle：
reproducibility_bundle.py 存在。
bundle_index.json 如果存在，则至少能读取。
生成 blockers / warnings / passed_checks。
readiness_score 可简单计算：
passed / total * 100
status 规则：
blockers > 0：BLOCKED
warnings > 0：WARNING
否则 READY

参考实现：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_DIRS = [
    "backend/app",
    "backend/app/api",
    "backend/app/tools",
    "backend/app/runtime",
    "frontend/src",
    "frontend/src/components",
    "matlab",
    "specs",
    "examples",
    "tests/unit",
]

REQUIRED_FILES = [
    "README.md",
    "backend/app/main.py",
    "backend/app/api/routes.py",
    "backend/app/api/models.py",
    "backend/app/runtime/node_registry.py",
    "frontend/src/App.tsx",
    "frontend/src/api.ts",
    "examples/project_config_dataset.yaml",
]

REQUIRED_SPECS = [
    "specs/dpabi_preflight_spec.md",
    "specs/dpabi_run_plan_spec.md",
    "specs/dpabi_execution_sandbox_spec.md",
    "specs/dpabi_signature_probe_spec.md",
    "specs/dpabi_single_function_wrapper_spec.md",
    "specs/dpabi_subject_wrapper_spec.md",
    "specs/dpabi_wrapper_validation_spec.md",
    "specs/dpabi_template_library_spec.md",
    "specs/dpabi_template_instantiation_spec.md",
    "specs/dpabi_pipeline_wizard_spec.md",
    "specs/experiment_tracking_spec.md",
    "specs/experiment_dashboard_spec.md",
    "specs/artifact_browser_spec.md",
    "specs/reproducibility_bundle_spec.md",
    "specs/release_readiness_spec.md",
]

REQUIRED_TOOLS = [
    "backend/app/tools/dpabi_adapter.py",
    "backend/app/tools/dpabi_preflight.py",
    "backend/app/tools/dpabi_run_plan.py",
    "backend/app/tools/dpabi_sandbox_runner.py",
    "backend/app/tools/dpabi_signature_runner.py",
    "backend/app/tools/dpabi_contract_registry.py",
    "backend/app/tools/dpabi_single_function_runner.py",
    "backend/app/tools/dpabi_subject_wrapper.py",
    "backend/app/tools/dpabi_wrapper_validation.py",
    "backend/app/tools/dpabi_template_library.py",
    "backend/app/tools/dpabi_template_instantiator.py",
    "backend/app/tools/dpabi_template_wizard.py",
    "backend/app/tools/experiment_tracker.py",
    "backend/app/tools/experiment_dashboard.py",
    "backend/app/tools/artifact_browser.py",
    "backend/app/tools/reproducibility_bundle.py",
    "backend/app/tools/release_readiness.py",
]

REQUIRED_FRONTEND = [
    "frontend/src/components/DpabiPanel.tsx",
    "frontend/src/components/DpabiTemplateWizard.tsx",
    "frontend/src/components/ExperimentPanel.tsx",
    "frontend/src/components/ExperimentDashboard.tsx",
    "frontend/src/components/ArtifactBrowser.tsx",
    "frontend/src/components/ReproducibilityBundlePanel.tsx",
]

REQUIRED_TESTS = [
    "tests/unit/test_dpabi_wrapper_validation.py",
    "tests/unit/test_dpabi_template_library.py",
    "tests/unit/test_dpabi_template_instantiator.py",
    "tests/unit/test_dpabi_template_wizard.py",
    "tests/unit/test_experiment_tracker.py",
    "tests/unit/test_experiment_dashboard.py",
    "tests/unit/test_artifact_browser.py",
    "tests/unit/test_reproducibility_bundle.py",
]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_exists(path_text: str, kind: str) -> dict[str, Any]:
    path = Path(path_text)
    return {
        "name": path_text,
        "kind": kind,
        "ok": path.exists(),
        "message": "exists" if path.exists() else "missing",
    }


def _safe_read_text(path: Path, max_chars: int = 300_000) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception:
        return ""


def _check_dpabi_contract_safety(work_dir: str) -> list[dict[str, Any]]:
    checks = []
    contracts_path = Path(work_dir) / "dpabi" / "dpabi_wrapper_contracts.json"
    contracts = _read_json(contracts_path)

    if not contracts:
        checks.append({
            "name": "dpabi_wrapper_contracts_readable",
            "ok": False,
            "severity": "warning",
            "message": f"Missing or unreadable: {contracts_path}",
        })
        return checks

    for fn in ["DPARSF_run", "DPARSFA_run"]:
        match = None
        for item in contracts.get("contracts", []):
            if item.get("function_name") == fn:
                match = item
                break

        if match is None:
            checks.append({
                "name": f"{fn}_contract_missing",
                "ok": True,
                "severity": "info",
                "message": f"{fn} was not found in contracts.",
            })
        else:
            ok = match.get("safety_classification") == "FULL_PIPELINE_BLOCKED"
            checks.append({
                "name": f"{fn}_blocked",
                "ok": ok,
                "severity": "blocker" if not ok else "info",
                "message": f"{fn} safety_classification={match.get('safety_classification')}",
            })

    return checks


def _check_template_safety(work_dir: str) -> list[dict[str, Any]]:
    checks = []
    template_root = Path(work_dir) / "dpabi" / "templates" / "pipelines"

    if not template_root.exists():
        checks.append({
            "name": "template_pipeline_dir_exists",
            "ok": False,
            "severity": "warning",
            "message": f"Missing template directory: {template_root}",
        })
        return checks

    for path in sorted(template_root.glob("*.yaml")):
        text = _safe_read_text(path)

        has_approved_false = "approved: false" in text
        has_dparsf_run = "DPARSF_run" in text or "DPARSFA_run" in text

        checks.append({
            "name": f"template_approved_false:{path.name}",
            "ok": has_approved_false,
            "severity": "blocker" if not has_approved_false else "info",
            "message": "template defaults approved=false" if has_approved_false else "template does not contain approved: false",
        })

        checks.append({
            "name": f"template_no_dparsf:{path.name}",
            "ok": not has_dparsf_run,
            "severity": "blocker" if has_dparsf_run else "info",
            "message": "no DPARSF_run/DPARSFA_run token found" if not has_dparsf_run else "template contains DPARSF_run or DPARSFA_run",
        })

    return checks


def _check_bundle_safety(work_dir: str) -> list[dict[str, Any]]:
    checks = []
    index_path = Path(work_dir) / "bundles" / "bundle_index.json"
    index = _read_json(index_path)

    if not index:
        checks.append({
            "name": "bundle_index_readable",
            "ok": False,
            "severity": "warning",
            "message": f"No bundle index found at {index_path}",
        })
        return checks

    checks.append({
        "name": "bundle_index_readable",
        "ok": True,
        "severity": "info",
        "message": f"bundles_total={index.get('bundles_total')}",
    })

    for bundle in index.get("bundles", []):
        manifest = _read_json(Path(bundle.get("manifest_path", "")))
        if not manifest:
            checks.append({
                "name": f"bundle_manifest_readable:{bundle.get('bundle_id')}",
                "ok": False,
                "severity": "warning",
                "message": "bundle manifest missing or unreadable",
            })
            continue

        safety = manifest.get("safety", {})
        ok = (
            safety.get("rawdata_packaged") is False
            and safety.get("third_party_packaged") is False
            and safety.get("pipelines_executed") is False
            and safety.get("matlab_launched") is False
        )

        checks.append({
            "name": f"bundle_safety:{bundle.get('bundle_id')}",
            "ok": ok,
            "severity": "blocker" if not ok else "info",
            "message": f"safety={safety}",
        })

    return checks


def _write_checklist_yaml(path: Path, payload: dict[str, Any]) -> None:
    lines = []
    lines.append('version: "0.1.0"')
    lines.append(f"status: {payload['status']}")
    lines.append(f"readiness_score: {payload['readiness_score']}")
    lines.append("checks:")
    for check in payload.get("checks", []):
        lines.append(f"  - name: \"{str(check.get('name')).replace('\"', '\\\"')}\"")
        lines.append(f"    ok: {'true' if check.get('ok') else 'false'}")
        lines.append(f"    severity: \"{check.get('severity', 'info')}\"")
        lines.append(f"    message: \"{str(check.get('message', '')).replace('\"', '\\\"')}\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_release_readiness(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    frontend_dir: str = "./frontend",
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    for item in REQUIRED_DIRS:
        check = _check_exists(item, "directory")
        check["severity"] = "blocker"
        checks.append(check)

    for item in REQUIRED_FILES:
        check = _check_exists(item, "file")
        check["severity"] = "blocker"
        checks.append(check)

    for item in REQUIRED_SPECS:
        check = _check_exists(item, "spec")
        check["severity"] = "warning"
        checks.append(check)

    for item in REQUIRED_TOOLS:
        check = _check_exists(item, "tool")
        check["severity"] = "blocker"
        checks.append(check)

    for item in REQUIRED_FRONTEND:
        check = _check_exists(item, "frontend")
        check["severity"] = "warning"
        checks.append(check)

    for item in REQUIRED_TESTS:
        check = _check_exists(item, "test")
        check["severity"] = "warning"
        checks.append(check)

    checks.extend(_check_dpabi_contract_safety(work_dir))
    checks.extend(_check_template_safety(work_dir))
    checks.extend(_check_bundle_safety(work_dir))

    artifact_index = Path(work_dir) / "artifacts" / "artifact_index.json"
    checks.append({
        "name": "artifact_index_exists",
        "kind": "artifact",
        "ok": artifact_index.exists(),
        "severity": "warning",
        "message": str(artifact_index),
    })

    experiment_dashboard = Path(work_dir) / "experiments" / "dashboard_data.json"
    checks.append({
        "name": "experiment_dashboard_exists",
        "kind": "experiment",
        "ok": experiment_dashboard.exists(),
        "severity": "warning",
        "message": str(experiment_dashboard),
    })

    for check in checks:
        if not check.get("ok"):
            if check.get("severity") == "blocker":
                blockers.append(f"{check.get('name')}: {check.get('message')}")
            else:
                warnings.append(f"{check.get('name')}: {check.get('message')}")

    total = len(checks)
    passed = sum(1 for item in checks if item.get("ok"))
    readiness_score = round((passed / total) * 100, 2) if total else 0.0

    if blockers:
        status = "BLOCKED"
    elif warnings:
        status = "WARNING"
    else:
        status = "READY"

    out_dir = Path(work_dir) / "release"
    report_out = Path(report_dir) / "release"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    checklist_path = out_dir / "release_checklist.yaml"
    json_path = out_dir / "release_readiness.json"
    report_path = report_out / "release_readiness_report.md"

    payload = {
        "ok": status in {"READY", "WARNING"},
        "node_id": "release_readiness",
        "backend": "python",
        "status": status,
        "readiness_score": readiness_score,
        "checks_total": total,
        "checks_passed": passed,
        "checks_failed": total - passed,
        "blockers_count": len(blockers),
        "warnings_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "safety": {
            "pipelines_executed": False,
            "matlab_launched": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dpabi_gui_called": False,
            "rawdata_modified": False,
            "files_deleted": False,
            "deployment_performed": False,
        },
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_checklist_yaml(checklist_path, payload)

    lines = []
    lines.append("# Release Readiness Report")
    lines.append("")
    lines.append(f"- Status: {status}")
    lines.append(f"- Readiness score: {readiness_score}")
    lines.append(f"- Checks passed: {passed}/{total}")
    lines.append(f"- Blockers: {len(blockers)}")
    lines.append(f"- Warnings: {len(warnings)}")
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    for key, value in payload["safety"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | OK | Severity | Message |")
    lines.append("|---|---:|---|---|")
    for check in checks:
        lines.append(
            f"| {check.get('name')} | {check.get('ok')} | "
            f"{check.get('severity')} | {check.get('message')} |"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload["outputs"] = [str(checklist_path), str(json_path), str(report_path)]
    return payload
3. 创建 backend/app/tools/run_release_readiness_cli.py

创建文件：

backend/app/tools/run_release_readiness_cli.py

内容：

from __future__ import annotations

import json

from backend.app.tools.release_readiness import build_release_readiness


def main() -> int:
    result = build_release_readiness()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"READY", "WARNING"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
4. 修改 backend/app/api/routes.py

新增 API：

GET  /api/release/readiness
POST /api/release/readiness/refresh

新增导入：

from backend.app.tools.release_readiness import build_release_readiness

新增路由：

@router.get("/api/release/readiness")
def api_get_release_readiness() -> dict[str, Any]:
    base = Path("work") / "release"
    report_base = Path("reports") / "release"

    readiness = _read_json_if_exists(base / "release_readiness.json")
    checklist = _read_text_if_exists(base / "release_checklist.yaml")
    report = _read_text_if_exists(report_base / "release_readiness_report.md")

    if readiness is None:
        readiness = build_release_readiness()

    return {
        "ok": True,
        "readiness": readiness,
        "checklist": checklist,
        "report": report,
    }


@router.post("/api/release/readiness/refresh")
def api_refresh_release_readiness() -> dict[str, Any]:
    result = build_release_readiness()

    if result.get("status") == "BLOCKED":
        return result

    return result
5. 修改 frontend/src/api.ts

新增：

export async function getReleaseReadiness(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/release/readiness"
  );
}

export async function refreshReleaseReadiness(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/release/readiness/refresh",
    { method: "POST" }
  );
}
6. 创建 frontend/src/components/ReleaseReadinessPanel.tsx

创建文件：

frontend/src/components/ReleaseReadinessPanel.tsx

内容：

import { useState } from "react";
import {
  getReleaseReadiness,
  refreshReleaseReadiness
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function ReleaseReadinessPanel({ baseUrl }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getReleaseReadiness(baseUrl);
      setPayload(result);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleRefresh() {
    setStatus("REFRESHING");
    setError("");

    try {
      const result = await refreshReleaseReadiness(baseUrl);
      setPayload({
        ok: true,
        readiness: result
      });
      setStatus("REFRESHED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const readiness = payload?.readiness as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleLoad}>加载 Release Readiness</button>
        <button onClick={handleRefresh}>刷新 Readiness Scan</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Status</span>
          <strong>{String(readiness?.status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Score</span>
          <strong>{String(readiness?.readiness_score ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Blockers</span>
          <strong>{String(readiness?.blockers_count ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Warnings</span>
          <strong>{String(readiness?.warnings_count ?? "-")}</strong>
        </div>
      </div>

      <h3>Release Readiness JSON</h3>
      <JsonBlock value={readiness} emptyText="尚未加载 release readiness" />

      <h3>Release Checklist YAML</h3>
      <TextViewer
        text={
          typeof payload?.checklist === "string"
            ? payload.checklist
            : null
        }
        emptyText="暂无 release checklist"
      />

      <h3>Release Readiness Report</h3>
      <TextViewer
        text={
          typeof payload?.report === "string"
            ? payload.report
            : null
        }
        emptyText="暂无 release readiness report"
      />
    </div>
  );
}
7. 修改 frontend/src/App.tsx

新增导入：

import { ReleaseReadinessPanel } from "./components/ReleaseReadinessPanel";

在 Reproducibility Bundle 后增加 Section：

<Section
  title="Release Checklist / Deployment Readiness"
  description="扫描项目结构、测试、safety gates、bundle 和前端面板，生成部署前检查报告。"
>
  <ReleaseReadinessPanel baseUrl={baseUrl} />
</Section>
8. 新增轻量测试

创建文件：

tests/unit/test_release_readiness.py

内容：

from __future__ import annotations

from pathlib import Path

from backend.app.tools.release_readiness import build_release_readiness


def test_release_readiness_reports_missing_files_without_crashing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "backend" / "app" / "tools").mkdir(parents=True)
    (tmp_path / "frontend" / "src" / "components").mkdir(parents=True)
    (tmp_path / "specs").mkdir()
    (tmp_path / "examples").mkdir()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "work").mkdir()
    (tmp_path / "reports").mkdir()

    result = build_release_readiness(
        work_dir="./work",
        report_dir="./reports",
        frontend_dir="./frontend",
    )

    assert result["node_id"] == "release_readiness"
    assert result["status"] in {"BLOCKED", "WARNING", "READY"}
    assert result["checks_total"] > 0
    assert (tmp_path / "work" / "release" / "release_readiness.json").exists()
    assert (tmp_path / "reports" / "release" / "release_readiness_report.md").exists()
9. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/release/readiness")

不要在 smoke test 中调用 POST refresh。

10. 更新 README.md

追加第三十二步说明：

## Step 32: Release Checklist and Deployment Readiness

This step adds a release readiness scanner.

It checks:

- required project structure
- required specs
- backend tools
- frontend panels
- unit tests
- DPABI safety gates
- generated template safety
- reproducibility bundle safety
- artifact index presence
- experiment dashboard presence

It does not execute pipelines.

### Run Release Readiness Scan

```bash
python -m backend.app.tools.run_release_readiness_cli

Expected outputs:

work/release/release_checklist.yaml
work/release/release_readiness.json
reports/release/release_readiness_report.md
API
curl http://127.0.0.1:8000/api/release/readiness

Refresh:

curl -X POST http://127.0.0.1:8000/api/release/readiness/refresh
Frontend

Use:

Release Checklist / Deployment Readiness
Safety

This step:

does not execute pipelines
does not launch MATLAB
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not modify rawdata
does not delete files
does not deploy automatically

---

## 11. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/release_readiness_spec.md
backend/app/tools/release_readiness.py
backend/app/tools/run_release_readiness_cli.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/ReleaseReadinessPanel.tsx
frontend/src/App.tsx
tests/unit/test_release_readiness.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有 bundle / artifact / dashboard：

python -m backend.app.tools.run_artifact_browser_cli
python -m backend.app.tools.run_experiment_dashboard_cli
python -m backend.app.tools.run_reproducibility_bundle_cli bundle_test

然后运行：

python -m backend.app.tools.run_release_readiness_cli

应生成：

work/release/release_checklist.yaml
work/release/release_readiness.json
reports/release/release_readiness_report.md

release_readiness.json 必须包含：

{
  "node_id": "release_readiness",
  "status": "READY",
  "readiness_score": 100,
  "safety": {
    "pipelines_executed": false,
    "matlab_launched": false,
    "dpabi_executed": false,
    "dparsf_run_executed": false,
    "dpabi_gui_called": false,
    "rawdata_modified": false,
    "files_deleted": false,
    "deployment_performed": false
  }
}

如果部分文件缺失，status 可以是 WARNING 或 BLOCKED，但不能崩溃。

运行测试：

python -m pytest tests/unit/test_release_readiness.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/release/readiness
curl -X POST http://127.0.0.1:8000/api/release/readiness/refresh

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Release Checklist / Deployment Readiness 区域。
点击加载 Release Readiness。
点击刷新 Readiness Scan。
显示 status。
显示 readiness score。
显示 blockers count。
显示 warnings count。
显示 release readiness JSON。
显示 release checklist YAML。
显示 release readiness report。
不执行任何 pipeline。
不启动 MATLAB。
不运行 DPABI。
不部署。
不修改或删除文件。
12. 重要限制

本步骤只做 release checklist 和 deployment readiness。

不要实现：

自动部署
Docker production build
云端上传
CI/CD 自动配置
自动运行 MATLAB
自动运行 DPABI
DPARSF_run 自动执行
DPARSFA_run 自动执行
真实医学影像处理
修改 rawdata
删除文件
生产权限系统

完成后请总结：

新增了哪些文件
修改了哪些文件
readiness scanner 检查哪些内容
什么情况会 BLOCKED
什么情况会 WARNING
为什么本步骤不自动部署
下一步如何做 Docker / local deployment profile

'''
Step 32 主要实现的是：

## Release Checklist + Deployment Readiness 闭环
### 核心目标
当前系统已经具备完整的功能（pipeline runtime、DPABI wrapper safety gates、template library、experiment tracking、artifact browser、reproducibility bundle），但还缺少 部署前的统一审查能力 。本步骤要新增一个 release readiness 层，用来回答项目是否适合演示、交付或进入下一阶段真实数据适配。

### 主要功能
1. Release Readiness 扫描器
   
   - 检查项目核心文件是否齐全
   - 检查 specs 是否齐全
   - 检查 README 是否覆盖关键功能
   - 检查后端 API 是否有 smoke test 覆盖
   - 检查前端关键面板是否存在
   - 检查 DPABI safety gates 是否仍然有效
   - 检查 generated templates 是否默认 approved=false
   - 检查 bundle 是否排除了 rawdata / third_party
   - 检查 artifact browser 是否禁止任意路径
   - 识别明显的 deployment blocker
2. Readiness Score 计算
   
   - 通过率 = (passed checks / total checks) × 100
   - 状态判定：
     - READY : 无 blocker，只有轻微 warning
     - WARNING : 无 blocker，但有重要 warning
     - BLOCKED : 至少有一个部署 blocker
3. Safety Gate 验证
   
   - DPARSF_run / DPARSFA_run 在 wrapper contracts 中被阻塞
   - Template library 不推广 full pipeline runners
   - Generated templates 默认 approved=false
   - Artifact browser 拒绝路径遍历
   - Bundles 排除 rawdata 和 third_party
### 解决的问题
- 部署前缺乏系统性检查
- 无法确定项目是否适合演示
- 无法评估交付 readiness
- 缺少 deployment blocker 识别
- 无法验证 safety gates 有效性
### 检查清单
结构检查：

- Required directories (backend/app, frontend/src, matlab, specs, examples, tests/unit)
- Required files (README.md, main.py, routes.py, App.tsx, etc.)
- Required specs (所有 DPABI、experiment、artifact、bundle specs)
- Required tools (所有 DPABI、experiment、artifact、bundle tools)
- Required frontend (DpabiPanel, ExperimentPanel, ArtifactBrowser, etc.)
- Required tests (所有单元测试)
Safety 检查：

- DPARSF_run blocked in contracts
- DPARSFA_run blocked in contracts
- Templates default approved=false
- Templates don't contain DPARSF_run/DPARSFA_run
- Bundle safety (rawdata_packaged=false, third_party_packaged=false)
- Artifact index exists
- Experiment dashboard exists
### 输出文件
```
work/release/
├── release_checklist.yaml       # YAML 检查清单
└── release_readiness.json       # JSON readiness 数据

reports/release/
└── release_readiness_report.md  # Markdown 报告
```
### API 端点
```
GET /api/release/readiness  - 获取 release readiness
```
### 安全规则
- 只读扫描 - 仅扫描文件，不修改
- 不执行 Pipeline
- 不启动 MATLAB
- 不运行 DPABI
- 不删除文件
- 不自动部署
### 使用场景
- 部署前检查 - 验证项目是否适合部署
- 演示准备 - 确保所有组件正常工作
- 交付审查 - 记录项目状态用于交接
- CI/CD 集成 - 自动化 readiness 检查
- 发布门禁 - 阻止有严重问题的发布
### 工作流程
1. Scan - 扫描项目结构
2. Check - 执行各项检查
3. Score - 计算 readiness score
4. Classify - 分类 blockers 和 warnings
5. Report - 生成 YAML/JSON/Markdown 报告
6. Review - 人工审查 readiness 状态
'''