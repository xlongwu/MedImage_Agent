# MedImage Agent 后端架构审查与优化方案

> **审查日期**: 2026-06-12  
> **审查人**: Backend Architect  
> **审查范围**: `src/backend/app/` 全部后端代码  
> **原则**: 仅提供分析建议，不修改任何代码  

---

## 目录

1. [架构现状总览](#1-架构现状总览)
2. [十大核心问题](#2-十大核心问题)
3. [目标架构蓝图](#3-目标架构蓝图)
4. [详细优化方案](#4-详细优化方案)
5. [实施路线图](#5-实施路线图)
6. [风险与依赖](#6-风险与依赖)

---

## 1. 架构现状总览

### 1.1 当前技术栈

| 层面 | 技术选型 | 评估 |
|------|---------|------|
| **Web 框架** | FastAPI + Uvicorn | ✅ 合理，异步性能优秀 |
| **数据验证** | Pydantic v2 | ✅ 合理，类型安全 |
| **持久化** | 文件系统 JSON + SQLite | ⚠️ 缺少事务保障 |
| **配置管理** | YAML + 环境变量 + JSON | ⚠️ 三套机制，未统一 |
| **并发模型** | ThreadPoolExecutor | ⚠️ 缺少异步/进程隔离 |
| **依赖注入** | 无框架 | ⚠️ 直接 import，耦合度高 |
| **日志系统** | 无结构化日志 | ❌ 缺失 |
| **中间件** | 仅 CORS | ❌ 严重不足 |
| **API 版本** | 无版本前缀 | ❌ 缺失 |
| **数据库 ORM** | 无 (手动 SQL + JSON) | ⚠️ 适合当前规模，但扩展受限 |

### 1.2 分层结构

```
┌──────────────────────────────────────────────────┐
│  API 层  (21 个路由文件, ~7,500 行)              │
│  ├── routes.py (1609 行) ← 单体巨石, 55+ 端点    │
│  ├── dashboard_routes.py (2646 行) ← 最大单文件   │
│  ├── execute_reviewed_routes.py (1042 行)         │
│  └── 其余 18 个路由文件                           │
├──────────────────────────────────────────────────┤
│  业务层  (运行引擎 + 服务 + 工具, ~340 文件)     │
│  ├── runtime/ (25 文件) ← 核心引擎                │
│  ├── services/ (50+ 文件)                         │
│  ├── tools/ (130+ 文件) ← 最大模块               │
│  ├── planner/ (10 文件)                           │
│  ├── advisor/ (7 文件)                            │
│  └── nodes/ (5 文件) ← GPU 节点                  │
├──────────────────────────────────────────────────┤
│  安全层  (safety/ + runtime/path_safety.py)      │
├──────────────────────────────────────────────────┤
│  存储层  (文件系统 + SQLite, 无 ORM)             │
└──────────────────────────────────────────────────┘
```

### 1.3 规模数据

| 指标 | 数值 |
|------|------|
| 后端源文件 (.py) | **339 个** |
| 测试文件 | **258 个** |
| API 路由文件 | **21 个** |
| 总 API 路由代码行 | **~7,500 行** |
| 最大单文件 (dashboard_routes) | **2,646 行** |
| 注册节点数 | **80+** |
| 测试通过率 | **2,426 passed / 8 skipped / 0 failed** |

---

## 2. 十大核心问题

### 🔴 P0 — 严重问题（影响稳定性与可维护性）

#### 问题 1: 全局异常处理缺失 — 无声崩溃风险

**现象**:
- 所有路由端点使用相同的 try/except 模式：`except Exception as exc: raise HTTPException(status_code=400, detail=str(exc))`
- 任何未预期的异常（如数据库连接失败、文件系统满）都返回 HTTP 400
- 没有全局异常处理器区分业务错误 vs 系统错误
- 缺少错误码映射表（error_code → HTTP status → message）

**具体位置**:
```python
# routes.py 中重复出现 40+ 次的模式
try:
    ...
except HTTPException:
    raise
except Exception as exc:
    raise HTTPException(status_code=400, detail=str(exc))  # ← 所有错误都是 400！
```

**影响**: 
- 生产环境无法区分客户端错误 vs 服务端错误
- 前端无法根据错误码做差异化处理
- 调试困难，无法追踪问题根因

#### 问题 2: 文件系统状态存储无事务保障

**现象**:
- `state_store.py` 使用 `path.write_text()` 直接写入，不保证原子性
- 写入过程中崩溃会导致 JSON 文件损坏
- 多个 `ThreadPoolExecutor` 并发写入同一 run_id 目录，存在竞态条件
- 没有状态文件版本号，迁移困难

**具体位置**: `state_store.py:52` — `state_path.write_text(json.dumps(...))`

**影响**:
- 流水线执行过程中断电 → 状态文件损坏 → 运行状态丢失
- 并发写入可能产生部分 JSON 文件 → 前端解析失败

#### 问题 3: middleware 基础设施严重不足

**现象**:
- 仅使用 FastAPI 内置 `CORSMiddleware`
- 缺少：请求日志、请求 ID 追踪、响应时间监控、请求体大小限制、超时控制
- 速率限制有 `express-rate-limit` 的概念（在架构文档中），但 **未在后端实现**

**具体位置**: `main.py:36-47` — 只注册了 CORS

**影响**:
- API 被滥用时无保护
- 排查问题时无法追踪请求链路
- 性能瓶颈无法定位到具体端点

#### 问题 4: 配置管理三套体系并存

**现象**:
- `core/config.py` → `BackendSettings` (dataclass + 环境变量)
- `config/settings.py` → `ProjectSettings` (dataclass + YAML)
- `runtime/desktop_config.py` → 桌面配置 (JSON 文件)
- 三套机制之间没有统一的加载顺序、验证规则或优先级

**影响**:
- 配置冲突时行为不可预测
- 新成员难理解配置来源
- 类型不一致（项目配置用 dict，BackendSettings 用 dataclass）

### 🟠 P1 — 高优先级（影响扩展性）

#### 问题 5: routes.py 单体巨石 — 1609 行 55+ 端点

**现象**:
- `routes.py` 包含健康检查、Agent 执行、DPABI、GPU、流水线、重试、调度器、rs-fMRI QC、报告导出、SessionDB、Sandbox 等所有遗留端点
- 文件头部有注释代码表明已意识到问题（`# Domain-specific routers (extracted ... activate once old endpoints are removed)`），但迟迟未迁移
- 新增功能不断塞入此文件

**影响**:
- 代码审查困难（单个 PR 可能修改多个无关领域）
- 合并冲突频繁
- 测试覆盖难以按领域隔离

#### 问题 6: node_registry.py 无限增长 — 1361 行

**现象**:
- 80+ 节点直接在文件中注册
- 每次新增处理步骤都要修改此文件
- 没有插件机制、没有延迟加载、没有分类组织

**影响**:
- 新增团队/外部贡献者难以安全注册节点
- 启动时加载全部 80+ 节点，即使只需要 5 个
- 180+ 行 import 语句（第 8-80 行），依赖图复杂

#### 问题 7: 无 API 版本管理

**现象**:
- 所有端点路径为 `/api/...`，无版本前缀
- 破坏性 API 变更需要前后端同步发布
- 无法同时支持多个 API 版本（桌面端可能使用旧版本）

**影响**:
- 桌面端和 Web 端可能使用不同版本 API → 兼容性问题
- API 演进受限于向后兼容约束

#### 问题 8: 错误处理风格不统一

**现象**:
- **API 层**: 使用 `HTTPException` (异常风格)
- **Runtime 层**: 使用 return `{"status": "FAILED", "error": "..."}` (返回值风格)
- **Safety 层**: 使用 `MatlabSafetyResult` (Result 模式)
- 三种风格混用，调用方需要适配

```python
# API 层 — 异常抛出
raise HTTPException(status_code=400, detail=str(exc))

# Runtime 层 — 返回值字典
return {"status": "INVALID", "error": f"Failed to load project config: {exc}"}

# Safety 层 — Result 对象
return MatlabSafetyResult(ok=False, errors=[...])
```

**影响**:
- API 层调用 Runtime 时经常 `try/except` 包裹，代码冗余
- 无法统一处理错误日志、告警、恢复

### 🟡 P2 — 中优先级（改善质量）

#### 问题 9: 缺少结构化日志系统

**现象**:
- 整个后端没有使用 `logging` 模块或任何日志框架
- 错误信息散落在 HTTPException detail 和 return dict 中
- 无法按请求 ID 追踪、按级别过滤、按模块聚合

**影响**:
- 生产环境问题排查效率低
- 无法建立监控告警基线

#### 问题 10: 测试聚焦单元测试，缺少集成/E2E 测试

**现象**:
- 258 个测试文件中绝大部分是单元测试
- API 端点测试主要通过 mock 调用底层函数，不经过 FastAPI TestClient
- 没有端到端的 pipeline 执行集成测试
- 缺少前后端契约测试

**影响**:
- 重构 API 路由时无法验证前后端兼容性
- 流水线端到端回归需要手动验证

---

## 3. 目标架构蓝图

### 3.1 推荐架构模式: **分层微服务化单体 (Modular Monolith)**

鉴于团队规模和当前阶段（v0.5.x 研究平台），不建议拆分为分布式微服务。推荐 **模块化单体** 架构：保持单进程部署，但内部按领域严格分层。

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Rate     │ │ Request  │ │ Error    │ │ Auth (未来)      │   │
│  │ Limiter  │ │ ID Gen   │ │ Handler  │ │                  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     API Router Layer (v1)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │health    │ │pipeline  │ │dpabi     │ │rsfmri    ...     │   │
│  │router    │ │router    │ │router    │ │router           │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                   Dependency Injection Layer                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI Depends() → ServiceContainer                     │   │
│  │  - get_config()     - get_pipeline_executor()             │   │
│  │  - get_node_registry()  - get_state_store()               │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Application Layer                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐    │
│  │ Pipeline   │ │ Planner    │ │ Advisor    │ │ Agent     │    │
│  │ Domain     │ │ Domain     │ │ Domain     │ │ Domain    │    │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                     Infrastructure Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ State    │ │ Logging  │ │ Config   │ │ Security         │   │
│  │ Store    │ │ Service  │ │ Service   │ │ Service          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Storage Layer                                │
│  ┌──────────────────┐ ┌──────────────────┐                      │
│  │ AtomicFileStore   │ │ SQLiteSessionDB  │                      │
│  │ (事务 JSON 文件)  │ │ (FTS5 全文搜索)  │                      │
│  └──────────────────┘ └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 部署模式 | 模块化单体 | 避免分布式复杂度，团队规模和阶段不支持微服务 |
| API 版本 | `/api/v1/...` 前缀 | 为桌面端和 Web 端提供独立演进空间 |
| 配置管理 | 统一 ConfigService | 单一真相来源，环境变量 > YAML > 默认值 |
| 状态存储 | 原子文件写 + 版本号 | 最小改动获得事务保障 |
| 错误处理 | 统一 Exception Hierarchy | API 层用异常，Runtime 层逐步迁移 |
| 依赖注入 | FastAPI Depends() | 框架原生支持，零额外依赖 |
| 日志 | structlog (structured logging) | JSON 格式，支持请求追踪 |

---

## 4. 详细优化方案

### 4.1 🚨 P0-1: 建立全局异常处理体系

**目标**: 区分业务错误(4xx)和系统错误(5xx)，统一错误响应格式

**方案设计:**

```
src/backend/app/
├── core/
│   ├── config.py              # [已有]
│   ├── exceptions.py          # [新增] 异常层次结构
│   └── error_codes.py         # [新增] 错误码枚举
├── api/
│   ├── middleware/
│   │   └── error_handler.py   # [新增] 全局异常处理器
│   └── ...
```

**异常层次结构**:
```python
# core/exceptions.py [新建]
class MedImageError(Exception):
    """基础异常，携带错误码和 HTTP 状态码"""
    code: str          # 机器可读错误码
    status_code: int   # HTTP 状态码
    message: str       # 人类可读消息
    details: dict | None  # 可选的额外信息

class ConfigError(MedImageError):        # 400 — 配置错误
class PipelineError(MedImageError):      # 400 — 流水线错误  
class SafetyError(MedImageError):        # 403 — 安全拒绝
class NotFoundError(MedImageError):      # 404 — 资源不存在
class StateStoreError(MedImageError):    # 500 — 状态存储故障
class ExternalServiceError(MedImageError): # 502 — 外部服务故障
```

**全局异常处理器**:
```python
# api/middleware/error_handler.py [新建]
from fastapi import Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, MedImageError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "request_id": request.state.request_id,  # 来自 RequestIDMiddleware
            }
        )
    # 未预期的异常 → 500
    logger.exception("Unhandled exception")  # 结构化日志
    return JSONResponse(status_code=500, ...)
```

**收益**:
- 前端可根据 `error.code` 做精确处理（如 `PIPELINE_NODE_FAILED` → 展示重试按钮）
- 所有 500 错误自动记录完整堆栈
- 统一响应格式，消除 `{"detail": "..."}` 和 `{"error": "..."}` 混用

---

### 4.2 🚨 P0-2: 文件系统状态存储原子化改造

**目标**: 保证状态文件写入的原子性，支持并发安全

**方案设计**:
```
src/backend/app/runtime/
├── state_store.py      # [已有] 重构为 AtomicStateStore 类
├── atomic_file.py      # [新增] 原子文件写入工具
└── state_schema.py     # [新增] 状态文件版本管理
```

**原子写入机制**:
```python
# runtime/atomic_file.py [新建]
import json
import os
import tempfile
from pathlib import Path

def atomic_write_json(path: Path, data: dict, schema_version: int = 1):
    """原子写入 JSON：先写临时文件，再 rename（POSIX 原子操作）"""
    data_with_version = {"_schema_version": schema_version, **data}
    
    # Step 1: 写入同目录临时文件
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data_with_version, f, ensure_ascii=False, indent=2)
        # Step 2: 原子 rename（在 POSIX 系统上是原子的）
        os.replace(tmp_path, path)  # os.replace 是原子操作
    except Exception:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

**StateStore 类化**:
```python
# runtime/state_store.py [重构方案]
class StateStore:
    """有状态存储服务，保证写入原子性和并发安全"""
    
    SCHEMA_VERSION = 1
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        # 使用 threading.Lock 保护目录创建 + 写入的竞态
        self._locks: dict[str, threading.Lock] = {}
    
    def write_node_state(self, run_id: str, node_id: str, ...) -> Path:
        state_dir = self.work_dir / "states" / run_id
        state_dir.mkdir(parents=True, exist_ok=True)
        
        state_data = {
            "run_id": run_id,
            "node": node_id,
            "status": status,
            ...
        }
        
        state_path = state_dir / f"{node_id}.json"
        atomic_write_json(state_path, state_data, self.SCHEMA_VERSION)
        return state_path
    
    def read_node_state(self, run_id: str, node_id: str) -> dict:
        """读取节点状态，自动处理版本兼容"""
        state_path = self.work_dir / "states" / run_id / f"{node_id}.json"
        data = json.loads(state_path.read_text())
        return self._migrate_if_needed(data)
```

**收益**:
- 写入过程中崩溃 → 不会损坏现有文件
- 状态文件带上版本号 → 未来迁移可追溯
- 降低 ThreadPoolExecutor 并发写入风险

---

### 4.3 🚨 P0-3: 中间件基础设施补全

**目标**: 添加请求追踪、日志记录、速率限制、超时控制

**方案设计**:
```
src/backend/app/api/middleware/
├── __init__.py
├── request_id.py       # [新增] 请求 ID 注入
├── request_logging.py   # [新增] 请求/响应日志
├── rate_limiter.py      # [新增] 速率限制
└── error_handler.py     # [新增] 全局异常处理 (见 4.1)
```

**1. 请求 ID 中间件**:
```python
# api/middleware/request_id.py [新建]
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

**2. 请求日志中间件**:
```python
# api/middleware/request_logging.py [新建]
import time
import structlog

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=getattr(request.state, "request_id", None),
        )
        return response
```

**3. 速率限制**:
```python
# api/middleware/rate_limiter.py [新建]
# 使用 slowapi 库 (基于 limits + redis/内存)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# 在 main.py 中注册
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**在 main.py 中注册顺序**:
```python
def create_app() -> FastAPI:
    app = FastAPI(...)
    
    # 顺序很重要：内→外 (最先添加的最外层)
    app.add_middleware(RequestIDMiddleware)        # 1. 注入 request_id
    app.add_middleware(RequestLoggingMiddleware)   # 2. 记录日志
    app.add_middleware(CORSMiddleware, ...)        # 3. CORS
    # RateLimiter 通过 slowapi 的 limiter 装饰器注入
    
    # 注册全局异常处理器
    app.add_exception_handler(Exception, global_exception_handler)
    
    return app
```

**收益**:
- 每个请求可通过 `X-Request-ID` 全链路追踪
- 自动记录所有 API 调用的响应时间
- 防止 API 滥用（尤其是重计算端点如流水线执行）

---

### 4.4 🚨 P0-4: 统一配置管理

**目标**: 单一配置加载入口，类型安全，启动时验证

**方案设计**:
```
src/backend/app/core/
├── config.py              # [重构] ConfigService — 统一入口
├── config_schema.py        # [新增] Pydantic 配置模型
└── config_sources.py       # [新增] 配置源 (YAML/ENV/JSON)
```

**统一配置模型**:
```python
# core/config_schema.py [新建]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class RuntimeConfig(BaseModel):
    work_dir: str
    log_dir: str
    derivatives_dir: str = "./derivatives"
    report_dir: str = "./reports"
    matlab_command: str = "matlab"

class ThirdPartyConfig(BaseModel):
    spm_dir: str
    dpabi_dir: str

class SafetyConfig(BaseModel):
    rawdata_readonly: bool = True
    require_confirmation: bool = True

class ProjectConfig(BaseModel):
    """统一项目配置，Pydantic 自动验证"""
    runtime: RuntimeConfig
    third_party: ThirdPartyConfig
    safety: SafetyConfig = SafetyConfig()
    source_path: str = ""

class ServerConfig(BaseSettings):
    """服务器配置，支持环境变量"""
    model_config = {"env_prefix": "MEDIMAGE_"}
    
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    desktop: bool = False
    matlab_enabled: bool = False
    log_level: str = "INFO"

class AppConfig(BaseModel):
    """顶层配置聚合"""
    server: ServerConfig
    project: ProjectConfig | None = None  # 项目配置可选（CLI 模式不需要）
```

**ConfigService**:
```python
# core/config.py [重构方案]
class ConfigService:
    """统一配置服务 — 单一加载入口
    
    加载顺序 (由低到高优先级):
    1. 代码默认值
    2. YAML 项目配置文件
    3. 环境变量 (MEDIMAGE_*)
    """
    
    def __init__(self, project_config_path: str | None = None):
        self.server = ServerConfig()  # 从环境变量加载
        
        if project_config_path:
            self.project = ProjectConfig.from_yaml(project_config_path)
        else:
            self.project = None
    
    @classmethod
    def from_yaml(cls, path: str) -> "ConfigService":
        return cls(project_config_path=path)
```

**收益**:
- Pydantic 自动验证所有字段类型和必填项
- 配置变更只需改 schema，IDE 有自动补全
- 环境变量优先级明确，调试方便

---

### 4.5 🟠 P1-5: routes.py 拆分 — 完成遗留端点迁移

**现状**: `routes.py` (1609 行) 中有 55+ 个端点，注释代码表明已提取的 domain router 还未激活

**问题定位**:
```python
# main.py 第 7-9 行的注释
# from src.backend.app.api.dpabi_routes import router as dpabi_router     # ← 已创建！
# from src.backend.app.api.rsfmri_routes import router as rsfmri_router   # ← 已创建！
# from src.backend.app.api.agent_routes import router as agent_router     # ← 已创建！
```

```python
# main.py 第 49 行
app.include_router(router)  # ← 这个是 routes.py 的整块巨石，包含所有遗留端点
```

**拆分方案**:
```
当前状态:
routes.py (1609 行) — 包含 55+ 端点，覆盖 8 个领域

目标状态:
routes.py → 只保留 /health 和 /api/project-config (2 个通用端点)
├── agent_routes.py     → Agent 执行/计划/重试/调度器 (已创建，未激活)
├── dpabi_routes.py     → DPABI 能力/脚手架/预检/沙箱 (已创建，未激活)
├── rsfmri_routes.py    → rs-fMRI QC/报告导出/验证 (已创建，未激活)
├── gpu_routes.py       → [新建] GPU 检测/基准测试
├── pipeline_routes.py  → [新建] 流水线执行/运行检查
└── session_routes.py   → [新建] SessionDB 查询
```

**迁移步骤（不修改代码，仅规划）**:
1. 对 `routes.py` 中每个端点标注归属领域
2. 确认已创建的 domain router (agent/dpabi/rsfmri) 端点是否与 routes.py 重复
3. 创建缺失的 domain router (gpu/pipeline/session)
4. 在 `main.py` 中去掉 `app.include_router(router)` (routes.py)，替换为各 domain router
5. 删除 routes.py 中已迁移的端点
6. 运行全量测试确认无路由冲突

---

### 4.6 🟠 P1-6: Node Registry 插件化改造

**目标**: 支持节点按领域分类、延迟加载、外部注册

**方案设计**:
```
src/backend/app/runtime/
├── node_registry.py          # [重构] 轻量 Registry 类
├── node_registry/
│   ├── __init__.py           # [新增] 自动发现
│   ├── base.py               # [新增] NodeRunner 协议
│   ├── core_nodes.py         # [新建] 核心节点 (data_inspector, matlab_check 等)
│   ├── spm_nodes.py          # [新建] SPM 节点
│   ├── dpabi_nodes.py        # [新建] DPABI 节点
│   ├── gpu_nodes.py          # [新建] GPU 节点
│   ├── rsfmri_nodes.py       # [新建] rs-fMRI 处理节点
│   └── qc_nodes.py           # [新建] QC 节点
```

**NodeRunner 协议**:
```python
# runtime/node_registry/base.py [新建]
from typing import Protocol, Any

class NodeRunner(Protocol):
    """节点运行器协议 — 不强制继承，满足接口即可"""
    
    @property
    def node_id(self) -> str: ...
    
    def run(self, context: "NodeExecutionContext") -> dict[str, Any]: ...

class NodeRegistry:
    """可扩展的节点注册中心"""
    
    def __init__(self):
        self._runners: dict[str, NodeRunner] = {}
    
    def register(self, runner: NodeRunner) -> None:
        """注册节点运行器"""
        if runner.node_id in self._runners:
            raise ValueError(f"Duplicate node: {runner.node_id}")
        self._runners[runner.node_id] = runner
    
    def get(self, node_id: str) -> NodeRunner:
        """获取节点运行器"""
        if node_id not in self._runners:
            raise KeyError(f"Unknown node: {node_id}")
        return self._runners[node_id]
    
    def list_nodes(self) -> list[str]:
        return sorted(self._runners.keys())
```

**自动发现**:
```python
# runtime/node_registry/__init__.py [新建]
# 通过模块导入自动注册（不使用 pkg_resources 扫描，可控）
from .core_nodes import register_core_nodes
from .spm_nodes import register_spm_nodes
from .dpabi_nodes import register_dpabi_nodes
from .gpu_nodes import register_gpu_nodes
from .rsfmri_nodes import register_rsfmri_nodes
from .qc_nodes import register_qc_nodes

def create_registry() -> NodeRegistry:
    registry = NodeRegistry()
    register_core_nodes(registry)
    register_spm_nodes(registry)
    register_dpabi_nodes(registry)
    register_gpu_nodes(registry)
    register_rsfmri_nodes(registry)
    register_qc_nodes(registry)
    return registry
```

**收益**:
- 新增节点只需在自己领域的文件中添加，不影响其他模块
- 按需加载（只导入需要的领域模块）
- 类型安全（Protocol 保证接口一致性）

---

### 4.7 🟠 P1-7: API 版本化

**目标**: 所有 API 端点使用 `/api/v1/` 前缀，支持多版本共存

**方案**:
```python
# main.py [重构方案]
def create_app() -> FastAPI:
    app = FastAPI(...)
    
    # 所有路由统一加 v1 前缀
    v1_prefix = "/api/v1"
    
    app.include_router(health_router, prefix=v1_prefix)
    app.include_router(pipeline_router, prefix=v1_prefix)
    app.include_router(dpabi_router, prefix=v1_prefix)
    # ...
    
    return app
```

**过渡期兼容**:
```python
# 短期方案：同时挂载 /api/ 和 /api/v1/ 指向同一路由
app.include_router(router, prefix="/api")       # 旧路径，标记 deprecated
app.include_router(router, prefix="/api/v1")    # 新路径
```

**收益**:
- 未来 `/api/v2/` 可做破坏性变更而不影响 v1 客户端
- 桌面端可渐进升级

---

### 4.8 🟠 P1-8: 统一错误处理风格

**目标**: API 层统一使用异常，Runtime 层逐步迁移到 Result 模式

**推荐**: API 层保持异常抛出（FastAPI 原生），Runtime 层采用 **Result[T, E]** 模式

```python
# core/result.py [新建]
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")

class Ok(Generic[T]):
    def __init__(self, value: T):
        self._value = value
    def unwrap(self) -> T:
        return self._value
    def is_ok(self) -> bool:
        return True

class Err(Generic[E]):
    def __init__(self, error: E):
        self._error = error
    def unwrap_err(self) -> E:
        return self._error
    def is_ok(self) -> bool:
        return False

type Result[T, E] = Ok[T] | Err[E]
```

**API 层转换**:
```python
# API 路由中统一转换
@router.post("/api/v1/pipeline/execute")
def execute_pipeline(request: ExecuteRequest):
    result = pipeline_service.execute(request)
    match result:
        case Ok(summary):
            return {"ok": True, "data": summary}
        case Err(error):
            raise error.to_http_exception()  # 转为 HTTPException
```

---

### 4.9 🟡 P2-9: 结构化日志系统

**目标**: 使用 structlog 实现请求级别的结构化日志

**依赖添加**: `structlog` (零额外依赖，纯 Python)

```python
# core/logging_config.py [新建]
import structlog
import logging

def setup_logging(level: str = "INFO"):
    """配置结构化日志"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),  # 开发环境
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 配置标准库 logging → structlog
    logging.basicConfig(format="%(message)s", level=level)
```

**使用示例**:
```python
logger = structlog.get_logger()

# 在路由中
logger.info("pipeline_started", run_id=run_id, pipeline_id=pipeline_id)

# 在运行时中
logger.error("node_execution_failed", node_id=node.id, subject=subject, error=str(exc))
```

---

### 4.10 🟡 P2-10: 集成测试补充策略

**目标**: 添加 API 级别的集成测试和流水线端到端测试

**方案**:
```
tests/
├── unit/                    # [现有] 单元测试
├── integration/
│   ├── api/                 # [新增] API 集成测试 (FastAPI TestClient)
│   │   ├── test_health.py
│   │   ├── test_pipeline_routes.py
│   │   └── ...
│   └── pipeline/            # [新增] 流水线端到端测试
│       ├── test_synthetic_pipeline.py
│       └── conftest.py      # 共享 fixture (setup/teardown)
└── contract/                # [新增] 前后端契约测试
    └── test_api_contract.py # OpenAPI schema vs 前端期望
```

**API 集成测试示例**:
```python
# tests/integration/api/test_health.py [新建]
from fastapi.testclient import TestClient
from src.backend.app.main import create_app

def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["status"] == "healthy"
    assert "version" in data
```

---

## 5. 实施路线图

### Phase 1: 基础补齐（预计 2-3 周）

> 不改业务逻辑，只补基础设施

| 序号 | 任务 | 涉及文件 | 风险 |
|------|------|---------|------|
| 1.1 | 建立异常层次结构 | `core/exceptions.py` (新增) | 低 — 新文件 |
| 1.2 | 添加全局异常处理器 | `api/middleware/error_handler.py` (新增) | 低 |
| 1.3 | 添加 RequestID + 日志中间件 | `api/middleware/` (新增 2 文件) | 低 |
| 1.4 | 配置 structlog | `core/logging_config.py` (新增) | 低 |
| 1.5 | 创建原子文件写入工具 | `runtime/atomic_file.py` (新增) | 低 |
| 1.6 | 创建统一 ConfigService | `core/config.py` (重构) + `core/config_schema.py` (新增) | 中 — 多处引用需更新 |
| 1.7 | 添加速率限制 | `api/middleware/rate_limiter.py` (新增) | 低 |

### Phase 2: 结构调整（预计 2-3 周）

> 重构现有代码，不改功能

| 序号 | 任务 | 涉及文件 | 风险 |
|------|------|---------|------|
| 2.1 | 完成 routes.py 拆分，激活 domain routers | `routes.py`, `main.py`, `dpabi_routes.py`, `rsfmri_routes.py`, `agent_routes.py` | 中 — 需确认无路由冲突 |
| 2.2 | 重构 StateStore 为类，使用原子写入 | `runtime/state_store.py`, `runtime/atomic_file.py` | 中 — 调用方需适配 |
| 2.3 | API 添加 `/api/v1/` 前缀 | `main.py` | 中 — 前端需同步更新 |
| 2.4 | 统一 API 层错误处理（替换所有 try/except 为统一异常） | 21 个路由文件 | 高 — 量大，需分批 |
| 2.5 | Node Registry 按领域拆分 | `runtime/node_registry.py` → 7 文件 | 中 — import 路径变更 |

### Phase 3: 增强优化（预计 2-3 周）

> 提升质量和开发体验

| 序号 | 任务 | 涉及文件 | 风险 |
|------|------|---------|------|
| 3.1 | 引入 FastAPI Depends() 依赖注入 | `api/` 路由文件 | 中 — 渐进式迁移 |
| 3.2 | 添加 API 集成测试 | `tests/integration/api/` (新增) | 低 |
| 3.3 | 添加流水线端到端测试 | `tests/integration/pipeline/` (新增) | 中 — 需要测试数据 |
| 3.4 | 异常迁移：Runtime 层使用统一异常 | `runtime/` 所有文件 | 高 — 调用链长 |

---

## 6. 风险与依赖

### 6.1 关键风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| routes.py 拆分导致路由冲突 | API 返回 404/500 | 先运行全量测试确认端点列表，逐一迁移 |
| ConfigService 重构破坏下游 | 配置加载失败 | 保留旧的 `from_yaml()` 作为兼容层 |
| API 版本前缀导致前端 404 | 桌面端/Web 端不可用 | 过渡期同时挂载 `/api/` 和 `/api/v1/` |
| StateStore 原子写入改变行为 | 状态文件路径变化 | 增加 schema_version，旧文件可继续读取 |

### 6.2 外部依赖

| 库 | 用途 | 版本 | 影响 |
|-----|------|------|------|
| structlog | 结构化日志 | >=24.1 | 零额外依赖，纯 Python |
| slowapi | 速率限制 | >=0.1.9 | 轻量，依赖 limits |
| pydantic-settings | 环境变量配置 | >=2.0 | 官方推荐，替换手写 env 读取 |

### 6.3 不变更项（明确排除）

- ❌ `pipeline_executor.py` 核心执行逻辑 — 不在本次优化范围
- ❌ `approval_gate.py` 审批门机制 — 安全关键路径，不动
- ❌ `path_safety.py` 路径安全检查 — 已有充分防护
- ❌ `tool_registry.py` 工具权限注册表 — 设计合理
- ❌ `data/` 和 `rawdata/` — 只读数据，永不修改
- ❌ 前端代码 — 架构审查范围仅限后端

---

## 附录 A: 文件影响范围

### 将新增的文件（Phase 1-3）

```
src/backend/app/
├── core/
│   ├── exceptions.py              # Phase 1
│   ├── error_codes.py             # Phase 1
│   ├── config_schema.py           # Phase 1
│   ├── logging_config.py          # Phase 1
│   └── result.py                  # Phase 2
├── api/
│   └── middleware/
│       ├── __init__.py            # Phase 1
│       ├── request_id.py          # Phase 1
│       ├── request_logging.py     # Phase 1
│       ├── rate_limiter.py        # Phase 1
│       └── error_handler.py       # Phase 1
├── runtime/
│   ├── atomic_file.py             # Phase 1
│   ├── state_schema.py            # Phase 2
│   └── node_registry/
│       ├── __init__.py            # Phase 2
│       ├── base.py                # Phase 2
│       ├── core_nodes.py          # Phase 2
│       ├── spm_nodes.py           # Phase 2
│       ├── dpabi_nodes.py         # Phase 2
│       ├── gpu_nodes.py           # Phase 2
│       ├── rsfmri_nodes.py        # Phase 2
│       └── qc_nodes.py            # Phase 2
tests/
├── integration/
│   ├── api/                       # Phase 3
│   └── pipeline/                  # Phase 3
└── contract/                      # Phase 3
```

### 将修改的文件（Phase 1-3）

```
src/backend/app/
├── main.py                        # Phase 1, 2 — 中间件注册，路由版本化
├── core/config.py                 # Phase 1 — ConfigService 重构
├── config/settings.py             # Phase 1 — 迁移到 core/config_schema.py
├── runtime/
│   ├── state_store.py             # Phase 2 — StateStore 类化
│   ├── node_registry.py           # Phase 2 — 插件化拆分
│   └── desktop_config.py          # Phase 1 — 纳入 ConfigService
├── api/
│   ├── routes.py                  # Phase 2 — 拆分清理
│   ├── _shared.py                 # Phase 2 — 统一错误处理
│   └── *.py (21 路由文件)         # Phase 2 — 替换 try/except 为统一异常
```

---

## 附录 B: 代码质量对比

| 指标 | 当前状态 | Phase 1 后 | Phase 3 后 |
|------|---------|-----------|-----------|
| 全局异常处理 | ❌ 无 | ✅ 分层异常体系 | ✅ 完整 |
| 请求追踪 | ❌ 无 | ✅ X-Request-ID | ✅ 全链路 |
| 结构化日志 | ❌ 无 | ✅ structlog | ✅ 含 metrics |
| 配置管理 | ⚠️ 3 套 | ✅ 统一 ConfigService | ✅ Pydantic 验证 |
| API 版本化 | ❌ 无 | — | ✅ /api/v1/ |
| 状态原子性 | ❌ 无 | ✅ 原子写入 | ✅ 事务保障 |
| 速率限制 | ❌ 无 | ✅ slowapi | ✅ 分级限制 |
| 依赖注入 | ❌ 无 | — | ✅ FastAPI Depends |
| 节点注册 | ⚠️ 单文件 1361 行 | — | ✅ 插件化 7 文件 |
| 集成测试 | ❌ 无 | — | ✅ API + E2E |

---

> **声明**: 本报告仅提供架构分析和优化建议，不包含任何代码修改。所有实施方案需经过团队评审和测试验证后方可执行。
