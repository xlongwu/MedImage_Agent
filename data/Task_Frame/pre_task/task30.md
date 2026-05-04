你是我的工程搭建助手。前二十九步已经完成：

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
Step 15：完成 GPU ALFF / fALFF 原型与 CPU fallback + Benchmark 闭环。
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

现在开始第三十步。

第三十步目标：实现“Run Artifact Browser + File Preview 闭环”。

当前系统已经会产生大量 artifact：

- work/pipeline_runs/*/summary.json
- work/states/*
- work/dpabi/*
- work/experiments/*
- reports/*
- logs/*
- derivatives/*
- examples/pipeline_*.yaml
- examples/project_config_*.yaml

但目前前端只能通过各个面板零散查看结果，缺少一个统一的 artifact browser。

本步骤要实现：

- 扫描允许目录下的 artifact
- 生成 artifact_index.json
- 支持按 run_id / category / extension / modified time 过滤
- 支持安全预览 JSON / Markdown / CSV / YAML / TXT / LOG
- 支持 NIfTI 文件只预览 metadata，不读取完整 voxel 数据
- 支持 HTML 报告以文本方式预览，不执行脚本
- 支持前端 artifact list
- 支持前端 file preview
- 支持刷新 artifact index
- validation suite 增加 artifact browser 轻量测试

本步骤只做读取和预览，不执行新的 pipeline。
本步骤不要启动 MATLAB。
本步骤不要运行 DPABI。
本步骤不要运行 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。
本步骤不要提供任意路径读取能力。
本步骤不要把二进制文件内容直接返回给前端。

---

## 1. 创建 specs/artifact_browser_spec.md

创建文件：

```text
specs/artifact_browser_spec.md

内容：

# Artifact Browser and File Preview Specification

This document defines the MVP artifact browser for MedImage Agent.

## Goals

The artifact browser provides a unified view of generated files.

It should:

- scan allowed artifact directories
- index generated files
- classify artifacts by category
- support safe preview of text-like files
- support metadata-only preview for NIfTI files
- expose index and preview through API
- render artifact browser in the frontend

## Scope

Supported in this step:

- scan work
- scan reports
- scan logs
- scan derivatives
- scan examples pipeline/config YAML files
- generate artifact index JSON
- preview JSON, YAML, Markdown, CSV, TXT, LOG, HTML as text
- preview NIfTI metadata only
- frontend artifact list and preview
- lightweight unit test

Unsupported in this step:

- arbitrary filesystem browsing
- file editing
- file deletion
- rawdata modification
- binary file streaming
- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- executing HTML or JavaScript reports

## Outputs

```text
work/artifacts/artifact_index.json
Allowed Roots
work/
reports/
logs/
derivatives/
examples/
Excluded Paths
third_party/
.git/
node_modules/
__pycache__/
rawdata/

The browser should avoid indexing rawdata paths by default, even synthetic rawdata, because the artifact browser is for generated artifacts.

Preview Rules

Text-like files:

.json
.yaml
.yml
.md
.txt
.log
.csv
.tsv
.html

NIfTI metadata-only files:

.nii
.nii.gz

Unsupported files should return metadata only.

Size Limits
Maximum text preview size: 200 KB
Maximum indexed file size metadata only: no hard limit
Do not return binary content
Safety Rules
Do not execute files.
Do not serve arbitrary filesystem paths.
Do not follow path traversal.
Do not modify files.
Do not delete files.
Do not read rawdata.
Do not execute HTML or JavaScript.

---

## 2. 创建 backend/app/tools/artifact_browser.py

创建文件：

```text
backend/app/tools/artifact_browser.py

目标：扫描 artifact、生成 index、安全预览文件。

提供函数：

build_artifact_index(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    log_dir: str = "./logs",
    derivatives_dir: str = "./derivatives",
    examples_dir: str = "./examples",
) -> dict

preview_artifact(
    path: str,
    max_text_bytes: int = 200_000,
) -> dict

实现要求：

只允许扫描这些目录：
work
reports
logs
derivatives
examples
排除：
third_party
.git
node_modules
pycache
rawdata
artifact 分类：
pipeline_run
report
log
dpabi
experiment
derivative
config
unknown
index 字段：
path
name
extension
size_bytes
modified_time
category
preview_supported
preview_type
run_id_guess
preview 规则：
JSON：解析并返回 parsed + text
CSV/TSV：返回前 100 行 text
Markdown/YAML/TXT/LOG/HTML：返回 text
NIfTI：只返回 metadata，不返回 voxel data
其他：只返回 metadata
path 必须在 allowed roots 内。
禁止 path traversal。
不修改文件。
不删除文件。
不执行 HTML。

参考实现：

from __future__ import annotations

import csv
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".log",
    ".csv",
    ".tsv",
    ".html",
}
NIFTI_EXTENSIONS = {".nii", ".nii.gz"}
EXCLUDED_PARTS = {"third_party", ".git", "node_modules", "__pycache__", "rawdata"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_nifti(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".nii") or name.endswith(".nii.gz")


def _extension(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nii.gz"):
        return ".nii.gz"
    return path.suffix.lower()


def _allowed_roots() -> list[Path]:
    return [
        Path("work").resolve(),
        Path("reports").resolve(),
        Path("logs").resolve(),
        Path("derivatives").resolve(),
        Path("examples").resolve(),
    ]


def _is_under_allowed_root(path: Path) -> bool:
    resolved = path.resolve()
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    return any(part in EXCLUDED_PARTS for part in parts)


def _category_for(path: Path) -> str:
    text = str(path).replace("\\", "/")

    if "/pipeline_runs/" in text:
        return "pipeline_run"
    if text.startswith("outputs/reports/") or "/reports/" in text:
        return "report"
    if text.startswith("outputs/logs/") or "/logs/" in text:
        return "log"
    if "/dpabi/" in text:
        return "dpabi"
    if "/experiments/" in text:
        return "experiment"
    if text.startswith("outputs/derivatives/") or "/derivatives/" in text:
        return "derivative"
    if text.startswith("examples/") and path.suffix.lower() in {".yaml", ".yml", ".json"}:
        return "config"
    return "unknown"


def _guess_run_id(path: Path) -> str | None:
    parts = list(path.parts)

    if "pipeline_runs" in parts:
        idx = parts.index("pipeline_runs")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    if "template_instances" in parts:
        idx = parts.index("template_instances")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return None


def _preview_type(path: Path) -> str:
    ext = _extension(path)
    if ext in TEXT_EXTENSIONS:
        return "text"
    if _is_nifti(path):
        return "nifti_metadata"
    return "metadata_only"


def _artifact_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    ext = _extension(path)
    preview_type = _preview_type(path)

    return {
        "path": str(path),
        "name": path.name,
        "extension": ext,
        "size_bytes": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "category": _category_for(path),
        "preview_supported": preview_type in {"text", "nifti_metadata"},
        "preview_type": preview_type,
        "mime_type": mimetypes.guess_type(str(path))[0],
        "run_id_guess": _guess_run_id(path),
    }


def build_artifact_index(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    log_dir: str = "./logs",
    derivatives_dir: str = "./derivatives",
    examples_dir: str = "./examples",
) -> dict[str, Any]:
    roots = [
        Path(work_dir),
        Path(report_dir),
        Path(log_dir),
        Path(derivatives_dir),
        Path(examples_dir),
    ]

    artifacts: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if _is_excluded(path):
                continue

            try:
                if not _is_under_allowed_root(path):
                    warnings.append(f"Skipped path outside allowed roots: {path}")
                    continue

                artifacts.append(_artifact_record(path))

            except Exception as exc:
                warnings.append(f"Failed to index {path}: {exc}")

    artifacts = sorted(
        artifacts,
        key=lambda item: item.get("modified_time") or "",
        reverse=True,
    )

    out_dir = Path(work_dir) / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "artifact_index.json"

    payload = {
        "ok": True,
        "node_id": "artifact_browser",
        "backend": "python",
        "generated_at": _now_iso(),
        "artifacts_total": len(artifacts),
        "artifacts": artifacts,
        "categories": _count_by(artifacts, "category"),
        "extensions": _count_by(artifacts, "extension"),
        "warnings": warnings,
        "errors": errors,
    }

    index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload["outputs"] = [str(index_path)]
    return payload


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items(), key=lambda pair: pair[0]))


def _read_text_preview(path: Path, max_text_bytes: int) -> dict[str, Any]:
    raw = path.read_bytes()
    truncated = len(raw) > max_text_bytes
    raw = raw[:max_text_bytes]

    text = raw.decode("utf-8", errors="replace")
    ext = _extension(path)

    parsed = None
    if ext == ".json":
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None

    if ext in {".csv", ".tsv"}:
        lines = text.splitlines()
        text = "\n".join(lines[:101])
        truncated = truncated or len(lines) > 101

    return {
        "preview_type": "text",
        "text": text,
        "parsed": parsed,
        "truncated": truncated,
        "bytes_returned": len(raw),
    }


def _nifti_metadata(path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
    except ImportError:
        return {
            "preview_type": "nifti_metadata",
            "ok": False,
            "error": "Missing dependency: nibabel. Install with: pip install nibabel",
        }

    try:
        img = nib.load(str(path))
        header = img.header

        return {
            "preview_type": "nifti_metadata",
            "ok": True,
            "shape": list(img.shape),
            "dtype": str(header.get_data_dtype()),
            "zooms": list(header.get_zooms()),
            "affine": img.affine.tolist(),
            "note": "Voxel data was not loaded or returned.",
        }
    except Exception as exc:
        return {
            "preview_type": "nifti_metadata",
            "ok": False,
            "error": str(exc),
        }


def preview_artifact(
    path: str,
    max_text_bytes: int = 200_000,
) -> dict[str, Any]:
    target = Path(path)

    if ".." in target.parts:
        return {
            "ok": False,
            "errors": ["Path traversal is not allowed."],
            "warnings": [],
        }

    if not target.exists() or not target.is_file():
        return {
            "ok": False,
            "errors": [f"Artifact file not found: {target}"],
            "warnings": [],
        }

    if _is_excluded(target):
        return {
            "ok": False,
            "errors": [f"Path is excluded from artifact preview: {target}"],
            "warnings": [],
        }

    if not _is_under_allowed_root(target):
        return {
            "ok": False,
            "errors": [f"Path is outside allowed roots: {target}"],
            "warnings": [],
        }

    record = _artifact_record(target)
    preview_type = record["preview_type"]

    if preview_type == "text":
        preview = _read_text_preview(target, max_text_bytes=max_text_bytes)
    elif preview_type == "nifti_metadata":
        preview = _nifti_metadata(target)
    else:
        preview = {
            "preview_type": "metadata_only",
            "text": None,
            "parsed": None,
            "truncated": False,
            "note": "Preview is not supported for this file type.",
        }

    return {
        "ok": True,
        "artifact": record,
        "preview": preview,
        "warnings": [],
        "errors": [],
    }
3. 创建 backend/app/tools/run_artifact_browser_cli.py

创建文件：

backend/app/tools/run_artifact_browser_cli.py

内容：

from __future__ import annotations

import json
import sys

from backend.app.tools.artifact_browser import build_artifact_index, preview_artifact


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--preview":
        if len(args) < 2:
            print(json.dumps({"ok": False, "errors": ["Missing path after --preview"]}, indent=2))
            return 2
        result = preview_artifact(args[1])
    else:
        result = build_artifact_index()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
4. 修改 backend/app/api/models.py

新增 request model：

class ArtifactPreviewRequest(BaseModel):
    path: str = Field(default="")
5. 修改 backend/app/api/routes.py

新增 API：

GET  /api/artifacts
POST /api/artifacts/refresh
POST /api/artifacts/preview

新增导入：

from backend.app.api.models import ArtifactPreviewRequest
from backend.app.tools.artifact_browser import build_artifact_index, preview_artifact

新增路由：

@router.get("/api/artifacts")
def api_get_artifacts() -> dict[str, Any]:
    index_path = Path("work") / "artifacts" / "artifact_index.json"

    index = _read_json_if_exists(index_path)
    if index is None:
        index = build_artifact_index()

    return {
        "ok": True,
        "index": index,
    }


@router.post("/api/artifacts/refresh")
def api_refresh_artifacts() -> dict[str, Any]:
    result = build_artifact_index()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/api/artifacts/preview")
def api_preview_artifact(request: ArtifactPreviewRequest) -> dict[str, Any]:
    result = preview_artifact(request.path)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result
6. 修改 frontend/src/api.ts

新增：

export async function getArtifacts(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/artifacts");
}

export async function refreshArtifacts(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/artifacts/refresh",
    { method: "POST" }
  );
}

export async function previewArtifact(baseUrl: string, path: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/artifacts/preview",
    {
      method: "POST",
      body: JSON.stringify({ path })
    }
  );
}
7. 创建 frontend/src/components/ArtifactBrowser.tsx

创建文件：

frontend/src/components/ArtifactBrowser.tsx

内容：

import { useMemo, useState } from "react";
import {
  getArtifacts,
  previewArtifact,
  refreshArtifacts
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

type ArtifactRecord = {
  path: string;
  name: string;
  extension: string;
  size_bytes: number;
  modified_time: string;
  category: string;
  preview_supported: boolean;
  preview_type: string;
  run_id_guess?: string | null;
};

function asArtifacts(payload: Record<string, unknown> | null): ArtifactRecord[] {
  const index = payload?.index as Record<string, unknown> | undefined;
  const artifacts = index?.artifacts;

  if (!Array.isArray(artifacts)) return [];
  return artifacts as ArtifactRecord[];
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function ArtifactBrowser({ baseUrl }: Props) {
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [extensionFilter, setExtensionFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleLoad() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await getArtifacts(baseUrl);
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
      const result = await refreshArtifacts(baseUrl);
      setPayload({ ok: true, index: result });
      setStatus("REFRESHED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handlePreview(path: string) {
    setStatus("PREVIEWING");
    setError("");

    try {
      const result = await previewArtifact(baseUrl, path);
      setPreview(result);
      setStatus("PREVIEW_READY");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const artifacts = asArtifacts(payload);

  const categories = useMemo(() => {
    return ["all", ...Array.from(new Set(artifacts.map((item) => item.category))).sort()];
  }, [artifacts]);

  const extensions = useMemo(() => {
    return ["all", ...Array.from(new Set(artifacts.map((item) => item.extension))).sort()];
  }, [artifacts]);

  const filtered = artifacts.filter((item) => {
    if (categoryFilter !== "all" && item.category !== categoryFilter) return false;
    if (extensionFilter !== "all" && item.extension !== extensionFilter) return false;

    const haystack = `${item.path} ${item.name} ${item.run_id_guess || ""}`.toLowerCase();
    if (search && !haystack.includes(search.toLowerCase())) return false;

    return true;
  });

  const previewPayload = preview?.preview as Record<string, unknown> | undefined;
  const previewText =
    typeof previewPayload?.text === "string" ? previewPayload.text : null;

  return (
    <div>
      <div className="row">
        <button onClick={handleLoad}>加载 Artifact Index</button>
        <button onClick={handleRefresh}>刷新 Artifact Index</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="formGrid">
        <label>
          Search
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="path / run_id / filename"
          />
        </label>

        <label>
          Category
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          Extension
          <select
            value={extensionFilter}
            onChange={(event) => setExtensionFilter(event.target.value)}
          >
            {extensions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="artifactSummary">
        Showing {filtered.length} / {artifacts.length} artifacts
      </div>

      <div className="artifactLayout">
        <div className="artifactList">
          {filtered.slice(0, 300).map((item) => (
            <button
              key={item.path}
              className="artifactItem"
              onClick={() => handlePreview(item.path)}
            >
              <span className="artifactName">{item.name}</span>
              <span className="artifactMeta">
                {item.category} · {item.extension || "no-ext"} · {formatBytes(item.size_bytes)}
              </span>
              <span className="artifactPath">{item.path}</span>
            </button>
          ))}
        </div>

        <div className="artifactPreview">
          <h3>Artifact Preview</h3>

          <JsonBlock value={preview?.artifact} emptyText="尚未选择 artifact" />

          {previewText ? (
            <TextViewer text={previewText} emptyText="暂无文本预览" />
          ) : (
            <JsonBlock value={previewPayload} emptyText="暂无 preview" />
          )}
        </div>
      </div>

      <h3>Artifact Index JSON</h3>
      <JsonBlock value={payload?.index} emptyText="尚未加载 artifact index" />
    </div>
  );
}
8. 修改 frontend/src/App.tsx

新增导入：

import { ArtifactBrowser } from "./components/ArtifactBrowser";

在 Experiment Dashboard 后增加 Section：

<Section
  title="Run Artifact Browser / File Preview"
  description="统一浏览 reports、logs、pipeline summaries、DPABI outputs 和 experiment artifacts。"
>
  <ArtifactBrowser baseUrl={baseUrl} />
</Section>
9. 修改 frontend/src/styles.css

追加：

.artifactSummary {
  margin: 12px 0;
  color: #667085;
  font-size: 13px;
}

.artifactLayout {
  display: grid;
  grid-template-columns: minmax(280px, 420px) 1fr;
  gap: 16px;
  align-items: start;
}

.artifactList {
  border: 1px solid #e1e6f2;
  border-radius: 14px;
  background: white;
  max-height: 620px;
  overflow: auto;
}

.artifactItem {
  width: 100%;
  display: block;
  text-align: left;
  border: 0;
  border-bottom: 1px solid #eef2f8;
  border-radius: 0;
  background: white;
  padding: 12px;
  cursor: pointer;
}

.artifactItem:hover {
  background: #f8fafc;
}

.artifactName {
  display: block;
  font-weight: 700;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifactMeta {
  display: block;
  font-size: 12px;
  color: #667085;
  margin-top: 4px;
}

.artifactPath {
  display: block;
  font-size: 11px;
  color: #98a2b3;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifactPreview {
  min-width: 0;
}

@media (max-width: 900px) {
  .artifactLayout {
    grid-template-columns: 1fr;
  }
}
10. 新增轻量测试

创建文件：

tests/unit/test_artifact_browser.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.artifact_browser import build_artifact_index, preview_artifact


def test_artifact_browser_indexes_and_previews_json(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    work = tmp_path / "work"
    reports = tmp_path / "reports"
    logs = tmp_path / "logs"
    derivatives = tmp_path / "derivatives"
    examples = tmp_path / "examples"

    run_dir = work / "pipeline_runs" / "run_test_001"
    run_dir.mkdir(parents=True)
    reports.mkdir()
    logs.mkdir()
    derivatives.mkdir()
    examples.mkdir()

    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps({
            "run_id": "run_test_001",
            "status": "SUCCESS",
        }),
        encoding="utf-8",
    )

    index = build_artifact_index(
        work_dir="./work",
        report_dir="./reports",
        log_dir="./logs",
        derivatives_dir="./derivatives",
        examples_dir="./examples",
    )

    assert index["ok"] is True
    assert index["artifacts_total"] >= 1

    paths = [item["path"] for item in index["artifacts"]]
    assert any("summary.json" in item for item in paths)

    preview = preview_artifact(str(summary_path))

    assert preview["ok"] is True
    assert preview["preview"]["parsed"]["run_id"] == "run_test_001"


def test_artifact_browser_rejects_path_traversal(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = preview_artifact("../../etc/passwd")

    assert result["ok"] is False
11. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/artifacts")

不要在 smoke test 中调用 POST preview 或 refresh。

12. 更新 README.md

追加第三十步说明：

## Step 30: Run Artifact Browser and File Preview

This step adds a unified artifact browser.

It supports:

- indexing work artifacts
- indexing reports
- indexing logs
- indexing derivatives
- indexing example pipeline/config files
- previewing JSON, Markdown, YAML, CSV, TXT, LOG, HTML as text
- previewing NIfTI metadata only
- frontend artifact list and preview

It does not execute pipelines.

### Build Artifact Index

```bash
python -m backend.app.tools.run_artifact_browser_cli

Expected output:

work/artifacts/artifact_index.json
Preview Artifact
python -m backend.app.tools.run_artifact_browser_cli --preview work/experiments/run_index.json
API
curl http://127.0.0.1:8000/api/artifacts

Refresh:

curl -X POST http://127.0.0.1:8000/api/artifacts/refresh

Preview:

curl -X POST http://127.0.0.1:8000/api/artifacts/preview \
  -H "Content-Type: application/json" \
  -d '{"path": "outputs/work/experiments/run_index.json"}'
Frontend

Use:

Run Artifact Browser / File Preview
Safety

The artifact browser:

does not execute files
does not browse arbitrary filesystem paths
does not modify files
does not delete files
does not read rawdata
does not return binary content
previews NIfTI files as metadata only

---

## 13. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/artifact_browser_spec.md
backend/app/tools/artifact_browser.py
backend/app/tools/run_artifact_browser_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/ArtifactBrowser.tsx
frontend/src/App.tsx
frontend/src/styles.css
tests/unit/test_artifact_browser.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有一些 artifacts：

python -m backend.app.tools.run_validation_cli
python -m backend.app.tools.run_experiment_dashboard_cli

然后运行：

python -m backend.app.tools.run_artifact_browser_cli

应生成：

work/artifacts/artifact_index.json

运行 preview：

python -m backend.app.tools.run_artifact_browser_cli --preview work/artifacts/artifact_index.json

应返回：

{
  "ok": true,
  "preview": {
    "preview_type": "text"
  }
}

运行测试：

python -m pytest tests/unit/test_artifact_browser.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/artifacts
curl -X POST http://127.0.0.1:8000/api/artifacts/refresh
curl -X POST http://127.0.0.1:8000/api/artifacts/preview \
  -H "Content-Type: application/json" \
  -d '{"path":"outputs/work/artifacts/artifact_index.json"}'

测试路径穿越必须失败：

curl -X POST http://127.0.0.1:8000/api/artifacts/preview \
  -H "Content-Type: application/json" \
  -d '{"path":"../../etc/passwd"}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Run Artifact Browser / File Preview 区域。
点击加载 Artifact Index。
点击刷新 Artifact Index。
显示 artifact 列表。
支持 search。
支持 category filter。
支持 extension filter。
点击 JSON 文件能显示 parsed/text preview。
点击 Markdown / log / CSV 文件能显示文本 preview。
点击 NIfTI 文件只显示 metadata。
不执行任何 pipeline。
不启动 MATLAB。
不运行 DPABI。
不读取 rawdata。
不修改或删除任何文件。
14. 重要限制

本步骤只做 artifact browser 和安全预览。

不要实现：

文件编辑
文件删除
文件上传
任意路径浏览
二进制文件下载
HTML 执行
rawdata 浏览
自动运行 pipeline
MATLAB 启动
DPABI 执行
生产级文件权限系统

完成后请总结：

新增了哪些文件
修改了哪些文件
artifact index 扫描哪些目录
artifact preview 支持哪些类型
为什么 NIfTI 只预览 metadata
前端如何浏览和过滤 artifact
下一步如何做 project packaging / reproducibility bundle

'''
Step 30 主要实现的是：

## Run Artifact Browser + File Preview 闭环
### 核心目标
当前系统已经产生了大量 artifact 文件（pipeline runs、reports、logs、experiments 等），但前端只能通过各个面板零散查看结果，缺少一个 统一的 artifact 浏览器 。本步骤要实现一个安全的、可过滤的、支持预览的 artifact 浏览器。

### 主要功能
1. Artifact 索引生成
   
   - 扫描允许的目录：work/、reports/、logs/、derivatives/、examples/
   - 生成 work/artifacts/artifact_index.json
   - 按 category 分类 artifact
   - 排除敏感路径（rawdata/、third_party/、.git/ 等）
2. Artifact 分类
   
   - pipeline_run - Pipeline 运行输出
   - report - 生成的报告
   - log - 日志文件
   - dpabi - DPABI 相关文件
   - experiment - 实验记录
   - derivative - 处理后的数据输出
   - config - 配置文件
   - unknown - 未分类文件
3. 安全文件预览
   
   - 文本文件 - JSON、YAML、Markdown、CSV、TXT、LOG、HTML（纯文本方式，不执行脚本）
   - NIfTI 元数据 - 只预览 shape、dtype、zooms、affine， 不读取 voxel 数据
   - 不支持文件 - 仅返回元数据
   - 大小限制 - 文本预览最大 200KB
4. 前端浏览器
   
   - 按 category / extension / modified time 过滤
   - 按 run_id 搜索
   - 支持安全预览各种文件类型
   - Artifact 列表展示
   - 文件内容预览面板
### 解决的问题
- Pipeline runs、states、DPABI 输出、experiments、reports、logs 等 artifact 分散在不同目录
- 前端只能通过各个独立面板查看，缺乏统一视图
- 需要安全地预览各种文件类型（特别是 NIfTI 医学影像文件）
- 需要防止访问敏感路径（rawdata、第三方代码等）
### 安全规则
- 只读扫描 - 仅读取现有产物，不执行任何操作
- 不执行 Pipeline
- 不启动 MATLAB
- 不运行 DPABI
- 不处理真实医学影像数据
- 不修改 rawdata
- 不修改 DPABI 源码
- 不删除文件
- 不提供任意路径读取 - 只允许访问指定的根目录
- 不把二进制文件内容直接返回给前端
- HTML 以文本方式预览，不执行脚本
### 工作流程
1. Scan - 递归扫描允许的目录
2. Filter - 排除敏感路径和文件类型
3. Index - 构建 artifact 记录（包含元数据）
4. Classify - 按路径模式分类
5. Preview - 安全的文本/NIfTI 元数据预览
6. Browse - 前端过滤和查看
### API 端点
```
GET  /api/artifacts          - 获取 artifact 索引
POST /api/artifacts/refresh  - 刷新 artifact 索引
POST /api/artifacts/preview  - 预览 artifact 文件
```
### 输出文件
```
work/artifacts/
└── artifact_index.json       # Artifact 索引（包含所有 artifact 的
元数据）
```
'''