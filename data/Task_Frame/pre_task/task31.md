你是我的工程搭建助手。前第三十步已经完成：

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
Step 30：完成 Run Artifact Browser + File Preview 闭环。

现在开始第三十一步。

第三十一步目标：实现“Project Packaging + Reproducibility Bundle 闭环”。

当前系统已经能产生大量可追踪结果：

- pipeline summaries
- dataset evaluation reports
- DPABI capability / preflight / run plan / wrapper validation / template library
- template instances
- experiment tracking
- experiment dashboard
- artifact index
- logs
- reports
- specs
- examples pipeline YAML
- project config YAML

但当前还缺少一个“可复现交付包”能力：

- 可以把当前项目状态打成 bundle
- 可以记录环境信息
- 可以记录 Git / Python / Node / MATLAB / SPM / DPABI 信息
- 可以记录关键配置文件 hash
- 可以记录 artifact manifest
- 可以排除大型二进制文件和 rawdata
- 可以生成 reproducibility README
- 可以生成 bundle zip
- 可以通过 API / 前端创建和查看 bundle

本步骤要实现：

- packaging spec
- reproducibility manifest
- environment snapshot
- artifact manifest
- bundle README
- bundle ZIP
- hash 校验
- bundle index
- 后端 API 暴露 bundle list / create / inspect
- 前端新增 Project Packaging / Reproducibility Bundle 面板
- validation suite 增加 packaging 轻量测试

本步骤只做读取、复制和压缩。
本步骤不要执行新的 pipeline。
本步骤不要启动 MATLAB。
本步骤不要运行 DPABI。
本步骤不要运行 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。
本步骤不要把 third_party / rawdata / node_modules / .git 打包进去。
本步骤不要把大型 NIfTI 数据默认打包进去。

---

## 1. 创建 specs/reproducibility_bundle_spec.md

创建文件：

```text
specs/reproducibility_bundle_spec.md

内容：

# Reproducibility Bundle Specification

This document defines the MVP project packaging and reproducibility bundle system.

## Goals

The reproducibility bundle should capture enough project state for review, audit, and reproduction of synthetic pipeline experiments.

It should include:

- project configs
- example pipelines
- specs
- selected reports
- selected logs
- experiment indexes
- artifact index
- DPABI wrapper metadata
- template library metadata
- environment snapshot
- file hashes
- reproducibility README

## Scope

Supported in this step:

- create reproducibility manifest
- create environment snapshot
- create artifact manifest
- copy selected text artifacts
- copy selected reports
- copy selected configs
- generate README
- generate ZIP bundle
- list bundles
- inspect bundle manifest
- API and frontend visibility
- lightweight unit test

Unsupported in this step:

- executing pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- packaging rawdata
- packaging third_party toolboxes
- packaging node_modules
- packaging .git
- packaging large binary data by default
- deleting files

## Outputs

```text
work/bundles/{bundle_id}/manifest.json
work/bundles/{bundle_id}/environment_snapshot.json
work/bundles/{bundle_id}/artifact_manifest.json
work/bundles/{bundle_id}/README.md
work/bundles/{bundle_id}/bundle.zip
work/bundles/bundle_index.json
reports/bundles/{bundle_id}_bundle_report.md
Included Paths

Default included paths:

specs/
examples/*.yaml
examples/*.json
README.md
work/experiments/
work/artifacts/artifact_index.json
work/dpabi/*.json
work/dpabi/*.yaml
work/dpabi/templates/
reports/
logs/*.log
Excluded Paths

Always excluded:

third_party/
.git/
node_modules/
frontend/node_modules/
__pycache__/
rawdata/
derivatives/
*.nii
*.nii.gz
*.mat
*.zip
Safety Rules
Do not execute pipelines.
Do not launch MATLAB.
Do not run DPABI.
Do not modify rawdata.
Do not modify DPABI source.
Do not delete files.
Do not package third_party source code.
Do not package rawdata by default.
Do not package large binary outputs by default.

---

## 2. 创建 backend/app/tools/reproducibility_bundle.py

创建文件：

```text
backend/app/tools/reproducibility_bundle.py

目标：创建 reproducibility bundle。

提供函数：

create_reproducibility_bundle(
    bundle_id: str | None = None,
    work_dir: str = "./work",
    report_dir: str = "./reports",
    include_logs: bool = True,
    include_reports: bool = True,
    include_artifact_index: bool = True,
    max_file_size_bytes: int = 2_000_000,
) -> dict

list_reproducibility_bundles(
    work_dir: str = "./work",
) -> dict

inspect_reproducibility_bundle(
    bundle_id: str,
    work_dir: str = "./work",
) -> dict

实现要求：

bundle_id 默认自动生成：
bundle_YYYYMMDD_HHMMSS
只允许安全 bundle_id：
不能包含 /
不能包含 \
不能包含 ..
创建目录：
work/bundles/{bundle_id}/
生成：
manifest.json
environment_snapshot.json
artifact_manifest.json
README.md
bundle.zip
更新：
work/bundles/bundle_index.json
复制文件时保留相对路径。
必须排除：
third_party
.git
node_modules
frontend/node_modules
pycache
rawdata
derivatives
.nii
.nii.gz
.mat
.zip
超过 max_file_size_bytes 的文件不复制，只记录 skipped。
记录 sha256。
环境 snapshot 至少记录：
python version
platform
cwd
pip freeze 前 200 行
node version，如果可用
npm version，如果可用
git commit，如果可用
git status short，如果可用
不调用 MATLAB。
不执行 pipeline。
不删除文件。

参考实现：

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCLUDED_PARTS = {
    "third_party",
    ".git",
    "node_modules",
    "__pycache__",
    "rawdata",
    "derivatives",
}

EXCLUDED_SUFFIXES = {
    ".nii",
    ".gz",
    ".mat",
    ".zip",
}

ALLOWED_ROOTS = [
    "specs",
    "examples",
    "outputs/work/experiments",
    "outputs/work/artifacts",
    "outputs/work/dpabi",
    "reports",
    "logs",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bundle_id_now() -> str:
    return "bundle_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_id(value: str) -> bool:
    return bool(value) and "/" not in value and "\\" not in value and ".." not in value


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_cmd(cmd: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout[:20_000],
            "stderr": completed.stderr[:20_000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def _environment_snapshot() -> dict[str, Any]:
    pip_freeze = _run_cmd([sys.executable, "-m", "pip", "freeze"])
    node_version = _run_cmd(["node", "--version"])
    npm_version = _run_cmd(["npm", "--version"])
    git_commit = _run_cmd(["git", "rev-parse", "HEAD"])
    git_status = _run_cmd(["git", "status", "--short"])

    pip_lines = pip_freeze.get("stdout", "").splitlines()[:200]

    return {
        "generated_at": _now_iso(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "platform": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cwd": str(Path.cwd()),
        "pip_freeze_head": pip_lines,
        "node_version": node_version,
        "npm_version": npm_version,
        "git_commit": git_commit,
        "git_status_short": git_status,
        "note": "MATLAB, SPM, and DPABI are not executed during bundle creation.",
    }


def _is_excluded(path: Path) -> bool:
    parts = set(path.parts)

    if any(part in EXCLUDED_PARTS for part in parts):
        return True

    name = path.name.lower()
    if name.endswith(".nii") or name.endswith(".nii.gz"):
        return True

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True

    return False


def _candidate_files() -> list[Path]:
    candidates: list[Path] = []

    for root_text in ALLOWED_ROOTS:
        root = Path(root_text)
        if not root.exists():
            continue

        if root.is_file():
            candidates.append(root)
            continue

        for path in root.rglob("*"):
            if path.is_file():
                candidates.append(path)

    for root_file in [Path("README.md"), Path("pyproject.toml"), Path("package.json")]:
        if root_file.exists():
            candidates.append(root_file)

    return sorted(set(candidates))


def _copy_artifacts(
    bundle_dir: Path,
    max_file_size_bytes: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    copied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    files_dir = bundle_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    for src in _candidate_files():
        if _is_excluded(src):
            skipped.append({
                "path": str(src),
                "reason": "excluded_path_or_suffix",
            })
            continue

        try:
            size = src.stat().st_size
        except Exception as exc:
            skipped.append({
                "path": str(src),
                "reason": f"stat_failed: {exc}",
            })
            continue

        if size > max_file_size_bytes:
            skipped.append({
                "path": str(src),
                "size_bytes": size,
                "reason": "file_too_large",
            })
            continue

        dst = files_dir / src
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        copied.append({
            "source_path": str(src),
            "bundle_path": str(dst.relative_to(bundle_dir)),
            "size_bytes": size,
            "sha256": _sha256(src),
        })

    return copied, skipped


def _write_bundle_index(work_dir: str, item: dict[str, Any]) -> None:
    root = Path(work_dir) / "bundles"
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "bundle_index.json"

    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            index = {"bundles": []}
    else:
        index = {"bundles": []}

    bundles = [
        existing for existing in index.get("bundles", [])
        if existing.get("bundle_id") != item.get("bundle_id")
    ]
    bundles.append(item)
    bundles = sorted(bundles, key=lambda x: x.get("created_at", ""), reverse=True)

    index = {
        "ok": True,
        "updated_at": _now_iso(),
        "bundles_total": len(bundles),
        "bundles": bundles,
    }

    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_reproducibility_bundle(
    bundle_id: str | None = None,
    work_dir: str = "./work",
    report_dir: str = "./reports",
    include_logs: bool = True,
    include_reports: bool = True,
    include_artifact_index: bool = True,
    max_file_size_bytes: int = 2_000_000,
) -> dict[str, Any]:
    bundle_id = bundle_id or _bundle_id_now()

    if not _safe_id(bundle_id):
        return {
            "ok": False,
            "errors": ["Invalid bundle_id."],
            "warnings": [],
        }

    bundle_root = Path(work_dir) / "bundles"
    bundle_dir = bundle_root / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    report_out = Path(report_dir) / "bundles"
    report_out.mkdir(parents=True, exist_ok=True)

    environment = _environment_snapshot()
    copied, skipped = _copy_artifacts(
        bundle_dir=bundle_dir,
        max_file_size_bytes=max_file_size_bytes,
    )

    artifact_manifest = {
        "bundle_id": bundle_id,
        "copied_total": len(copied),
        "skipped_total": len(skipped),
        "copied": copied,
        "skipped": skipped,
    }

    manifest = {
        "ok": True,
        "bundle_id": bundle_id,
        "created_at": _now_iso(),
        "bundle_dir": str(bundle_dir),
        "include_logs": include_logs,
        "include_reports": include_reports,
        "include_artifact_index": include_artifact_index,
        "max_file_size_bytes": max_file_size_bytes,
        "files_copied": len(copied),
        "files_skipped": len(skipped),
        "safety": {
            "pipelines_executed": False,
            "matlab_launched": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dpabi_gui_called": False,
            "rawdata_packaged": False,
            "third_party_packaged": False,
            "rawdata_modified": False,
            "files_deleted": False,
        },
        "outputs": [],
        "warnings": [],
        "errors": [],
    }

    environment_path = bundle_dir / "environment_snapshot.json"
    artifact_manifest_path = bundle_dir / "artifact_manifest.json"
    manifest_path = bundle_dir / "manifest.json"
    readme_path = bundle_dir / "README.md"
    zip_path = bundle_dir / "bundle.zip"
    report_path = report_out / f"{bundle_id}_bundle_report.md"

    environment_path.write_text(
        json.dumps(environment, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    artifact_manifest_path.write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    readme_lines = []
    readme_lines.append(f"# Reproducibility Bundle: {bundle_id}")
    readme_lines.append("")
    readme_lines.append("This bundle captures selected project artifacts for review and reproducibility.")
    readme_lines.append("")
    readme_lines.append("## Contents")
    readme_lines.append("")
    readme_lines.append("- manifest.json")
    readme_lines.append("- environment_snapshot.json")
    readme_lines.append("- artifact_manifest.json")
    readme_lines.append("- files/")
    readme_lines.append("")
    readme_lines.append("## Safety")
    readme_lines.append("")
    readme_lines.append("- Pipelines executed during packaging: false")
    readme_lines.append("- MATLAB launched during packaging: false")
    readme_lines.append("- DPABI executed during packaging: false")
    readme_lines.append("- Rawdata packaged: false")
    readme_lines.append("- Third-party toolboxes packaged: false")
    readme_lines.append("")
    readme_lines.append("## Notes")
    readme_lines.append("")
    readme_lines.append("Large binary files, rawdata, third_party toolboxes, node_modules, .git, and derivatives are excluded by default.")

    readme_path.write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    manifest["outputs"] = [
        str(manifest_path),
        str(environment_path),
        str(artifact_manifest_path),
        str(readme_path),
        str(zip_path),
        str(report_path),
    ]

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in bundle_dir.rglob("*"):
            if path == zip_path:
                continue
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(bundle_dir)))

    zip_sha = _sha256(zip_path)
    manifest["zip_sha256"] = zip_sha
    manifest["zip_size_bytes"] = zip_path.stat().st_size

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report_lines = []
    report_lines.append(f"# Reproducibility Bundle Report: {bundle_id}")
    report_lines.append("")
    report_lines.append(f"- Bundle directory: `{bundle_dir}`")
    report_lines.append(f"- Zip: `{zip_path}`")
    report_lines.append(f"- Zip SHA256: `{zip_sha}`")
    report_lines.append(f"- Files copied: {len(copied)}")
    report_lines.append(f"- Files skipped: {len(skipped)}")
    report_lines.append("")
    report_lines.append("## Safety")
    report_lines.append("")
    for key, value in manifest["safety"].items():
        report_lines.append(f"- {key}: {value}")
    report_lines.append("")
    report_lines.append("## Skipped Files")
    report_lines.append("")
    for item in skipped[:100]:
        report_lines.append(f"- `{item.get('path')}`: {item.get('reason')}")
    if len(skipped) > 100:
        report_lines.append(f"- ... {len(skipped) - 100} more")

    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    index_item = {
        "bundle_id": bundle_id,
        "created_at": manifest["created_at"],
        "bundle_dir": str(bundle_dir),
        "zip_path": str(zip_path),
        "zip_sha256": zip_sha,
        "zip_size_bytes": manifest["zip_size_bytes"],
        "files_copied": len(copied),
        "files_skipped": len(skipped),
        "manifest_path": str(manifest_path),
    }

    _write_bundle_index(work_dir, index_item)

    return manifest


def list_reproducibility_bundles(
    work_dir: str = "./work",
) -> dict[str, Any]:
    index_path = Path(work_dir) / "bundles" / "bundle_index.json"

    if not index_path.exists():
        return {
            "ok": True,
            "bundles_total": 0,
            "bundles": [],
            "warnings": [],
            "errors": [],
        }

    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "bundles_total": 0,
            "bundles": [],
            "warnings": [],
            "errors": [str(exc)],
        }


def inspect_reproducibility_bundle(
    bundle_id: str,
    work_dir: str = "./work",
) -> dict[str, Any]:
    if not _safe_id(bundle_id):
        return {
            "ok": False,
            "errors": ["Invalid bundle_id."],
            "warnings": [],
        }

    bundle_dir = Path(work_dir) / "bundles" / bundle_id
    manifest_path = bundle_dir / "manifest.json"
    environment_path = bundle_dir / "environment_snapshot.json"
    artifact_manifest_path = bundle_dir / "artifact_manifest.json"
    readme_path = bundle_dir / "README.md"

    if not manifest_path.exists():
        return {
            "ok": False,
            "errors": [f"Bundle manifest not found: {manifest_path}"],
            "warnings": [],
        }

    def read_json(path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    return {
        "ok": True,
        "bundle_id": bundle_id,
        "manifest": read_json(manifest_path),
        "environment_snapshot": read_json(environment_path),
        "artifact_manifest": read_json(artifact_manifest_path),
        "readme": readme_path.read_text(encoding="utf-8") if readme_path.exists() else None,
        "warnings": [],
        "errors": [],
    }
3. 创建 backend/app/tools/run_reproducibility_bundle_cli.py

创建文件：

backend/app/tools/run_reproducibility_bundle_cli.py

内容：

from __future__ import annotations

import json
import sys

from backend.app.tools.reproducibility_bundle import (
    create_reproducibility_bundle,
    inspect_reproducibility_bundle,
    list_reproducibility_bundles,
)


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--list":
        result = list_reproducibility_bundles()
    elif args and args[0] == "--inspect":
        if len(args) < 2:
            result = {"ok": False, "errors": ["Missing bundle_id after --inspect"]}
        else:
            result = inspect_reproducibility_bundle(args[1])
    else:
        bundle_id = args[0] if args else None
        result = create_reproducibility_bundle(bundle_id=bundle_id)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
4. 修改 backend/app/api/models.py

新增 request model：

class ReproducibilityBundleCreateRequest(BaseModel):
    bundle_id: str | None = Field(default=None)
    include_logs: bool = Field(default=True)
    include_reports: bool = Field(default=True)
    include_artifact_index: bool = Field(default=True)
    max_file_size_bytes: int = Field(default=2_000_000)


class ReproducibilityBundleInspectRequest(BaseModel):
    bundle_id: str = Field(default="")
5. 修改 backend/app/api/routes.py

新增 API：

GET  /api/bundles
POST /api/bundles/create
POST /api/bundles/inspect

新增导入：

from backend.app.api.models import (
    ReproducibilityBundleCreateRequest,
    ReproducibilityBundleInspectRequest,
)
from backend.app.tools.reproducibility_bundle import (
    create_reproducibility_bundle,
    inspect_reproducibility_bundle,
    list_reproducibility_bundles,
)

新增路由：

@router.get("/api/bundles")
def api_list_reproducibility_bundles() -> dict[str, Any]:
    return list_reproducibility_bundles(work_dir="./work")


@router.post("/api/bundles/create")
def api_create_reproducibility_bundle(
    request: ReproducibilityBundleCreateRequest,
) -> dict[str, Any]:
    result = create_reproducibility_bundle(
        bundle_id=request.bundle_id,
        work_dir="./work",
        report_dir="./reports",
        include_logs=request.include_logs,
        include_reports=request.include_reports,
        include_artifact_index=request.include_artifact_index,
        max_file_size_bytes=request.max_file_size_bytes,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/api/bundles/inspect")
def api_inspect_reproducibility_bundle(
    request: ReproducibilityBundleInspectRequest,
) -> dict[str, Any]:
    result = inspect_reproducibility_bundle(
        bundle_id=request.bundle_id,
        work_dir="./work",
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result
6. 修改 frontend/src/api.ts

新增：

export async function listBundles(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/bundles");
}

export async function createBundle(
  baseUrl: string,
  payload: {
    bundle_id?: string | null;
    include_logs: boolean;
    include_reports: boolean;
    include_artifact_index: boolean;
    max_file_size_bytes: number;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/bundles/create",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function inspectBundle(
  baseUrl: string,
  bundle_id: string
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/bundles/inspect",
    {
      method: "POST",
      body: JSON.stringify({ bundle_id })
    }
  );
}
7. 创建 frontend/src/components/ReproducibilityBundlePanel.tsx

创建文件：

frontend/src/components/ReproducibilityBundlePanel.tsx

内容：

import { useState } from "react";
import {
  createBundle,
  inspectBundle,
  listBundles
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function ReproducibilityBundlePanel({ baseUrl }: Props) {
  const [bundleId, setBundleId] = useState("");
  const [maxFileSize, setMaxFileSize] = useState(2_000_000);
  const [bundleList, setBundleList] = useState<Record<string, unknown> | null>(null);
  const [created, setCreated] = useState<Record<string, unknown> | null>(null);
  const [inspected, setInspected] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleList() {
    setStatus("LOADING");
    setError("");

    try {
      const result = await listBundles(baseUrl);
      setBundleList(result);
      setStatus("LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleCreate() {
    const confirmed = window.confirm(
      "确认创建 reproducibility bundle？这只会复制和压缩允许的配置、报告和文本 artifact，不会运行 pipeline。"
    );

    if (!confirmed) return;

    setStatus("CREATING");
    setError("");

    try {
      const result = await createBundle(baseUrl, {
        bundle_id: bundleId || null,
        include_logs: true,
        include_reports: true,
        include_artifact_index: true,
        max_file_size_bytes: maxFileSize
      });
      setCreated(result);
      setStatus("CREATED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleInspect() {
    if (!bundleId) {
      setError("请输入 bundle_id");
      return;
    }

    setStatus("INSPECTING");
    setError("");

    try {
      const result = await inspectBundle(baseUrl, bundleId);
      setInspected(result);
      setStatus("INSPECTED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  return (
    <div>
      <div className="row">
        <button onClick={handleList}>加载 Bundle Index</button>
        <button className="dangerButton" onClick={handleCreate}>创建 Bundle</button>
        <button onClick={handleInspect}>Inspect Bundle</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="formGrid">
        <label>
          Bundle ID
          <input
            value={bundleId}
            placeholder="留空自动生成"
            onChange={(event) => setBundleId(event.target.value)}
          />
        </label>

        <label>
          Max File Size Bytes
          <input
            type="number"
            value={maxFileSize}
            onChange={(event) => setMaxFileSize(Number(event.target.value))}
          />
        </label>
      </div>

      <h3>Bundle Index</h3>
      <JsonBlock value={bundleList} emptyText="尚未加载 bundle index" />

      <h3>Created Bundle</h3>
      <JsonBlock value={created} emptyText="尚未创建 bundle" />

      <h3>Inspected Bundle</h3>
      <JsonBlock value={inspected?.manifest} emptyText="尚未 inspect bundle" />

      <h3>Environment Snapshot</h3>
      <JsonBlock value={inspected?.environment_snapshot} emptyText="暂无 environment snapshot" />

      <h3>Artifact Manifest</h3>
      <JsonBlock value={inspected?.artifact_manifest} emptyText="暂无 artifact manifest" />

      <h3>Bundle README</h3>
      <TextViewer
        text={
          typeof inspected?.readme === "string"
            ? inspected.readme
            : null
        }
        emptyText="暂无 README"
      />
    </div>
  );
}
8. 修改 frontend/src/App.tsx

新增导入：

import { ReproducibilityBundlePanel } from "./components/ReproducibilityBundlePanel";

在 Artifact Browser 后增加 Section：

<Section
  title="Project Packaging / Reproducibility Bundle"
  description="创建可复现交付包，包含配置、报告、实验索引、环境快照和文件 hash。"
>
  <ReproducibilityBundlePanel baseUrl={baseUrl} />
</Section>
9. 新增轻量测试

创建文件：

tests/unit/test_reproducibility_bundle.py

内容：

from __future__ import annotations

import json
from pathlib import Path

from backend.app.tools.reproducibility_bundle import (
    create_reproducibility_bundle,
    inspect_reproducibility_bundle,
    list_reproducibility_bundles,
)


def test_reproducibility_bundle_excludes_rawdata_and_creates_zip(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    specs = tmp_path / "specs"
    examples = tmp_path / "examples"
    work = tmp_path / "work"
    reports = tmp_path / "reports"
    logs = tmp_path / "logs"

    specs.mkdir()
    examples.mkdir()
    work.mkdir()
    reports.mkdir()
    logs.mkdir()

    (specs / "test_spec.md").write_text("# Spec\n", encoding="utf-8")
    (examples / "pipeline_test.yaml").write_text("pipeline_id: test\n", encoding="utf-8")
    (reports / "report.md").write_text("# Report\n", encoding="utf-8")
    (logs / "run.log").write_text("log\n", encoding="utf-8")

    rawdata = examples / "synthetic_bids" / "rawdata"
    rawdata.mkdir(parents=True)
    (rawdata / "secret_rawdata.json").write_text("{}", encoding="utf-8")

    result = create_reproducibility_bundle(
        bundle_id="bundle_test",
        work_dir="./work",
        report_dir="./reports",
    )

    assert result["ok"] is True

    manifest_path = work / "bundles" / "bundle_test" / "manifest.json"
    artifact_manifest_path = work / "bundles" / "bundle_test" / "artifact_manifest.json"
    zip_path = work / "bundles" / "bundle_test" / "bundle.zip"

    assert manifest_path.exists()
    assert artifact_manifest_path.exists()
    assert zip_path.exists()

    artifact_manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))
    copied_paths = [item["source_path"] for item in artifact_manifest["copied"]]

    assert not any("rawdata" in path for path in copied_paths)

    listing = list_reproducibility_bundles(work_dir="./work")
    assert listing["bundles_total"] == 1

    inspected = inspect_reproducibility_bundle("bundle_test", work_dir="./work")
    assert inspected["ok"] is True
    assert inspected["manifest"]["bundle_id"] == "bundle_test"
10. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/bundles")

不要在 smoke test 中自动创建 bundle，避免写入 zip。

11. 更新 README.md

追加第三十一步说明：

## Step 31: Project Packaging and Reproducibility Bundle

This step adds reproducibility bundle creation.

It supports:

- environment snapshot
- artifact manifest
- file hashes
- reproducibility README
- bundle ZIP
- bundle index
- API and frontend visibility

It does not execute pipelines.

### Create Bundle

```bash
python -m backend.app.tools.run_reproducibility_bundle_cli

Expected outputs:

work/bundles/{bundle_id}/manifest.json
work/bundles/{bundle_id}/environment_snapshot.json
work/bundles/{bundle_id}/artifact_manifest.json
work/bundles/{bundle_id}/README.md
work/bundles/{bundle_id}/bundle.zip
work/bundles/bundle_index.json
reports/bundles/{bundle_id}_bundle_report.md
List Bundles
python -m backend.app.tools.run_reproducibility_bundle_cli --list
Inspect Bundle
python -m backend.app.tools.run_reproducibility_bundle_cli --inspect bundle_test
API
curl http://127.0.0.1:8000/api/bundles

Create:

curl -X POST http://127.0.0.1:8000/api/bundles/create \
  -H "Content-Type: application/json" \
  -d '{
    "bundle_id": "bundle_test",
    "include_logs": true,
    "include_reports": true,
    "include_artifact_index": true,
    "max_file_size_bytes": 2000000
  }'

Inspect:

curl -X POST http://127.0.0.1:8000/api/bundles/inspect \
  -H "Content-Type: application/json" \
  -d '{"bundle_id": "bundle_test"}'
Frontend

Use:

Project Packaging / Reproducibility Bundle
Safety

Bundle creation:

does not execute pipelines
does not launch MATLAB
does not run DPABI
does not package rawdata
does not package third_party
does not package node_modules
does not modify rawdata
does not delete files

---

## 12. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/reproducibility_bundle_spec.md
backend/app/tools/reproducibility_bundle.py
backend/app/tools/run_reproducibility_bundle_cli.py
backend/app/api/models.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/ReproducibilityBundlePanel.tsx
frontend/src/App.tsx
tests/unit/test_reproducibility_bundle.py
backend/app/tools/api_smoke_test.py
README.md

先确保已有 artifact index：

python -m backend.app.tools.run_artifact_browser_cli

然后运行：

python -m backend.app.tools.run_reproducibility_bundle_cli bundle_test

应生成：

work/bundles/bundle_test/manifest.json
work/bundles/bundle_test/environment_snapshot.json
work/bundles/bundle_test/artifact_manifest.json
work/bundles/bundle_test/README.md
work/bundles/bundle_test/bundle.zip
work/bundles/bundle_index.json
reports/bundles/bundle_test_bundle_report.md

manifest 必须包含：

{
  "safety": {
    "pipelines_executed": false,
    "matlab_launched": false,
    "dpabi_executed": false,
    "dparsf_run_executed": false,
    "dpabi_gui_called": false,
    "rawdata_packaged": false,
    "third_party_packaged": false,
    "rawdata_modified": false,
    "files_deleted": false
  }
}

运行测试：

python -m pytest tests/unit/test_reproducibility_bundle.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/bundles

curl -X POST http://127.0.0.1:8000/api/bundles/create \
  -H "Content-Type: application/json" \
  -d '{"bundle_id":"bundle_test","include_logs":true,"include_reports":true,"include_artifact_index":true,"max_file_size_bytes":2000000}'

curl -X POST http://127.0.0.1:8000/api/bundles/inspect \
  -H "Content-Type: application/json" \
  -d '{"bundle_id":"bundle_test"}'

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Project Packaging / Reproducibility Bundle 区域。
可以加载 Bundle Index。
可以创建 bundle。
可以 inspect bundle。
显示 manifest。
显示 environment snapshot。
显示 artifact manifest。
显示 bundle README。
不执行任何 pipeline。
不启动 MATLAB。
不运行 DPABI。
不打包 rawdata。
不打包 third_party。
不修改或删除任何文件。
13. 重要限制

本步骤只做 project packaging 和 reproducibility bundle。

不要实现：

bundle 下载 API
任意文件打包
rawdata 打包
third_party 打包
大型二进制打包
自动运行 pipeline
MATLAB 启动
DPABI 执行
DPARSF_run 自动执行
DPARSFA_run 自动执行
文件删除
云端上传

完成后请总结：

新增了哪些文件
修改了哪些文件
bundle 包含哪些内容
bundle 排除了哪些内容
environment snapshot 记录哪些信息
artifact manifest 如何用于复现
下一步如何做 release checklist / deployment readiness

'''
Step 31 主要实现的是：

## Project Packaging + Reproducibility Bundle 闭环
### 核心目标
当前系统已经能产生大量可追踪的结果（pipeline summaries、reports、experiment tracking、artifact index 等），但缺少一个**"可复现交付包"**能力。本步骤要实现一个打包系统，可以把当前项目状态打成 bundle，用于审查、审计和复现实验。

### 主要功能
1. Bundle 创建
   
   - 扫描允许目录下的 artifact（specs/、examples/、work/experiments/ 等）
   - 复制文件并记录 SHA256 哈希
   - 生成环境快照（Python/Node/Git/平台信息）
   - 创建 ZIP 压缩包
   - 生成可复现性 README
2. 环境快照 (Environment Snapshot)
   
   - Python 版本和可执行文件路径
   - 平台信息（操作系统、架构）
   - 当前工作目录
   - pip freeze 前 200 个包
   - Node/npm 版本（如果可用）
   - Git commit 和 status（如果可用）
3. 安全记录
   
   - 记录打包过程中没有执行 pipeline
   - 记录没有启动 MATLAB
   - 记录没有运行 DPABI
   - 记录没有打包 rawdata
   - 记录没有打包第三方代码
4. Bundle 管理
   
   - 列出所有 bundles
   - 查看 bundle 详情
   - Bundle 索引维护
### 解决的问题
- 实验结果难以分享和复现
- 缺少环境信息记录
- 无法追踪项目状态变化
- 没有标准化的交付格式
### 安全规则
- 只读复制 - 仅复制文件，不修改或删除
- 不执行 Pipeline
- 不启动 MATLAB
- 不运行 DPABI
- 不处理真实医学影像数据
- 不修改 rawdata
- 不修改 DPABI 源码
- 不删除文件
- 不打包 third_party / rawdata / node_modules / .git
- 不打包大型 NIfTI 数据 （默认排除）
### 包含路径
```
specs/
examples/*.yaml
examples/*.json
README.md
work/experiments/
work/artifacts/artifact_index.json
work/dpabi/*.json
work/dpabi/*.yaml
work/dpabi/templates/
reports/
logs/*.log
```
### 排除路径
```
third_party/
.git/
node_modules/
__pycache__/
rawdata/
derivatives/
*.nii
*.nii.gz
*.mat
*.zip
```
### 输出文件
```
work/bundles/{bundle_id}/
├── manifest.json              # Bundle 元数据
├── environment_snapshot.json  # 环境信息
├── artifact_manifest.json     # 文件清单和 SHA256 哈希
├── README.md                  # 可复现性说明
└── bundle.zip                 # ZIP 压缩包

work/bundles/bundle_index.json          # Bundle 索引
reports/bundles/{bundle_id}_bundle_report.md  # Markdown 报告
```
### API 端点
```
GET  /api/bundles              - 列出所有 bundles
POST /api/bundles/create       - 创建新 bundle
GET  /api/bundles/{bundle_id}  - 查看 bundle 详情
```
### 工作流程
1. Scan - 从允许的路径收集候选文件
2. Filter - 排除敏感路径和大型二进制文件
3. Copy - 复制文件到 bundle 目录，计算 SHA256
4. Snapshot - 记录环境信息
5. Generate - 创建 manifest、README 和 ZIP
6. Index - 更新 bundle 索引
7. Report - 生成 Markdown 报告
### 使用场景
- 实验分享 - 打包实验配置和结果
- 可复现性 - 捕获精确环境用于复现
- 审计追踪 - 记录运行内容和时间
- 备份 - 创建重要项目状态的快照
- 论文发表 - 打包论文提交材料
'''