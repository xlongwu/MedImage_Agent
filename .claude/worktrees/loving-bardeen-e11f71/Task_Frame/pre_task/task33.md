你是我的工程搭建助手。前三十二步已经完成：

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
Step 32：完成 Release Checklist + Deployment Readiness 闭环。

现在开始第三十三步。

第三十三步目标：实现 “Docker / Local Deployment Profile + Health Check 闭环”。

当前系统已经可以做 release readiness scan，但还缺少一个部署配置层，用来回答：

- 本地开发模式如何启动？
- Docker demo 模式如何启动？
- 后端、前端、work/reports/logs/examples 挂载是否合理？
- MATLAB / SPM / DPABI 是否作为外部依赖声明？
- Docker demo 是否默认禁用 MATLAB / DPABI 执行？
- API health check 是否可用？
- 前端 health check 是否可视化？
- 部署 profile 是否明确禁止 rawdata / third_party 打包或暴露？
- 当前项目是否能进入本地演示或 Docker demo 阶段？

本步骤要实现：

- deployment profile spec
- `.env.example`
- local deployment profile YAML
- Docker demo compose 文件
- backend Dockerfile
- frontend Dockerfile
- nginx config
- deployment profile scanner
- health check API
- deployment report
- 前端 Deployment / Health Panel
- validation suite 增加 deployment profile 轻量测试

本步骤只做部署配置、静态检查和 health check。
本步骤不要执行新的 pipeline。
本步骤不要启动 MATLAB。
本步骤不要运行 DPABI。
本步骤不要运行 DPARSF_run / DPARSFA_run。
本步骤不要调用 DPABI GUI。
本步骤不要处理真实医学影像数据。
本步骤不要修改 rawdata。
本步骤不要修改 DPABI 源码。
本步骤不要删除文件。
本步骤不要真正执行 docker build。
本步骤不要自动部署到云端。

---

## 1. 创建 specs/deployment_profile_spec.md

创建文件：

```text
specs/deployment_profile_spec.md

内容：

# Deployment Profile Specification

This document defines the MVP local and Docker demo deployment profiles for MedImage Agent.

## Goals

Deployment profiles should make the project easier to run, demo, and audit.

They should provide:

- local development profile
- Docker demo profile
- environment variable template
- backend service definition
- frontend service definition
- volume policy
- health check API
- deployment readiness report
- explicit MATLAB / SPM / DPABI external dependency notes

## Scope

Supported in this step:

- local profile YAML
- Docker demo compose YAML
- backend Dockerfile
- frontend Dockerfile
- nginx config
- .env.example
- deployment profile scanner
- API health endpoint
- frontend deployment panel
- lightweight unit test

Unsupported in this step:

- automatic Docker build
- automatic Docker deployment
- cloud deployment
- production authentication
- HTTPS certificate automation
- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- real medical image processing

## Deployment Modes

### local_dev

- backend runs with uvicorn
- frontend runs with npm run dev
- MATLAB/SPM/DPABI may be available locally
- full execution still requires approval gates

### docker_demo

- backend and frontend run in containers
- MATLAB is disabled by default
- DPABI execution is disabled by default
- only read/report/preview/dashboard functions are expected
- work/reports/logs/examples are mounted
- third_party is not copied into images

## Required Outputs

```text
deploy/local_profile.yaml
deploy/docker-compose.demo.yml
deploy/backend.Dockerfile
deploy/frontend.Dockerfile
deploy/nginx.conf
.env.example
work/deployment/deployment_profile.json
reports/deployment/deployment_profile_report.md
Safety Rules
Do not run Docker automatically.
Do not execute pipelines.
Do not launch MATLAB.
Do not run DPABI.
Do not expose rawdata by default.
Do not copy third_party toolboxes into Docker images.
Do not delete files.
Do not deploy to cloud automatically.

---

## 2. 创建 .env.example

创建文件：

```text
.env.example

内容：

# MedImage Agent environment example

MEDIMAGE_ENV=local_dev

# Backend
MEDIMAGE_BACKEND_HOST=127.0.0.1
MEDIMAGE_BACKEND_PORT=8000
MEDIMAGE_API_BASE_URL=http://127.0.0.1:8000

# Frontend
MEDIMAGE_FRONTEND_HOST=127.0.0.1
MEDIMAGE_FRONTEND_PORT=5173
VITE_API_BASE_URL=http://127.0.0.1:8000

# Runtime directories
MEDIMAGE_WORK_DIR=./work
MEDIMAGE_REPORT_DIR=./reports
MEDIMAGE_LOG_DIR=./logs
MEDIMAGE_DERIVATIVES_DIR=./derivatives

# MATLAB / SPM / DPABI external dependencies
# In docker_demo these should remain disabled unless explicitly configured.
MEDIMAGE_MATLAB_ENABLED=false
MEDIMAGE_MATLAB_COMMAND=matlab
MEDIMAGE_SPM_DIR=./third_party/spm12
MEDIMAGE_DPABI_DIR=./third_party/DPABI_V8.2_240510

# Safety defaults
MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION=false
MEDIMAGE_ALLOW_DPARFS_RUN=false
MEDIMAGE_ALLOW_DPARFSA_RUN=false
MEDIMAGE_ALLOW_RAWDATA_WRITE=false
MEDIMAGE_SYNTHETIC_ONLY=true

注意：变量名里保留 DPARSF 拼写，不要写错。上面如果发现 DPARFS / DPARFSA 拼写错误，请改成：

MEDIMAGE_ALLOW_DPARSF_RUN=false
MEDIMAGE_ALLOW_DPARSFA_RUN=false
3. 创建 deploy/local_profile.yaml

创建目录：

deploy/

创建文件：

deploy/local_profile.yaml

内容：

profile_id: local_dev
version: "0.1.0"
description: "Local development profile for MedImage Agent."

services:
  backend:
    command: "uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
    health_url: "http://127.0.0.1:8000/api/health"
    env_file: ".env"

  frontend:
    command: "cd frontend && npm run dev"
    url: "http://127.0.0.1:5173"

runtime:
  work_dir: "./work"
  report_dir: "./reports"
  log_dir: "./logs"
  derivatives_dir: "./derivatives"

external_dependencies:
  matlab:
    enabled_by_default: false
    command_env: "MEDIMAGE_MATLAB_COMMAND"
    note: "MATLAB is used only when explicitly running approved MATLAB-backed nodes."
  spm:
    bundled: false
    path_env: "MEDIMAGE_SPM_DIR"
  dpabi:
    bundled: false
    path_env: "MEDIMAGE_DPABI_DIR"

safety:
  execute_pipelines_on_startup: false
  launch_matlab_on_startup: false
  full_dpabi_execution_allowed: false
  dparsf_run_allowed: false
  dparsfa_run_allowed: false
  dpabi_gui_allowed: false
  rawdata_write_allowed: false
  synthetic_only_default: true
4. 创建 deploy/backend.Dockerfile

创建文件：

deploy/backend.Dockerfile

内容：

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MEDIMAGE_ENV=docker_demo
ENV MEDIMAGE_MATLAB_ENABLED=false
ENV MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION=false
ENV MEDIMAGE_ALLOW_DPARSF_RUN=false
ENV MEDIMAGE_ALLOW_DPARSFA_RUN=false
ENV MEDIMAGE_ALLOW_RAWDATA_WRITE=false
ENV MEDIMAGE_SYNTHETIC_ONLY=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY specs ./specs
COPY examples ./examples
COPY README.md ./README.md

RUN mkdir -p /app/work /app/reports /app/logs /app/derivatives

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

注意：如果项目没有 requirements.txt，请创建一个最小 requirements.txt，包含当前后端需要的依赖，例如：

fastapi
uvicorn[standard]
pydantic
PyYAML
numpy
nibabel

不要把 third_party/、rawdata/、node_modules/ 复制进 Docker image。

5. 创建 deploy/frontend.Dockerfile

创建文件：

deploy/frontend.Dockerfile

内容：

FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend ./
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ || exit 1
6. 创建 deploy/nginx.conf

创建文件：

deploy/nginx.conf

内容：

server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 10m;

    location / {
        try_files $uri /index.html;
    }

    location /health {
        return 200 "ok\n";
        add_header Content-Type text/plain;
    }
}
7. 创建 deploy/docker-compose.demo.yml

创建文件：

deploy/docker-compose.demo.yml

内容：

services:
  backend:
    build:
      context: ..
      dockerfile: deploy/backend.Dockerfile
    container_name: medimage-agent-backend
    environment:
      MEDIMAGE_ENV: docker_demo
      MEDIMAGE_MATLAB_ENABLED: "false"
      MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION: "false"
      MEDIMAGE_ALLOW_DPARSF_RUN: "false"
      MEDIMAGE_ALLOW_DPARSFA_RUN: "false"
      MEDIMAGE_ALLOW_RAWDATA_WRITE: "false"
      MEDIMAGE_SYNTHETIC_ONLY: "true"
    ports:
      - "8000:8000"
    volumes:
      - ../work:/app/work
      - ../reports:/app/reports
      - ../logs:/app/logs
      - ../derivatives:/app/derivatives
      - ../examples:/app/examples:ro
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  frontend:
    build:
      context: ..
      dockerfile: deploy/frontend.Dockerfile
      args:
        VITE_API_BASE_URL: "http://127.0.0.1:8000"
    container_name: medimage-agent-frontend
    depends_on:
      - backend
    ports:
      - "5173:80"
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1/health"]
      interval: 30s
      timeout: 5s
      retries: 3
8. 创建 backend/app/tools/deployment_profile.py

创建文件：

backend/app/tools/deployment_profile.py

目标：扫描部署配置、生成 deployment profile JSON 和 Markdown report。

提供函数：

build_deployment_profile(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict

输出：

work/deployment/deployment_profile.json
reports/deployment/deployment_profile_report.md

参考实现：

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


REQUIRED_DEPLOYMENT_FILES = [
    ".env.example",
    "deploy/local_profile.yaml",
    "deploy/docker-compose.demo.yml",
    "deploy/backend.Dockerfile",
    "deploy/frontend.Dockerfile",
    "deploy/nginx.conf",
]

FORBIDDEN_COPY_PATTERNS = [
    "COPY third_party",
    "COPY .git",
    "COPY node_modules",
    "COPY frontend/node_modules",
    "COPY examples/synthetic_bids/rawdata",
]


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _run_cmd(cmd: list[str], timeout: int = 5) -> dict[str, Any]:
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
            "stdout": completed.stdout[:5000],
            "stderr": completed.stderr[:5000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def _check_file_exists(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    return {
        "name": path_text,
        "ok": path.exists(),
        "message": "exists" if path.exists() else "missing",
    }


def _check_forbidden_patterns(path_text: str) -> list[dict[str, Any]]:
    path = Path(path_text)
    text = _read_text(path)
    checks = []

    for pattern in FORBIDDEN_COPY_PATTERNS:
        found = pattern in text
        checks.append({
            "name": f"{path_text}:{pattern}",
            "ok": not found,
            "message": "not found" if not found else "forbidden pattern found",
        })

    return checks


def build_deployment_profile(
    work_dir: str = "./work",
    report_dir: str = "./reports",
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    blockers: list[str] = []

    for item in REQUIRED_DEPLOYMENT_FILES:
        check = _check_file_exists(item)
        checks.append(check)
        if not check["ok"]:
            blockers.append(f"Missing deployment file: {item}")

    for dockerfile in ["deploy/backend.Dockerfile", "deploy/frontend.Dockerfile"]:
        if Path(dockerfile).exists():
            checks.extend(_check_forbidden_patterns(dockerfile))

    for check in checks:
        if not check.get("ok") and ":" in check.get("name", ""):
            blockers.append(f"Forbidden deployment pattern: {check.get('name')}")

    docker_version = _run_cmd(["docker", "--version"])
    docker_compose_version = _run_cmd(["docker", "compose", "version"])
    node_version = _run_cmd(["node", "--version"])
    npm_version = _run_cmd(["npm", "--version"])

    if not docker_version.get("ok"):
        warnings.append("Docker CLI not available. Docker demo profile can still be reviewed but not run locally.")

    if not docker_compose_version.get("ok"):
        warnings.append("Docker Compose plugin not available.")

    env_example = _read_text(Path(".env.example"))
    required_env_tokens = [
        "MEDIMAGE_MATLAB_ENABLED=false",
        "MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION=false",
        "MEDIMAGE_ALLOW_DPARSF_RUN=false",
        "MEDIMAGE_ALLOW_DPARSFA_RUN=false",
        "MEDIMAGE_ALLOW_RAWDATA_WRITE=false",
        "MEDIMAGE_SYNTHETIC_ONLY=true",
    ]

    for token in required_env_tokens:
        ok = token in env_example
        checks.append({
            "name": f".env.example:{token}",
            "ok": ok,
            "message": "present" if ok else "missing",
        })
        if not ok:
            blockers.append(f"Missing safety env token: {token}")

    compose_text = _read_text(Path("deploy/docker-compose.demo.yml"))
    compose_required_tokens = [
        "MEDIMAGE_MATLAB_ENABLED: \"false\"",
        "MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION: \"false\"",
        "MEDIMAGE_ALLOW_DPARSF_RUN: \"false\"",
        "MEDIMAGE_ALLOW_DPARSFA_RUN: \"false\"",
        "MEDIMAGE_ALLOW_RAWDATA_WRITE: \"false\"",
        "MEDIMAGE_SYNTHETIC_ONLY: \"true\"",
    ]

    for token in compose_required_tokens:
        ok = token in compose_text
        checks.append({
            "name": f"docker-compose.demo.yml:{token}",
            "ok": ok,
            "message": "present" if ok else "missing",
        })
        if not ok:
            blockers.append(f"Missing docker safety env token: {token}")

    status = "READY" if not blockers else "BLOCKED"
    if warnings and status == "READY":
        status = "WARNING"

    out_dir = Path(work_dir) / "deployment"
    report_out = Path(report_dir) / "deployment"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "deployment_profile.json"
    report_path = report_out / "deployment_profile_report.md"

    payload = {
        "ok": status in {"READY", "WARNING"},
        "node_id": "deployment_profile",
        "backend": "python",
        "status": status,
        "checks_total": len(checks),
        "checks_passed": sum(1 for item in checks if item.get("ok")),
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "environment": {
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "docker_version": docker_version,
            "docker_compose_version": docker_compose_version,
            "node_version": node_version,
            "npm_version": npm_version,
        },
        "profiles": {
            "local_dev": {
                "backend": "uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000",
                "frontend": "cd frontend && npm run dev",
                "matlab_enabled_by_default": False,
            },
            "docker_demo": {
                "compose_file": "deploy/docker-compose.demo.yml",
                "matlab_enabled_by_default": False,
                "full_dpabi_execution_allowed": False,
                "rawdata_write_allowed": False,
            },
        },
        "safety": {
            "pipelines_executed": False,
            "docker_build_executed": False,
            "docker_compose_executed": False,
            "matlab_launched": False,
            "dpabi_executed": False,
            "dparsf_run_executed": False,
            "dpabi_gui_called": False,
            "rawdata_modified": False,
            "files_deleted": False,
            "cloud_deployment_performed": False,
        },
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# Deployment Profile Report")
    lines.append("")
    lines.append(f"- Status: {status}")
    lines.append(f"- Checks passed: {payload['checks_passed']}/{payload['checks_total']}")
    lines.append(f"- Blockers: {len(blockers)}")
    lines.append(f"- Warnings: {len(warnings)}")
    lines.append("")
    lines.append("## Local Dev")
    lines.append("")
    lines.append("```bash")
    lines.append("uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000")
    lines.append("cd frontend && npm run dev")
    lines.append("```")
    lines.append("")
    lines.append("## Docker Demo")
    lines.append("")
    lines.append("```bash")
    lines.append("cd deploy")
    lines.append("docker compose -f docker-compose.demo.yml up --build")
    lines.append("```")
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

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload["outputs"] = [str(json_path), str(report_path)]
    return payload
9. 创建 backend/app/tools/run_deployment_profile_cli.py

创建文件：

backend/app/tools/run_deployment_profile_cli.py

内容：

from __future__ import annotations

import json

from backend.app.tools.deployment_profile import build_deployment_profile


def main() -> int:
    result = build_deployment_profile()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
10. 修改 backend/app/api/models.py

如果不需要 request model，可以不新增。
本步骤 API 只需要 GET / POST refresh，无 body。

11. 修改 backend/app/api/routes.py

新增 API：

GET  /api/health
GET  /api/deployment/profile
POST /api/deployment/profile/refresh

新增导入：

from backend.app.tools.deployment_profile import build_deployment_profile

新增路由：

@router.get("/api/health")
def api_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "medimage-agent-backend",
        "status": "healthy",
        "matlab_enabled": False,
        "full_dpabi_execution_allowed": False,
        "dparsf_run_allowed": False,
        "dparsfa_run_allowed": False,
        "dpabi_gui_allowed": False,
        "rawdata_write_allowed": False,
    }


@router.get("/api/deployment/profile")
def api_get_deployment_profile() -> dict[str, Any]:
    base = Path("work") / "deployment"
    report_base = Path("reports") / "deployment"

    profile = _read_json_if_exists(base / "deployment_profile.json")
    report = _read_text_if_exists(report_base / "deployment_profile_report.md")

    if profile is None:
        profile = build_deployment_profile()

    return {
        "ok": True,
        "profile": profile,
        "report": report,
    }


@router.post("/api/deployment/profile/refresh")
def api_refresh_deployment_profile() -> dict[str, Any]:
    result = build_deployment_profile()

    if not result.get("ok"):
        return result

    return result
12. 修改 frontend/src/api.ts

新增：

export async function getHealth(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/health");
}

export async function getDeploymentProfile(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/deployment/profile"
  );
}

export async function refreshDeploymentProfile(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/deployment/profile/refresh",
    { method: "POST" }
  );
}
13. 创建 frontend/src/components/DeploymentPanel.tsx

创建文件：

frontend/src/components/DeploymentPanel.tsx

内容：

import { useState } from "react";
import {
  getDeploymentProfile,
  getHealth,
  refreshDeploymentProfile
} from "../api";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

export function DeploymentPanel({ baseUrl }: Props) {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("IDLE");
  const [error, setError] = useState("");

  async function handleHealth() {
    setStatus("CHECKING_HEALTH");
    setError("");

    try {
      const result = await getHealth(baseUrl);
      setHealth(result);
      setStatus("HEALTHY");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleLoadProfile() {
    setStatus("LOADING_PROFILE");
    setError("");

    try {
      const result = await getDeploymentProfile(baseUrl);
      setPayload(result);
      setStatus("PROFILE_LOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  async function handleRefreshProfile() {
    setStatus("REFRESHING_PROFILE");
    setError("");

    try {
      const result = await refreshDeploymentProfile(baseUrl);
      setPayload({
        ok: true,
        profile: result
      });
      setStatus("PROFILE_REFRESHED");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("ERROR");
    }
  }

  const profile = payload?.profile as Record<string, unknown> | undefined;

  return (
    <div>
      <div className="row">
        <button onClick={handleHealth}>检查 API Health</button>
        <button onClick={handleLoadProfile}>加载 Deployment Profile</button>
        <button onClick={handleRefreshProfile}>刷新 Deployment Profile</button>
        <StatusBadge status={status} />
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      <div className="metricGrid">
        <div className="metricCard">
          <span>Health</span>
          <strong>{String(health?.status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Deployment Status</span>
          <strong>{String(profile?.status ?? "-")}</strong>
        </div>
        <div className="metricCard">
          <span>Checks</span>
          <strong>
            {profile
              ? `${String(profile.checks_passed ?? "-")}/${String(profile.checks_total ?? "-")}`
              : "-"}
          </strong>
        </div>
        <div className="metricCard">
          <span>MATLAB Enabled</span>
          <strong>{String(health?.matlab_enabled ?? false)}</strong>
        </div>
      </div>

      <h3>Health JSON</h3>
      <JsonBlock value={health} emptyText="尚未检查 health" />

      <h3>Deployment Profile JSON</h3>
      <JsonBlock value={profile} emptyText="尚未加载 deployment profile" />

      <h3>Deployment Report</h3>
      <TextViewer
        text={
          typeof payload?.report === "string"
            ? payload.report
            : null
        }
        emptyText="暂无 deployment report"
      />
    </div>
  );
}
14. 修改 frontend/src/App.tsx

新增导入：

import { DeploymentPanel } from "./components/DeploymentPanel";

在 Release Readiness 后增加 Section：

<Section
  title="Docker / Local Deployment Profile"
  description="检查本地开发与 Docker demo 配置、health check、安全环境变量和部署前配置完整性。"
>
  <DeploymentPanel baseUrl={baseUrl} />
</Section>
15. 新增轻量测试

创建文件：

tests/unit/test_deployment_profile.py

内容：

from __future__ import annotations

from pathlib import Path

from backend.app.tools.deployment_profile import build_deployment_profile


def test_deployment_profile_detects_required_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (tmp_path / "work").mkdir()
    (tmp_path / "reports").mkdir()

    (tmp_path / ".env.example").write_text(
        "\n".join([
            "MEDIMAGE_MATLAB_ENABLED=false",
            "MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION=false",
            "MEDIMAGE_ALLOW_DPARSF_RUN=false",
            "MEDIMAGE_ALLOW_DPARSFA_RUN=false",
            "MEDIMAGE_ALLOW_RAWDATA_WRITE=false",
            "MEDIMAGE_SYNTHETIC_ONLY=true",
        ]),
        encoding="utf-8",
    )

    (deploy / "local_profile.yaml").write_text("profile_id: local_dev\n", encoding="utf-8")
    (deploy / "docker-compose.demo.yml").write_text(
        "\n".join([
            'MEDIMAGE_MATLAB_ENABLED: "false"',
            'MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION: "false"',
            'MEDIMAGE_ALLOW_DPARSF_RUN: "false"',
            'MEDIMAGE_ALLOW_DPARSFA_RUN: "false"',
            'MEDIMAGE_ALLOW_RAWDATA_WRITE: "false"',
            'MEDIMAGE_SYNTHETIC_ONLY: "true"',
        ]),
        encoding="utf-8",
    )
    (deploy / "backend.Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (deploy / "frontend.Dockerfile").write_text("FROM node:20-alpine\n", encoding="utf-8")
    (deploy / "nginx.conf").write_text("server { listen 80; }\n", encoding="utf-8")

    result = build_deployment_profile(work_dir="./work", report_dir="./reports")

    assert result["node_id"] == "deployment_profile"
    assert result["status"] in {"READY", "WARNING"}
    assert result["safety"]["docker_build_executed"] is False
    assert (tmp_path / "work" / "deployment" / "deployment_profile.json").exists()
    assert (tmp_path / "reports" / "deployment" / "deployment_profile_report.md").exists()
16. 修改 backend/app/tools/api_smoke_test.py

新增只读测试：

call("GET", "/api/health")
call("GET", "/api/deployment/profile")

不要在 smoke test 中调用 POST refresh。

17. 更新 README.md

追加第三十三步说明：

## Step 33: Docker / Local Deployment Profile

This step adds local and Docker demo deployment profiles.

It supports:

- .env.example
- local deployment profile
- Docker demo compose
- backend Dockerfile
- frontend Dockerfile
- nginx config
- health check API
- deployment profile scanner
- frontend deployment panel

It does not build or deploy automatically.

### Local Dev

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend
npm run dev
Docker Demo
cd deploy
docker compose -f docker-compose.demo.yml up --build

In Docker demo mode:

MATLAB is disabled by default
full DPABI execution is disabled
DPARSF_run / DPARSFA_run are disabled
rawdata write is disabled
third_party is not copied into images
Build Deployment Profile
python -m backend.app.tools.run_deployment_profile_cli

Expected outputs:

work/deployment/deployment_profile.json
reports/deployment/deployment_profile_report.md
API
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/deployment/profile

Refresh:

curl -X POST http://127.0.0.1:8000/api/deployment/profile/refresh
Frontend

Use:

Docker / Local Deployment Profile
Safety

This step:

does not execute pipelines
does not launch MATLAB
does not run DPABI
does not call DPARSF_run
does not call DPARSFA_run
does not call DPABI GUI
does not build Docker automatically
does not deploy to cloud
does not modify rawdata

---

## 18. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/deployment_profile_spec.md
.env.example
deploy/local_profile.yaml
deploy/docker-compose.demo.yml
deploy/backend.Dockerfile
deploy/frontend.Dockerfile
deploy/nginx.conf
backend/app/tools/deployment_profile.py
backend/app/tools/run_deployment_profile_cli.py
backend/app/api/routes.py
frontend/src/api.ts
frontend/src/components/DeploymentPanel.tsx
frontend/src/App.tsx
tests/unit/test_deployment_profile.py
backend/app/tools/api_smoke_test.py
README.md

运行：

python -m backend.app.tools.run_deployment_profile_cli

应生成：

work/deployment/deployment_profile.json
reports/deployment/deployment_profile_report.md

deployment_profile.json 必须包含：

{
  "node_id": "deployment_profile",
  "safety": {
    "pipelines_executed": false,
    "docker_build_executed": false,
    "docker_compose_executed": false,
    "matlab_launched": false,
    "dpabi_executed": false,
    "dparsf_run_executed": false,
    "dpabi_gui_called": false,
    "rawdata_modified": false,
    "files_deleted": false,
    "cloud_deployment_performed": false
  }
}

运行测试：

python -m pytest tests/unit/test_deployment_profile.py -q

启动后端：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试 API：

curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/deployment/profile
curl -X POST http://127.0.0.1:8000/api/deployment/profile/refresh

启动前端：

cd frontend
npm run dev

页面应该能完成：

显示 Docker / Local Deployment Profile 区域。
可以检查 API health。
可以加载 deployment profile。
可以刷新 deployment profile。
显示 health JSON。
显示 deployment profile JSON。
显示 deployment report。
不执行 pipeline。
不启动 MATLAB。
不运行 DPABI。
不自动 docker build。
不自动部署。
不修改或删除文件。
19. 重要限制

本步骤只做 local / Docker deployment profile。

不要实现：

自动 Docker build
自动 Docker compose up
云端部署
HTTPS / 证书自动配置
生产鉴权
用户系统
MATLAB 容器化
DPABI 容器化
真实医学影像处理
DPARSF_run 自动执行
DPARSFA_run 自动执行
修改 rawdata
删除文件

完成后请总结：

新增了哪些文件
修改了哪些文件
local_dev profile 如何启动
docker_demo profile 如何启动
Docker demo 为什么默认禁用 MATLAB / DPABI 执行
health check 返回哪些安全状态
下一步如何做 CI / automated quality gate

'''
Step 33 主要实现的是：

## Docker / Local Deployment Profile + Health Check 闭环
### 核心目标
当前系统已经可以做 release readiness scan，但还缺少一个 部署配置层 ，用来回答：

- 本地开发模式如何启动？
- Docker demo 模式如何启动？
- 后端、前端、work/reports/logs/examples 挂载是否合理？
- MATLAB / SPM / DPABI 是否作为外部依赖声明？
- Docker demo 是否默认禁用 MATLAB / DPABI 执行？
- API health check 是否可用？
- 前端 health check 是否可视化？
- 部署 profile 是否明确禁止 rawdata / third_party 打包或暴露？
- 当前项目是否能进入本地演示或 Docker demo 阶段？
### 主要功能
1. Deployment Profile 配置
   
   - local_dev - 本地开发模式（uvicorn + npm run dev）
   - docker_demo - Docker 容器化演示模式
   - 环境变量模板（ .env.example ）
   - 服务定义和配置
2. Docker 配置
   
   - Backend Dockerfile - Python 3.11 slim 基础镜像
   - Frontend Dockerfile - Node 20 + Nginx 多阶段构建
   - Docker Compose - 编排 backend 和 frontend 服务
   - Nginx 配置 - 反向代理和静态文件服务
3. Health Check
   
   - Backend health endpoint: GET /api/health
   - Frontend health endpoint: GET /health
   - Docker 容器健康检查配置
4. Deployment Profile Scanner
   
   - 验证部署文件是否存在
   - 检查 Docker 安全配置
   - 验证环境变量安全默认值
   - 检测禁止的 COPY 模式（third_party、.git、node_modules）
   - 生成部署报告
### 解决的问题
- 缺乏标准化的本地开发启动方式
- 缺乏容器化部署配置
- 无法验证部署配置完整性
- 缺少部署前安全检查
- 无法确认 Docker 配置是否安全
- 缺少 health check 机制
### 部署模式对比
特性 local_dev docker_demo 启动方式 uvicorn + npm docker compose 热重载 ✅ 支持 ❌ 不支持 MATLAB 可选可用 ❌ 禁用 DPABI 执行 需审批 ❌ 禁用 适用场景 开发调试 演示/交付 数据访问 完整访问 只读/报告

### 检查清单
文件检查：

- .env.example 存在
- deploy/local_profile.yaml 存在
- deploy/docker-compose.demo.yml 存在
- deploy/backend.Dockerfile 存在
- deploy/frontend.Dockerfile 存在
- deploy/nginx.conf 存在
安全检查：

- Dockerfile 不复制 third_party
- Dockerfile 不复制 .git
- Dockerfile 不复制 node_modules
- .env.example 包含安全默认值
- docker-compose.demo.yml 禁用 MATLAB
- docker-compose.demo.yml 禁用 DPABI 执行
环境检查：

- Docker CLI 可用性
- Docker Compose 可用性
- Node.js 可用性
- npm 可用性
### 输出文件
```
work/deployment/
└── deployment_profile.json       # JSON 部署数据

reports/deployment/
└── deployment_profile_report.md  # Markdown 报告
```
### 状态分类
状态 说明 READY 所有部署文件存在，安全检查通过 WARNING 部署文件存在，有轻微问题 BLOCKED 缺少必需文件或安全违规

### 安全规则
- ✅ 不自动执行 Docker build
- ✅ 不自动部署
- ✅ 不执行 pipeline
- ✅ Docker demo 禁用 MATLAB
- ✅ Docker demo 禁用 DPABI
- ✅ 不暴露 rawdata
- ✅ 不复制 third_party 到镜像
### 使用场景
- 本地开发 - 快速启动，热重载调试
- Docker Demo - 无 MATLAB 依赖的容器化演示
- CI/CD 集成 - 自动化部署配置检查
- 部署审查 - 部署前验证配置
- 环境审计 - 检查开发和部署环境完整性
'''