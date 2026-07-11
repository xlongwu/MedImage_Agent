# 项目长期目标 (PROJECT_GOAL)

## 1. 愿景

MedImage Agent 的长期目标是建立一个**安全、可审计、可复现的医学影像分析 Agent 工作流平台**。研究者用自然语言描述分析目标，系统自动生成结构化 pipeline plan，经人工审批后确定性执行，最终输出完整的 QC 报告和可复现性捆绑包。

## 2. 核心用户场景

### 场景 1：rs-fMRI 预处理全流程

研究者给定一个 BIDS 格式的数据集，希望完成从原始 DICOM 到组分析报告的完整预处理：

1. 研究者描述目标（自然语言或结构化配置）
2. LLM Planner 生成预处理 pipeline plan
3. Plan Validator 校验参数合法性、依赖完整性、安全边界
4. 研究者审批 plan（Approval Gate）
5. Pipeline Executor 按 DAG 顺序执行：数据检查 → Motion QC → Slice Timing → Realign → Coregister → Segment → Normalize → Smooth → Nuisance Regression → Temporal Filtering → ALFF/fALFF → ReHo → Functional Connectivity
6. 每个节点执行后自动触发配套 QC
7. 最终输出：组水平报告、可复现性捆绑包（含环境快照、文件校验和、git 状态、参数记录）

### 场景 2：人工定位步骤（AC-PC 定位）

对于需要人工定位或交互确认的步骤（如 AC-PC / 前联合定位），系统通过 GUI Agent Node 接入：

1. Pipeline 执行到 GUI Agent Node 时暂停
2. 在独立 GUI 沙箱中打开图像，等待人工标注
3. 人工标注完成后，结果写回 pipeline 状态
4. Pipeline 继续执行后续节点

### 场景 3：多中心数据对比研究

研究者需要对比多个中心的 rs-fMRI 数据质量：

1. 研究者在项目配置中指定多个数据源
2. Pipeline Executor 并行处理各中心数据
3. 统一生成跨中心 QC 对比报告
4. 自动标记异常受试者（如 FD > 阈值、配准失败）

### 场景 4：方法学对比（不同参数 / 不同工具）

研究者想对比 SPM 和 DPABI 在相同数据上的差异：

1. 配置两个 pipeline plan，使用不同 backend（SPM vs DPABI）
2. 并行执行
3. 自动生成对比报告

## 3. 最终系统能力

### 完整工作流

```
用户自然语言任务
  → LLM Planner 生成结构化 pipeline plan
  → Plan Validator 校验（schema + safety + dependency）
  → Human Approval Gate 审批（plan 级 + step 级）
  → Pipeline Executor 调用具体工具节点执行
  → SPM / DPABI / Python / GPU / GUI Agent 节点完成处理
  → 自动 QC / 报告 / 可复现性捆绑包输出
```

### 核心能力清单

| 能力 | 状态 |
|------|------|
| 自然语言 → 结构化 plan | 🔄 M4 计划中 |
| Plan schema 校验 | ✅ 已实现 `pipeline_schema.py` |
| Plan safety 校验 | 🔄 M3 计划中 |
| Human Approval Gate（plan 级） | ✅ 已实现 `agent_runtime.py` |
| Human Approval Gate（step 级） | ✅ 已实现 `tool_registry.py` |
| DAG 拓扑排序执行 | ✅ 已实现 `pipeline_executor.py` |
| Subject 级并行调度 | ✅ 已实现 `scheduler.py` |
| SPM 集成（6 个核心模块） | ✅ 已实现 |
| Python 原生处理（ALFF/ReHo/FC 等） | ✅ 已实现 |
| GPU 加速（5 个模块，CuPy） | ✅ 已实现 |
| DPABI 集成 | 🔄 接口设计完成，待实现 |
| GUI Agent Node | 🔄 M5 计划中 |
| 自动 QC 报告 | ✅ 已实现 |
| 可复现性捆绑包 | ✅ 已实现 |
| 前端 Pipeline Canvas | ✅ 已实现 |
| 前端 Plan Review Console | 🔄 M6 计划中 |
| 真实数据安全沙箱 | 🔄 M7 计划中 |

## 4. 非目标（明确边界）

以下能力**不属于**本项目的长期目标：

1. **临床诊断产品**：本项目定位于研究工程平台，不用于临床诊断或临床决策。不提供临床级别的敏感度/特异度指标，不输出诊断报告。
2. **开放式 LLM 自主循环**：本项目采用 Plan-then-Execute 模式，不实现 "LLM 在循环中自主决定每一步做什么" 的架构。
3. **替代研究者决策**：所有关键决策（参数选择、异常受试者排除、分析方法选择）必须经过人工审批。系统只提供建议，不代替研究者做决策。
4. **通用医学影像平台**：当前聚焦 rs-fMRI，不扩展到 CT、PET、超声等其他模态（架构可扩展，但不纳入当前 roadmap）。
5. **云端 SaaS 产品**：当前以本地部署和 Docker 容器为主，不考虑多租户 SaaS 架构。

## 5. 核心架构原则

这些原则写入 `docs/ARCHITECTURE.md` 和 `AGENTS.md`，所有开发者和 Agent 必须遵守：

1. **LLM 只做规划**：LLM 只能做规划、建议、解释，不能绕过 Pipeline Executor 直接执行工具。
2. **Pipeline Executor 统一入口**：所有真实执行必须经过 Pipeline Executor。
3. **Approval Gate 强制**：所有会写文件、运行 MATLAB/SPM/DPABI 或修改 derivatives 的操作必须经过 approval gate。
4. **rawdata 只读**：`data/` 目录永远只读，禁止任何代码修改原始数据。
5. **GUI Agent 是节点**：GUI Agent 只能作为特殊 node runner 接入 pipeline，不能接管整个系统控制流。
6. **节点规范**：每个 pipeline node 必须有清晰的 inputs、outputs、params、backend、risk、approval requirement。
7. **测试 + 文档**：新功能必须包含测试、文档、验收命令。
8. **无硬编码私密信息**：不允许把 API key、绝对私有路径、实验数据路径写死进代码或文档。
9. **前端隔离**：前端只能调用后端 API，不能直接操作本地文件系统。
10. **Plan-then-Execute**：长期目标是 Plan-then-Execute，而不是开放式 LLM autonomous loop。

---

*最后更新：2025-07-18*
