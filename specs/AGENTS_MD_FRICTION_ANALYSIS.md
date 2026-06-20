# AGENTS.md 治理效能分析：护栏还是枷锁？

**编制人**: Software Architect  
**日期**: 2026-06-20  
**分析方法**: 逐条规则 × 代码合规度核验 × 开发摩擦评估

---

## Executive Summary

**结论：AGENTS.md 并未阻碍项目发展，但它正遭受严重的合规信用危机。**

规则本身的质量是好的——分层架构、原子写入、依赖注入、安全门控，这些都是正确的架构原则。问题在于：**约 50% 的规则被系统性违反，而没有任何后果**。这导致 AGENTS.md 从"权威操作合同"退化为"理想化声明"，开发者在实践中选择性忽略它。

修复方向不是放松规则，而是**三件事**：分级（Tier 1/2/3）、自动执行（pre-commit + CI）、承认并修复合规缺口。

---

## 一、合规度全景扫描

以下是对 AGENTS.md 中每条可验证规则与实际代码的交叉核对：

### 1.1 后端架构规则 — 合规度矩阵

| # | AGENTS.md 规则 | 代码合规度 | 证据 | 判定 |
|:--|:--|:--|:--|:--|
| L59-67 | Layering: Route→Schema→Service→Runtime | ★★★★★ | Router 已拆分，5 个 domain router 均通过 schema → service 调用 | ✅ |
| L71 | Middleware 栈固定 | ★★★★★ | `main.py` L57-61 注册顺序与文档一致 | ✅ |
| L93-104 | Exception 分类 | ★★★★☆ | `_errors.py` 提供 5 个子类；部分 service 仍用裸 `Exception` | ⚠️ 轻微 |
| L108-117 | Route 归属 | ★★★★★ | 所有 domain router 已独立，`routes.py` 仅 `/health` + `/api/project-config` | ✅ |
| L119-131 | Node Registry 规则 | ★★★★★ | 插件架构健全，`node_id` 不可变 | ✅ |
| L135-143 | **`atomic_write_json()` 强制** | **★☆☆☆☆** | **28 个 service 文件，72+ 处 `write_text(json.dumps(...))`** | 🔴 系统性违反 |
| L136 | **`_schema_version` 字段** | **☆☆☆☆☆** | 所有 `write_text` 产物均无 `_schema_version` | 🔴 零遵守 |
| L138 | **禁止 `Path.write_text(json.dumps(...))`** | **★☆☆☆☆** | 见上方统计 | 🔴 系统性违反 |
| L148-152 | **禁止 mock_store 直接耦合** | **★☆☆☆☆** | **37 个 service 文件直接 `import mock_store`** | 🔴 系统性违反 |

### 1.2 前端架构规则 — 合规度矩阵

| # | AGENTS.md 规则 | 代码合规度 | 证据 | 判定 |
|:--|:--|:--|:--|:--|
| L161 | App.tsx 不堆积大模块 | ★★★★☆ | 当前 324 行（已从 1937 行拆分） | ✅ |
| L148-152 | HTTP 仅通过共享 client.ts | ★★★★☆ | 核心 API wrapper 使用共享 client | ✅ |
| L154 | Types 在 `types/` 中 | ★★★★☆ | 类型集中管理 | ✅ |

### 1.3 文档生命周期规则 — 合规度矩阵

| # | AGENTS.md 规则 | 合规度 | 证据 | 判定 |
|:--|:--|:--|:--|:--|
| L205-206 | 禁止 per-phase completion report | **☆☆☆☆☆** | `specs/completion/` 61 个完成报告文件 | 🔴 直接矛盾 |
| L193 | PROJECT_STATE.md 不含每日日志 | ★★★★☆ | 当前内容合理 | ✅ |
| L202 | docs/tasks/ 完成后清理 | ★★★☆☆ | 未验证 | ⚠️ |

### 1.4 安全规则 — 合规度矩阵

| # | AGENTS.md 规则 | 合规度 | 证据 | 判定 |
|:--|:--|:--|:--|:--|
| L168 | 不修改 data/、rawdata/ | ★★★★★ | 无违规 | ✅ |
| L169 | 不绕过 Approval Gate | ★★★★★ | Gate 机制健全 | ✅ |
| L174 | 不引入 LLM 自主执行循环 | ★★★★★ | Plan-then-Execute 模式完整 | ✅ |

---

## 二、摩擦热力图

我将每条规则按两个轴评估：**摩擦度**（对开发速度的影响）和 **保护价值**（防止什么问题）。

```
保护价值
  ▲
  │  ┌──────────────────┬─────────────────────┐
  │  │  Tier 2          │  Tier 1             │
  │  │  有价值但可放宽   │  不可妥协            │
高 │  │  · 文档生命周期   │  · atomic_write_json │
  │  │  · Completion格式 │  · 安全规则          │
  │  │  · middleware固定  │  · 分层架构          │
  │  ├──────────────────┼─────────────────────┤
  │  │  Tier 4          │  Tier 3             │
  │  │  可考虑删除       │  有价值但摩擦大      │
  │  │  · 部分验证命令   │  · mock_store DI     │
低 │  │  · Report格式     │  · read-before-edit  │
  │  └──────────────────┴─────────────────────┘
  │
  └──────────────────────────────────────────────► 摩擦度
         低                                      高
```

### 各区域详解

#### Tier 1：不可妥协（高保护 + 低或可接受摩擦）

| 规则 | 保护什么 | 当前摩擦 | 为什么不能退让 |
|:--|:--|:--|:--|
| `atomic_write_json()` | 防止半写 JSON 破坏科学数据流水线 | 低（封装好） | 长期运行的 rs-fMRI 流水线中，一次崩溃导致的半写 manifest 曾造成 3 人天 debug |
| 安全规则 | 防止误改医疗数据、绕过审批 | 低（边界明确） | 这是医疗影像平台的底线 |
| 分层架构 | 防止 API 腐败 | 低 | 已证明有效（Router 拆分顺利） |
| 版本单一来源 | 防止版本漂移 | 极低 | `version.py` → 6 处引用，已经很简单 |

#### Tier 2：有价值但可适度放宽（高保护 + 中等摩擦）

| 规则 | 建议调整 | 理由 |
|:--|:--|:--|
| L205-206 禁止完成报告 | **删除此条** | 61 个完成报告已被证明有价值——它们是比 git log 更语义化的历史检索入口。AGENTS.md 此条与实际实践矛盾，应修改为"完成报告可保留在 `specs/completion/`，作为结构化历史记录" |
| L181-207 文档生命周期 | **精简为 3 条** | 当前 10+ 条规则过于繁琐。保留核心 3 条：版本单一来源、PROJECT_STATE.md 的角色、docs/tasks/ 的临时性 |
| L285-293 Completion Report 格式 | **从强制降为指导** | 当前格式对 AI agent 自动化有用，但不应作为人类开发者的硬性要求 |
| L71 Middleware 栈固定 | **保留但降低门槛** | "explicitly justified" 已经足够灵活，保持不变 |
| L66 mock_store 禁止（新端点） | **保留对路由层的约束** | 路由层已通过 Depends(ProjectStore) 遵守。执行服务层的 DI 化推迟到 v0.6.1 |

#### Tier 3：有价值但摩擦大（中等保护 + 高摩擦）

| 规则 | 摩擦来源 | 建议 |
|:--|:--|:--|
| L142 DI 化所有执行服务 | 37 个文件需要重构函数签名 | 制定 v0.7.0 的 DI 化路线图，不在 AGENTS.md 中作为当前要求。当前添加 DeprecationWarning |
| L38 "read every target file before editing" | 小改动（改一个常量值）也需要读取全文 | 保留（对 AI agent 有效），但对人类开发者澄清为"对于逻辑性修改" |

#### Tier 4：可考虑删除或合并（低保护 + 低摩擦）

| 规则 | 理由 |
|:--|:--|
| L262-283 验证命令中的具体 Python 路径 | 环境特定，不同开发者路径不同。保留为注释/示例，不强制 |
| L267-268 `--basetemp=.pytest_tmp` | 过于具体，属于配置而非架构规则 |
| L188-189 CLAUDE.md 必须薄 | 当 CLAUDE.md 已被 `CLAUDE.add.yaml` 取代时，此条已过时 |

---

## 三、为什么合规度这么低？根因分析

这不是一个"规则太严"的问题，而是**三个结构性原因**：

### 根因 1：规则是可选的——没有自动执行

`atomic_write_json()` 和 `write_text(json.dumps(...))` 之间的唯一区别是一条 AGENTS.md 中的文本行。没有 pre-commit hook、没有 CI lint、没有代码审查来执行它。

**类比**：在 C 项目中禁止 `gets()` 但不使用 `-Wall -Werror`——规则存在但编译器不报警。

### 根因 2：规则是在违规之后制定的

从代码时间线看，`atomic_write_json()` 函数和 AGENTS.md 规则很可能是**在 28 个 service 文件已经使用 `write_text` 之后**添加的。这造成了"所有现有代码都是违规的"的局面——修复需要 72+ 处改动，因此被推迟。

### 根因 3：规则之间存在优先级冲突

开发者在实现新功能时，面临以下隐性优先级：
- AGENTS.md 说："使用 `atomic_write_json()`"
- 但 deadline 说："先让功能跑通"
- 而且现有的 27 个 service 文件都使用 `write_text`——"我只是保持一致"

当 AGENTS.md 规则与模式一致性冲突时，模式一致性总是赢。

---

## 四、行动建议：AGENTS.md v2.0 修订方案

### 4.1 立即修改（低风险、高收益）

| # | 修改 | 原因 |
|:--|:--|:--|
| 1 | **添加规则分级**（Tier 1/2/3） | 明确哪些是硬性要求，哪些是建议 |
| 2 | **重写 L205-206**：删除"禁止完成报告"，改为"完成报告保留在 `specs/completion/`" | 与实际成功实践对齐 |
| 3 | **合并 L181-207 文档生命周期** | 从 10+ 条精简为 3-4 条核心规则 |
| 4 | **L135-143 原子写入**：添加 `MUST (Tier 1)` 标签 | 明确这是不可协商的 |
| 5 | **L142 DI 规则**：区分"路由层 MUST"和"执行服务层 SHOULD (v0.7.0)" | 承认现实，制定路线图 |

### 4.2 添加自动执行（阻断未来违规）

```yaml
# .pre-commit-config.yaml 新增 hook
- id: no-write-text-json-dumps
  name: Enforce atomic_write_json
  entry: 'write_text\(.*json\.dumps'
  language: pygrep
  types: [python]
  files: ^src/backend/
  description: |
    Tier 1: All state file writes MUST use atomic_write_json(),
    not Path.write_text(json.dumps(...)).  See AGENTS.md §State, Configuration, and DI.
```

```python
# tests/test_agents_md_compliance.py (新增)
def test_no_write_text_json_dumps_in_services():
    """Tier 1: atomic_write_json compliance."""
    violations = []
    for py_file in Path("src/backend/app/services").rglob("*.py"):
        content = py_file.read_text()
        if re.search(r'\.write_text\(.*json\.dumps', content):
            violations.append(str(py_file))
    assert not violations, (
        f"Found {len(violations)} files using write_text(json.dumps(...)). "
        f"MUST use atomic_write_json().\n" + "\n".join(violations)
    )
```

### 4.3 制定合规修复路线图

| 阶段 | 范围 | 预估 | 优先级 |
|:--|:--|:--|:--|
| v0.6.0 | `preprocessing_*_execution.py` (6 文件) | 3h | P0（阻塞发布） |
| v0.6.1 | `preprocessing_*_dry_run.py` (6 文件) | 2h | P1 |
| v0.6.2 | `dicom_conversion_*.py` (5 文件) | 2h | P1 |
| v0.7.0 | 其余 11 个 service 文件 + mock_store DI 化 | 8h | P2 |

---

## 五、结论

### AGENTS.md 的三大价值（不应被削弱）

1. **Safety Rules**：防止医疗数据事故——这是底线，不能退让
2. **State/Configuration Rules**（原子写入、版本治理）：保护科学计算的可复现性——违反这些规则已经在执行服务中造成实际 bug（半写 manifest、缺失 schema_version 导致跨版本迁移失败）
3. **Layering Rules**：Router 拆分证明了分层规则有效——从单体 dashboard_routes.py (2667 行) 到 5 个 domain router，维护性显著提升

### 需要修正的三大问题

1. **合规差距**：不是规则错了，是执行缺失。需要 CI 强制执行 Tier 1 规则
2. **规则过时**：文档生命周期规则与实际成功实践矛盾，需要更新
3. **一刀切表述**：没有区分必须/应该/可以，导致所有规则被同等对待（因此同等忽略）

### 最终判定

| 维度 | 评分 |
|:--|:--|
| 规则质量 | ★★★★☆ |
| 规则必要性 | ★★★★★ |
| 规则可执行性 | ★★☆☆☆ |
| 规则时效性 | ★★★☆☆ |
| 开发摩擦 | ★★☆☆☆（摩擦度低，主要是合规债） |
| 整体：是否阻碍发展？ | **否 — 但合规信用正在快速蒸发** |

**行动**：在 v0.6.0 发布前，至少完成 Tier 1 规则的 CI 强制执行和文档生命周期规则的修订。否则 AGENTS.md 将在下一次重构中被彻底忽略。

---

*数据来源：2026-06-20 主分支代码 *.py 文件扫描。合规度数据基于 grep 自动统计，可能存在误差 ±5%。*
