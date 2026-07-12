# CPU 多线程并行预处理实施方案

**Status:** Ready for Implementation

**Task Mode:** Scientific Validation Mode

**Version:** v1.0

**Date:** 2026-07-12

**Primary target:** Windows 桌面端、Python 原生 rs-fMRI 全预处理

## 1. Scope Anchor

### 1.1 目标

在不改变预处理公式、产物结构、审批门、原始数据只读边界和能力真实性的前提下，将当前“多个受试者依次执行”的原生预处理改造为资源受控的 CPU 并行执行，并改善长任务的进度可见性。

本方案沿用用户习惯中的“CPU 多线程”名称，但实现必须区分两类并行：

- **受试者级 CPU 密集计算使用多进程**，绕开 Python GIL；
- **NumPy/SciPy 底层线程受控使用**，避免多个进程内再次启动大量 BLAS/OpenMP 线程造成过度订阅。

### 1.2 必须完成

- 多受试者注册输入可通过受控 `ProcessPoolExecutor` 并行执行。
- 单受试者内部阶段顺序和 DAG 依赖保持不变。
- 每个子进程仅写自己的 `<batch_run_dir>/<subject_id>/`。
- 父进程独占批次清单、验证报告和最终报告的汇总写入。
- 提供 `serial`、`process`、`auto` 三种 CPU 调度模式，默认初期仍为 `serial`，验证通过后才允许把 `auto` 作为产品默认值。
- 工作进程数同时受 CPU、可用内存、受试者数和配置上限约束。
- 在 `process/auto` 模式下，worker 数、每 worker 的底层线程预算、内存预留和任务提交节奏必须由运行时资源规划器自动计算；用户配置只作为上限、下限或显式覆盖，不作为所有机器通用的固定执行值。
- 自动计算必须同时考虑受试者数量、每个 BOLD 的空间维度和时间点数、启用阶段、当前系统负载、实时可用内存以及同机其他 MedImage 任务。
- 长任务必须暴露批次、受试者、阶段、时间和心跳进度，不能一直只显示 `Executing...`。
- 子进程异常、进程池破裂、内存不足和应用关闭必须产生真实的 partial/failed 状态，不能伪报成功。
- 并行与串行运行的数值产物、状态、校验和策略和溯源字段必须可比较。

### 1.3 禁止事项

- 不修改 DICOM、BIDS、NIfTI 源数据或 `rawdata/`。
- 不调用 MATLAB、SPM、DPABI 或任意自由形式外部命令。
- 不在多个进程中并发写同一个 JSON、报告或产物路径。
- 不使用线程池直接并行当前逐体素 Python ReHo 循环。
- 不同时启用“受试者多进程”和“单受试者 ReHo 多进程”两层嵌套进程池。
- 不以“运行未抛异常”代替数值等价验证。
- 不把中间元数据或 planned 状态报告为 computed/succeeded。

### 1.4 成功标准

- [ ] 三受试者批次至少出现两个真实并发的受试者工作进程。
- [ ] `max_subject_workers=1` 与现有串行行为兼容。
- [ ] 三受试者真实数据墙钟时间相对串行基线至少降低 35%；目标为降低 50% 以上，但目标值不是科学正确性的放行条件。
- [ ] dry-run 和正式运行均输出资源决策报告，说明探测值、估算值、最终 worker/thread 数及每个限制因素。
- [ ] 相同样本在低内存、高 CPU 占用和空闲机器三种环境下能够选择不同的安全并行度。
- [ ] 并行和串行的所有数值 NIfTI 可重载，shape、dtype、affine 一致。
- [ ] 确定性阶段满足逐阶段定义的数值容差；离散清单、状态和路径集合完全一致。
- [ ] 任意受试者失败不会破坏其他受试者已经完成的产物。
- [ ] 父进程最终汇总中 subject_count、artifact_count、blocked/failed/warning 列表准确。
- [ ] 前端能够看到每个受试者的当前阶段和最后心跳时间。
- [ ] 原始数据执行前后校验保持不变。

## 2. 当前证据

| 事实 | 代码锚点 | 结论 |
|---|---|---|
| 注册转换输入会展开为多个 `NativeFullPreprocRequest` | `src/backend/app/services/native_preproc_full.py:369-439` | 已有稳定的受试者拆分边界 |
| 当前批处理按 `for subject_request` 串行执行 | `src/backend/app/services/native_preproc_full.py:719-760` | 主要墙钟时间瓶颈位于批次调度层 |
| 每个受试者已有独立输出目录 | `src/backend/app/services/native_preproc_full.py:738-744` | 可安全形成进程隔离写入边界 |
| 批次汇总由父层统一生成 | `src/backend/app/services/native_preproc_full.py:553-716` | 并行任务不应直接写批次汇总 |
| 单受试者 runner 按固定阶段顺序执行 | `src/backend/app/native_preproc/orchestrator/runner.py:548-1159` | 单受试者内部不得无序并发阶段 |
| 当前 ReHo CPU 实现是逐空间体素三重循环 | `src/backend/app/tools/reho_compute.py:25-90` | Python 线程不能有效消除该瓶颈 |
| 请求模型当前没有 CPU 调度参数 | `src/backend/app/schemas/native_preproc_api.py:26-64` | 需要显式、可审阅的资源策略字段 |
| 响应模型已有受试者阶段结果聚合基础 | `src/backend/app/schemas/native_preproc_api.py:67-108` | 可兼容扩展进度和资源统计 |
| 已有注册批次回归测试 | `tests/unit/test_native_preproc_registered_batch.py` | 必须扩展而不能另建平行批处理路径 |
| 原生预处理已有单元、集成、golden 测试矩阵 | `tests/unit/test_native_preproc_registered_batch.py`, `tests/integration/test_native_preproc_artifact_integrity.py`, `tests/golden/test_native_preproc_reference_comparison.py` | 并行改造必须复用现有科学验证 |

### 2.1 真实测试基线

当前三受试者 DemoData 的完整 DPARSFA-like 测试显示：

- 单个受试者约需要一小时；
- ReHo 是占比最高的 CPU 阶段，单受试者曾观测约 57 分钟；
- 后台在 ReHo 期间持续占用一个 CPU 核，但不会持续写文件；
- 前端只显示 `Executing...` 和 dry-run 的 `planned` 行，无法区分“正在计算”和“挂起”。

该基线只用于性能比较，不进入稳定代码或便携溯源中的绝对本机路径。

## 3. 目标架构

```text
Reviewed native request
  -> registered subject expansion
  -> resource planner
       -> serial mode
       -> process mode (bounded subject workers)
  -> one sequential native runner per subject process
  -> per-subject manifest + progress events
  -> parent-only batch aggregation
  -> validation/final report
```

### 3.1 并行粒度决策

第一阶段只开放**受试者级多进程**：

- 一个工作进程负责一个受试者的完整阶段链；
- 同一受试者的 slice timing、realignment、normalization、ReHo 等保持串行；
- 项目级 group summary、validation report、final report 在所有受试者结束后由父进程生成；
- 不复用 `runtime/pipeline_executor.py` 的线程池来执行 CPU 密集原生预处理，因为当前服务已有独立的批次聚合和产物契约。

第二阶段才评估单受试者 ReHo 的分块向量化。只有在受试者数量为 1 或资源规划器选择单受试者模式时，才允许考虑 ReHo 内部分块并行，且不得形成嵌套进程池。

### 3.2 自适应工作进程计算

资源规划器不得使用“固定 2 个 worker”一类机器无关默认值。它先对输入和机器建立快照，再计算候选并行度：

**数据侧输入：**

- 受试者数、session/run 数；
- BOLD shape、timepoints、dtype 和压缩状态；
- 是否启用 T1、normalization、smoothing、ALFF/fALFF、ReHo、atlas/FC；
- 每阶段内存放大系数和最近一次同 shape/config 的实测峰值；
- 尚未开始、运行中和已完成的受试者数量。

**机器侧输入：**

- 逻辑/物理核心数、当前系统 CPU 利用率和可调度核心预算；
- 总内存、实时 available memory、页面文件压力；
- Electron、backend 和其他项目任务的当前占用；
- 当前进程已有的 BLAS/OpenMP 线程配置；
- 电源模式或系统明确报告的降频/资源限制（可获得时）。

建议计算模型：

```text
pending_subjects = total_subjects - completed_subjects - running_subjects
usable_cpu = max(1, available_logical_cpu - adaptive_cpu_reserve)
usable_memory = max(0, available_memory - adaptive_memory_reserve)

cpu_limited_workers = floor(usable_cpu / estimated_cpu_threads_per_subject)
memory_limited_workers = floor(usable_memory / estimated_peak_bytes_per_subject)

workers = clamp(
  min(pending_subjects, cpu_limited_workers, memory_limited_workers, user_ceiling_if_any),
  lower=1,
  upper=validated_hard_safety_ceiling
)
```

其中：

- `estimated_peak_bytes_per_subject` 优先使用相同机器指纹、pipeline profile、shape bucket 的历史高分位峰值；没有历史时由输入大小乘各启用阶段的保守工作集模型计算；
- `adaptive_cpu_reserve` 根据当前前台负载和核心数计算，确保桌面 UI 与操作系统仍有响应能力；
- `adaptive_memory_reserve` 根据总内存、当前 available memory 和内存压力计算，不使用固定百分比覆盖所有机器；
- `validated_hard_safety_ceiling` 只是防止配置失控的发布保护上限，不是日常 worker 数；
- 用户可设置 `max_subject_workers`，但该值仅是 ceiling，规划器仍可因资源不足选择更小值；
- 没有可靠探测数据、估算结果不可信或资源压力过高时回退到串行；
- 对本次约 950 MB/受试者的观测只作为历史估算样本，不作为其他数据和机器的固定内存值。

### 3.3 动态调度与反馈修正

进程池容量和实际提交节奏分离：

- 进程池可以按本轮最大安全容量创建，但父进程只在资源令牌充足时提交新受试者；
- 每个受试者完成后读取真实峰值 RAM、CPU 时间和阶段耗时，更新本次运行估算；
- 若实际峰值显著超过估算，后续不再填满原并行度；
- 若系统出现持续高内存压力、页面换入换出或前台 CPU 饱和，暂停提交新受试者，但不粗暴终止已经运行的科学阶段；
- 若机器资源恢复，允许在安全上限内重新增加后续任务并行度；
- 自适应调整只改变调度资源，不改变 TR、滤波频段、FWHM、ReHo 邻域、回归变量等科学参数。

### 3.4 底层线程预算

Windows spawn 子进程启动前，根据 `usable_cpu / active_workers` 自动计算 `threads_per_worker`，再通过 `threadpoolctl` 或进程启动环境应用并记录：

```text
OMP_NUM_THREADS=<calculated_threads_per_worker>
OPENBLAS_NUM_THREADS=<calculated_threads_per_worker>
MKL_NUM_THREADS=<calculated_threads_per_worker>
NUMEXPR_NUM_THREADS=<calculated_threads_per_worker>
VECLIB_MAXIMUM_THREADS=<calculated_threads_per_worker>
```

逐体素 Python ReHo 不会因为 BLAS 线程增加而受益，应由阶段能力表声明 `useful_native_threads=1`；FFT、线性代数等阶段可以使用经基准验证的线程范围。资源规划器按当前阶段能力动态收紧线程预算，不能继承不可控的机器环境值。

### 3.5 进度模型

新增运行级原子状态文件或状态存储记录：

- `queued/running/succeeded/partial/failed/cancel_requested/cancelled`；
- subject_id、stage_id、stage_status；
- started_at、updated_at、heartbeat_at、finished_at；
- completed_subjects/total_subjects；
- completed_stages/total_stages；
- worker_pid、worker_count、调度模式；
- 当前阶段已知时的 processed/total；未知时至少有心跳；
- error_code、error_message 和最后完成的可恢复边界。

状态写入必须使用 `atomic_write_json()` 或已有状态存储，不得让多个子进程直接覆盖同一文件。工作进程通过父进程队列上报事件，由父进程持久化。

## 4. API 与状态契约调整

### 4.1 请求扩展

在 `NativeFullPreprocRequest` 增加经过校验的结构化资源策略，建议使用嵌套模型而不是继续增加松散字典：

```python
class NativeCpuExecutionPolicy(BaseModel):
    mode: Literal["serial", "process", "auto"] = "serial"
    max_subject_workers: int | None = Field(default=None, ge=1)
    cpu_threads_per_worker: int | None = Field(default=None, ge=1)
    memory_budget_bytes: int | None = Field(default=None, ge=1)
    reserve_cpu_threads: int | None = Field(default=None, ge=0)
    adaptive_replanning: bool = True
```

`None` 表示交由资源规划器计算；显式值表示用户 ceiling/override，仍需通过硬安全边界。兼容性规则：旧请求没有 `cpu_policy` 时必须保持当前串行行为；当用户选择 process/auto 但没有填写资源参数时必须自动计算。

### 4.2 响应扩展

响应和 manifest 增加：

- `execution_backend="cpu"`；
- `scheduler_mode`；
- `worker_count_requested/used`；
- `worker_count_calculated`、`threads_per_worker_calculated`；
- `calculation_inputs`、`limiting_factors`、`replan_events`；
- `started_at/finished_at/runtime_seconds`；
- `progress_url`；
- `subject_execution` 摘要；
- `resource_warnings`；
- 每个阶段实际 backend 和 runtime_seconds。

### 4.3 后台任务边界

当前同步 HTTP 请求会导致前端直到完整执行结束才收到新状态。实施时应将执行提交与状态查询拆开：

1. 审批后的 execute 端点创建运行并立即返回 `running` 与 run_id；
2. 后台任务管理器执行批次；
3. GET run/progress 端点读取持久化状态；
4. 前端定时轮询并渲染实时阶段；
5. 重启后仍可读取最后已持久化状态，不能永久停留在按钮本地的 `Executing...`。

## 5. Implementation Ledger

### Phase A：基线、模型与资源规划器

#### A.1 固化串行性能和科学基线

- **文件：** 扩展 `tests/benchmark/`，新增不进入默认 CI 的真实/中型合成基准。
- **工作：** 记录逐阶段墙钟、CPU 时间、峰值内存、产物数、输出校验和。
- **DoD：** 生成机器可读 JSON 和 Markdown 摘要；不记录私有绝对数据路径。

#### A.2 增加 CPU 资源策略 schema

- **文件：** `src/backend/app/schemas/native_preproc_api.py`。
- **工作：** 增加结构化 policy、范围验证和旧请求兼容。
- **DoD：** 非法 worker 数或内存比例在进入执行层前被拒绝。

#### A.3 新建资源规划器

- **建议文件：** `src/backend/app/native_preproc/orchestrator/resource_planner.py`。
- **工作：** 基于实时 CPU/内存、受试者数、BOLD shape/timepoints、启用阶段、历史峰值和显式上限计算 worker/thread/内存令牌；输出可审计决策。
- **DoD：** 无探测信息、低内存、高系统负载、单受试者、不同 shape 和超大配置均有确定且不同的合理决策。

#### A.4 建立机器与工作负载指纹

- **建议文件：** `src/backend/app/native_preproc/orchestrator/resource_profile.py`。
- **工作：** 用匿名机器能力、pipeline profile、shape bucket、dtype 和阶段集合关联历史运行指标；不保存私有绝对路径。
- **DoD：** 历史数据仅改善估算，过期/版本变化/异常样本不会直接控制新运行。

### Phase B：受试者级多进程

#### B.1 提取可 pickling 的顶层工作函数

- **文件：** `src/backend/app/services/native_preproc_full.py` 或新建窄职责 worker 模块。
- **工作：** 只传 JSON 可序列化请求、project_id/project_dir 和独立输出目录；子进程内重建 Pydantic 请求。
- **DoD：** Windows spawn 和打包 sidecar 都能启动；不能捕获不可序列化闭包、数据库连接或 logger handler。

#### B.2 改造 `_run_registered_batch`

- **文件：** `src/backend/app/services/native_preproc_full.py:719-760`。
- **工作：** 保留 serial 分支；process/auto 分支使用有界进程池和 `as_completed`；结果最终按原始 subject_id 稳定排序。
- **DoD：** 一个 worker 异常被转换为该受试者 failed 响应；父进程继续收集其余结果。

#### B.3 防止并发写冲突

- **文件：** 批次服务、artifact registry、report/manifest 写入相关测试。
- **工作：** 子进程只写 subject 目录；父进程独占 batch root 聚合；已有文件遵守 overwrite policy。
- **DoD：** 并发压力测试不存在损坏 JSON、临时文件残留或交叉受试者产物。

#### B.4 控制 BLAS/OpenMP 线程

- **文件：** sidecar 启动/worker 初始化模块及溯源。
- **工作：** 在科学库执行前应用动态线程预算；按阶段能力收紧或释放；记录计算依据和最终值。
- **DoD：** 任意 worker 数都不会各自扩张到全部逻辑核心，且不同机器/负载可得到不同线程预算。

#### B.5 运行中自适应重规划

- **工作：** 父进程维护 CPU/内存令牌，受试者结束后使用真实资源指标修正后续提交节奏。
- **DoD：** 故障注入造成内存压力时并行度下降；资源恢复后可增加待提交任务；运行中科学参数不变化。

### Phase C：进度、心跳与安全停止

#### C.1 运行状态事件模型

- **建议文件：** `src/backend/app/native_preproc/orchestrator/progress.py`。
- **工作：** 定义事件 schema、父进程队列、原子状态快照和心跳。
- **DoD：** ReHo 长时间无产物写入时仍每 5-10 秒更新心跳。

#### C.2 异步执行与查询 API

- **文件：** `src/backend/app/api/preprocessing_routes.py`、服务、schema、API 测试。
- **工作：** 提交后快速返回；提供运行详情和进度查询；错误使用结构化领域异常。
- **DoD：** Electron/浏览器请求不会因小时级同步响应而看似冻结。

#### C.3 前端实时进度

- **文件：** `src/frontend/src/lib/api/preprocessing.ts`、`PreprocessingReviewedFlow.tsx` 及测试。
- **工作：** 按 run_id 轮询；展示受试者/阶段/心跳/耗时；页面刷新后恢复监控。
- **DoD：** 不再用 dry-run 的 planned 表格冒充执行中实时状态。

#### C.4 取消语义

- **工作：** 首版只做协作式“阶段边界取消”；正在运行的不可中断 NumPy/SciPy 调用完成后停止后续阶段。
- **DoD：** UI 明确显示 `cancel_requested`，不声称瞬时取消；已完成产物保留并标为 partial/cancelled。

### Phase D：CPU ReHo 专项优化

#### D.1 建立精确基准

- **文件：** `tests/unit/test_native_preproc_reho.py`、`tests/golden/`、新 benchmark。
- **工作：** 覆盖 7/19/27 邻域、并列值、常量信号、掩膜、NaN、边界体素和真实尺寸。
- **DoD：** 当前 `compute_reho_numpy` 成为冻结参考实现。

#### D.2 分块向量化候选实现

- **建议文件：** `src/backend/app/tools/reho_compute_vectorized.py`。
- **工作：** 按 z 块构建邻域，严格实现 average rank 与 tie correction；限制峰值内存。
- **DoD：** 全部 golden 和并列值测试通过；未通过前能力等级保持 experimental。

#### D.3 后端选择

- **工作：** `reference` 与 `vectorized` 显式选择，auto 仅在验证通过后启用。
- **DoD：** provenance 记录算法 ID、版本、chunk size、dtype 和 fallback 原因。

### Phase E：打包、发布与回归

- 验证 PyInstaller/Windows spawn 支持，防止递归启动 sidecar。
- 更新 sidecar hidden imports 和依赖检查（如新增 `psutil` 或其他资源探测依赖必须显式批准）。
- 执行 unpacked 构建和真实三受试者冒烟。
- 仅在串行/并行科学等价与异常恢复验证均通过后，才允许默认 `auto`。

## 6. Blast Radius Map

| 表面 | 预计影响 | 风险 |
|---|---|---|
| `services/native_preproc_full.py` | 批次调度主入口 | 高 |
| `native_preproc/orchestrator/runner.py` | 阶段事件与取消检查 | 高 |
| `schemas/native_preproc_api.py` | 请求、响应和状态契约 | 中高 |
| artifact registry / atomic state | 并发安全 | 高 |
| preprocessing routes | 异步提交和查询 | 中高 |
| frontend preprocessing workspace | 实时监控 | 中 |
| PyInstaller sidecar | Windows spawn/依赖 | 高 |
| 科学 kernels | Phase D ReHo 优化 | 高 |

安全解耦表面：DICOM 转换执行、MATLAB/SPM/DPABI 外部工具、原始数据目录和其他项目域不得因本方案改变行为。

## 7. Hazards & Mitigations

| H-ID | 风险 | 缓解措施 | 验证 |
|---|---|---|---|
| H-CPU-01 | Python 线程受 GIL 限制 | CPU 密集受试者使用进程池 | CPU 利用率和墙钟基准 |
| H-CPU-02 | 内存随 worker 数放大 | 内存预算、上限、低内存回退 | 模拟低内存与真实峰值测试 |
| H-CPU-03 | BLAS/OpenMP 过度订阅 | 子进程线程数显式限制 | 进程/线程观测测试 |
| H-CPU-04 | Windows spawn/PyInstaller 递归启动 | 顶层 worker、freeze 支持、打包冒烟 | unpacked sidecar 多进程测试 |
| H-CPU-05 | 多进程写同一 manifest | subject 独立目录，父进程唯一聚合者 | 并发压力与 JSON 重载测试 |
| H-CPU-06 | 结果完成顺序不稳定 | 聚合前按输入 subject_id 排序 | 稳定顺序单元测试 |
| H-CPU-07 | 单受试者失败破坏批次 | 捕获每个 future，生成 failed child response | 一失败两成功集成测试 |
| H-CPU-08 | 强制关闭留下永远 running | 心跳、启动恢复审计、stale 状态转 interrupted | 模拟崩溃恢复测试 |
| H-CPU-09 | 并行结果数值漂移 | 串行参考、逐阶段容差、产物重载 | golden/集成等价测试 |
| H-CPU-10 | 取消误导用户 | 只承诺阶段边界协作取消 | 长阶段取消状态测试 |
| H-CPU-11 | 嵌套进程池耗尽资源 | 第一阶段禁止嵌套；资源规划器单一所有者 | 配置拒绝测试 |
| H-CPU-12 | 旧客户端不兼容 | 缺省策略保持 serial | 旧 payload API 回归 |
| H-CPU-13 | 启动时资源快照很快过期 | 提交前复检、运行中令牌和重规划 | 动态负载变化测试 |
| H-CPU-14 | 历史峰值低估新数据 | shape/stage 指纹、高分位估计、安全余量 | 工作负载突增测试 |
| H-CPU-15 | 自适应调度频繁震荡 | 滞回区间、最短调整周期、只影响待提交任务 | 抖动负载测试 |
| H-CPU-16 | 自动优化误改科学参数 | 资源参数和科学参数 schema 分离 | 请求/manifest 合同测试 |

## 8. Test & Validation Plan

### 8.1 新增测试

| 测试 | 类型 | 验证内容 |
|---|---|---|
| CPU policy schema tests | unit | 范围、默认串行、旧请求兼容 |
| resource planner tests | unit | CPU/内存/受试者约束和回退 |
| adaptive planner tests | unit | 样本规模、shape、实时负载、历史峰值和滞回 |
| registered batch process tests | unit/integration | 多进程、稳定聚合、部分失败 |
| concurrent artifact tests | integration | 无交叉写入、JSON 可重载 |
| progress heartbeat tests | unit/integration | 长阶段持续心跳、崩溃状态 |
| serial/process equivalence | scientific integration | 数值、shape、affine、状态和产物集合 |
| packaged process smoke | packaging | Windows sidecar 可安全 spawn |
| three-subject benchmark | manual benchmark | 墙钟、CPU、峰值内存、吞吐 |

### 8.2 必须运行的验证命令

```powershell
python -m pytest tests/unit/test_native_preproc_registered_batch.py --tb=short --basetemp=.pytest_tmp
python -m pytest tests/unit -k native_preproc --tb=short --basetemp=.pytest_tmp
python -m pytest tests/integration -k native_preproc --tb=short --basetemp=.pytest_tmp
python -m pytest tests/golden/test_native_preproc_reference_comparison.py --tb=short --basetemp=.pytest_tmp
python -m pytest --tb=short --basetemp=.pytest_tmp
npm --prefix src/frontend run typecheck
npm --prefix src/frontend run test
npm --prefix src/frontend run build
```

另需执行：sidecar 构建、Electron unpacked 构建、打包后多进程启动冒烟、三受试者串行/并行对照。构建成功不得替代真实工作流成功。

### 8.3 数值判定

- 离散字段、路径角色、artifact type、shape、dtype、affine：完全一致；
- 确定性 CPU 算法原则上要求相同；如底层并行归约导致浮点顺序变化，必须为每个阶段单独给出基于参考误差分析的容差；
- ReHo 并列秩、有效体素集合和边界处理必须与冻结参考一致；
- 任何容差都不得只为通过失败测试而临时放宽。

## 9. Proof Obligations

| 声明 | 验证方式 |
|---|---|
| 并行仅发生在受试者层 | 检查调度器与 stage runner 调用图 |
| 子进程不写批次根清单 | 路径所有权测试和写入审计 |
| 旧请求仍串行 | API 兼容测试 |
| 并行产物科学等价 | golden + 串行/并行真实产物比较 |
| 前端显示真实执行状态 | API 状态迁移和前端轮询测试 |
| 原始数据未修改 | 前后 checksum 比较 |
| 进程数受内存控制 | 资源规划器决策记录与压力测试 |
| 自动参数因样本与机器变化 | 多机器能力和多 workload 合成矩阵测试 |
| 自动调整不改变科学参数 | 请求、stage 参数和 provenance 比较 |

## 10. Assumption Registry

| A-ID | 假设 | 分类 | 影响 |
|---|---|---|---|
| A-CPU-01 | 受试者之间没有共享可变科学状态 | VERIFIED | 若错误则不能安全并行 |
| A-CPU-02 | 当前首要瓶颈是受试者串行和 CPU ReHo | VERIFIED（真实测试） | 决定优化优先级 |
| A-CPU-03 | Windows 桌面 sidecar 使用 spawn 语义 | VERIFIED | 决定 worker 必须可 pickling |
| A-CPU-04 | worker/thread 数应由当前 workload 与资源快照计算，用户值仅作上限或覆盖 | USER DECISION | 需要完整资源规划器与可解释输出 |
| A-CPU-05 | 默认行为在验证前保持 serial | CRITICAL | 防止未经验证的执行语义改变 |

## 11. 实施顺序与放行门

1. A 基线与资源模型；
2. B 受试者多进程，但默认 serial；
3. C 异步进度与阶段边界取消；
4. 串行/并行科学等价审核；
5. E Windows 打包和真实数据基准；
6. 通过后开放用户选择 process/auto；
7. D ReHo 向量化作为独立科学验证子任务；
8. 所有门通过后再评估将 auto 设为默认。

**CPU 并行方案不依赖 GPU 方案。GPU 方案应复用本方案的运行状态、资源规划和前端进度模型。**

## 12. 未完成项与风险声明

本文档是实施方案，不代表 CPU 并行已经实现或验证。当前已运行的真实数据结果仍来自串行 CPU 路径。实施过程中若需要修改未列出的受保护模块，必须说明必要性、补充回归测试并在完成报告中列出兼容性和科学影响。
