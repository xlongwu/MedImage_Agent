# 阶段十一：自动 AC-PC 与受控 Agent Harness

> 状态：Proposed，尚未进入实现或发布范围。  
> 前置条件：先完成 RC2 收敛，维护者重新开启 capability review，并把当前工作区整理为可追溯的基线。

本阶段有三个独立计划：先完善现有规划、执行、工具和记忆，再实现自动 AC-PC；Harness 最后接入，避免多个任务同时改动 Agent Task、ProjectStore 和审批链。

1. [计划 01：自动 AC-PC 定位并移除 GUI Agent](计划01_自动ACPC定位与移除GUIAgent.md)
2. [计划 02：受控单 Agent Harness](计划02_受控单AgentHarness.md)
3. [计划 03：规划、执行、工具调用与记忆完善](计划03_规划执行工具调用与记忆完善.md)

## 建议实施顺序

`计划 03 -> 计划 01 -> 计划 02`。计划 01 与计划 03 可在不同分支准备，但不得并行修改 `agent_task_command_service.py`、`mock_store.py`、`agent_task.py` 或 `PROJECT_STATE.md`。

## 阶段共同边界

- 不写入、重命名或删除 `rawdata/`、源 BIDS、源 DICOM 或已登记源 NIfTI。
- LLM 只能提出结构化建议；只有既有的 Approval Gate、Execution Ticket 和 Execution Gateway 能启动科学计算。
- 每项能力默认关闭，先有迁移、测试和文档，再允许在隔离项目中启用。
- 阶段完成后，把长期规则迁入正式规范、架构与安全文档；本目录只保留阶段计划和验收记录。
