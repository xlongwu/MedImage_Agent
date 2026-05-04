# 第五十三步 Prompt：Demo Replay / Run History Browser + 统一运行历史浏览闭环

```text
你是我的工程搭建助手。前五十二步已经完成：

- MedImage Agent 工程骨架
- Pipeline runtime
- Agent runtime
- MATLAB / SPM / DPABI 环境检查
- synthetic BIDS 数据生成与扫描
- rs-fMRI preprocessing protocol
- rs-fMRI step registry
- SPM Slice Timing Correction + Metadata QC
- SPM Realignment + Motion QC
- Slice Timing → Realignment → Motion QC 链式核心 pipeline
- SPM Coregistration + Registration QC
- SPM Segmentation + Tissue QC
- SPM Normalization + Normalization QC
- SPM Smoothing + Smoothing QC
- Nuisance Regression 参数计划 + Confound Matrix + Python/DPABI 双后端设计
- Temporal Filtering + Filtering QC
- ALFF / fALFF 计算 + QC + GPU Candidate Backend 设计
- ReHo 计算 + ReHo QC + GPU/DPABI Backend Contract
- Functional Connectivity ROI/Seed 相关分析 + FC QC + GPU/DPABI Backend Contract
- Group-level Dataset Summary + Cross-subject Metrics Dashboard
- Dataset Report Exporter + 可交付报告包
- Report Package Validator + Integrity / Safety Audit
- Project Release Readiness Check + MVP 发布准备度审计
- MVP User Guide + Developer Guide 文档体系
- Quickstart Demo Orchestrator + 一键安全演示流程

现在开始第五十三步。

第五十三步目标：实现 “Demo Replay / Run History Browser + 统一运行历史浏览闭环”。

当前系统已经能一键运行 Quickstart Demo，并在不同位置生成很多历史产物：

```text
demo_runs/{demo_id}/quickstart_demo_summary.json
demo_runs/{demo_id}/quickstart_demo_report.md

work/pipeline_runs/{run_id}/summary.json

exports/rsfmri_report_package/{export_id}/export_summary.json
exports/rsfmri_report_package/{export_id}/validation/validation_result.json

reports/release_readiness/release_readiness_result.json
reports/docs_inventory/docs_inventory.json
reports/rsfmri/group_summary/dataset_summary.json
```

但目前用户查看历史运行需要手动进入不同目录。  
本步骤要实现一个统一的 run history browser，把 demo、pipeline runs、report packages、validations、release readiness、docs inventory 等记录聚合为一个可浏览、可筛选、可 replay 的历史中心。

这里的 **Replay** 只表示“重新加载历史结果、重新生成索引、查看已有输出”，不表示重新执行真实预处理。  
默认不自动重新运行 demo 或 pipeline。

---

## 0. 总体约束

本步骤必须满足：

- 默认只读取历史记录。
- 默认不重新执行 demo。
- 默认不重新执行 pipeline。
- 默认不修改历史 package。
- 默认不修改 derivatives / reports / work / exports / demo_runs 中已有源文件。
- 只写入：

```text
reports/run_history/
```

- 不处理真实医学影像数据。
- 不读取真实 rawdata。
- 不修改 rawdata。
- 不运行 SPM。
- 不运行 MATLAB。
- 不调用 DPABI。
- 不调用 DPARSF_run。
- 不调用 DPARSFA_run。
- 不调用 DPABI GUI。
- 不执行 GPU。
- 不要求 CUDA / CuPy / Torch。
- 不做医学结论。
- 不做 clinical interpretation。
- 不做 group-level statistics / inference。
- 不自动排除 subject。
- 不删除文件。
- 不自动修复项目。

本步骤不要实现：

- 自动 rerun full preprocessing。
- 自动 rerun SPM/MATLAB。
- 自动 rerun DPABI。
- 自动 rerun GPU。
- 自动删除旧 demo / package。
- 真实医学影像处理。
- Docker / CI / release。
- PDF / Word / PPT 生成。
- 在线文档部署。
- 临床报告生成。

本步骤只做：**统一历史索引、只读浏览、详情读取、轻量 replay metadata、前端 Run History Browser**。

---

## 1. 创建 specs/run_history_browser_spec.md

创建文件：

```text
specs/run_history_browser_spec.md
```

内容：

```markdown
# Run History Browser Specification

This document defines the MVP run history browser for the MedImage Agent project.

## Goals

The run history browser aggregates previously generated demo runs, pipeline runs, report packages, validation results, release readiness outputs, docs inventory outputs, and group summaries into a single read-only history index.

It helps users answer:

- Which demos have been run?
- Which pipeline runs exist?
- Which report packages were exported?
- Which report packages were validated?
- What was the latest release readiness status?
- What was the latest docs inventory status?
- Where are the important output files?

## Scope

Supported in this step:

- scan demo_runs
- scan work/pipeline_runs
- scan exports/rsfmri_report_package
- scan report package validations
- scan reports/release_readiness
- scan reports/docs_inventory
- scan reports/rsfmri/group_summary
- generate run history index JSON
- generate run history timeline JSON
- generate run history Markdown report
- load latest item details
- list history records via API
- frontend Run History Browser panel
- lightweight unit tests

Unsupported in this step:

- automatic rerun of preprocessing
- automatic deletion of history
- package repair
- real medical image preprocessing
- clinical interpretation
- statistical inference
- DPABI execution
- SPM execution
- MATLAB execution
- GPU execution
- rawdata modification
- file deletion

## Inputs

```text
demo_runs/*/quickstart_demo_summary.json
demo_runs/*/quickstart_demo_report.md
work/pipeline_runs/*/summary.json
exports/rsfmri_report_package/*/export_summary.json
exports/rsfmri_report_package/*/validation/validation_result.json
reports/release_readiness/release_readiness_result.json
reports/docs_inventory/docs_inventory.json
reports/rsfmri/group_summary/dataset_summary.json
```

## Outputs

```text
reports/run_history/run_history_index.json
reports/run_history/run_history_timeline.json
reports/run_history/run_history_report.md
```

## Record Types

- quickstart_demo
- pipeline_run
- report_package
- report_validation
- release_readiness
- docs_inventory
- group_summary

## Safety Rules

- Read only from demo_runs / work / exports / reports.
- Write only under reports/run_history.
- Do not modify rawdata.
- Do not modify derivatives.
- Do not modify existing reports.
- Do not modify work.
- Do not modify exports.
- Do not modify demo_runs.
- Do not delete files.
- Do not run SPM.
- Do not run MATLAB.
- Do not execute DPABI.
- Do not execute GPU.
- Do not perform statistical inference.
- Do not generate clinical conclusions.
```

---

## 2. 创建 backend/app/tools/run_history.py

创建文件：

```text
backend/app/tools/run_history.py
```

目标：实现统一运行历史索引、详情读取和报告生成。

提供函数：

```python
build_run_history_index(
    project_root: str = ".",
    demo_root: str = "./demo_runs",
    work_dir: str = "./work",
    reports_dir: str = "./reports",
    exports_dir: str = "./exports",
) -> dict

get_run_history(
    reports_dir: str = "./reports",
) -> dict

get_run_history_detail(
    record_id: str,
    reports_dir: str = "./reports",
) -> dict

get_latest_run_history_record(
    record_type: str | None = None,
    reports_dir: str = "./reports",
) -> dict
```

实现要求：

1. 只读取：
   - demo_runs
   - work/pipeline_runs
   - exports/rsfmri_report_package
   - reports
2. 只写：
   - reports/run_history
3. 每条 record 必须包含：
   - record_id
   - record_type
   - title
   - status
   - ok
   - created_at 或 finished_at
   - source_path
   - summary_path
   - report_path
   - outputs
   - warnings_count
   - errors_count
   - tags
4. record_id 生成规则：
   - quickstart demo: `quickstart_demo:{demo_id}`
   - pipeline run: `pipeline_run:{run_id}`
   - report package: `report_package:{export_id}`
   - validation: `report_validation:{export_id}`
   - release readiness: `release_readiness:latest`
   - docs inventory: `docs_inventory:latest`
   - group summary: `group_summary:latest`
5. 生成 timeline：
   - 按时间倒序。
   - 无时间的放最后。
6. 生成 run_history_report.md：
   - overview cards
   - latest records
   - table of all records
   - safety note
7. get_run_history 读取已有 index。
8. get_run_history_detail 根据 record_id 返回：
   - record
   - parsed JSON payload
   - Markdown report text，如存在
9. get_latest_run_history_record 支持按 record_type 过滤。
10. 不删除文件。
11. 不修改源文件。
12. 只使用 Python 标准库。

参考实现：

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _warnings_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    warnings = payload.get("warnings", [])
    return len(warnings) if isinstance(warnings, list) else 0


def _errors_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    errors = payload.get("errors", [])
    return len(errors) if isinstance(errors, list) else 0


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _time_key(record: dict[str, Any]) -> str:
    return str(record.get("created_at") or record.get("finished_at") or record.get("validated_at") or "")


def _record(
    record_id: str,
    record_type: str,
    title: str,
    status: str | None,
    ok: bool | None,
    source_path: Path,
    summary_path: Path | None = None,
    report_path: Path | None = None,
    created_at: str | None = None,
    finished_at: str | None = None,
    outputs: list[Any] | None = None,
    warnings_count: int = 0,
    errors_count: int = 0,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "record_type": record_type,
        "title": title,
        "status": status,
        "ok": ok,
        "created_at": created_at,
        "finished_at": finished_at,
        "source_path": str(source_path),
        "summary_path": str(summary_path) if summary_path else None,
        "report_path": str(report_path) if report_path else None,
        "outputs": outputs or [],
        "warnings_count": warnings_count,
        "errors_count": errors_count,
        "tags": tags or [],
    }


def _collect_quickstart_demos(demo_root: Path) -> list[dict[str, Any]]:
    records = []

    if not demo_root.exists():
        return records

    for demo_dir in sorted(demo_root.iterdir()):
        if not demo_dir.is_dir():
            continue

        summary_path = demo_dir / "quickstart_demo_summary.json"
        report_path = demo_dir / "quickstart_demo_report.md"
        payload = _read_json(summary_path)
        if not payload:
            continue

        demo_id = payload.get("demo_id") or demo_dir.name
        records.append(_record(
            record_id=f"quickstart_demo:{demo_id}",
            record_type="quickstart_demo",
            title=f"Quickstart Demo {demo_id}",
            status=payload.get("demo_status"),
            ok=payload.get("ok"),
            source_path=demo_dir,
            summary_path=summary_path,
            report_path=report_path if report_path.exists() else None,
            created_at=payload.get("created_at"),
            finished_at=payload.get("finished_at"),
            outputs=_safe_list(payload.get("outputs")),
            warnings_count=_warnings_count(payload),
            errors_count=_errors_count(payload),
            tags=["demo", "synthetic", "quickstart"],
        ))

    return records


def _collect_pipeline_runs(work_dir: Path) -> list[dict[str, Any]]:
    records = []
    base = work_dir / "pipeline_runs"

    if not base.exists():
        return records

    for summary_path in sorted(base.glob("*/summary.json")):
        payload = _read_json(summary_path)
        if not payload:
            continue

        run_id = payload.get("run_id") or summary_path.parent.name
        pipeline_id = payload.get("pipeline_id") or "unknown_pipeline"

        records.append(_record(
            record_id=f"pipeline_run:{run_id}",
            record_type="pipeline_run",
            title=f"Pipeline Run {pipeline_id} / {run_id}",
            status=payload.get("status"),
            ok=payload.get("status") in {"SUCCESS", "PARTIAL"},
            source_path=summary_path.parent,
            summary_path=summary_path,
            report_path=None,
            created_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            outputs=_safe_list(payload.get("outputs")),
            warnings_count=_warnings_count(payload),
            errors_count=_errors_count(payload),
            tags=["pipeline", str(pipeline_id)],
        ))

    return records


def _collect_report_packages(exports_dir: Path) -> list[dict[str, Any]]:
    records = []
    base = exports_dir / "rsfmri_report_package"

    if not base.exists():
        return records

    for package_dir in sorted(base.iterdir()):
        if not package_dir.is_dir():
            continue

        summary_path = package_dir / "export_summary.json"
        manifest_path = package_dir / "MANIFEST.json"
        index_path = package_dir / "index.md"
        payload = _read_json(summary_path)
        if not payload:
            continue

        export_id = payload.get("export_id") or package_dir.name

        records.append(_record(
            record_id=f"report_package:{export_id}",
            record_type="report_package",
            title=f"Report Package {export_id}",
            status="PASS" if payload.get("ok") else "FAIL",
            ok=payload.get("ok"),
            source_path=package_dir,
            summary_path=summary_path,
            report_path=index_path if index_path.exists() else None,
            created_at=payload.get("created_at"),
            finished_at=None,
            outputs=_safe_list(payload.get("outputs")),
            warnings_count=_warnings_count(payload),
            errors_count=_errors_count(payload),
            tags=["report", "export", "package"],
        ))

        validation_path = package_dir / "validation" / "validation_result.json"
        validation_report = package_dir / "validation" / "validation_report.md"
        validation = _read_json(validation_path)
        if validation:
            records.append(_record(
                record_id=f"report_validation:{export_id}",
                record_type="report_validation",
                title=f"Report Package Validation {export_id}",
                status=validation.get("validation_status"),
                ok=validation.get("ok"),
                source_path=package_dir / "validation",
                summary_path=validation_path,
                report_path=validation_report if validation_report.exists() else None,
                created_at=validation.get("validated_at"),
                finished_at=None,
                outputs=_safe_list(validation.get("outputs")),
                warnings_count=_warnings_count(validation),
                errors_count=_errors_count(validation),
                tags=["report", "validation", "integrity"],
            ))

    return records


def _collect_singleton_reports(reports_dir: Path) -> list[dict[str, Any]]:
    records = []

    release_path = reports_dir / "release_readiness" / "release_readiness_result.json"
    release_report = reports_dir / "release_readiness" / "release_readiness_report.md"
    release = _read_json(release_path)
    if release:
        records.append(_record(
            record_id="release_readiness:latest",
            record_type="release_readiness",
            title="Latest Release Readiness",
            status=release.get("readiness_status"),
            ok=release.get("ok"),
            source_path=release_path.parent,
            summary_path=release_path,
            report_path=release_report if release_report.exists() else None,
            created_at=release.get("checked_at"),
            outputs=_safe_list(release.get("outputs")),
            warnings_count=_warnings_count(release),
            errors_count=_errors_count(release),
            tags=["release", "readiness"],
        ))

    docs_path = reports_dir / "docs_inventory" / "docs_inventory.json"
    docs_report = reports_dir / "docs_inventory" / "docs_inventory_report.md"
    docs = _read_json(docs_path)
    if docs:
        records.append(_record(
            record_id="docs_inventory:latest",
            record_type="docs_inventory",
            title="Latest Docs Inventory",
            status=docs.get("docs_status"),
            ok=docs.get("ok"),
            source_path=docs_path.parent,
            summary_path=docs_path,
            report_path=docs_report if docs_report.exists() else None,
            created_at=docs.get("checked_at"),
            outputs=_safe_list(docs.get("outputs")),
            warnings_count=_warnings_count(docs),
            errors_count=_errors_count(docs),
            tags=["docs", "inventory"],
        ))

    group_path = reports_dir / "rsfmri" / "group_summary" / "dataset_summary.json"
    group_report = reports_dir / "rsfmri" / "group_summary" / "dataset_summary_report.md"
    group = _read_json(group_path)
    if group:
        records.append(_record(
            record_id="group_summary:latest",
            record_type="group_summary",
            title="Latest Group Dataset Summary",
            status="PASS" if group.get("ok") else "FAIL",
            ok=group.get("ok"),
            source_path=group_path.parent,
            summary_path=group_path,
            report_path=group_report if group_report.exists() else None,
            created_at=group.get("created_at"),
            outputs=_safe_list(group.get("outputs")),
            warnings_count=_warnings_count(group),
            errors_count=_errors_count(group),
            tags=["group", "summary", "rsfmri"],
        ))

    return records


def _write_history_report(path: Path, index: dict[str, Any]) -> None:
    lines = []
    lines.append("# Run History Browser Report")
    lines.append("")
    lines.append(f"- Generated at: `{index.get('generated_at')}`")
    lines.append(f"- Records total: {index.get('records_total')}")
    lines.append("")
    lines.append("## Record Counts")
    lines.append("")
    for key, value in index.get("record_type_counts", {}).items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Timeline")
    lines.append("")
    lines.append("| Type | Title | Status | OK | Time |")
    lines.append("|---|---|---|---|---|")
    for record in index.get("timeline", []):
        time_value = record.get("created_at") or record.get("finished_at") or ""
        lines.append(
            f"| {record.get('record_type')} | {record.get('title')} | "
            f"{record.get('status')} | {record.get('ok')} | {time_value} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This run history browser is read-only for demo_runs, work, exports, and existing reports. It does not rerun preprocessing, execute SPM, execute MATLAB, execute DPABI, execute GPU code, or modify rawdata.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_run_history_index(
    project_root: str = ".",
    demo_root: str = "./demo_runs",
    work_dir: str = "./work",
    reports_dir: str = "./reports",
    exports_dir: str = "./exports",
) -> dict[str, Any]:
    reports = Path(reports_dir)
    out_dir = reports / "run_history"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "run_history_index.json"
    timeline_path = out_dir / "run_history_timeline.json"
    report_path = out_dir / "run_history_report.md"

    records = []
    records.extend(_collect_quickstart_demos(Path(demo_root)))
    records.extend(_collect_pipeline_runs(Path(work_dir)))
    records.extend(_collect_report_packages(Path(exports_dir)))
    records.extend(_collect_singleton_reports(reports))

    records = sorted(records, key=_time_key, reverse=True)

    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for record in records:
        rtype = record.get("record_type", "unknown")
        status = str(record.get("status") or "UNKNOWN")
        type_counts[rtype] = type_counts.get(rtype, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    timeline = records

    index = {
        "ok": True,
        "node_id": "run_history_index",
        "backend": "python",
        "generated_at": _iso_now(),
        "project_root": project_root,
        "demo_root": demo_root,
        "work_dir": work_dir,
        "reports_dir": reports_dir,
        "exports_dir": exports_dir,
        "records_total": len(records),
        "record_type_counts": type_counts,
        "status_counts": status_counts,
        "records": records,
        "timeline": timeline,
        "outputs": [
            str(index_path),
            str(timeline_path),
            str(report_path),
        ],
        "safety": {
            "read_only_history_scan": True,
            "rawdata_read": False,
            "rawdata_modified": False,
            "spm_executed": False,
            "matlab_executed": False,
            "dpabi_executed": False,
            "gpu_executed": False,
            "files_deleted": False,
            "statistical_inference_performed": False,
            "clinical_conclusions_generated": False,
        },
        "warnings": [],
        "errors": [],
    }

    timeline_payload = {
        "ok": True,
        "generated_at": index["generated_at"],
        "records_total": len(timeline),
        "timeline": timeline,
    }

    _write_json(index_path, index)
    _write_json(timeline_path, timeline_payload)
    _write_history_report(report_path, index)

    return index


def get_run_history(
    reports_dir: str = "./reports",
) -> dict[str, Any]:
    path = Path(reports_dir) / "run_history" / "run_history_index.json"
    payload = _read_json(path)
    if not payload:
        return {
            "ok": False,
            "warnings": [],
            "errors": ["Run history index not found. Run build_run_history_index first."],
        }
    return payload


def get_run_history_detail(
    record_id: str,
    reports_dir: str = "./reports",
) -> dict[str, Any]:
    history = get_run_history(reports_dir=reports_dir)
    if not history.get("ok"):
        return history

    records = history.get("records", [])
    record = next((item for item in records if item.get("record_id") == record_id), None)

    if not record:
        return {
            "ok": False,
            "record_id": record_id,
            "warnings": [],
            "errors": [f"Record not found: {record_id}"],
        }

    summary_path = record.get("summary_path")
    report_path = record.get("report_path")

    payload = _read_json(Path(summary_path)) if summary_path else None
    report_text = _read_text(Path(report_path)) if report_path else None

    return {
        "ok": True,
        "record": record,
        "payload": payload,
        "report": report_text,
        "warnings": [],
        "errors": [],
    }


def get_latest_run_history_record(
    record_type: str | None = None,
    reports_dir: str = "./reports",
) -> dict[str, Any]:
    history = get_run_history(reports_dir=reports_dir)
    if not history.get("ok"):
        return history

    records = history.get("records", [])
    if record_type:
        records = [item for item in records if item.get("record_type") == record_type]

    if not records:
        return {
            "ok": False,
            "record_type": record_type,
            "warnings": [],
            "errors": ["No matching run history record found."],
        }

    latest = records[0]
    return get_run_history_detail(latest["record_id"], reports_dir=reports_dir)
```

---

## 3. 修改 backend/app/runtime/node_registry.py

新增节点：

```text
run_history_index
```

新增导入：

```python
from backend.app.tools.run_history import build_run_history_index
```

新增 runner：

```python
def run_run_history_index_node(
    context: NodeExecutionContext,
    node: PipelineNode,
) -> dict[str, Any]:
    result = build_run_history_index(
        project_root=node.params.get("project_root", "."),
        demo_root=node.params.get("demo_root", "./demo_runs"),
        work_dir=context.work_dir,
        reports_dir=context.project_config.get("runtime", {}).get("report_dir", "./reports"),
        exports_dir=node.params.get("exports_dir", "./exports"),
    )
    result["node_id"] = node.id
    return result
```

更新 `NODE_REGISTRY`：

```python
"run_history_index": run_run_history_index_node,
```

---

## 4. 创建 examples/pipeline_run_history.yaml

创建文件：

```text
examples/pipeline_run_history.yaml
```

内容：

```yaml
pipeline_id: run_history_pipeline
version: "0.1.0"
modality: project
description: "Build a read-only unified run history index across demos, pipeline runs, report packages, validations, docs, and release readiness outputs."

execution:
  stop_on_failure: true
  run_id: "run_history_index_001"
  scheduler:
    mode: "local"
    max_workers: 1
    matlab_max_workers: 0

nodes:
  - id: run_history_index
    name: Run History Index
    agent: report-runner
    backend: python
    depends_on: []
    inputs:
      - "./demo_runs"
      - "./work/pipeline_runs"
      - "./exports"
      - "./reports"
    outputs:
      - "./reports/run_history/run_history_index.json"
      - "./reports/run_history/run_history_timeline.json"
      - "./reports/run_history/run_history_report.md"
    params:
      project_root: "."
      demo_root: "./demo_runs"
      exports_dir: "./exports"
    parallel_level: project
    gpu_supported: false
    cache: false
```

本 pipeline 不执行任何 SPM / MATLAB / DPABI / GPU。  
它只扫描历史结果并生成 run history index。

---

## 5. 创建 backend/app/tools/run_history_cli.py

创建文件：

```text
backend/app/tools/run_history_cli.py
```

内容：

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    args = sys.argv[1:]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_run_history.yaml")

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
```

---

## 6. 修改 backend/app/api/models.py

新增 request model：

```python
class RunHistoryRequest(BaseModel):
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_run_history.yaml")


class RunHistoryDetailRequest(BaseModel):
    record_id: str
```

---

## 7. 修改 backend/app/api/routes.py

新增 API：

```text
POST /api/run-history/build
GET  /api/run-history
GET  /api/run-history/latest
GET  /api/run-history/detail
```

新增导入：

```python
from backend.app.api.models import RunHistoryRequest
from backend.app.runtime.pipeline_executor import run_pipeline
from backend.app.tools.run_history import (
    get_run_history,
    get_run_history_detail,
    get_latest_run_history_record,
)
```

新增路由：

```python
@router.post("/api/run-history/build")
def api_build_run_history(
    request: RunHistoryRequest,
) -> dict[str, Any]:
    try:
        summary = run_pipeline(
            request.project_config_path,
            request.pipeline_path,
        )

        if summary.get("status") not in {"SUCCESS", "PARTIAL"}:
            raise HTTPException(status_code=400, detail=summary)

        return summary

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/run-history")
def api_get_run_history() -> dict[str, Any]:
    return get_run_history(reports_dir="./reports")


@router.get("/api/run-history/latest")
def api_get_latest_run_history(
    record_type: str | None = None,
) -> dict[str, Any]:
    return get_latest_run_history_record(
        record_type=record_type,
        reports_dir="./reports",
    )


@router.get("/api/run-history/detail")
def api_get_run_history_detail(
    record_id: str,
) -> dict[str, Any]:
    return get_run_history_detail(
        record_id=record_id,
        reports_dir="./reports",
    )
```

注意：本 POST 不需要 approved，因为不执行 SPM / DPABI / GPU，只做只读历史索引构建。

---

## 8. 修改 frontend/src/api.ts

新增：

```ts
export async function buildRunHistory(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/run-history/build",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRunHistory(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/run-history"
  );
}

export async function getLatestRunHistory(baseUrl: string, recordType?: string) {
  const suffix = recordType ? `?record_type=${encodeURIComponent(recordType)}` : "";
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/run-history/latest${suffix}`
  );
}

export async function getRunHistoryDetail(baseUrl: string, recordId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/run-history/detail?record_id=${encodeURIComponent(recordId)}`
  );
}
```

---

## 9. 创建 frontend/src/components/RunHistoryBrowserPanel.tsx

创建文件：

```text
frontend/src/components/RunHistoryBrowserPanel.tsx
```

内容：

```tsx
import { useState } from "react";
import {
  buildRunHistory,
  getRunHistory,
  getRunHistoryDetail
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

type HistoryRecord = {
  record_id?: string;
  record_type?: string;
  title?: string;
  status?: string;
  ok?: boolean;
  created_at?: string;
  finished_at?: string;
};

export function RunHistoryBrowserPanel({ baseUrl }: Props) {
  const [buildResult, setBuildResult] = useState<Record<string, unknown> | null>(null);
  const [history, setHistory] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleBuild() {
    setStatus("RUNNING");
    setError("");

    try {
      const response = await buildRunHistory(baseUrl, {
        project_config_path: "examples/project_config_dataset.yaml",
        pipeline_path: "examples/pipeline_run_history.yaml"
      });
      setBuildResult(response);
      setStatus("SUCCESS");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const response = await getRunHistory(baseUrl);
      setHistory(response);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadDetail(recordId?: string) {
    const id = recordId || selectedRecordId;
    if (!id) return;

    setStatus("LOADING_DETAIL");
    setError("");

    try {
      const response = await getRunHistoryDetail(baseUrl, id);
      setDetail(response);
      setSelectedRecordId(id);
      setStatus("DETAIL_LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const records = Array.isArray(history?.records)
    ? (history.records as HistoryRecord[])
    : [];

  const typeCounts = history?.record_type_counts as Record<string, unknown> | undefined;
  const statusCounts = history?.status_counts as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleBuild}>生成 Run History Index</button>
        <button onClick={handleLoad}>加载 Run History</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Records</span>
          <strong>{String(history?.records_total ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Demos</span>
          <strong>{String(typeCounts?.quickstart_demo ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Pipeline Runs</span>
          <strong>{String(typeCounts?.pipeline_run ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Report Packages</span>
          <strong>{String(typeCounts?.report_package ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>PASS</span>
          <strong>{String(statusCounts?.PASS ?? "-")}</strong>
        </div>
      </div>

      <h3>Build Summary</h3>
      <JsonBlock value={buildResult} emptyText="尚未生成 index" />

      <h3>Run History Records</h3>
      {records.length === 0 ? (
        <div className="emptyBox">暂无 run history records</div>
      ) : (
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Title</th>
                <th>Status</th>
                <th>OK</th>
                <th>Time</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => {
                const id = String(record.record_id ?? "");
                return (
                  <tr key={id}>
                    <td>{String(record.record_type ?? "-")}</td>
                    <td>{String(record.title ?? "-")}</td>
                    <td>{String(record.status ?? "-")}</td>
                    <td>{String(record.ok ?? "-")}</td>
                    <td>{String(record.created_at ?? record.finished_at ?? "-")}</td>
                    <td>
                      <button onClick={() => handleLoadDetail(id)}>查看</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <h3>Selected Record</h3>
      <div className="row">
        <input
          value={selectedRecordId}
          onChange={(event) => setSelectedRecordId(event.target.value)}
          placeholder="record_id，例如 quickstart_demo:quickstart_..."
          style={{ minWidth: "360px" }}
        />
        <button onClick={() => handleLoadDetail()}>加载详情</button>
      </div>

      <h3>Record Detail JSON</h3>
      <JsonBlock value={detail} emptyText="暂无 record detail" />

      <h3>Record Report</h3>
      <TextViewer
        text={
          typeof detail?.report === "string"
            ? detail.report
            : null
        }
        emptyText="该 record 没有 Markdown report"
      />

      <h3>Raw Run History Index</h3>
      <JsonBlock value={history} emptyText="暂无 run history index" />
    </div>
  );
}
```

---

## 10. 修改 frontend/src/App.tsx

新增导入：

```tsx
import { RunHistoryBrowserPanel } from "./components/RunHistoryBrowserPanel";
```

建议放在 Quickstart Demo 后。新增 Section：

```tsx
<Section
  title="Run History Browser"
  description="统一浏览 quickstart demos、pipeline runs、report packages、validation、docs inventory、release readiness 和 group summary 历史记录。"
>
  <RunHistoryBrowserPanel baseUrl={baseUrl} />
</Section>
```

---

## 11. 新增轻量测试

创建文件：

```text
tests/unit/test_run_history.py
```

内容：

```python
from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.run_history import (
    build_run_history_index,
    get_run_history,
    get_run_history_detail,
    get_latest_run_history_record,
)


def test_run_history_builds_index(tmp_path: Path):
    demo_root = tmp_path / "demo_runs"
    work = tmp_path / "work"
    reports = tmp_path / "reports"
    exports = tmp_path / "exports"

    demo = demo_root / "quickstart_test"
    demo.mkdir(parents=True)
    (demo / "quickstart_demo_summary.json").write_text(
        json.dumps({
            "ok": True,
            "demo_id": "quickstart_test",
            "demo_status": "PASS",
            "subject_ids": ["sub-001"],
            "outputs": [],
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )
    (demo / "quickstart_demo_report.md").write_text("# Demo Report\n", encoding="utf-8")

    run_dir = work / "pipeline_runs" / "run_test"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps({
            "status": "SUCCESS",
            "pipeline_id": "test_pipeline",
            "run_id": "run_test",
            "started_at": "2026-01-01T00:00:00",
            "finished_at": "2026-01-01T00:00:01",
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )

    package = exports / "rsfmri_report_package" / "export_test"
    package.mkdir(parents=True)
    (package / "export_summary.json").write_text(
        json.dumps({
            "ok": True,
            "export_id": "export_test",
            "created_at": "2026-01-01T00:00:02",
            "outputs": [],
            "warnings": [],
            "errors": [],
        }),
        encoding="utf-8",
    )
    (package / "index.md").write_text("# Package Index\n", encoding="utf-8")

    result = build_run_history_index(
        project_root=str(tmp_path),
        demo_root=str(demo_root),
        work_dir=str(work),
        reports_dir=str(reports),
        exports_dir=str(exports),
    )

    assert result["ok"] is True
    assert result["records_total"] >= 3

    out_dir = reports / "run_history"
    assert (out_dir / "run_history_index.json").exists()
    assert (out_dir / "run_history_timeline.json").exists()
    assert (out_dir / "run_history_report.md").exists()

    history = get_run_history(reports_dir=str(reports))
    assert history["ok"] is True

    detail = get_run_history_detail(
        record_id="quickstart_demo:quickstart_test",
        reports_dir=str(reports),
    )
    assert detail["ok"] is True
    assert detail["record"]["record_type"] == "quickstart_demo"

    latest = get_latest_run_history_record(
        record_type="pipeline_run",
        reports_dir=str(reports),
    )
    assert latest["ok"] is True
```

---

## 12. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

```python
call("GET", "/api/run-history")
call("GET", "/api/run-history/latest")
```

不要在 smoke test 中调用 POST build，避免改变 reports。

---

## 13. 更新 docs/user_guide.md

追加 Run History Browser 说明：

```markdown
## Run History Browser

After running demos or pipelines, build the unified run history index:

```bash
python -m backend.app.tools.run_history_cli
```

This creates:

```text
reports/run_history/run_history_index.json
reports/run_history/run_history_timeline.json
reports/run_history/run_history_report.md
```

The browser is read-only and does not rerun preprocessing.
```

---

## 14. 更新 docs/pipeline_guide.md

在 pipeline 列表中加入：

```text
pipeline_run_history.yaml
```

并追加：

```markdown
## Run History Pipeline

```bash
python -m backend.app.tools.run_history_cli
```

This pipeline builds a read-only index over demo runs, pipeline runs, report packages, validations, docs inventory, release readiness, and group summary outputs.
```

---

## 15. 更新 docs/api_reference.md

新增：

```markdown
### Run History

```text
POST /api/run-history/build
GET  /api/run-history
GET  /api/run-history/latest
GET  /api/run-history/detail
```
```

---

## 16. 更新 docs/frontend_guide.md

在 panels 列表中加入：

```text
Run History Browser
```

并说明：

```markdown
## Run History Browser Panel

The Run History Browser panel displays historical quickstart demos, pipeline runs, report packages, validation results, docs inventory, release readiness, and group summary records.
```

---

## 17. 更新 docs/troubleshooting.md

追加：

```markdown
## Run History Is Empty

Run:

```bash
python -m backend.app.tools.run_history_cli
```

If the index is still empty, run a quickstart demo first:

```bash
python -m backend.app.tools.run_quickstart_demo_cli
```
```

---

## 18. 更新 README.md

追加第五十三步说明：

```markdown
## Step 53: Run History Browser

This step adds a unified read-only run history browser.

It scans:

- quickstart demo runs
- pipeline run summaries
- report packages
- report validations
- release readiness outputs
- docs inventory outputs
- group summary outputs

It writes:

```text
reports/run_history/run_history_index.json
reports/run_history/run_history_timeline.json
reports/run_history/run_history_report.md
```

It does not rerun preprocessing, execute SPM, execute MATLAB, execute DPABI, or execute GPU code.

### Run

```bash
python -m backend.app.tools.run_history_cli
```

### API

```bash
curl http://127.0.0.1:8000/api/run-history
curl http://127.0.0.1:8000/api/run-history/latest
```

Build index:

```bash
curl -X POST http://127.0.0.1:8000/api/run-history/build \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_run_history.yaml"
  }'
```

Load detail:

```bash
curl "http://127.0.0.1:8000/api/run-history/detail?record_id=quickstart_demo:quickstart_..."
```

### Frontend

Use:

```text
Run History Browser
```

### Safety

This step:

- only reads demo_runs / work / exports / reports
- writes only reports/run_history
- does not read rawdata
- does not modify rawdata
- does not modify derivatives
- does not modify existing reports except reports/run_history
- does not modify exports
- does not modify demo_runs
- does not run SPM
- does not run MATLAB
- does not run DPABI
- does not run GPU
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not perform group-level statistical inference
- does not make clinical conclusions
```

---

## 19. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/run_history_browser_spec.md
backend/app/tools/run_history.py
backend/app/runtime/node_registry.py
examples/pipeline_run_history.yaml
backend/app/tools/run_history_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/RunHistoryBrowserPanel.tsx
frontend/src/App.tsx
tests/unit/test_run_history.py
backend/app/tools/api_smoke_test.py
docs/user_guide.md
docs/pipeline_guide.md
docs/api_reference.md
docs/frontend_guide.md
docs/troubleshooting.md
README.md
```

运行 run history index：

```bash
python -m backend.app.tools.run_history_cli
```

应生成：

```text
reports/run_history/run_history_index.json
reports/run_history/run_history_timeline.json
reports/run_history/run_history_report.md
```

run_history_index JSON 必须包含：

```json
{
  "node_id": "run_history_index",
  "records_total": 0,
  "record_type_counts": {},
  "status_counts": {},
  "records": [],
  "timeline": [],
  "safety": {
    "read_only_history_scan": true,
    "rawdata_read": false,
    "rawdata_modified": false,
    "spm_executed": false,
    "matlab_executed": false,
    "dpabi_executed": false,
    "gpu_executed": false
  }
}
```

实际 records_total 取决于已有 demo_runs、work、exports、reports。

运行测试：

```bash
python -m pytest tests/unit/test_run_history.py -q
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

测试 API：

```bash
curl http://127.0.0.1:8000/api/run-history
curl http://127.0.0.1:8000/api/run-history/latest

curl -X POST http://127.0.0.1:8000/api/run-history/build \
  -H "Content-Type: application/json" \
  -d '{}'
```

启动前端：

```bash
cd frontend
npm run dev
```

页面应该能完成：

1. 显示 Run History Browser 区域。
2. 可以生成 Run History Index。
3. 可以加载 Run History。
4. 显示 records 总数。
5. 显示 demo 数量。
6. 显示 pipeline run 数量。
7. 显示 report package 数量。
8. 显示 PASS 数量。
9. 显示 records 表格。
10. 可以点击查看某条 record 详情。
11. 可以显示 record JSON payload。
12. 可以显示 record Markdown report。
13. 不修改 rawdata。
14. 不修改 derivatives。
15. 不修改 exports。
16. 不修改 demo_runs。
17. 不运行 SPM / MATLAB。
18. 不运行 DPABI。
19. 不运行 GPU。
20. 不执行统计推断。
21. 不生成临床结论。

---

## 20. 重要限制

本步骤只做 Demo Replay / Run History Browser。

不要实现：

- 自动 rerun demo
- 自动 rerun pipeline
- 自动删除历史
- 自动修复 report package
- 真实 SPM demo
- 真实 MATLAB demo
- 真实 DPABI demo
- 真实 GPU demo
- 真实医学影像处理
- Docker build
- CI/CD
- PDF / Word / PPT 报告生成
- group-level statistical testing
- clinical interpretation
- subject exclusion automation
- rawdata 修改
- 文件删除

完成后请总结：

1. 新增了哪些文件
2. 修改了哪些文件
3. run history 会扫描哪些目录
4. record_id 如何定义
5. timeline 如何排序
6. detail API 如何读取 payload 和 Markdown report
7. Run History Browser 前端如何展示记录
8. 为什么本步骤的 Replay 不是重新执行 preprocessing
9. 为什么本步骤不修改 demo_runs / exports / work
10. 下一步如何实现 Project Cleanup / Archive Planner：只读识别临时文件、缓存和可归档产物，但不自动删除

```
写了 reports/project_final_summary.md，汇总了全部 53 步的产出：20 个 pipeline 阶段、30+ 个 Python 工具、6 个 MATLAB wrapper、15+ 个 spec、50+ 个 API 端点、20+ 个前端面板、15+ 个单元测试、5 个 DPABI contract、4 个 GPU contract，以及完整的安全架构说明。
```
