你是我的工程搭建助手。前八步已经完成：

Step 1：完成项目工程骨架，并打通 MATLAB / SPM / DPABI 环境检查闭环。
Step 2：完成单节点执行闭环，可以运行一个 SPM smoke test 节点。
Step 3：完成最小 Pipeline DAG 执行闭环。
Step 4：完成 synthetic BIDS-like 数据集扫描与索引闭环。
Step 5：完成 synthetic subject-level SPM smoothing + QC 闭环。
Step 6：完成数据集级评估与 Markdown/HTML 报告闭环。
Step 7：完成 deterministic Agent Runtime、Plan Mode、Execute Mode、Tool Registry、Hook Manager 和 approval 机制。
Step 8：完成最小长期记忆、后台复盘和错误知识库闭环。

现在开始第九步。

第九步目标：实现“最小 FastAPI 后端服务闭环”。

这一步为后续可视化 UI 做准备，把已有 CLI 能力包装成 HTTP API。  
当前仍然不做前端 UI，不做数据库，不做异步队列，不做 WebSocket，不做真实 LLM。

本步骤要实现：

- FastAPI app
- health check
- project config 读取 API
- pipeline 列表 API
- pipeline 详情 API
- agent plan API
- agent execute API，需要 approved=true
- agent run summary API
- dataset evaluation report API
- 安全文件读取 API，只允许读取 work/、logs/、reports/、memory/、examples/ 下的文本/JSON/CSV/Markdown/HTML 文件
- API smoke test CLI
- README 更新

不要实现 UI。
不要实现 WebSocket。
不要实现数据库。
不要实现 Celery / Redis。
不要实现并行调度。
不要实现真实 LLM API。
不要实现多 Agent 对话。
不要实现 GPU。
不要实现 DPABI pipeline。
不要修改 SPM / DPABI 源码。
不要处理真实医学影像数据。
不要让 API 任意读取系统文件。
不要让 API 删除文件。

本步骤只做最小本地 FastAPI 服务。

---

## 1. 创建 specs/api_service_spec.md

创建文件：

```text
specs/api_service_spec.md

内容：

# API Service Specification

This document defines the MVP FastAPI service for MedImage Agent.

## Goals

Expose existing deterministic CLI/runtime capabilities through HTTP APIs.

The API is intended for a future visual frontend.

## Scope

Supported in MVP:

- health check
- project config inspection
- pipeline listing
- pipeline detail reading
- agent plan creation
- approved agent execution
- agent run summary reading
- dataset evaluation report reading
- safe file reading from allowlisted folders

Unsupported in MVP:

- authentication
- multi-user accounts
- database
- async job queue
- WebSocket streaming
- real LLM calls
- UI
- GPU scheduling
- DPABI pipeline
- production deployment

## Safety Rules

- API must not delete files.
- API must not modify rawdata.
- API must not modify SPM or DPABI source.
- API must not allow arbitrary path traversal.
- API execution requires approved=true.
- API file reading is limited to allowlisted folders.

## Allowlisted Read Folders

```text
examples/
work/
logs/
reports/
memory/
specs/
Endpoints
GET /health

Returns service status.

GET /api/project-config

Reads the default project config.

GET /api/pipelines

Lists YAML files in examples/.

GET /api/pipelines/{pipeline_name}

Reads and validates a pipeline YAML.

POST /api/agent/plan

Creates a plan.

POST /api/agent/execute

Executes an approved plan.

Requires:

{
  "approved": true
}
GET /api/agent-runs/{agent_run_id}

Reads plan, agent_summary, review_summary, and proposed_memory_patch if they exist.

GET /api/reports/dataset-evaluation

Reads dataset evaluation outputs if they exist.

GET /api/files/read?path=...

Reads a safe text file from an allowlisted folder.


---

## 2. 创建 backend/app/runtime/path_safety.py

创建文件：

```text id="5ixke0"
backend/app/runtime/path_safety.py

目标：防止 API 任意读文件和路径穿越。

功能要求：

提供：
get_repo_root()
resolve_under_root(path)
is_allowed_read_path(path)
assert_allowed_read_path(path)
read_safe_text_file(path)
只允许读取这些目录下文件：
examples/
work/
logs/
reports/
memory/
specs/
禁止读取：
third_party/
rawdata/
sourcedata/
derivatives/ 下的 NIfTI
绝对路径逃逸
.. 路径穿越
只允许读取扩展名：
.json
.yaml
.yml
.md
.txt
.csv
.html
.log
返回清晰错误。

参考实现：

from __future__ import annotations

from pathlib import Path


class PathSafetyError(Exception):
    pass


ALLOWED_READ_DIRS = [
    "examples",
    "work",
    "logs",
    "reports",
    "memory",
    "specs",
]

ALLOWED_TEXT_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".csv",
    ".html",
    ".log",
}


def get_repo_root() -> Path:
    return Path.cwd().resolve()


def resolve_under_root(path: str | Path) -> Path:
    root = get_repo_root()
    target = Path(path)

    if not target.is_absolute():
        target = root / target

    target = target.resolve()

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PathSafetyError(f"Path escapes repository root: {path}") from exc

    return target


def is_allowed_read_path(path: str | Path) -> bool:
    try:
        root = get_repo_root()
        target = resolve_under_root(path)
        rel = target.relative_to(root)

        if not rel.parts:
            return False

        if rel.parts[0] not in ALLOWED_READ_DIRS:
            return False

        if target.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
            return False

        return target.is_file()
    except Exception:
        return False


def assert_allowed_read_path(path: str | Path) -> Path:
    target = resolve_under_root(path)

    if not is_allowed_read_path(target):
        raise PathSafetyError(
            f"File is not allowed for API reading: {path}. "
            f"Allowed folders: {ALLOWED_READ_DIRS}; "
            f"allowed suffixes: {sorted(ALLOWED_TEXT_SUFFIXES)}"
        )

    return target


def read_safe_text_file(path: str | Path) -> dict:
    target = assert_allowed_read_path(path)
    content = target.read_text(encoding="utf-8", errors="replace")

    return {
        "ok": True,
        "path": str(target),
        "relative_path": str(target.relative_to(get_repo_root())),
        "content": content,
        "size_bytes": target.stat().st_size,
    }
3. 创建 backend/app/api/models.py

创建目录和文件：

backend/app/api/models.py

目标：定义 API request / response 模型。

要求：

可以使用 pydantic，因为 FastAPI 默认依赖 pydantic。
定义：
AgentPlanRequest
AgentExecuteRequest
FileReadResponse
ErrorResponse

参考实现：

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentPlanRequest(BaseModel):
    agent_run_id: str = Field(default="agent_run_001")
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_subject_preprocess.yaml")


class AgentExecuteRequest(BaseModel):
    agent_run_id: str = Field(default="agent_run_001")
    project_config_path: str = Field(default="examples/project_config_dataset.yaml")
    pipeline_path: str = Field(default="examples/pipeline_subject_preprocess.yaml")
    approved: bool = Field(default=False)


class FileReadResponse(BaseModel):
    ok: bool
    path: str
    relative_path: str
    content: str
    size_bytes: int


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
4. 创建 backend/app/api/routes.py

创建文件：

backend/app/api/routes.py

目标：实现所有 MVP API 路由。

功能要求：

使用 FastAPI APIRouter。
所有异常转成 JSON。
不允许 API 崩溃成 HTML traceback。
路由包括：
GET  /health
GET  /api/project-config
GET  /api/pipelines
GET  /api/pipelines/{pipeline_name}
POST /api/agent/plan
POST /api/agent/execute
GET  /api/agent-runs/{agent_run_id}
GET  /api/reports/dataset-evaluation
GET  /api/files/read
/api/agent/execute 必须要求 approved=true。
/api/files/read 必须使用 path_safety。
/api/pipelines/{pipeline_name} 只能读取 examples/ 下 .yaml 或 .yml。
/api/agent-runs/{agent_run_id} 读取：
work/agent_runs/{agent_run_id}/plan.json
work/agent_runs/{agent_run_id}/agent_summary.json
work/agent_runs/{agent_run_id}/review_summary.md
work/agent_runs/{agent_run_id}/proposed_memory_patch.md
/api/reports/dataset-evaluation 读取：
reports/dataset_evaluation/dataset_summary.json
reports/dataset_evaluation/subject_qc_table.csv
reports/dataset_evaluation/exclusion_recommendations.csv
reports/dataset_evaluation/dataset_evaluation_report.md
reports/dataset_evaluation/dataset_evaluation_report.html

参考实现方向：

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.api.models import AgentExecuteRequest, AgentPlanRequest
from backend.app.runtime.agent_runtime import (
    run_orchestrator_execute,
    run_orchestrator_plan,
)
from backend.app.runtime.path_safety import PathSafetyError, read_safe_text_file
from backend.app.schemas.pipeline_schema import load_pipeline_yaml

router = APIRouter()


def _read_json_if_exists(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_text_if_exists(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "medimage-agent-api",
        "status": "healthy",
    }


@router.get("/api/project-config")
def get_project_config(
    path: str = Query(default="examples/project_config_dataset.yaml"),
) -> dict[str, Any]:
    try:
        data = read_safe_text_file(path)
        import yaml
        parsed = yaml.safe_load(data["content"]) or {}
        return {
            "ok": True,
            "path": data["relative_path"],
            "config": parsed,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/pipelines")
def list_pipelines() -> dict[str, Any]:
    examples = Path("examples")
    pipelines = []
    for path in sorted(examples.glob("*.yaml")):
        pipelines.append(str(path))
    for path in sorted(examples.glob("*.yml")):
        pipelines.append(str(path))
    return {
        "ok": True,
        "pipelines": pipelines,
    }


@router.get("/api/pipelines/{pipeline_name}")
def get_pipeline(pipeline_name: str) -> dict[str, Any]:
    try:
        if "/" in pipeline_name or "\\" in pipeline_name or ".." in pipeline_name:
            raise ValueError("Invalid pipeline name.")

        path = Path("examples") / pipeline_name
        if path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError("Pipeline must be a YAML file.")

        data = read_safe_text_file(path)
        pipeline = load_pipeline_yaml(path)

        return {
            "ok": True,
            "path": data["relative_path"],
            "pipeline": {
                "pipeline_id": pipeline.pipeline_id,
                "version": pipeline.version,
                "modality": pipeline.modality,
                "description": pipeline.description,
                "nodes_total": len(pipeline.nodes),
                "nodes": [
                    {
                        "id": node.id,
                        "name": node.name,
                        "backend": node.backend,
                        "parallel_level": node.parallel_level,
                        "depends_on": node.depends_on,
                    }
                    for node in pipeline.nodes
                ],
            },
            "raw": data["content"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/agent/plan")
def agent_plan(request: AgentPlanRequest) -> dict[str, Any]:
    result = run_orchestrator_plan(
        agent_run_id=request.agent_run_id,
        project_config_path=request.project_config_path,
        pipeline_path=request.pipeline_path,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/api/agent/execute")
def agent_execute(request: AgentExecuteRequest) -> dict[str, Any]:
    if not request.approved:
        raise HTTPException(
            status_code=403,
            detail="Execution requires approved=true.",
        )

    plan_path = Path("work") / "agent_runs" / request.agent_run_id / "plan.json"

    result = run_orchestrator_execute(
        agent_run_id=request.agent_run_id,
        project_config_path=request.project_config_path,
        pipeline_path=request.pipeline_path,
        plan_path=str(plan_path),
        approved=request.approved,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/api/agent-runs/{agent_run_id}")
def get_agent_run(agent_run_id: str) -> dict[str, Any]:
    if "/" in agent_run_id or "\\" in agent_run_id or ".." in agent_run_id:
        raise HTTPException(status_code=400, detail="Invalid agent_run_id.")

    base = Path("work") / "agent_runs" / agent_run_id

    plan = _read_json_if_exists(base / "plan.json")
    agent_summary = _read_json_if_exists(base / "agent_summary.json")
    review_summary = _read_text_if_exists(base / "review_summary.md")
    proposed_memory_patch = _read_text_if_exists(base / "proposed_memory_patch.md")

    return {
        "ok": True,
        "agent_run_id": agent_run_id,
        "plan": plan,
        "agent_summary": agent_summary,
        "review_summary": review_summary,
        "proposed_memory_patch": proposed_memory_patch,
    }


@router.get("/api/reports/dataset-evaluation")
def get_dataset_evaluation_report() -> dict[str, Any]:
    base = Path("reports") / "dataset_evaluation"

    return {
        "ok": True,
        "dataset_summary": _read_json_if_exists(base / "dataset_summary.json"),
        "subject_qc_table": _read_text_if_exists(base / "subject_qc_table.csv"),
        "exclusion_recommendations": _read_text_if_exists(base / "exclusion_recommendations.csv"),
        "report_markdown": _read_text_if_exists(base / "dataset_evaluation_report.md"),
        "report_html": _read_text_if_exists(base / "dataset_evaluation_report.html"),
    }


@router.get("/api/files/read")
def read_file(path: str = Query(...)) -> dict[str, Any]:
    try:
        return read_safe_text_file(path)
    except PathSafetyError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
5. 创建 backend/app/main.py

创建文件：

backend/app/main.py

内容：

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="MedImage Agent API",
        version="0.1.0",
        description="MVP API service for MedImage Agent.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
6. 创建 backend/app/tools/api_smoke_test.py

创建文件：

backend/app/tools/api_smoke_test.py

目标：用 Python 标准库或 requests 对本地 API 做 smoke test。

要求：

默认 base URL：
http://127.0.0.1:8000
测试：
GET /health
GET /api/pipelines
POST /api/agent/plan
GET /api/agent-runs/agent_run_001
不自动执行 /api/agent/execute，避免误运行 MATLAB。
如果 requests 不存在，提示：
pip install requests

参考实现：

from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        import requests
    except ImportError:
        print("Missing dependency: requests. Install with: pip install requests")
        return 1

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    checks = []

    def call(method: str, path: str, **kwargs):
        url = base_url.rstrip("/") + path
        response = requests.request(method, url, timeout=30, **kwargs)
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}

        checks.append({
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "ok": 200 <= response.status_code < 300,
            "payload": payload,
        })

    call("GET", "/health")
    call("GET", "/api/pipelines")
    call("POST", "/api/agent/plan", json={
        "agent_run_id": "agent_run_001",
        "project_config_path": "examples/project_config_dataset.yaml",
        "pipeline_path": "examples/pipeline_subject_preprocess.yaml",
    })
    call("GET", "/api/agent-runs/agent_run_001")

    print(json.dumps({
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
    }, ensure_ascii=False, indent=2))

    return 0 if all(item["ok"] for item in checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
7. 创建 backend/app/api/init.py

创建空文件：

backend/app/api/__init__.py

如果 backend/app/ 下面缺少 __init__.py，也补上：

backend/__init__.py
backend/app/__init__.py
backend/app/tools/__init__.py
backend/app/runtime/__init__.py
backend/app/schemas/__init__.py

不要破坏已有代码。

8. 更新 README.md

追加第九步说明：

## Step 9: MVP FastAPI Backend Service

This step exposes the deterministic MedImage Agent runtime through a local FastAPI service.

Install dependencies:

```bash
pip install fastapi uvicorn pydantic requests pyyaml

Start API server:

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

Health check:

curl http://127.0.0.1:8000/health

List pipelines:

curl http://127.0.0.1:8000/api/pipelines

Create an agent plan:

curl -X POST http://127.0.0.1:8000/api/agent/plan \
  -H "Content-Type: application/json" \
  -d '{
    "agent_run_id": "agent_run_001",
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_subject_preprocess.yaml"
  }'

Execute an approved plan:

curl -X POST http://127.0.0.1:8000/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_run_id": "agent_run_001",
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_subject_preprocess.yaml",
    "approved": true
  }'

Run API smoke test:

python -m backend.app.tools.api_smoke_test

Safety:

/api/agent/execute requires approved=true.
/api/files/read can only read allowlisted text files.
The API cannot delete files.
The API cannot modify rawdata.

---

## 9. 验收标准

完成后确认新增或修改了这些文件：

```text
specs/api_service_spec.md
backend/app/runtime/path_safety.py
backend/app/api/__init__.py
backend/app/api/models.py
backend/app/api/routes.py
backend/app/main.py
backend/app/tools/api_smoke_test.py
README.md

并确认必要 __init__.py 存在：

backend/__init__.py
backend/app/__init__.py
backend/app/tools/__init__.py
backend/app/runtime/__init__.py
backend/app/schemas/__init__.py

安装依赖：

pip install fastapi uvicorn pydantic requests pyyaml

启动服务：

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

测试：

curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/pipelines
python -m backend.app.tools.api_smoke_test

应该能生成或读取：

work/agent_runs/agent_run_001/plan.json

测试安全行为：

未批准执行应该失败：
curl -X POST http://127.0.0.1:8000/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_run_id": "agent_run_001",
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_subject_preprocess.yaml",
    "approved": false
  }'

应该返回 403 或清晰错误。

路径穿越应该失败：
curl "http://127.0.0.1:8000/api/files/read?path=../../etc/passwd"

应该返回 403 或清晰错误。

读取允许文件应该成功：
curl "http://127.0.0.1:8000/api/files/read?path=work/agent_runs/agent_run_001/plan.json"

如果文件存在，应返回内容。

10. 重要限制

本步骤只做最小 FastAPI 后端服务。

不要实现：

前端 UI
WebSocket
数据库
认证系统
用户系统
异步任务队列
Celery / Redis
真实 LLM API
多 Agent 对话
并行调度
GPU
DPABI pipeline
文件删除 API
任意文件读取 API

完成后请总结：

新增了哪些文件
修改了哪些文件
如何启动 API
如何创建 plan
如何批准执行
API 安全限制有哪些
如果服务失败应该看哪里

'''
这一步主要做的是：

## 第九步：最小 FastAPI 后端服务闭环
这一步为后续可视化 UI 做准备，把已有的 CLI 能力包装成 HTTP API。

### 核心目标
将前八步实现的 deterministic Agent Runtime 通过 FastAPI 暴露为 HTTP API，供未来的前端 UI 调用。

### 实现的功能
1. FastAPI 应用
   
   - backend/app/main.py - 主应用入口
   - CORS 中间件支持前端开发服务器
2. API 路由 ( backend/app/api/routes.py )
   
   - GET /health - 服务健康检查
   - GET /api/project-config - 读取项目配置
   - GET /api/pipelines - 列出所有 pipeline YAML
   - GET /api/pipelines/{pipeline_name} - 读取 pipeline 详情
   - POST /api/agent/plan - 创建执行计划
   - POST /api/agent/execute - 执行已批准的计划
   - GET /api/agent-runs/{agent_run_id} - 读取 Agent Run 汇总
   - GET /api/reports/dataset-evaluation - 读取数据集评估报告
   - GET /api/files/read?path=... - 安全文件读取
3. 路径安全 ( backend/app/runtime/path_safety.py )
   
   - 只允许读取白名单目录： examples/ , work/ , logs/ , reports/ , memory/ , specs/
   - 只允许读取白名单扩展名： .json , .yaml , .yml , .md , .txt , .csv , .html , .log
   - 防止路径穿越攻击（ .. 和绝对路径逃逸）
4. 数据模型 ( backend/app/api/models.py )
   
   - AgentPlanRequest - 创建计划请求
   - AgentExecuteRequest - 执行请求（需要 approved=true ）
   - FileReadResponse - 文件读取响应
   - ErrorResponse - 错误响应
5. API Smoke Test ( backend/app/tools/api_smoke_test.py )
   
   - 测试所有关键 API 端点
   - 不自动执行 /api/agent/execute ，避免误运行 MATLAB
### 安全规则
- /api/agent/execute 必须设置 approved=true
- API 不能删除文件
- API 不能修改 rawdata
- API 不能修改 SPM/DPABI 源码
- API 文件读取限制在白名单目录和扩展名
### 使用方式
```
# 安装依赖
pip install fastapi uvicorn pydantic requests pyyaml

# 启动服务
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 
8000

# 健康检查
curl http://127.0.0.1:8000/health

# 创建计划
curl -X POST http://127.0.0.1:8000/api/agent/plan \
  -H "Content-Type: application/json" \
  -d '{"agent_run_id": "agent_run_001", ...}'

# 执行计划（需要 approved=true）
curl -X POST http://127.0.0.1:8000/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"approved": true, ...}'

# Smoke test
python -m backend.app.tools.api_smoke_test
```
### 明确不做的事情
- ❌ UI（只做后端 API）
- ❌ WebSocket
- ❌ 数据库
- ❌ Celery / Redis
- ❌ 并行调度
- ❌ 真实 LLM API
- ❌ 多 Agent 对话
- ❌ GPU
- ❌ DPABI pipeline
- ❌ 修改 SPM/DPABI 源码
- ❌ 处理真实医学影像数据
- ❌ 让 API 任意读取系统文件
- ❌ 让 API 删除文件
这一步已经 全部完成 并验证通过。成功实现了：

- FastAPI 服务 ✅
- 所有 MVP API 端点 ✅
- 路径安全机制 ✅
- API Smoke Test ✅

'''