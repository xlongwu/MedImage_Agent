你是我的工程搭建助手。前十五步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
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
Step 14：完成最小本地 subject-level 并行调度 + 资源限制闭环。
Step 15：完成最小 GPU ALFF / fALFF 原型 + CPU fallback + Benchmark 闭环。

现在开始第十六步。

第十六步目标：实现“Validation / Benchmark / Regression Suite 闭环”。

当前项目已经有很多模块，但还缺系统性验证。  
本步骤要建立一个最小测试与验证体系，用来确认：

- 基础工具函数没有坏
- pipeline schema 校验正常
- Data Inspector 能扫描 synthetic BIDS
- ALFF / fALFF CPU 计算结果稳定
- GPU 不可用时能 fallback CPU
- path safety 能阻止路径穿越
- Agent Plan 不会自动执行
- API 基础接口可用
- 前端能 build
- 验证结果能生成 report

不要处理真实医学影像数据。
不要运行长耗时任务。
不要默认调用 MATLAB 大规模预处理。
不要强依赖 GPU。
不要强制要求 CuPy。
不要强制要求前端必须安装 node_modules 才能通过 Python validation。
不要引入数据库。
不要引入 Celery / Redis。
不要修改 SPM / DPABI 源码。
不要删除文件。
不要修改 rawdata。

本步骤只做最小 validation / benchmark / regression 闭环。

---

## 1. 创建 specs/validation_runtime_spec.md

创建文件：

```text
specs/validation_runtime_spec.md

内容：

# Validation Runtime Specification

This document defines the MVP validation and regression suite for MedImage Agent.

## Goals

The validation suite ensures that core modules remain stable as the project grows.

It should validate:

- pipeline schema parsing
- path safety
- synthetic BIDS generation
- dataset inspection
- ALFF / fALFF CPU computation
- GPU detection and CPU fallback
- agent plan safety
- report generation existence
- API smoke checks
- frontend build readiness

## Scope

Supported:

- pytest-based unit tests
- lightweight integration tests
- deterministic synthetic data
- CPU-only execution by default
- optional GPU checks
- optional API checks
- optional frontend build check
- validation summary JSON
- validation report Markdown

Unsupported:

- real medical imaging datasets
- long-running SPM/DPABI validation
- clinical validation
- statistical group analysis
- production CI/CD
- GPU requirement
- external network calls

## Outputs

```text
reports/validation/validation_summary.json
reports/validation/validation_report.md
Test Categories
unit
integration
api
frontend
gpu_optional
Safety Rules
Do not modify rawdata.
Do not delete files.
Do not modify third_party.
Do not require GPU.
Do not require MATLAB for default unit tests.
Do not make clinical conclusions.

---

## 2. 创建 tests/ 目录结构

如果没有 tests/，创建：

```text
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_path_safety.py
│   ├── test_pipeline_schema.py
│   ├── test_alff_compute.py
│   ├── test_gpu_utils.py
│   └── test_memory_store.py
├── integration/
│   ├── __init__.py
│   ├── test_synthetic_bids_and_inspection.py
│   ├── test_agent_plan.py
│   └── test_dataset_evaluation_report.py
└── api/
    ├── __init__.py
    └── test_api_basic.py
3. 创建 tests/conftest.py

内容：

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture()
def clean_synthetic_dir(tmp_path: Path) -> Path:
    root = tmp_path / "synthetic_bids" / "rawdata"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root
4. 创建 unit tests
tests/unit/test_path_safety.py
from __future__ import annotations

import pytest

from backend.app.runtime.path_safety import PathSafetyError, assert_allowed_read_path


def test_path_safety_rejects_path_traversal():
    with pytest.raises(PathSafetyError):
        assert_allowed_read_path("../../etc/passwd")


def test_path_safety_rejects_third_party():
    with pytest.raises(PathSafetyError):
        assert_allowed_read_path("third_party/spm12/spm.m")
tests/unit/test_pipeline_schema.py
from __future__ import annotations

import pytest

from backend.app.schemas.pipeline_schema import PipelineValidationError, validate_pipeline_dict


def test_pipeline_schema_accepts_minimal_valid_pipeline():
    spec = validate_pipeline_dict({
        "pipeline_id": "test_pipeline",
        "version": "0.1.0",
        "modality": "test",
        "description": "test",
        "execution": {"run_id": "run_test"},
        "nodes": [
            {
                "id": "node_a",
                "name": "Node A",
                "agent": "system",
                "backend": "python",
                "depends_on": [],
                "inputs": [],
                "outputs": [],
                "params": {},
                "parallel_level": "project",
                "gpu_supported": False,
                "cache": False,
            }
        ],
    })

    assert spec.pipeline_id == "test_pipeline"
    assert len(spec.nodes) == 1


def test_pipeline_schema_rejects_missing_dependency():
    with pytest.raises(PipelineValidationError):
        validate_pipeline_dict({
            "pipeline_id": "bad_pipeline",
            "version": "0.1.0",
            "modality": "test",
            "description": "bad",
            "execution": {"run_id": "run_bad"},
            "nodes": [
                {
                    "id": "node_b",
                    "name": "Node B",
                    "agent": "system",
                    "backend": "python",
                    "depends_on": ["missing_node"],
                    "inputs": [],
                    "outputs": [],
                    "params": {},
                    "parallel_level": "project",
                    "gpu_supported": False,
                    "cache": False,
                }
            ],
        })
tests/unit/test_alff_compute.py
from __future__ import annotations

import numpy as np

from backend.app.tools.alff_compute import compute_alff_backend, compute_alff_numpy


def test_compute_alff_numpy_shapes():
    rng = np.random.default_rng(42)
    data = rng.normal(size=(4, 4, 4, 20)).astype("float32")

    alff, falff, warnings = compute_alff_numpy(data, tr=2.0, freq_band=(0.01, 0.08))

    assert alff.shape == (4, 4, 4)
    assert falff.shape == (4, 4, 4)
    assert np.isfinite(alff).all()
    assert np.isfinite(falff).all()
    assert isinstance(warnings, list)


def test_compute_alff_backend_cpu_fallback():
    rng = np.random.default_rng(42)
    data = rng.normal(size=(4, 4, 4, 20)).astype("float32")

    result = compute_alff_backend(
        data=data,
        tr=2.0,
        freq_band=(0.01, 0.08),
        prefer_gpu=False,
        require_gpu=False,
    )

    assert result["ok"] is True
    assert result["backend"] == "cpu-numpy"
    assert result["alff"].shape == (4, 4, 4)
    assert result["falff"].shape == (4, 4, 4)
tests/unit/test_gpu_utils.py
from __future__ import annotations

from backend.app.tools.gpu_utils import detect_gpu


def test_detect_gpu_never_requires_gpu():
    result = detect_gpu()

    assert result["ok"] is True
    assert "cupy_available" in result
    assert "gpu_available" in result
    assert "warnings" in result
    assert "errors" in result
tests/unit/test_memory_store.py
from __future__ import annotations

import json
from pathlib import Path

from backend.app.runtime.memory_store import append_run_history, ensure_memory_layout


def test_memory_layout_and_run_history(tmp_path: Path):
    ensure_memory_layout(str(tmp_path))

    history_path = append_run_history(
        project_name="test_project",
        record={"agent_run_id": "agent_test", "phi": "should_not_store"},
        root_dir=str(tmp_path),
    )

    assert history_path.exists()
    line = history_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["agent_run_id"] == "agent_test"
    assert "phi" not in payload
5. 创建 integration tests
tests/integration/test_synthetic_bids_and_inspection.py
from __future__ import annotations

from pathlib import Path

from backend.app.tools.data_inspector import inspect_dataset
from backend.app.tools.synthetic_bids import create_synthetic_bids_dataset


def test_synthetic_bids_and_inspection(tmp_path: Path):
    rawdata = tmp_path / "synthetic_bids" / "rawdata"
    output = tmp_path / "work" / "dataset_index"

    created = create_synthetic_bids_dataset(str(rawdata), subjects=["sub-001", "sub-002"])
    assert created["ok"] is True

    result = inspect_dataset(
        rawdata_dir=str(rawdata),
        output_dir=str(output),
        read_nifti_metadata=True,
    )

    assert result["ok"] is True
    assert result["metrics"]["subjects_total"] == 2
    assert result["metrics"]["subjects_complete"] == 2
    assert (output / "dataset_index.json").exists()
    assert (output / "data_completeness_report.json").exists()
    assert (output / "subject_table.csv").exists()
tests/integration/test_agent_plan.py
from __future__ import annotations

from pathlib import Path

import yaml

from backend.app.runtime.agent_plan import create_agent_plan


def test_agent_plan_does_not_execute_pipeline(tmp_path: Path):
    project_config = tmp_path / "project_config.yaml"
    pipeline = tmp_path / "pipeline.yaml"

    project_config.write_text(
        yaml.safe_dump({
            "project": {"name": "test_project", "root_dir": "."},
            "third_party": {"spm_dir": "./third_party/spm12", "dpabi_dir": "./third_party/DPABI"},
            "runtime": {"work_dir": str(tmp_path / "work"), "log_dir": str(tmp_path / "logs"), "report_dir": str(tmp_path / "reports")},
            "safety": {"rawdata_readonly": True},
        }),
        encoding="utf-8",
    )

    pipeline.write_text(
        yaml.safe_dump({
            "pipeline_id": "test_plan_pipeline",
            "version": "0.1.0",
            "modality": "test",
            "description": "plan only",
            "execution": {"run_id": "run_plan_only"},
            "nodes": [
                {
                    "id": "data_inspection",
                    "name": "Data Inspection",
                    "agent": "data-inspector",
                    "backend": "python",
                    "depends_on": [],
                    "inputs": [],
                    "outputs": ["./work/dataset_index/dataset_index.json"],
                    "params": {},
                    "parallel_level": "project",
                    "gpu_supported": False,
                    "cache": False,
                }
            ],
        }),
        encoding="utf-8",
    )

    plan = create_agent_plan(
        agent_run_id="agent_test",
        project_config_path=str(project_config),
        pipeline_path=str(pipeline),
    )

    assert plan["ok"] is True
    assert plan["mode"] == "PLAN"
    assert plan["requires_approval"] is True
    assert plan["approved"] is False
tests/integration/test_dataset_evaluation_report.py
from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.report_writer import write_dataset_evaluation_report


def test_report_writer_generates_markdown_and_html(tmp_path: Path):
    report_dir = tmp_path / "reports" / "dataset_evaluation"
    report_dir.mkdir(parents=True)

    summary_path = report_dir / "dataset_summary.json"
    table_path = report_dir / "subject_qc_table.csv"
    exclusion_path = report_dir / "exclusion_recommendations.csv"

    summary_path.write_text(
        json.dumps({
            "run_id": "run_test",
            "subjects_total": 1,
            "subjects_complete": 1,
            "subjects_preprocess_success": 1,
            "subjects_qc_success": 1,
            "subjects_include": 1,
            "subjects_manual_review": 0,
            "subjects_exclude": 0,
            "dataset_quality_score": 100,
            "dataset_index": "dataset_index.json",
        }),
        encoding="utf-8",
    )

    table_path.write_text("subject_id,recommendation\nsub-001,INCLUDE\n", encoding="utf-8")
    exclusion_path.write_text("subject_id,recommendation,reasons\n", encoding="utf-8")

    result = write_dataset_evaluation_report(
        dataset_summary_path=str(summary_path),
        subject_qc_table_path=str(table_path),
        exclusion_recommendations_path=str(exclusion_path),
        output_dir=str(report_dir),
    )

    assert result["ok"] is True
    assert (report_dir / "dataset_evaluation_report.md").exists()
    assert (report_dir / "dataset_evaluation_report.html").exists()
6. 创建 API test
tests/api/test_api_basic.py
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_api():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True


def test_pipelines_api():
    client = TestClient(app)
    response = client.get("/api/pipelines")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "pipelines" in payload


def test_path_traversal_rejected():
    client = TestClient(app)
    response = client.get("/api/files/read", params={"path": "../../etc/passwd"})

    assert response.status_code in {400, 403}
7. 创建 backend/app/tools/validation_runner.py

创建文件：

backend/app/tools/validation_runner.py

目标：统一运行 validation，并生成 summary/report。

提供函数：

run_validation_suite(
    include_api: bool = True,
    include_frontend: bool = False,
    include_gpu_optional: bool = True,
) -> dict

要求：

使用 subprocess 调用 pytest。
默认运行：
tests/unit
tests/integration
tests/api
frontend build 默认不跑，除非 include_frontend=true。
GPU optional 只调用 gpu_check_cli，不要求 GPU 可用。
输出：
reports/validation/validation_summary.json
reports/validation/validation_report.md
不删除文件。
不执行长耗时 pipeline。
不要求 MATLAB。

参考实现：

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


def _run_command(cmd: list[str], cwd: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - started

    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "ok": completed.returncode == 0,
        "duration_seconds": duration,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def run_validation_suite(
    include_api: bool = True,
    include_frontend: bool = False,
    include_gpu_optional: bool = True,
) -> dict[str, Any]:
    out_dir = Path("reports") / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, Any]] = []

    checks.append({
        "name": "pytest_unit",
        **_run_command(["python", "-m", "pytest", "tests/unit", "-q"]),
    })

    checks.append({
        "name": "pytest_integration",
        **_run_command(["python", "-m", "pytest", "tests/integration", "-q"]),
    })

    if include_api:
        checks.append({
            "name": "pytest_api",
            **_run_command(["python", "-m", "pytest", "tests/api", "-q"]),
        })

    if include_gpu_optional:
        checks.append({
            "name": "gpu_check_optional",
            **_run_command(["python", "-m", "backend.app.tools.gpu_check_cli"]),
        })

    if include_frontend:
        checks.append({
            "name": "frontend_build",
            **_run_command(["npm", "run", "build"], cwd="frontend"),
        })

    ok = all(item["ok"] for item in checks)

    summary = {
        "ok": ok,
        "checks_total": len(checks),
        "checks_passed": sum(1 for item in checks if item["ok"]),
        "checks_failed": sum(1 for item in checks if not item["ok"]),
        "checks": checks,
    }

    summary_path = out_dir / "validation_summary.json"
    report_path = out_dir / "validation_report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"- Overall status: {'PASS' if ok else 'FAIL'}")
    lines.append(f"- Checks total: {summary['checks_total']}")
    lines.append(f"- Checks passed: {summary['checks_passed']}")
    lines.append(f"- Checks failed: {summary['checks_failed']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | OK | Return Code | Duration seconds |")
    lines.append("|---|---:|---:|---:|")

    for item in checks:
        lines.append(
            f"| {item['name']} | {item['ok']} | {item['returncode']} | "
            f"{item['duration_seconds']:.3f} |"
        )

    lines.append("")
    lines.append("## Failed Check Details")
    lines.append("")

    failed = [item for item in checks if not item["ok"]]
    if not failed:
        lines.append("No failed checks.")
    else:
        for item in failed:
            lines.append(f"### {item['name']}")
            lines.append("")
            lines.append("STDOUT:")
            lines.append("```text")
            lines.append(item.get("stdout", ""))
            lines.append("```")
            lines.append("")
            lines.append("STDERR:")
            lines.append("```text")
            lines.append(item.get("stderr", ""))
            lines.append("```")
            lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary["outputs"] = [str(summary_path), str(report_path)]
    return summary
8. 创建 backend/app/tools/run_validation_cli.py

创建文件：

backend/app/tools/run_validation_cli.py

内容：

from __future__ import annotations

import json
import sys

from backend.app.tools.validation_runner import run_validation_suite


def main() -> int:
    args = set(sys.argv[1:])

    include_frontend = "--frontend" in args
    include_api = "--no-api" not in args
    include_gpu_optional = "--no-gpu" not in args

    result = run_validation_suite(
        include_api=include_api,
        include_frontend=include_frontend,
        include_gpu_optional=include_gpu_optional,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
9. 修改 backend/app/api/routes.py

新增 API：

POST /api/validation/run
GET  /api/validation/latest

要求：

/api/validation/run 默认不跑 frontend build。
/api/validation/run 调用 run_validation_suite。
/api/validation/latest 读取：
reports/validation/validation_summary.json
reports/validation/validation_report.md
不执行长耗时 pipeline。
不要求 MATLAB。
不要求 GPU。

新增导入：

from backend.app.tools.validation_runner import run_validation_suite

新增路由：

@router.post("/api/validation/run")
def api_run_validation(include_frontend: bool = False) -> dict[str, Any]:
    result = run_validation_suite(
        include_api=True,
        include_frontend=include_frontend,
        include_gpu_optional=True,
    )
    if not result.get("ok"):
        return result
    return result


@router.get("/api/validation/latest")
def api_validation_latest() -> dict[str, Any]:
    base = Path("reports") / "validation"

    return {
        "ok": True,
        "validation_summary": _read_json_if_exists(base / "validation_summary.json"),
        "validation_report": _read_text_if_exists(base / "validation_report.md"),
    }
10. 修改 frontend/src/api.ts

新增：

export async function runValidation(baseUrl: string, includeFrontend = false) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/validation/run?include_frontend=${includeFrontend ? "true" : "false"}`,
    { method: "POST" }
  );
}

export async function getValidationLatest(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/validation/latest");
}
11. 创建 frontend/src/components/ValidationPanel.tsx

创建文件：

frontend/src/components/ValidationPanel.tsx

内容：

import { useState } from "react";
import { getValidationLatest, runValidation } from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function ValidationPanel({ baseUrl }: Props) {
  const [includeFrontend, setIncludeFrontend] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleRunValidation() {
    setStatus("RUNNING");
    setError("");

    try {
      const payload = await runValidation(baseUrl, includeFrontend);
      setResult(payload);
      setStatus(payload.ok ? "SUCCESS" : "FAILED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadLatest() {
    setError("");

    try {
      const payload = await getValidationLatest(baseUrl);
      setLatest(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <div className="row">
        <label className="inlineCheck">
          <input
            type="checkbox"
            checked={includeFrontend}
            onChange={(event) => setIncludeFrontend(event.target.checked)}
          />
          Include frontend build
        </label>

        <button onClick={handleRunValidation}>运行 Validation</button>
        <button onClick={handleLoadLatest}>加载最新报告</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <h3>Validation Result</h3>
      <JsonBlock value={result} emptyText="尚未运行 validation" />

      <h3>Latest Validation Summary</h3>
      <JsonBlock
        value={latest?.validation_summary}
        emptyText="暂无 validation summary"
      />

      <h3>Latest Validation Report</h3>
      <TextViewer
        text={
          typeof latest?.validation_report === "string"
            ? latest.validation_report
            : null
        }
        emptyText="暂无 validation report"
      />
    </div>
  );
}
12. 修改 frontend/src/App.tsx

新增导入：

import { ValidationPanel } from "./components/ValidationPanel";

在页面靠后增加 Section：

<Section
  title="Validation / Regression"
  description="运行最小测试与验证套件，生成 validation summary 和 report。"
>
  <ValidationPanel baseUrl={baseUrl} />
</Section>
13. 修改 frontend/src/styles.css

追加：

.inlineCheck {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.inlineCheck input {
  min-width: unset;
}
14. 修改 backend/app/tools/api_smoke_test.py

追加测试：

call("GET", "/api/validation/latest")

不要在 smoke test 中自动调用 /api/validation/run，避免测试套件递归或耗时。

15. 更新 README.md

追加第十六步说明：

## Step 16: Validation / Benchmark / Regression Suite

This step adds a lightweight validation suite.

Install dependencies:

```bash
pip install pytest httpx fastapi pyyaml numpy nibabel

Run validation:

python -m backend.app.tools.run_validation_cli

Run validation with frontend build:

python -m backend.app.tools.run_validation_cli --frontend

Expected outputs:

reports/validation/validation_summary.json
reports/validation/validation_report.md

API:

curl -X POST "http://127.0.0.1:8000/api/validation/run"
curl "http://127.0.0.1:8000/api/validation/latest"

Frontend:

Use the Validation / Regression panel.

Safety:

Default validation does not require MATLAB.
Default validation does not require GPU.
Validation does not process real medical data.
Validation does not modify rawdata.

---

## 16. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/validation_runtime_spec.md
tests/__init__.py
tests/conftest.py
tests/unit/test_path_safety.py
tests/unit/test_pipeline_schema.py
tests/unit/test_alff_compute.py
tests/unit/test_gpu_utils.py
tests/unit/test_memory_store.py
tests/integration/test_synthetic_bids_and_inspection.py
tests/integration/test_agent_plan.py
tests/integration/test_dataset_evaluation_report.py
tests/api/test_api_basic.py
backend/app/tools/validation_runner.py
backend/app/tools/run_validation_cli.py
backend/app/api/routes.py
backend/app/tools/api_smoke_test.py
frontend/src/api.ts
frontend/src/components/ValidationPanel.tsx
frontend/src/App.tsx
frontend/src/styles.css
README.md

安装依赖：

pip install pytest httpx fastapi pyyaml numpy nibabel

运行：

python -m backend.app.tools.run_validation_cli

成功后生成：

reports/validation/validation_summary.json
reports/validation/validation_report.md

其中 validation_summary.json 应包含：

{
  "ok": true,
  "checks_total": 4,
  "checks_failed": 0
}

运行 pytest：

python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/api -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl -X POST "http://127.0.0.1:8000/api/validation/run"
curl "http://127.0.0.1:8000/api/validation/latest"

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Validation / Regression 区域。
点击运行 Validation。
显示 validation_summary。
显示 validation_report。
默认不要求 GPU。
默认不要求 MATLAB。
默认不处理真实医学影像数据。
17. 重要限制

本步骤只做 MVP validation / benchmark / regression suite。

不要实现：

真实数据验证
大型 benchmark
MATLAB 必跑测试
GPU 必跑测试
GitHub Actions
Docker CI
复杂性能仪表盘
临床有效性验证
自动修复失败测试
自动修改代码

完成后请总结：

新增了哪些测试文件
新增了哪些 validation 工具
如何运行 pytest
如何运行 validation suite
validation 输出在哪里
哪些测试默认不依赖 MATLAB/GPU
当前验证体系的限制是什么

'''
Step 16 主要实现的是 Validation / Benchmark / Regression Suite 闭环 。

## 核心目标
建立一个 最小测试与验证体系 ，用来系统性确认项目核心模块的稳定性，确保：

- 基础工具函数没有坏
- Pipeline schema 校验正常
- Data Inspector 能扫描 synthetic BIDS
- ALFF / fALFF CPU 计算结果稳定
- GPU 不可用时能 fallback CPU
- Path safety 能阻止路径穿越
- Agent Plan 不会自动执行
- API 基础接口可用
- 前端能 build
- 验证结果能生成 report
## 主要组件
组件 功能 tests/unit/ 单元测试（path safety、schema、ALFF、GPU、memory） tests/integration/ 集成测试（synthetic BIDS、agent plan、report） tests/api/ API 测试（health、pipelines、path traversal） validation_runner.py 统一运行所有测试并生成报告 run_validation_cli.py CLI 入口

## 测试分类
1. Unit Tests - 独立测试单个模块
2. Integration Tests - 测试模块间协作
3. API Tests - 测试 FastAPI 接口
4. GPU Optional - 可选 GPU 检测（不强制要求）
5. Frontend - 可选前端构建检查（默认不运行）
## 输出
```
reports/validation/
├── validation_summary.json   # 结构化验证结果
└── validation_report.md      # 人类可读报告
```
## 安全规则
- 不处理真实医学影像数据
- 不运行长耗时任务
- 不默认调用 MATLAB
- 不强依赖 GPU
- 不强制要求 CuPy
- 不引入数据库
- 不修改 SPM / DPABI 源码
- 不删除文件
- 不修改 rawdata
'''