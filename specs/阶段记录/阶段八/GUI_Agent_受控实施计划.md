# 阶段八规划：GUI Agent 受控实施计划

> **Status：Planned — Not Ready for Implementation**
> **实施状态：维护者明确要求当前暂不执行；本文件只定义后续立项门槛与实施路线。**
> 预期任务模式：Feature Bundle Mode + Protected Change
> 前置条件：阶段七 7A–7D 完成；维护者以新的 implementation-ready handoff 重新批准。

## Scope Anchor

**目标**：若后续确认确有 API 不可替代的桌面交互需求，在隔离 Windows 环境中实现可观察、逐步确认、可审计、默认不执行且无法接触 rawdata 的 GUI 适配能力；它始终是确定性 Pipeline/官方 API 的补充，而非主执行路径。

**必须满足**：

- 真实 GUI 操作只能由阶段七的 `ExecutionTicket` / Execution Gateway 触发，并继承项目、审批、允许窗口、允许 action、输入/输出根和审计边界。
- 默认是 observation-only；任何鼠标、键盘、菜单或提交操作均须逐动作确认、显示预期副作用，并在允许的 target window 内执行。
- 在专用 Windows 沙箱和受控测试应用上完成真实 E2E 后，才允许讨论受限研究环境 pilot；不得直接以 SPM/DPABI、真实研究数据或用户桌面作为首个验证环境。
- 截图、可见 UI 文本、剪贴板、日志和模型输入必须最小化、脱敏并可审计；未经批准不得进入模型上下文或持久化。

**明确不做**：

- 当前不修改代码、不启用 `pywinauto`、不改变 mock-only provider policy。
- 不提供任意窗口控制、坐标点击、无限动作循环、后台无人值守执行、跨应用操作、网络访问、rawdata 访问或临床用途。
- 不用 GUI 代替可重现的 MATLAB Engine、SPM Batch、DPABI function wrapper 或现有 Pipeline Runtime。

## Evidence Summary

| 事实 | 代码锚点 | 规划含义 |
|---|---|---|
| Runtime 虽定义 `PyWinAutoGuiProvider`，但 provider guard 只允许 `mock` | `src/backend/app/runtime/gui_agent.py:13-15,115-136` | 不能把已定义的 provider 当作真实能力 |
| mock 操作返回 `executed=False`，截图是占位文本 | `src/backend/app/runtime/gui_agent.py:27-47` | 当前能力只能称为 mock/审计原型 |
| API 在创建、动作、截图前执行 provider policy，真实 provider 返回 403 | `src/backend/app/api/gui_agent_routes.py:1-6,46-50,89-98` | 任何未来启用都必须保留并加强 API/runtime 双层 gate |
| action/session guard 已涵盖动作层级、窗口、文件、截图、剪贴板、网络、停止条件和审计 | `src/backend/app/api/gui_agent_routes.py:53-81,101-214` | 后续实现应扩展既有 guard，而非另建旁路 |
| 模型输入红线明确禁止原始截图、剪贴板、凭据、路径、原始 UI 文本和不安全动作 | `src/backend/app/runtime/gui_model_input_redaction.py:1-12,26-87,170-190` | 真实视觉观察必须先通过最小化/脱敏契约 |

## 实施路线（仅供未来立项，不授权当前开发）

### P0：立项与威胁模型

- 明确 GUI 的唯一业务理由，并证明无确定性 API/Batch/Runtime 替代方案；若可替代，关闭 GUI 路线。
- 选择单一受支持 target application、版本范围和受控测试应用；不以泛化桌面自动化为目标。
- 对窗口伪装、焦点漂移、坐标变化、敏感屏幕内容、剪贴板泄露、错误提交、执行票据重放、应用崩溃及紧急停止完成威胁建模。
- **DoD**：维护者批准新 handoff，指定应用/版本、沙箱、风险等级、人工职责、禁用场景和 rollback 方案。

### P1：隔离环境与 observation-only

- 在可销毁的 Windows VM/沙箱中部署最小依赖和受控假目标应用；禁止挂载真实 rawdata、共享剪贴板和非必需网络。
- 实现可靠的 target window/application identity：进程路径签名或 allowlist、版本、窗口属性、前景焦点和 session 绑定；身份不匹配立即停止。
- 仅开放脱敏的观察结果；真实截图须先经过明确定义的红线扫描与遮罩，默认不持久化，不发送给模型。
- **DoD**：真实 provider 仍无副作用，只能读取受控测试应用的允许状态，并有窗口外阻止和急停测试。

### P2：声明式动作与逐步审批

- 将每个动作定义为版本化 declaration：目标控件稳定标识、预条件、预期可见状态、允许副作用、超时、回滚/人工交接、action tier。
- 动作前须同时满足：有效执行票据、匹配的 GUI approval context、窗口身份、每动作确认、未超过步骤/时长配额、审计已预创建。
- 禁止坐标驱动、自由文本脚本和任意键盘输入；只允许为单一应用验证过的稳定控件选择器。
- **DoD**：每个 action 都可在受控假应用上成功、失败、焦点漂移和拒绝场景中重放；失败不执行下一步。

### P3：受控测试应用 E2E 与恢复

- 构建受控假应用 fixture，覆盖正常窗口、同名伪造窗口、异常弹窗、窗口关闭、延迟响应、坐标/控件变化、截图包含敏感文本和紧急停止。
- 验证 session/ticket/audit/replay 链可复核；应用重启或未知窗口出现时进入 `HUMAN_HANDOFF`，不自动恢复。
- 与阶段七状态机整合：GUI 只报告观察/动作结果，不能自行把 Pipeline 标为成功或发起重规划。
- **DoD**：Windows interactive E2E、故障注入、停止/恢复边界和审计检索全通过；未做真实研究数据 E2E 时必须明确标记。

### P4：研究环境限定 pilot（需再次单独批准）

- 仅在 P0–P3 证据完整、维护者书面批准和受控非临床研究场景下考虑。
- 首次 pilot 仅观察或只读动作；任何会运行 SPM/DPABI、写派生数据或改变研究状态的动作必须另行评审，且不取代 Pipeline Runtime。

## 风险与缓解

| 风险 | 强制缓解 | 验证 |
|---|---|---|
| 同名/伪造窗口、焦点漂移 | 进程/路径/版本/window identity allowlist；每动作复验 | 伪窗口与焦点切换 E2E |
| 误点击或控件变化 | 禁用坐标；声明式控件、预条件、可见状态校验、单步确认 | 控件缺失/变化 fixture |
| 数据与隐私泄露 | 沙箱、无 rawdata、截图/剪贴板默认禁用、模型输入脱敏 | PHI/credential/path redaction tests |
| 无人值守副作用 | session 时限、步骤上限、急停、人工在场、默认 observation-only | 超时/急停/无人场景拒绝 |
| 绕过阶段七执行边界 | GUI actions 必须绑定 ExecutionTicket、audit、capability context | 票据缺失/过期/跨项目/动作不在票据内测试 |
| 把 mock 当成真实能力 | 文档、API status 和 UI 显式区分 `mock_recorded`、`observed`、`executed` | API/schema/UI truthfulness tests |

## Future Files to Read / Likely Change

- `src/backend/app/runtime/gui_agent.py`
- `src/backend/app/runtime/gui_agent_guard.py`
- `src/backend/app/runtime/gui_model_input_redaction.py`
- `src/backend/app/api/gui_agent_routes.py`
- `src/backend/app/api/models.py`
- 阶段七的 `ExecutionGateway`、`ExecutionTicket`、`ToolExecutionContext`、Agent lifecycle 实现
- `tests/unit/test_gui_agent_*.py`、`tests/unit/test_gui_model_*.py`，以及新增 Windows sandbox E2E suite。

具体 Files to Edit、测试环境、允许命令和验收脚本必须由未来 implementation-ready handoff 指定；本计划不授权现在修改这些文件。

## Re-entry Criteria

只有同时满足以下条件，才可将状态改为 `Ready for Codex`：

- [ ] 阶段七 7A–7D 已完成并有可用的网关、ticket、capability、状态机和节点契约。
- [ ] 维护者确认 GUI 不能由确定性 API/Batch 替代，并指定单一 target application 与版本范围。
- [ ] 可销毁 Windows 沙箱、受控假应用、人工急停和无敏感数据测试环境已经就绪。
- [ ] 独立安全审查已批准 provider policy 从 mock-only 向 observation-only 的最小放宽；不包含动作执行放宽。
- [ ] Windows interactive E2E、隐私红线和审计/票据失败路径的验证矩阵已写入新的 handoff。

## Current Conclusion

GUI Agent 仍是“Guard / Mock Adapter Prototype”。本计划保留未来受控实施路线，但**当前不执行、不启用真实 provider，也不将其作为项目已交付能力**。
