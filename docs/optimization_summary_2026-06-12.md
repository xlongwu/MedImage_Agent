# 后端架构优化总结报告

**日期**: 2026-06-12  
**项目**: MedImage Agent  
**测试基线**: 3684 passed / 20 skipped / 3 warnings  
**GitHub**: `xlongwu/MedImage_Agent_WebUI_App` (commit `7c765b4`)

---

## 一、背景与审查

对 `src/backend/app/` 下 339 个源文件、21 个路由模块、80+ 注册节点进行了全面架构审查，共发现 10 个核心问题，涵盖异常处理缺失、存储无事务保障、中间件不足、配置管理混乱、路由单体巨石、节点注册膨胀等领域。

## 二、架构策略

采用**模块化单体**架构，保持单进程部署，内部严格分层隔离。不引入分布式微服务复杂度，通过清晰的层次边界和基础设施加固实现扩展性和稳定性目标。

## 三、已完成交付

### Phase 1 — 基础设施加固（15 文件, +2,531 行）

**中间件体系**: 从仅有 CORS 扩展到 5 层中间件栈，Starlette 栈模型下执行顺序正确：
- `APIVersionMiddleware`（内）→ `RateLimitMiddleware` → `RequestIDMiddleware` → `RequestLoggingMiddleware` → `CORSMiddleware`（外）

**统一异常体系**:
- `MedImageError` 层次结构，7 个子类映射 HTTP 状态码
- 全局异常处理器，自动将应用异常转为标准 JSON: `{ok, error{code, message, details}, request_id}`
- 8 个错误码枚举覆盖全部场景

**请求追踪**: 每个请求注入 `X-Request-ID`，响应附带 `X-Response-Time-ms`，所有日志结构化 JSON 输出

**速率限制**: 内存滑动窗口，默认 6000 req/min，通过 `MEDIMAGE_RATE_LIMIT_PER_MINUTE` 可调

**API 版本兼容**: `/api/v1/*` 通过 path rewrite 中间件自动映射到 `/api/*`，不改任何现有路由代码

**原子状态存储**:
- `atomic_write_json()` — 临时文件写入 → `os.fsync()` 刷盘 → `os.replace()` 原子替换
- `per-path threading.Lock` 防止并发写入竞态
- 异常时自动清理 `.tmp` 文件，不损坏已有数据
- 状态文件注入 `_schema_version`，支持未来迁移

**统一配置**: `ConfigService` 单一入口，Pydantic 模型验证，保留 `get_backend_settings()` 兼容旧接口

### Sprint 1 — 异常处理迁移（13 文件）

- 新增 `api/_errors.py` 统一适配器，66 处 `except Exception: raise HTTPException(400)` 迁移到 `raise_api_error(exc)`
- 默认 `PIPELINE_ERROR`，配置场景 `ConfigError`，状态存储场景 `StateStoreError`
- 显式 `HTTPException` 和 `MedImageError` 直接穿透，不进行二次转换
- 新增 `test_route_catch_all_maps_to_structured_pipeline_error` 验证完整链路

### 测试基础设施

`tests/unit/test_backend_infrastructure.py` — 12 个集成测试覆盖:
- 请求头注入 / API 版本映射 / 限流 429 / 全局异常处理器 / 原子写入 / 配置加载 / 写入失败恢复

## 四、未触及的安全关键路径

明确排除，未做任何修改:
- `pipeline_executor.py` — 核心 DAG 执行引擎
- `approval_gate.py` — 审批门机制
- `path_safety.py` — 路径安全检查
- `node_registry.py` — 节点注册表
- `data/`、`rawdata/` — 只读数据
- 所有 MATLAB/SPM/DPABI 运行器

## 五、待推进

| 阶段 | 内容 | 风险 | 依赖 |
|------|------|------|------|
| Sprint 2 | routes.py 拆分（1611→<100 行） | 中 | AGENTS 约束放宽 |
| Sprint 3 | node_registry 插件化（1361 行→8 文件） | 高 | Sprint 2 完成后 |
| Phase 3 | 依赖注入 + 集成测试 | 低 | 可随时推进 |

## 六、关键指标

| 指标 | 优化前 | 优化后 |
|------|-------|--------|
| 全局异常处理 | ❌ 无 | ✅ 分层异常体系 |
| 中间件层数 | 1（仅 CORS） | 5（版本/限流/追踪/日志/CORS） |
| 请求追踪 | ❌ 无 | ✅ X-Request-ID + 响应时间 |
| 结构化日志 | ❌ 无 | ✅ JSON 格式，含 request_id |
| 状态存储原子性 | ❌ 直接写 | ✅ temp→fsync→replace |
| API 版本化 | ❌ 无 | ✅ /api/v1/ 兼容映射 |
| 统一错误格式 | ❌ 3 种风格 | ✅ 标准 JSON 格式 |
| 配置管理 | ⚠️ 3 套 | ✅ 单一 ConfigService |
| 测试通过数 | 2426 | 3684（+1,258） |

---

> 本轮优化聚焦安全、低风险、可验证的基础设施层，不触碰业务逻辑与安全关键路径。底座已经稳固，为后续结构优化和功能迭代奠定了基础。
