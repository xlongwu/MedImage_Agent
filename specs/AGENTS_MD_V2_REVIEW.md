# AGENTS.md v2.0 草案审查报告

**审查人**: Software Architect  
**日期**: 2026-06-20  
**参照**: 原版 AGENTS.md (293 行)、AGENTS_MD_FRICTION_ANALYSIS.md、当前代码合规度数据

---

## 总体评价：★★★★☆ — 这是一次质变式的改进

新版从"被动防御的约束清单"升级为"主动治理的操作合同"。**新增的 Task Modes (§3)** 是整个文件中最有价值的部分——它解决了原版最大的问题："所有任务被同等对待，所有规则被同等忽略"。

核心优势：**模式驱动差异化**。不再强迫一个文档修正和一个架构重构遵循同样的工作流。

---

## 一、逐章审查

### §1 Project Boundary — ★★★★★ 显著改进

| 维度 | 原版 | 新版 | 评判 |
|:--|:--|:--|:--|
| 身份定义 | 一段话 | 4 条 is + 4 条 is not | ✅ 更精确，消除歧义 |
| 外部执行准入条件 | 4 项 | **8 项**（新增 audit logging, env gating, failure handling, tests） | ✅ 更完整 |

**无问题。**

---

### §2 Authority and Sources of Truth — ★★★★☆ 大幅重构

| 维度 | 原版 | 新版 | 评判 |
|:--|:--|:--|:--|
| 结构 | 单一优先级列表 | 5 个子层级（policy / code / task / state / archive） | ✅ 更清晰 |
| 关键新增 | — | §2.2 "当前代码不是自动证明正确" | ✅ 解决了科学计算语境下代码≠正确的关键区别 |
| 冲突处理 | 静默"follow code" | §2.5 列出三步报告流程 | ✅ 可操作 |

**小问题**：§2.2 说"当前代码不是自动证明科学正确"——这是正确的，但下一条 §2.3 说"task handoff 是权威"。当代码行为正确但 handoff 要求错误行为时，会出现冲突。建议在 §2.5 的冲突报告流程中显式增加一条："当 task handoff 要求的变更与已验证的科学正确性冲突时，暂停并报告。"

---

### §3 Task Modes — ★★★★★ 本文件最大亮点

这是**全新的章节**，是原版完全缺失的结构。

| Mode | 覆盖范围 | 代码例子 | 评判 |
|:--|:--|:--|:--|
| Focused Fix | 单文件小修正 | 改一个常量、修复一个测试 | ✅ 防止 over-engineering |
| Feature Bundle | 端到端功能 | 新增 ALFF pipeline | ✅ 完整调用链覆盖 |
| Architecture & Refactor | 结构变更 | Router 拆分、DI 化 | ✅ 明确 refactor ≠ 新功能 |
| Scientific Validation | 数值验证 | ALFF/ReHo/FC kernel | ✅ 首次将科学验证提升为独立模式 |
| Release & Packaging | 发版 | version bump, PyInstaller | ✅ 隔离发版的特殊要求 |

**每个 mode 的 rules 都非常精准**。例如 Focused Fix 的"不编辑未列出文件，发现需要时停止报告"——这直接解决了原版中"严格规则 vs 必要改动"的冲突。

**一个小冗余**：§3.1 Focused Fix 的"stop and report if an unlisted file is required" 与 §4.4 的详细规则重复。建议 §3.1 简化为"follow the escalation rules in §4.4"，避免维护两套规则。

---

### §4 Agent Roles and Change Ownership — ★★★★☆ 很好的治理层

| 新增内容 | 价值 |
|:--|:--|
| Single-owner rule (§4.1) | ✅ 防止多 agent 并发编辑冲突 |
| Handoff readiness (§4.2) | ✅ 明确状态检查，"未就绪就停止" |
| Required handoff fields (§4.3) | ✅ 15 个字段的完整规范 |
| Unlisted-file escalation (§4.4) | ✅ 按 mode 分级处理 |

**小问题**：§4.1 的 "One task → one owner agent → one branch → one diff" 原则非常好，但 §4.3 进一步要求 15 个 handoff 字段。对于简单的 Focused Fix，这 15 个字段中的部分（如 "Safety Invariants"、"Stop Conditions"）可能显得仪式化。建议在 §4.3 开头增加一句："字段的严格程度应匹配 Task Mode。"

---

### §5 Required Workflow — ★★★★☆ 细化为三阶段

| 阶段 | 原版 | 新版 |
|:--|:--|:--|
| Before editing | 3 条 | **8 条**（新增检查 task mode、验证 anchors、检查已有实现） |
| During | 2 条 | **7 条**（新增不隐藏不完整行为、不弱化测试、不跳过验证） |
| After | 2 条 | **5 条**（新增 git status 检查、产物分类） |

**关键改进**：新增的 "Do not hide incomplete behavior behind successful status values" 直接解决了当前代码中 `write_text(json.dumps(...))` 的核心问题——状态文件声称成功但数据完整性无保障。

**小冗余**：§5 "Before editing" 中的 "Read AGENTS.md" + "Read CLAUDE.md" 在原版 §2-3 有，新版 §5 再次重复。建议删除 §5 中的重复，改为 "Follow §2-§4 确立的 authority 和 mode 规则。"

---

### §6 Backend Architecture Rules — ★★★★☆ 精细化的增量改进

| 修改 | 评判 |
|:--|:--|
| Layering 增加 "Scientific Kernel" 层 | ✅ 响应了科学计算需求 |
| Prohibited 新增 "services that duplicate existing scientific kernels" | ✅ 直击 DRY 问题 |
| Prohibited 新增 "successful API responses for artifacts that were not actually created" | ✅ 解决了 status 虚假问题 |
| Middleware 表格改为 "innermost first" 排列 | ✅ 更符合 Starlette 的实际注册顺序 |
| "fixed unless justified" 删除 | ⚠️ 微妙——有理由移除（已被 Task Mode 机制覆盖），但失去了一条防御线 |
| Exception handling 新增 "Do not replace structured domain errors with generic 500" | ✅ 防止退化 |
| Route ownership 新增 "When touching a monolithic router in Architecture Mode, prefer extracting one complete domain" | ✅ 精确的操作指南 |

**唯一担忧**：中间件 "fixed unless justified" → 删除。在 Architecture Mode 下中间件变更已经是允许的，但删除这条失去了一层对 Focused Fix Mode 的防御。建议在 §6.2 开头加一句："In Focused Fix and Feature Bundle Modes, the middleware stack must not be changed."

---

### §7 Frontend Architecture Rules — ★★★★☆ 显著增强

| 新增 | 价值 |
|:--|:--|
| "A complete feature must represent loading, empty, disabled, success, partial, and failure states" | ✅ 前端状态完备性——可能是全文件中最被低估的一条 |
| API contract 变更必须同步 5 层 | ✅ 防止前后端断开 |
| §7 最后新增 API 变更影响清单 | ✅ 可操作性强 |

**无问题。**

---

### §8 Safety Invariants — ★★★★★ 安全规则的质变

| 原版 | 新版 | 评判 |
|:--|:--|:--|
| 17 条"禁止事项"扁平列表 | §8.1 "Absolute invariants" 9 条 + §8.2 "Protected modules" 6 条准入条件 + §8.3 "External execution" 7 条要求 | ✅ 三级结构化安全模型 |
| 无变更指引 | §8.2 明确 6 条修改 protected module 的准入条件 | ✅ 解决了"既不能改又必须改"的困境 |
| 无"绕过"指引 | §8.2 末尾："Do not work around a core bug by duplicating logic in a route or service merely to avoid editing a protected module" | ✅ 精确阻止了一种常见的规避模式 |

**这是新版中最接近"完美"的章节。** 安全模型从"不做什么"升级为"什么条件下可以做"，可操作性大幅提升。

---

### §9 Scientific Computing Contract — ★★★★★ 全新的科学正确性支柱

**整个章节是原版完全缺失的**。9 个子章节覆盖了从"能力真相级别"到"CPU/GPU 对等验证"的完整科学计算生命周期。

| 子章节 | 关键贡献 |
|:--|:--|
| §9.1 Capability truth levels | ✅ 5 级分层（unavailable→scaffolded→metadata_only→computed→validated），终结了"succeeded"一词的歧义 |
| §9.2 End-to-end path | ✅ 9 层调用链的完整覆盖 |
| §9.3 Single numerical source of truth | ✅ 禁止重复实现——AD-1 的规则化 |
| §9.4 Artifact integrity | ✅ "Metadata sidecars supplement numerical artifacts. They do not replace them." — 金句 |
| §9.5 Provenance | ✅ 20+ 字段的 provenance 要求 |
| §9.6 Numerical validation | ✅ 11 种验证维度 |
| §9.8 Simplified/partial algorithms | ✅ 防止"预览版"悄无声息升级为"生产版" |

**无问题。** 这章可以独立作为科学计算平台的代码审查检查清单。

---

### §10 Dependency and Reproducibility — ★★★★☆ 好但可精简

| 好 | 可改进 |
|:--|:--|
| "Do not introduce latest dependency versions" | 部分规则（如路径、记录版本）与 §6.6、§14 重复 |
| "Record exact toolchain versions in release records, not in permanent generic commands" | 可精简为 5-6 条 |

**不算大问题。**

---

### §11 Documentation and Task Lifecycle — ★★★☆☆ 最大改进空间

| 子章节 | 评判 |
|:--|:--|
| §11.1 Stable documents | ✅ 清晰定义 6 类稳定文档 |
| §11.2 PROJECT_STATE | ✅ 保留"不是开发日记"，但语气更温和 |
| §11.3 Task handoffs | ✅ "不要假设本地任务文件在别处可用"——非常实用的提醒 |
| §11.4 Completion reports | ⚠️ **核心问题**（见下方） |

**§11.4 的问题**：

> "Do not create a permanent per-fix or per-sprint Markdown report unless it is an explicit deliverable."

这条与当前 61 个 `specs/completion/` 完成报告的实践**直接矛盾**。在我的摩擦分析中，我建议将其改为"完成报告可保留在 `specs/completion/` 作为结构化历史记录"——因为 61 个报告已被证明有价值（它们是比 git log 更语义化的历史检索入口）。

**建议修改**：

```markdown
### 11.4 Completion reports

Routine Completion Reports belong in:

* the final agent response;
* the pull request description;
* a commit message when appropriate;
* a release record for release work.

Phase-level or milestone-level completion reports may be retained as
historical records under `specs/completion/` when they:

* document a completed phase's architecture decisions and outcomes;
* serve as a historical reference for future developers;
* are explicitly designated as deliverables.

Do not create a per-tick or per-sprint Markdown report for routine work
that duplicates commit history.
```

---

### §12 Git and Artifact Rules — ★★★★★ 安全感十足

| 新增 | 价值 |
|:--|:--|
| §12.2 "Tracked resources versus runtime artifacts" | ✅ 防止误删 tracked 资源——这是基于实际事故的防御（之前有人讨论过清理 memory/ 目录） |
| "Do not blanket-ignore or blanket-delete a directory that also contains tracked fixtures" | ✅ 精确、可操作 |
| 新增示例路径列表 | ✅ 直观 |

**无问题。**

---

### §13 Version Governance — ★★★★☆ 保持稳定

基本不变，增加了"版本 bump 必须是显式 release task"的声明。

**无问题。**

---

### §14 Validation Policy — ★★★★★ 从"几条命令"到"完整策略"

| 原版 | 新版 | 评判 |
|:--|:--|:--|
| 硬编码 `D:\Anaconda3\envs\mamba\python.exe` | `python`（使用当前环境解释器） | ✅ **这正是我在摩擦分析中建议的** |
| 3-4 条命令 | 6 种 Mode × 各自的验证矩阵 + 失败处理策略 | ✅ 精确、可操作 |
| 无 mode 区分 | 每个 Task Mode 有专属的验证要求 | ✅ 与 §3 完美呼应 |

**§14.5 的验证矩阵是亮点**：Documentation-only 任务不需要跑 pytest，Scientific Validation 任务必须跑 golden tests——规则因模式而异，恰到好处。

**一个小瑕疵**：§14.3 仍保留了 `--basetemp=.pytest_tmp`。我在摩擦分析中建议将其作为配置而非架构规则。但考虑到 Windows temp 权限问题仍在，保留也是合理的。

---

### §15 Completion Report — ★★★★☆ 结构化但不冗余

15 个子章节涵盖了从 Task Mode 到 Remaining Risks 的完整交付报告。与前文 §4.3 的 handoff fields 呼应良好。

**小冗余**：§15 中的 "Task mode"、"Files changed"、"Validation" 等字段与 §4.3 的 handoff 字段有重叠，但角度看不同（§4.3 是 handoff 规范，§15 是 completion 格式）——这是合理的，不需要合并。

---

## 二、对照我的摩擦分析的修正度

| 摩擦分析建议 | 新版是否落实 | 评判 |
|:--|:--|:--|
| 添加 Task Modes 分级 | ✅ §3 全面实现 | 超出预期——5 种模式远超我建议的 3 种 |
| Tier 1/2/3 规则分级 | ⚠️ 未实现 | Task Modes 部分替代了分级（通过模式差异化），但缺少显式的合规等级声明 |
| 删除硬编码解释器路径 | ✅ §14.2 `python` | 完美 |
| 精简文档生命周期规则 | ⚠️ 改进但未完全解决 | §11 结构清晰，但 §11.4 仍与现有实践矛盾 |
| 添加 pre-commit hook / CI 强制执行 | ❌ 未提及 | 这是 AGENTS.md 自身无法做的事——需要配套的 CI 配置 |
| 删除 completion report 禁令 | ⚠️ 部分改进 | 比原版温和但仍有限制 |
| mock_store DI 路线图 | ❌ 未提及 | 不属于 AGENTS.md 规则层面，正确 |
| 合并 middleware 固定规则 | ⚠️ 删除了而非合并 | 见 §6 审查 |

---

## 三、整体架构评判

### 3.1 新版解决了原版的三大结构性问题

| 原版问题 | 新版解决方案 | 评分 |
|:--|:--|:--|
| "所有任务被同等对待" → "所有规则被同等忽略" | §3 Task Modes — 5 种模式，任务可窄可宽 | ★★★★★ |
| 科学正确性是隐含假设，不是显式规则 | §9 Scientific Computing Contract — 9 子章节，独立支柱 | ★★★★★ |
| 规则是"禁止清单"，没有"何时可以改"的出口 | §8.2 Protected modules — 6 条准入条件 | ★★★★★ |

### 3.2 两个仍存在的问题

**问题 1：§11.4 与现有实践冲突**

这是新版中唯一一处与当前代码库实践直接矛盾的地方。61 个 `specs/completion/` 文件是项目历史的重要组成部分。建议按上文建议修改。

**问题 2：缺少执行机制**

AGENTS.md v2.0 作为规范文本已经非常优秀，但它自身无法执行自己。`atomic_write_json()` 的规则从 v1.0 就存在，但仍然被 28 个文件违反——因为没有任何东西在检查。

建议在文件末尾的 §15 之后，增加一个独立小节：

```markdown
## 16. Compliance and Enforcement

### 16.1 Automated enforcement

The following Tier 1 rules are enforced by CI and pre-commit hooks:

| Rule | Enforcement | Location |
|:--|:--|:--|
| atomic_write_json() | pre-commit grep hook | `.pre-commit-config.yaml` |
| No mock_store coupling in new endpoints | pytest compliance test | `tests/test_agents_md_compliance.py` |
| Version consistency | CI version check | `.github/workflows/ci.yml` |
| Scientific artifact integrity | Scientific Validation CI | `.github/workflows/scientific.yml` |

### 16.2 Compliance debt

Known compliance gaps are tracked as technical debt issues:

| Issue | Scope | Target | 
|:--|:--|:--|
| write_text → atomic_write_json | 28 service files | v0.7.0 |
| mock_store DI migration | 37 service files | v0.8.0 |

This section is updated when a new enforcement mechanism is added.
```

### 3.3 文档长度分析

| 版本 | 行数 | 章节数 |
|:--|:--|:--|
| 原版 | 293 | 12 (实际上是无序的) |
| 新版 | ~700 | 15 + 附录 |

700 行对 AGENTS.md 来说偏长，但考虑到这是仓库中最重要的操作合同，长度是合理的。关键问题是**可查找性**——建议在文件开头增加一个 5 行的"速查表"（Quick Reference）：

```markdown
## Quick Reference

| 我该做什么？ | 看这里 | 验证要求 |
|:--|:--|:--|
| 修一个 bug | §3.1 Focused Fix | 回归测试 |
| 做一个新功能 | §3.2 Feature Bundle | 全栈测试 |
| 重构架构 | §3.3 Architecture Mode | 特征测试 + 回归测试 |
| 验证算法 | §3.4 + §9 Scientific | Golden tests |
| 发版 | §3.5 + §13 + §14.5 | 全矩阵 |
```

---

## 四、最终判定

| 维度 | 原版 | 新版 |
|:--|:--|:--|
| 规则完整性 | ★★★☆☆ | ★★★★★ |
| 可操作执行性 | ★★☆☆☆ | ★★★★☆ |
| 科学正确性覆盖 | ★☆☆☆☆ | ★★★★★ |
| 安全性覆盖 | ★★★☆☆ | ★★★★★ |
| 与现有实践一致性 | ★★★☆☆（大量违规） | ★★★★☆（仅 §11.4 一处冲突） |
| 可读性/可查找性 | ★★★☆☆ | ★★★☆☆（建议加速查表） |
| **整体** | **★★★☆☆** | **★★★★☆** |

**结论：新版 AGENTS.md 是一次从"及格"到"优秀"的质变。它合理、完整、可操作。建议在以下 3 处微调后正式采用：**

1. **§11.4**：将 completion report 禁令改为允许 phase/milestone 级别的保留
2. **§3.1**：引用 §4.4 的 escalation 规则，避免重复
3. **新增 §16** 或附录：声明 Tier 1 规则的 CI 执行机制和已知合规债务

完成这 3 处修改后，新版 AGENTS.md 可以立即生效，作为 v0.6.0 发布的一部分。
