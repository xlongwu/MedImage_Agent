# 阶段十：Agent-first 前端与交互收敛

> 状态：Proposed — Blocked by Phase 9 `G9-6`
>
> 目标版本：`v0.7.0-rc1` 候选能力线，不得并入 `v0.6.0-rc2` 冻结主线。
>
> 主任务模式：Feature Bundle Mode + Architecture and Refactor Mode。
>
> 涉及受控执行、DICOM 转换或真实科学链路时，叠加 Scientific Validation Mode 与受保护模块规则。

本阶段把项目内默认操作模式从“用户逐页驱动流水线”收敛为“用户描述目标，Agent 生成受控计划并在一次集中审批后推进”。Agent Task 只是既有 Agent Lifecycle、Reviewed Plan、Execution Ticket、Observation、Goal Evaluation、Recovery 和 Artifact Evidence 的前端投影，不保存第二份流程状态。

## 启动前置条件

只有同时满足以下条件，维护者才可把任务状态改为 `Ready for Implementation`：

1. 阶段九 `G9-6` 已关闭，RC2 已发布或维护者明确终止 RC2 主线；
2. 为阶段十创建独立 `codex/` 分支或 worktree；
3. 当前未提交的前端改动已经归属清楚，不与阶段十实现并行编辑；
4. 维护者确认 DICOM 路径是纳入 10E，还是先只交付 BIDS Agent-first 流程；
5. 维护者确认生命周期最小扩展（等待补充信息、等待科学决策、执行前取消）可以进入 `v0.7.0-rc1`。

## 文档导航

1. [阶段十总体计划](阶段十_Agent-first前端与交互收敛总体计划.md)
2. [任务 10A：交互基线与 Agent Task 投影层](任务10A_交互基线与AgentTask投影层.md)
3. [任务 10B：目标编排、科学决策与集中审批](任务10B_目标编排科学决策与集中审批.md)
4. [任务 10C：Agent Workspace 与导航收敛](任务10C_AgentWorkspace与导航收敛.md)
5. [任务 10D：自动观察、结果、恢复与高级证据](任务10D_自动观察结果恢复与高级证据.md)
6. [任务 10E：DICOM 执行入口收敛](任务10E_DICOM执行入口收敛.md)
7. [任务 10F：真实 E2E 与交互验收](任务10F_真实E2E与交互验收.md)

## 推荐实施顺序

```text
阶段九 G9-6
  -> 10A 投影层与基线
  -> 10B BIDS 目标编排与审批
  -> 10C Agent-first Shell
  -> 10D 自动观察、结果与恢复
  -> 10E DICOM Gateway 收敛（独立保护性关卡）
  -> 10F BIDS / DICOM / Recovery 真实 E2E
```

10C 可以在 10B API 契约冻结后开始，但同一任务仍遵守单一代码所有者规则；不允许多个实现 Agent 同时编辑同一分支。10E 失败不得阻止 BIDS Agent-first 能力按真实范围验收，但会阻止宣称“DICOM 一句话完成”已交付。

## 冻结边界

- 阶段十计划文档可以在 RC2 冻结期内维护。
- 新公共 Agent Task API、生命周期 schema、执行入口、前端默认导航和持久化变化均属于能力扩展，在阶段九关闭前禁止实施。
- 本阶段不得借交互收敛修改科学公式、能力等级或 rawdata 只读边界。
