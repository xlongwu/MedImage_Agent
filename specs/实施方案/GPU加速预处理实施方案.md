# GPU 加速预处理实施方案

**Status:** Ready for Implementation

**Task Mode:** Scientific Validation Mode

**Version:** v1.0

**Date:** 2026-07-12

**Primary target:** NVIDIA CUDA / CuPy 可选后端，Windows 桌面端

**Reference validation device:** NVIDIA GeForce RTX 4060 Laptop GPU，8 GB VRAM

## 1. Scope Anchor

### 1.1 目标

在原生 Python 预处理保持唯一工作流入口的前提下，为适合矩阵、FFT、卷积和分块体素计算的阶段增加可审阅、资源受控、可回退、可验证的 GPU 后端。GPU 不得成为独立的旁路流水线，也不得跳过现有审批、状态、产物、溯源和安全边界。

### 1.2 首批目标阶段

按风险和收益分级开放：

| 级别 | 阶段 | 原因 | 初始状态 |
|---|---|---|---|
| Tier 1 | ALFF/fALFF | 体素时间序列 FFT，已有 CuPy/PyTorch 计算候选 | 优先接入 CuPy |
| Tier 1 | temporal filtering | 批量 FFT/频域掩膜，已有 CuPy 计算候选 | 优先接入 CuPy |
| Tier 1 | nuisance regression | 大型矩阵回归，已有 CuPy 计算候选 | 优先接入 CuPy |
| Tier 1 | functional connectivity | ROI/seed 矩阵运算，已有 CuPy 计算候选 | 数据规模足够时启用 |
| Tier 2 | spatial smoothing | 3D 卷积，适合 `cupyx.scipy.ndimage` | 新增并验证 |
| Tier 2 | atlas resampling | 插值/标签重采样 | 仅 nearest-neighbor 标签语义验证后开放 |
| Tier 2 | ReHo | 当前最大耗时阶段 | 必须先补齐严格并列秩校正 |
| Deferred | realignment/coregistration/normalization | 优化目标、插值和仿射估计科学风险高 | 本方案首轮不开放 |
| CPU only | I/O、BIDS 校验、报告、审批和审计 | GPU 收益低或属于控制面 | 保持 CPU |

### 1.3 必须完成

- 生产 GPU 后端统一选择 CuPy，不将 PyTorch 作为首轮桌面打包依赖。
- 请求必须显式选择 `cpu`、`gpu` 或 `auto`；初始默认 `cpu`。
- `auto` 允许 GPU 不可用/OOM 时回退 CPU，并必须在状态与溯源中明确记录。
- `gpu` 表示 require_gpu；GPU 不可用或数值安全条件不满足时必须阻断，不能静默回退。
- 每个阶段记录实际 backend、设备、驱动/CUDA/CuPy、dtype、chunk、显存峰值、耗时和 fallback 原因。
- 每个 GPU 产物必须通过 reload、shape、dtype、affine、有限值和 CPU 参考比较。
- 同一 GPU 的重计算并发由资源令牌规划器动态决定；当阶段工作集接近显存容量时通常会收紧为一个任务，轻量阶段和更大显存设备则可在验证上限内提高并发。
- GPU 并发数、每阶段 chunk、显存预算和 CPU/GPU 选择不得写死；应根据受试者数量、输入 shape/timepoints、阶段工作集、当前空闲显存、GPU 利用率、同机任务和历史实测自动计算。
- 自动规划只调整计算资源，不得自动修改 TR、频段、FWHM、ReHo 邻域、atlas、回归变量等科学参数。
- 原始数据继续只读；输出仅写项目衍生目录。
- CPU 后端始终保留，且是 GPU 科学验证的参考路径。

### 1.4 禁止事项

- 不直接开放当前 scaffold-only GPU runner 为 computed/succeeded。
- 不把当前缺少 average ranks/tie correction 的 GPU ReHo 作为正式 ReHo。
- 不使用随机抽样“未发现 ties”作为完整数据科学等价证明。
- 不依赖 MATLAB、SPM、DPABI、FSL 或 AFNI。
- 不允许任意 device 字符串、任意输出路径、多 GPU 自动扩张或无限显存分配。
- 不在 GPU OOM 后保留半写产物并报告成功。
- 不因 GPU 更快而放宽算法定义、掩膜规则或状态真实性。

### 1.5 成功标准

- [ ] Tier 1 每个阶段有 CPU/GPU 独立实现比较、产物重载和溯源测试。
- [ ] `backend=cpu` 完全保持当前原生工作流行为。
- [ ] `backend=auto` 在无 CuPy、无 CUDA、显存不足或计算异常时安全回退并明确警告。
- [ ] `backend=gpu` 不允许静默回退。
- [ ] RTX 4060 8 GB 实机可完成三受试者流程，无 OOM、无设备锁泄漏。
- [ ] dry-run 返回每阶段自动计算的 backend、chunk、显存预算、并发令牌、估算耗时和限制因素。
- [ ] 同一输入在 GPU 空闲、显存被占用和小规模数据三种情况下可以分别选择不同的安全策略。
- [ ] Tier 1 组合在真实数据上相对对应 CPU 阶段达到可测量加速；单阶段数据搬运成本高于计算时可合理保持 CPU。
- [ ] ReHo 只有在严格 ties 测试和 golden 比较通过后才能从 experimental 进入 computed。
- [ ] 并行和 GPU 调度不会造成 CPU/GPU 过度订阅。
- [ ] Electron unpacked 包能检测 GPU、执行受控 GPU 冒烟并在无 GPU 机器回退 CPU。

## 2. 当前证据

| 事实 | 代码/文档锚点 | 结论 |
|---|---|---|
| GPU 规范最初仅将 ALFF/fALFF 定义为 MVP | `specs/规范/科学计算/GPU加速规范.md` | 扩展阶段必须分批验证 |
| CuPy 仍是 optional 且未默认安装 | `requirements-optional.txt` | 打包和依赖策略尚未完成 |
| ALFF 已有 CuPy 和 Torch 计算内核 | `src/backend/app/tools/alff_compute.py:74-218` | 生产首选应统一为 CuPy |
| temporal filtering 已有 CuPy backend | `src/backend/app/tools/temporal_filtering_compute.py:66-168` | 可作为 Tier 1 |
| nuisance regression 已有 CuPy backend | `src/backend/app/tools/nuisance_regression_compute.py:69-181` | 可作为 Tier 1 |
| FC 已有 CuPy backend 与 CPU fallback | `src/backend/app/tools/functional_connectivity_compute.py:115-242` | 可接入原生 stage，但小 ROI 需先判断收益 |
| 当前原生 ReHo 固定调用严格 CPU kernel | `src/backend/app/native_preproc/stages/reho.py:15,61` | 这是现有 canonical 路径 |
| GPU ReHo 省略 tie correction | `src/backend/app/tools/reho_compute.py:169-288` | 目前不能宣称与 CPU 等价 |
| ReHo backend 明确在 ties 风险时回退 CPU | `src/backend/app/tools/reho_compute.py:325-418` | 正式接入前必须消除概率性安全门 |
| 五个 GPU subject runner 目前明确 scaffold-only | `src/backend/app/tools/gpu_alff_runner.py:149`、`gpu_reho_runner.py:122`、`gpu_temporal_filtering_runner.py:120`、`gpu_functional_connectivity_runner.py:125`、`gpu_nuisance_regression_runner.py:144` | 不得只改状态字段就开放 |
| 现有 GPU guard 限制 auto/cpu/cuda:0 | `src/backend/app/safety/gpu_safety.py:60-125` | 可复用但需要 CuPy 实际设备信息 |
| 现有内存 guard 是静态元素/字节上限 | `src/backend/app/safety/gpu_safety.py:182-256` | 需升级为基于实时空闲显存和阶段工作集 |
| GPU consistency 测试已有 ALFF、FC、ReHo 框架 | `tests/test_scientific_gpu_consistency.py` | 必须扩展而非重复建立验证体系 |
| 请求/响应目前只有统一 `native_python` backend | `src/backend/app/schemas/native_preproc_api.py:26-108` | 需增加显式后端策略和实际阶段 backend |

## 3. 架构决策

### 3.1 单一原生工作流，多计算后端

```text
Native stage
  -> validated backend policy
  -> capability + resource preflight
  -> canonical CPU or validated CuPy kernel
  -> common artifact writer
  -> common QC + provenance + registry
  -> CPU/GPU validation record
```

GPU 不创建另一套 stage graph，不使用现有 GPU node runner 旁路原生流水线。每个原生 stage 仍负责输入验证、产物命名、保存、QC、artifact registration 和状态真实性，只将纯数值核心委托给 backend-neutral kernel。

### 3.2 后端策略

建议 schema：

```python
class NativeComputePolicy(BaseModel):
    backend: Literal["cpu", "gpu", "auto"] = "cpu"
    device: Literal["auto", "cuda:0"] = "auto"
    precision: Literal["float32", "float64"] = "float32"
    gpu_memory_budget_bytes: int | None = Field(default=None, ge=1)
    max_gpu_jobs: int | None = Field(default=None, ge=1)
    chunk_size: int | None = Field(default=None, ge=1)
    allow_cpu_fallback: bool = True
    adaptive_replanning: bool = True
    stage_backends: dict[str, Literal["cpu", "gpu", "auto"]] = Field(default_factory=dict)
```

约束：

- `backend=cpu`：不导入 CuPy，不探测 CUDA；
- `backend=auto`：通过 capability、显存、算法安全和预计收益检查后选择 GPU；否则 CPU，并记录原因；
- `backend=gpu`：等价于 require_gpu，失败即该阶段 blocked/failed；
- `gpu_memory_budget_bytes`、`max_gpu_jobs`、`chunk_size` 为 `None` 时自动计算；显式值是用户 ceiling/override，仍受安全门约束；
- `stage_backends` 只允许已注册阶段 ID，未知键拒绝；
- 首轮不允许 frontend 发送任意 kernel 名、CUDA 参数或自由形式代码。

### 3.3 CuPy 作为首选依赖

生产桌面首轮只选择 CuPy：

- 覆盖 ndarray、FFT、线性代数和 `cupyx.scipy.ndimage`；
- 避免同时打包 PyTorch 带来的体积、CUDA 运行库和双后端差异；
- 与现有多数 GPU compute 模块一致；
- PyTorch 内核保留为实验或测试候选，不进入首轮默认安装。

CuPy 版本必须与目标 CUDA runtime 明确匹配，不能使用 `latest`。桌面打包必须记录 wheel 版本、CUDA runtime、驱动要求和打包后 DLL 清单。

### 3.4 自适应资源调度

GPU 规划器每次准备进入 GPU 阶段时采集：

- 待处理受试者数、input shape/timepoints/dtype；
- 阶段类型、临时数组数量、FFT/排序/卷积/线性代数工作集模型；
- `memGetInfo()` 的实时 free/total VRAM、GPU utilization、已有 GPU 任务；
- CUDA context 和 CuPy memory pool 当前占用；
- 主机可用内存和数据传输规模；
- 相同 device、stage、shape bucket 的历史 cold/warm 耗时与峰值显存。

自动计算模型：

```text
usable_vram = free_vram - adaptive_vram_reserve - active_context_overhead
estimated_stage_peak(chunk) = input_buffers + output_buffers + temporary_factor(stage, chunk)

chunk = largest_valid_chunk(
  estimated_stage_peak(chunk) <= usable_vram,
  bounded_by=user_chunk_ceiling_if_any
)

gpu_job_tokens = floor(usable_vram / high_percentile_stage_peak)
active_gpu_jobs = min(
  pending_gpu_subjects,
  gpu_job_tokens,
  utilization_limited_jobs,
  user_job_ceiling_if_any,
  validated_hard_safety_ceiling
)
```

- 对单块 GPU，首轮验证可能经常计算出一个 active job，但这必须是显存、利用率和阶段工作集共同推导的结果，而不是固定常量；
- CPU 多进程调度器可以准备输入或处理 CPU-only stage，进入 GPU 阶段前必须获得 GPU 资源令牌；
- 使用进程间 GPU device lock，而不是只使用进程内计数；
- 每个 kernel 在分配前根据 `cp.cuda.runtime.memGetInfo()` 获取实时空闲显存；
- 预算使用预计峰值而不是仅输入数组大小，包含邻域展开、FFT 复数数组、排序索引、输出和安全余量；
- 显存预留根据当前桌面显示占用、CUDA context、近期峰值误差和系统压力计算；固定比例只可作为探测失败时的保守兜底和发布硬上限；
- OOM 后清理内存池和临时引用；auto 可回退 CPU，require_gpu 返回结构化错误。

### 3.5 自适应 CPU/GPU 选择

`backend=auto` 不以“存在 CUDA”作为唯一条件。规划器估算：

```text
predicted_gpu_total = context_warmup + host_to_device + gpu_compute + device_to_host
predicted_cpu_total = cpu_compute_under_current_load
```

只有在以下条件同时满足时才选择 GPU：

- GPU kernel 已达到该阶段要求的 validation level；
- 自动 chunk 可在显存预算内成立；
- 预测 GPU 总耗时相对 CPU 有超过测量噪声和安全裕量的收益；
- 当前 GPU 队列等待不会抵消加速；
- require_gpu/用户 stage override 与安全策略一致。

真实完成后将 cold/warm、传输、compute 和峰值显存反馈给本机性能模型。模型按算法版本、CuPy/CUDA/driver、device、shape bucket 和 stage 参数隔离；代码或环境变化时旧样本失效。

### 3.6 可变显存策略

- 8 GB RTX 4060 是当前验证设备，不是硬编码运行前提；4D BOLD 的 z-slice/voxel chunk 必须由实时可用显存和阶段工作集反推；
- ReHo 不一次性构造全脑 `(voxels, 27, timepoints)`；
- FFT 阶段按空间块处理，输出可在 CPU 侧预分配；
- float32 为性能默认，但必须与 CPU 参考比较；需要 float64 的阶段由能力表显式声明；
- 每阶段完成后释放 CuPy 内存池缓存，记录峰值。

### 3.7 自动计算的边界

允许自动调整：backend、worker/GPU job 数、chunk、批次提交节奏、显存/RAM 预算和经验证的底层线程数。

禁止自动调整：TR、slice order、滤波频段、FWHM、回归变量、scrubbing 阈值、ReHo 邻域、atlas/template、插值语义和算法版本。precision 只能在该阶段 CPU/GPU 两种精度均通过独立科学验证后作为受审阅策略选择，不能因显存不足静默从 float64 降为 float32。

## 4. 阶段迁移设计

### 4.1 Tier 1A：ALFF/fALFF

- 选定 `alff_compute.py` 为共享数值 source of truth；
- 统一 CPU/CuPy 的 detrend、FFT 归一化、频段掩膜和零分母语义；
- 原生 `alff_falff` stage 调用 backend selector，不重复公式；
- 输出仍由原生 stage 写 NIfTI 和 provenance；
- 验证 constant、zero denominator、Nyquist、短时间序列、NaN 和不同 TR。

### 4.2 Tier 1B：Temporal filtering

- 统一 CPU/CuPy frequency grid、passband 边界和逆 FFT 实数处理；
- 不把数据传输时间排除在用户可见 runtime 之外；
- 当数据体量不足、预计 GPU 无收益时 auto 保持 CPU；
- 验证频率混合信号、边界频率、低时间点和重载结果。

### 4.3 Tier 1C：Nuisance regression

- 设计矩阵仍由 CPU 的受审阅逻辑构造；GPU 只执行数值线性代数；
- CPU/GPU 必须使用一致的 rank-deficiency、伪逆/rcond、scrubbing 和常量列处理；
- 记录 design matrix checksum、rank、condition 指标和实际 dtype；
- 对病态矩阵或 GPU 求解失败，auto 回退 CPU，gpu 模式明确失败。

### 4.4 Tier 1D：Functional connectivity

- ROI 提取、空 ROI 和 label 语义保持原生 stage 权威；
- GPU 计算相关矩阵、Fisher-Z 和可选 seed map；
- 空/常量 ROI 的 warning 必须与 CPU 一致，不能用零替代掩盖；
- 小 ROI 数时 auto 可选择 CPU，避免传输开销大于计算收益。

### 4.5 Tier 2A：Smoothing 与 Atlas resampling

- smoothing 使用与 CPU 相同的 FWHM->sigma、边界模式和只处理空间轴规则；
- atlas labels 强制 nearest-neighbor，不允许线性插值制造新标签；
- 连续模板/图像与离散 atlas 必须使用不同 interpolation policy；
- affine、输出 grid、voxel size 和标签集合必须严格验证。

### 4.6 Tier 2B：严格 ReHo GPU

当前 CuPy ReHo 使用 double argsort 产生普通秩，且分母没有完整 ties correction。正式实现必须：

1. 对每个邻域体素的时间序列计算 average ranks；
2. 精确计算每个 judge 的 `sum(t_i^3 - t_i)`；
3. 使用与 CPU `_kcc_numpy` 相同的 Kendall W 分子和分母；
4. 对 7/19/27 邻域、掩膜、非有限值、边界和常量序列保持一致；
5. 使用确定性的 chunk 顺序，不以随机抽样决定是否安全；
6. 对 ties-heavy fixture、量化信号和真实 BOLD 做全体素比较；
7. 在完全验证前保持 `experimental`，原生 stage 继续使用 CPU canonical kernel。

ReHo 是最可能获得显著加速的阶段，也是科学风险最高的首批 GPU 目标，必须作为独立交付包审核。

## 5. API、状态与溯源

### 5.1 请求与干跑

dry-run 必须返回每阶段：

- requested_backend；
- selected_backend；
- gpu_available/cupy_available；
- estimated_input_bytes/peak_bytes；
- chunk strategy、chunk calculation inputs；
- current free/total VRAM、GPU utilization、queue estimate；
- predicted_cpu_seconds/predicted_gpu_seconds；
- gpu_jobs_calculated、limiting_factors；
- fallback_allowed；
- blocking issues；
- validation level。

### 5.2 运行状态

复用 CPU 并行方案中的异步 run/progress 模型，增加：

- device_name/device_id；
- gpu stage queue；
- allocated/peak VRAM；
- transfer/compute/total runtime；
- fallback event；
- GPU heartbeat。

### 5.3 Provenance

每个 GPU 科学产物至少记录：

- algorithm_id/version；
- CPU reference algorithm/version；
- requested/actual backend；
- fallback reason；
- CuPy、CUDA runtime、driver、device；
- dtype、chunk、memory policy；
- 输入/输出 checksum；
- 参数、TR、频段、atlas/mask identity；
- numerical validation status 与 tolerance；
- warnings 和 runtime metrics。

不能把本机私有绝对路径写入可移植 provenance；使用项目相对路径或稳定 artifact ID。

## 6. Implementation Ledger

### Phase A：依赖、能力和资源防护

#### A.1 冻结目标工具链

- **文件：** requirements/packaging 配置、发布文档。
- **工作：** 选择与目标 CUDA 匹配的有界 CuPy 版本；记录 RTX 4060 验证环境。
- **DoD：** 开发环境和 packaged sidecar 均能执行 CuPy allocation/FFT 冒烟；无 GPU 环境可正常启动 CPU 模式。

#### A.2 升级 GPU capability 与 guard

- **文件：** `src/backend/app/safety/gpu_safety.py`、`src/backend/app/tools/gpu_utils.py`。
- **工作：** 使用 CuPy 实际 device count、memGetInfo、利用率和设备属性；保留 device allowlist；实现跨任务资源令牌与 device lock。
- **DoD：** OOM、无驱动、错误 DLL、锁冲突、显存不足和 GPU 繁忙都有稳定错误码及自动重规划路径。

#### A.3 增加 compute policy schema

- **文件：** `src/backend/app/schemas/native_preproc_api.py` 及 API tests。
- **工作：** 后端、设备、精度、内存比例和 stage overrides 均结构化校验。
- **DoD：** 旧客户端仍默认 CPU；自由形式参数无法进入 kernel。

#### A.4 建立自适应 GPU 规划器

- **建议文件：** `src/backend/app/native_preproc/orchestrator/gpu_resource_planner.py`。
- **工作：** 根据 workload、实时 VRAM/利用率、历史 stage profile 和用户 ceiling 计算 backend、chunk、GPU job 令牌和预测耗时。
- **DoD：** 不同 shape、受试者数、可用显存和 GPU 占用能够产生不同且可解释的决策；探测失败时保守回退。

#### A.5 建立性能反馈模型

- **工作：** 保存去路径化的机器/算法/workload 指纹与 cold/warm 指标，使用高分位显存峰值校正后续估算。
- **DoD：** 模型版本化、可失效、可清除；历史数据不会绕过安全门或改变科学参数。

### Phase B：共享 kernel 接口

#### B.1 定义 backend-neutral result

- **建议文件：** `src/backend/app/native_preproc/core/compute_backend.py`。
- **字段：** ok、backend、array(s)、warnings/errors、runtime、transfer time、memory、fallback、validation metadata。
- **DoD：** 原生 stages 不依赖 CuPy array，公共边界返回 NumPy 或标准 artifact payload。

#### B.2 统一产物写入

- **工作：** CPU/GPU 共用原生 stage 的 NIfTI、QC、registry 和 provenance 写入。
- **DoD：** 不存在 GPU 专用产物目录绕开当前 run manifest。

### Phase C：逐阶段开放 Tier 1

按照以下顺序，每个阶段独立完成“kernel -> stage -> API -> tests -> packaged real GPU smoke”后再进入下一个：

1. ALFF/fALFF；
2. temporal filtering；
3. nuisance regression；
4. functional connectivity。

每个阶段初始仅允许显式 `backend=gpu` 的审阅执行；通过真实数据基准后才加入 auto 选择。

### Phase D：Smoothing 与 Atlas resampling

- 使用 `cupyx.scipy.ndimage` 或经批准的等价 CuPy 实现；
- 连续图像和标签图建立不同插值合同；
- 增加 affine/grid/label-set golden 测试；
- 完成后才允许 DPARSFA-like profile 选择 GPU。

### Phase E：ReHo 独立科学验证包

#### E.1 冻结 CPU 参考

- 当前 tie-corrected CPU `_kcc_numpy` 与 golden fixtures 作为参考；
- 增加 ties-heavy、constant、quantized 和 mask fixtures。

#### E.2 实现精确 CuPy kernel

- 分块 average-rank 和 tie correction；
- 显存预算与确定性错误处理；
- 不复用当前概率性 ties 检测作为正确性门。

#### E.3 数值与性能放行

- 全体素比较有效体素集合、最大/平均绝对误差；
- 记录 GPU/CPU runtime 和峰值内存；
- 只有科学审核通过后，原生 ReHo stage 才可选择 GPU。

### Phase F：前端、打包与发布

- 前端显示 CPU/GPU/Auto、设备状态、实际后端和 fallback；
- 技术参数默认折叠，安全/科学警告保持可见；
- PyInstaller 收集 CuPy 模块、CUDA DLL 和 license；
- 检查 sidecar/installer 体积与启动时间；
- 执行 GPU 机器 packaged smoke 和无 GPU 机器 CPU fallback smoke；
- 更新资源、用户指南、功能覆盖矩阵和 `PROJECT_STATE.md`（仅在完成验证后）。

## 7. Blast Radius Map

| 表面 | 预计影响 | 风险 |
|---|---|---|
| native scientific stages | 后端选择和公共写入 | 高 |
| scientific compute kernels | GPU 数值实现 | 极高 |
| `gpu_safety.py` / `gpu_utils.py` | 设备、内存、锁和错误 | 高 |
| native API schema/routes | 资源策略和状态 | 中高 |
| provenance/artifact registry | 实际 backend 与验证记录 | 高 |
| frontend preprocessing | 后端选择和实时状态 | 中 |
| PyInstaller/Electron packaging | CuPy/CUDA DLL 和体积 | 高 |
| optional requirements/lock surfaces | 可复现依赖 | 高 |

明确不受影响：DICOM 转换、rawdata、MATLAB/SPM/DPABI 执行、安全路径允许列表中的外部命令策略和临床边界。

## 8. Hazards & Mitigations

| H-ID | 风险 | 缓解措施 | 验证 |
|---|---|---|---|
| H-GPU-01 | CuPy/CUDA/驱动不匹配 | 固定版本、启动预检、CPU fallback | packaged capability smoke |
| H-GPU-02 | 不同显存容量或当前占用导致 OOM | 实时空闲显存、自适应预留与 chunk、峰值反馈、清理 | 强制小预算/OOM 测试 |
| H-GPU-03 | 多受试者争抢 GPU | 跨任务单设备锁 | 并发提交测试 |
| H-GPU-04 | GPU runner 仍是 scaffold | 原生 stage 只接受真实数值 artifact | 状态真实性测试 |
| H-GPU-05 | ReHo ties 不等价 | 精确 average rank/tie correction | ties-heavy 全体素 golden |
| H-GPU-06 | float32 数值漂移 | 阶段级参考误差和显式 precision | CPU/GPU consistency |
| H-GPU-07 | OOM 后半写产物 | 临时路径、成功后原子登记、失败清理 | 故障注入测试 |
| H-GPU-08 | auto 静默回退 | provenance、warning、actual backend | fallback API 测试 |
| H-GPU-09 | require_gpu 被静默降级 | require_gpu 失败即 blocked/failed | 无 GPU 测试 |
| H-GPU-10 | GPU 数据传输反而更慢 | auto 收益阈值、端到端计时 | 小/中/大输入 benchmark |
| H-GPU-11 | atlas 插值生成非法标签 | label 强制 nearest-neighbor | 标签集合完全一致测试 |
| H-GPU-12 | 打包遗漏 CUDA DLL | sidecar import + real kernel smoke | unpacked/package smoke |
| H-GPU-13 | 私有路径写入 provenance | artifact ID/项目相对路径 | provenance contract test |
| H-GPU-14 | GPU 与 CPU 并行过度订阅 | 统一 CPU/GPU 资源令牌规划器，动态限制待提交任务 | 混合负载压力测试 |
| H-GPU-15 | 测试只覆盖 synthetic | 真实三受试者人工验证矩阵 | real-data validation record |
| H-GPU-16 | 启动时显存快照过期 | kernel 前复检、资源令牌、运行中重规划 | 动态占用故障注入 |
| H-GPU-17 | 历史性能模型误导选择 | 版本/设备/workload 隔离、置信度与保守回退 | 过期模型测试 |
| H-GPU-18 | 自适应 chunk 抖动或过小 | 对齐约束、滞回、最小有效 chunk、收益门 | 多负载边界测试 |
| H-GPU-19 | 自动降精度改变结果 | precision 与资源参数分离，禁止静默降级 | OOM/precision 合同测试 |
| H-GPU-20 | 自动并发造成 CPU/GPU 资源互抢 | 统一 CPU/GPU token planner | 混合阶段压力测试 |

## 9. Test & Validation Plan

### 9.1 每个阶段的科学测试

- synthetic known-signal；
- zero/constant；
- NaN/Inf；
- insufficient timepoints；
- mask/atlas mismatch；
- deterministic repeated run；
- CPU/GPU output reload；
- shape/dtype/affine/checksum；
- GPU fallback 和 require_gpu failure；
- 自适应 backend/chunk/job 计算及决策可重复性；
- provenance 完整性；
- stage status truthfulness。

ReHo 额外覆盖：7/19/27 邻域、并列值、量化信号、全零邻域、边界体素、GM mask、有效体素集合完全比较。

### 9.2 初始容差策略

- 不预先用一个全局容差覆盖所有算法；
- ALFF/fALFF、filtering、regression、FC、smoothing、resampling、ReHo 各自从 CPU reference 误差分布确定并文档化；
- 现有 `tests/test_scientific_gpu_consistency.py` 的 `1e-4` 只能作为已有测试基线，不自动证明新阶段或真实数据已验证；
- 离散标签、有效体素集合、shape、affine 和状态必须精确一致；
- 如果 GPU 算法定义不同，即使误差看似很小也不能放行。

### 9.3 必须运行的验证命令

```powershell
python -m pytest tests/unit -k gpu --tb=short --basetemp=.pytest_tmp
python -m pytest tests/test_scientific_gpu_consistency.py -m gpu --tb=short --basetemp=.pytest_tmp
python -m pytest tests/unit -k native_preproc --tb=short --basetemp=.pytest_tmp
python -m pytest tests/integration -k native_preproc --tb=short --basetemp=.pytest_tmp
python -m pytest tests/golden/test_native_preproc_reference_comparison.py --tb=short --basetemp=.pytest_tmp
python -m pytest --tb=short --basetemp=.pytest_tmp
npm --prefix src/frontend run typecheck
npm --prefix src/frontend run test
npm --prefix src/frontend run build
```

另需完成：CuPy capability smoke、每个 Tier 1 kernel 实机 CPU/GPU benchmark、完整真实数据 GPU run、无 GPU fallback、sidecar build、Electron unpacked build 和 packaged launch/workflow smoke。

### 9.4 性能报告

每阶段报告：

- input shape/timepoints/voxel count；
- CPU total runtime；
- GPU host-to-device、compute、device-to-host、total runtime；
- speedup；
- peak RAM/VRAM；
- numerical max/mean absolute error；
- actual backend/fallback；
- warm-up 与重复运行统计。

首次 GPU 调用包含 CUDA context 初始化，应同时报告 cold 和 warm 结果，不得只选择最好的一次。

## 10. Proof Obligations

| 声明 | 验证方式 |
|---|---|
| GPU 走现有原生 stage 而非旁路 | 检查调用图、manifest 和 artifact registry |
| CPU 默认行为不变 | 旧请求与完整 CPU 回归 |
| auto 回退可见 | response/provenance/fallback tests |
| require_gpu 不回退 | 无 GPU/OOM 故障注入 |
| ReHo 数学定义一致 | ties-heavy 全体素 golden 比较 |
| GPU 产物真实存在并可重载 | artifact integrity tests |
| 8 GB 显存不会失控 | 实时预算、chunk 和实机峰值 |
| 参数会随样本和机器状态变化 | workload/resource 矩阵测试和 dry-run 决策报告 |
| 自动规划不改变科学参数 | CPU/GPU 请求、stage 参数和 provenance 比较 |
| 打包后真正调用 GPU | actual backend/device/provenance + packaged smoke |
| 原始数据不变 | 执行前后 checksum |

## 11. Assumption Registry

| A-ID | 假设 | 分类 | 影响 |
|---|---|---|---|
| A-GPU-01 | 验证机器为 RTX 4060 Laptop 8 GB | VERIFIED | 决定首轮实机预算 |
| A-GPU-02 | CuPy 是首轮统一生产 GPU 依赖 | WORKER CONSENSUS | 降低双框架打包复杂度 |
| A-GPU-03 | CPU 保持默认直到逐阶段验证 | CRITICAL | 防止实验后端默认生效 |
| A-GPU-04 | GPU 并发和 chunk 应由实时资源与 workload 自动计算，单作业仅是某些机器/阶段可能得到的安全结果 | USER DECISION | 需要统一资源令牌和动态显存模型 |
| A-GPU-05 | ReHo 是最高收益但最高科学风险阶段 | VERIFIED | 决定独立交付与审核 |
| A-GPU-06 | GPU 方案复用 CPU 方案的进度模型 | WORKER CONSENSUS | 避免两套任务状态系统 |

## 12. 实施顺序与放行门

1. 完成 CPU 方案中的异步状态和统一资源规划基础，或先抽取等价公共基础；
2. A 依赖、capability、显存和设备锁；
3. B backend-neutral kernel/result 边界；
4. C 按 ALFF/fALFF -> filtering -> regression -> FC 顺序逐个开放；
5. 每个阶段单独完成科学验证与 packaged GPU smoke；
6. D smoothing/atlas resampling；
7. E ReHo 独立科学验证；
8. F 前端、打包、无 GPU fallback 和完整真实数据；
9. 通过全部放行门后才允许 DPARSFA-like profile 使用 auto/GPU；
10. realignment/coregistration/normalization GPU 化另立后续科学任务，不在本轮顺带实现。

## 13. 未完成项与风险声明

本文档是实施方案，不代表当前完整预处理已经支持 GPU。现有 GPU compute 候选、GPU 节点注册或 consistency 测试不等于原生完整流程已接入、已打包或已科学验证。尤其是当前 GPU ReHo 缺少严格 ties correction，必须继续使用 CPU canonical 路径，直到本方案 Phase E 完成。
