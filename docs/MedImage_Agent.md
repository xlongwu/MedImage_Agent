MedImaging Agent：基于 Hermes Agent + Claude Code Agent 架构的可视化医学影像预处理、加速、质控与数据集评估平台。

它不是单纯把 SPM/DPABI 包一层 UI，而是做成一个可视化、多 Agent、可复现、可并行、可 GPU 扩展、能持续积累经验的医学影像工作流系统。

1. 项目定位
1.1 核心目标

构建一个面向医学影像，尤其是 MRI / fMRI / rs-fMRI 的 Agent 系统，支持：

1. 可视化搭建预处理流程
2. 调用 MATLAB / SPM / DPABI / DPARSF 等已有工具
3. 对现有流程进行工程增强：
   - subject 级并行
   - session / run 级并行
   - 断点续跑
   - 缓存复用
   - GPU 加速部分模块
4. 自动执行质量控制 QC
5. 数据集级别评估与报告生成
6. 记忆沉淀：
   - 运行环境
   - 项目经验
   - 错误案例
   - 常用 pipeline
   - 用户偏好
7. 支持长期演进：
   - 失败复盘
   - Skill 自动沉淀
   - Pipeline 模板迭代
1.2 最小可行产品 MVP

第一版不建议做成全模态平台，建议聚焦：

MVP v0.1：rs-fMRI 可视化预处理与数据集评估 Agent

输入：
- BIDS / BIDS-like NIfTI 数据
- T1w
- resting-state BOLD
- participants.tsv / phenotype.csv 可选

后端：
- SPM
- DPABI / DPARSF
- Python QC
- subject 级并行

输出：
- derivatives/
- logs/
- QC figures
- subject_qc_table.csv
- exclusion_recommendations.csv
- dataset_evaluation_report.html / pdf / md
- reproducibility manifest
2. 架构借鉴来源

你的方案可以融合两类思想。

2.1 借鉴 Claude Code：可控执行 Agent

Claude Code 的关键启发是：Agent 不是普通聊天机器人，而是一个“感知—决策—行动”的自主循环系统；用户给目标后，Agent 自己决定读文件、执行命令、修改内容或结束任务。你上传的 Claude Code 解读中明确提到，Agent 的核心是一个自主循环，会根据当前上下文决定下一步行动，直到任务完成。

对你的项目来说，Claude Code 最值得借鉴的是：

1. Tool-Use Loop
   不采用复杂 ReAct 文本解析，而是：
   模型判断 → tool_use 或 end_turn → 工具执行 → 继续循环

2. Plan Mode
   复杂任务先只读探索、生成计划，用户审批后再执行

3. 四层架构
   - 引擎层
   - 工具层
   - 服务层
   - 安全与治理层

4. 工具权限模型
   每个工具声明：
   - 是否只读
   - 是否会修改文件
   - 是否破坏性
   - 是否可并行

5. Hook 系统
   工具执行前后插入验证、审计、QC、错误处理

6. 上下文压缩
   日志和大文件不能直接塞进上下文，要做分层压缩和按需读取

Claude Code 的四层架构里，引擎层只负责协调、分发和决策，不包含业务逻辑；工具层提供读写文件、执行命令、生成子 Agent 等能力；服务层负责模型 API、上下文压缩和 MCP；安全治理层负责权限、Hook 和 Bash 安全分析。这个分层非常适合作为你的系统骨架。

2.2 借鉴 Hermes：长期成长 Agent

Hermes 的关键启发是：Agent 不应该每次都从零开始，而应该能长期积累。你上传的 Hermes 架构解析中把 Hermes 概括为“与你共同成长”，并指出传统 Agent 的问题是无状态、没有积累、没有自检、上下文管理混乱。

对你的项目来说，Hermes 最值得借鉴的是：

1. 三层骨架
   - 感知层 Perception
   - 决策层 Cognition
   - 执行层 Action

2. 六个子系统
   - 用户消息触发器
   - 周期性 Nudge
   - 后台复盘
   - 双文件存储
   - 全息记忆
   - 记忆管理器

3. 四层记忆
   - Prompt Memory
   - Session Archive
   - Skill Memory
   - External Providers

4. 闭合学习回路
   执行 → 评估 → 提炼 → 进化

5. Planner
   Plan → Execute → Replan，而不是一次性计划到底

6. 工程保障
   - 异步复盘
   - 多平台网关
   - 多种部署方式
   - 安全机制
   - 可观测性

Hermes 的架构解析中也强调，其三层结构分别负责理解输入、任务拆解/规划/记忆调取，以及真正调用工具执行任务；这和你的医学影像系统非常贴合。

3. 总体系统架构

建议采用：

Hermes 的三层认知架构 + Claude Code 的四层工程架构

合并后可以设计为七层：

┌───────────────────────────────────────────────┐
│ 1. Visual UI Layer                             │
│    项目管理 / Pipeline Builder / QC Dashboard │
├───────────────────────────────────────────────┤
│ 2. Perception Layer                            │
│    解析用户意图、读取项目状态、扫描数据        │
├───────────────────────────────────────────────┤
│ 3. Cognition / Planner Layer                   │
│    规划、任务拆解、Agent 调度、记忆召回        │
├───────────────────────────────────────────────┤
│ 4. Agent Runtime Layer                         │
│    Tool-Use Loop / Plan Mode / Subagent Router│
├───────────────────────────────────────────────┤
│ 5. Tool & MCP Layer                            │
│    文件、MATLAB、SPM、DPABI、Slurm、GPU、QC    │
├───────────────────────────────────────────────┤
│ 6. Execution Backend Layer                     │
│    MATLAB / SPM / DPABI / Python / GPU / HPC   │
├───────────────────────────────────────────────┤
│ 7. Memory, Safety & Governance Layer           │
│    记忆、权限、Hook、审计、PHI 安全、报告追踪   │
└───────────────────────────────────────────────┘
4. 全流程设计

完整流程如下：

项目创建
  ↓
数据导入与索引
  ↓
BIDS / NIfTI / metadata 检查
  ↓
用户选择或 Agent 推荐 pipeline
  ↓
进入 Plan Mode：只读探索 + 生成计划
  ↓
用户确认
  ↓
生成可执行 DAG
  ↓
资源规划：CPU / GPU / MATLAB license / Slurm
  ↓
执行预处理
  ↓
断点续跑 / 缓存 / 失败重试
  ↓
Subject 级 QC
  ↓
数据集级评估
  ↓
报告生成
  ↓
后台复盘
  ↓
更新长期记忆 / Skill / 错误知识库
5. Agent 角色设计
5.1 主 Agent：Orchestrator Agent

职责：

- 接收用户目标
- 判断任务复杂度
- 决定是否进入 Plan Mode
- 调度各个 subagent
- 合并执行结果
- 控制是否继续 tool-use loop
- 决定何时 end_turn

借鉴 Claude Code 的 Tool-Use Loop：

while true:
    读取当前任务状态
    调用模型判断下一步
    if tool_use:
        执行对应工具
        将结果写入消息 / 状态
        continue
    if end_turn:
        返回结果
        break

对于医学影像任务，主 Agent 不直接执行 MATLAB 或写文件，而是把任务分给专用 Agent。

5.2 Data Inspector Agent

负责数据检查。

输入：

rawdata/
participants.tsv
dataset_description.json
sidecar json

功能：

- 扫描 subject / session / run
- 检查 T1w、BOLD、DWI、fmap 是否存在
- 检查 BIDS 命名
- 检查 NIfTI 是否可读取
- 读取 TR、slice timing、phase encoding direction
- 检查 participants.tsv / phenotype.csv
- 生成 dataset_index.json

输出：

dataset_index.json
data_completeness_report.json
missing_files.csv
naming_issues.csv
5.3 Pipeline Designer Agent

负责生成流程图。

功能：

- 根据任务类型推荐 pipeline
- 生成 DAG
- 为每个节点绑定 backend
- 检查输入输出依赖
- 判断哪些节点可并行
- 判断哪些节点可 GPU 加速
- 生成 pipeline.yaml

例如：

pipeline_id: rsfmri_dpabi_v1
modality: rs-fmri
nodes:
  - id: remove_first_volumes
    backend: python
    parallel_level: subject
    gpu_supported: false

  - id: realign
    backend: spm
    parallel_level: subject
    gpu_supported: false

  - id: normalize
    backend: spm
    parallel_level: subject
    gpu_supported: false

  - id: nuisance_regression
    backend: python-gpu
    parallel_level: subject
    gpu_supported: true

  - id: alff
    backend: cupy
    parallel_level: subject
    gpu_supported: true
5.4 MATLAB / SPM Agent

职责：

- 检查 MATLAB 路径
- 检查 SPM 路径
- 生成 matlabbatch
- 调用 spm_jobman
- 保存 batch 文件
- 捕获 stdout / stderr
- 解析 SPM 错误

要求：

- 不直接修改 rawdata
- 所有输出进入 derivatives 或 work
- 所有 batch 文件保存
- 所有命令记录到 manifest
- 失败时返回结构化错误
5.5 DPABI / DPARSF Agent

职责：

- 生成 DPABI / DPARSF 参数文件
- 调用 DPABI 批处理
- 检查输出目录
- 解析 DPABI 输出
- 生成 DPABI 节点级 QC

适合第一版承担：

- rs-fMRI 标准预处理
- ALFF / fALFF
- ReHo
- FC / ROI time series
5.6 Scheduler Agent

职责：

- subject 级并行
- session / run 级并行
- Slurm array job
- Docker / Singularity worker
- MATLAB license 队列
- GPU 资源分配
- 失败重试
- 断点续跑

调度原则：

优先 subject 级并行
再做 node 级并行
最后才做 GPU kernel 级优化
5.7 GPU Optimizer Agent

职责：

- 判断哪些节点适合 GPU
- 选择 GPU backend
- 估计显存需求
- 自动 chunking
- CPU fallback
- benchmark CPU vs GPU

第一阶段建议 GPU 化：

高优先级：
- ALFF / fALFF
- ROI / voxel-wise correlation
- nuisance regression
- temporal filtering
- FC matrix

暂不建议第一阶段 GPU 化：
- SPM normalization
- segmentation
- registration
5.8 QC Agent

负责 subject 级质量控制。

指标：

- mean FD
- max FD
- FD > 0.2 / 0.5 / 1.0 volume count
- motion plots
- DVARS
- tSNR
- mean BOLD
- coregistration snapshot
- normalization snapshot
- brain mask overlap

输出：

qc/sub-001/
├── motion_plot.png
├── fd_summary.json
├── normalization_snapshot.png
├── coreg_snapshot.png
└── qc_status.json
5.9 Dataset Evaluation Agent

负责数据集级评估。

它回答：

- 这个数据集是否完整？
- 预处理成功率是多少？
- 哪些 subject 可用？
- 哪些 subject 建议排除？
- 哪些需要人工复核？
- 组间 / 站点 / 扫描仪是否有偏倚？
- 是否适合后续统计分析或机器学习？

输出：

dataset_evaluation/
├── report.html
├── report.pdf
├── report.md
├── dataset_summary.json
├── subject_qc_table.csv
├── exclusion_recommendations.csv
└── figures/

报告章节：

1. Executive Summary
2. Dataset Overview
3. Data Completeness
4. Preprocessing Success Rate
5. Motion QC
6. Registration / Normalization QC
7. Signal Quality Assessment
8. Group / Site / Scanner Balance
9. Outlier Subjects
10. Recommended Exclusion List
11. Downstream Analysis Readiness
12. Reproducibility Information
13. Appendix
5.10 Error Diagnosis Agent

职责：

- 读取 MATLAB / SPM / DPABI / Python / Slurm 日志
- 匹配错误知识库
- 判断是否可重试
- 给出修复建议
- 生成 retry plan

示例结构：

error_pattern: "CUDA out of memory"
source: gpu
probable_causes:
  - chunk size too large
  - insufficient GPU memory
suggested_fixes:
  - reduce voxel chunk size
  - use CPU fallback
  - submit to larger GPU
retryable: true
5.11 Report Agent

负责最终报告生成：

- 技术报告
- QC 报告
- 数据集评估报告
- 方法学报告
- 可复现性报告

输出格式：

Markdown
HTML
PDF
CSV
JSON
6. 可视化 UI 设计
6.1 页面结构
1. Project Dashboard
2. Dataset Browser
3. Pipeline Builder
4. Parameter Panel
5. Run Monitor
6. Log Viewer
7. QC Dashboard
8. Dataset Evaluation Dashboard
9. Report Center
10. Memory / Settings
6.2 Project Dashboard

显示：

Project: ADHD_rsFMRI_2026
Total subjects: 120
Valid subjects: 112
Preprocessed: 104
Manual review: 8
Recommended exclusion: 16
Dataset quality score: 78 / 100
6.3 Pipeline Builder

采用拖拽式 DAG：

[DICOM to NIfTI]
        ↓
[BIDS Check]
        ↓
[Remove First Volumes]
        ↓
[Slice Timing]
        ↓
[Realignment]
        ↓
[Coregistration]
        ↓
[Normalization]
        ↓
[Smoothing]
        ↓
[Nuisance Regression]
        ↓
[Filtering]
        ↓
[ALFF / fALFF]
        ↓
[QC Report]
        ↓
[Dataset Evaluation]

每个节点有参数面板：

node: smoothing
backend: spm
params:
  fwhm: [6, 6, 6]
parallel:
  level: subject
gpu:
  enabled: false
qc:
  required_outputs:
    - smoothed_bold
6.4 Run Monitor

显示：

sub-001  normalize       done
sub-002  smoothing       running
sub-003  normalization   failed
sub-004  alff_gpu        queued

支持操作：

- 查看日志
- 解释错误
- 重跑该节点
- 跳过 subject
- 标记为人工复核
- 标记为排除
6.5 QC Dashboard

显示：

- FD 分布
- tSNR 分布
- DVARS
- motion plots
- normalization snapshots
- failed subjects
- suspicious subjects
- recommended exclusion list
7. Plan Mode 设计

借鉴 Claude Code 的 Plan Mode：复杂任务先规划，用户确认后执行。Claude Code 解读中提到，Plan Mode 是“先规划、再执行”的两阶段工作流，进入该模式后先只读探索，用户审批后才恢复执行权限。

在你的系统中：

7.1 什么时候进入 Plan Mode
- 创建新项目
- 第一次运行 pipeline
- 批量处理超过 N 个 subject
- 会覆盖已有 derivatives
- 会提交 Slurm / GPU 任务
- 会使用新 GPU 模块
- 会修改 pipeline template
7.2 Plan Mode 权限

只允许：

- 读取目录
- 扫描数据
- 读取配置
- 检查软件版本
- 估算资源
- 生成计划

禁止：

- 写 derivatives
- 删除文件
- 运行 MATLAB
- 提交 Slurm
- 启动 GPU 任务
- 覆盖历史结果
7.3 Plan 输出
plan_id: plan_2026_05_01_001
project: ADHD_rsFMRI_2026
pipeline: rsfmri_dpabi_v1
subjects: 120
estimated_runtime: "8-12 hours"
execution_mode: slurm_array
risk_level: medium
requires_confirmation:
  - write_derivatives
  - submit_slurm_jobs
  - use_gpu_nodes

用户确认后进入执行阶段。

8. Tool / MCP 层设计

借鉴 Claude Code 的专用工具原则：能用专用工具就不用 Bash，因为专用工具更可审查，也更容易做权限控制。你上传的文档明确指出，专用工具不仅改善可审查性，还能做路径和权限检查，比直接用 Bash 更安全。

8.1 Tool Registry
filesystem.read
filesystem.write
filesystem.list
filesystem.hash

nifti.inspect
nifti.snapshot
bids.validate
metadata.read

matlab.check
matlab.run
spm.build_batch
spm.run_batch
dpabi.build_config
dpabi.run_pipeline

scheduler.submit
scheduler.status
scheduler.cancel
scheduler.retry

gpu.check
gpu.benchmark
gpu.run_node

qc.compute_motion
qc.compute_tsnr
qc.generate_snapshot

report.write_html
report.write_pdf

memory.read
memory.write
memory.search
8.2 每个工具必须声明
name: spm.run_batch
read_only: false
writes_files: true
destructive: false
requires_confirmation: true
parallel_safe: false
allowed_paths:
  read:
    - rawdata/
    - work/
  write:
    - derivatives/
    - logs/
    - work/
9. 安全与权限模型

Claude Code 的操作安全原则强调用“可逆性”和“影响范围”判断风险：可逆、只影响本地的操作可以放行；不可逆或影响他人的操作需要确认。

医学影像场景建议更严格。

9.1 默认目录权限
rawdata/        只读
sourcedata/     只读
derivatives/   可写，不默认覆盖
work/          可写
logs/          可写
reports/       可写
memory/        可写，但禁止 PHI
9.2 高风险操作

必须确认：

- 删除文件
- 覆盖 derivatives
- 修改 rawdata
- 批量重跑
- 上传数据到外部 API
- 修改全局 MATLAB path
- 修改 SPM / DPABI 安装目录
- 提交大规模 Slurm job
- 使用全部 GPU 资源
9.3 PHI / 隐私边界

长期记忆禁止保存：

- 患者姓名
- 身份证
- 住院号
- 原始 DICOM header 中的敏感字段
- 原始影像内容

允许保存：

- 脱敏 subject ID
- pipeline 参数
- 软件版本
- QC 指标
- 错误类型
- 运行时间
- 文件 hash
10. 记忆系统设计

融合 Hermes 和 Claude Code。

Hermes 的记忆系统分为 Prompt Memory、Session Archive、Skill Memory 和 External Providers；其中 Prompt Memory 用 MEMORY.md / USER.md 保持稳定底座，Session Archive 用 SQLite / FTS 检索历史，会话需要时再摘要注入，Skill Memory 则沉淀“怎么做”。

你的系统可以设计为：

memory/
├── global/
│   ├── MEMORY.md
│   ├── USER.md
│   ├── ENVIRONMENT.md
│   ├── ERROR_KB.md
│   └── TOOL_REGISTRY.md
├── projects/
│   └── ADHD_rsFMRI_2026/
│       ├── PROJECT.md
│       ├── PIPELINE_DEFAULTS.yaml
│       ├── QC_RULES.yaml
│       ├── LESSONS.md
│       └── RUN_HISTORY.sqlite
├── skills/
│   ├── spm-rsfmri-preprocessing.md
│   ├── dpabi-rsfmri-preprocessing.md
│   ├── gpu-alff.md
│   └── dataset-evaluation.md
└── sessions/
    └── archive.sqlite
10.1 短期记忆

保存当前运行状态：

{
  "run_id": "run_001",
  "current_subject": "sub-017",
  "current_node": "normalization",
  "status": "failed",
  "error": "missing T1w",
  "next_action": "manual review"
}
10.2 长期记忆

保存跨项目经验：

## DPABI rs-fMRI default

For local lab rs-fMRI datasets:
- discard first 10 volumes
- default smoothing FWHM = 6mm
- mean FD threshold = 0.5
- generate normalization snapshots for all subjects

Why:
These settings match the lab's historical preprocessing protocol.

How to apply:
Use only for adult resting-state fMRI unless project-specific config overrides it.
10.3 记忆原则
记：
- 用户偏好
- 运行环境
- 项目约定
- 错误经验
- QC 阈值
- pipeline 模板
- 工具坑点

不记：
- 原始影像内容
- 可从文件系统重新扫描的信息
- Git / 文件历史
- 临时日志全文
- PHI
11. Skill 系统设计

Hermes 的 Skill Memory 是程序性记忆，记录“怎么做”；其闭合学习回路是执行、评估、提炼、进化，并且 Skill 会通过补丁方式持续迭代。

你的系统中 Skill 可以包括：

skills/
├── bids-inspection/
├── spm-rsfmri-preprocessing/
├── dpabi-rsfmri-preprocessing/
├── gpu-alff/
├── gpu-connectivity/
├── motion-qc/
├── normalization-qc/
├── dataset-evaluation/
└── slurm-execution/

每个 Skill 包含：

SKILL.md
templates/
scripts/
references/
tests/

示例：

---
name: dataset-evaluation
description: evaluate a preprocessed neuroimaging dataset by aggregating data completeness, preprocessing success, motion qc, registration qc, signal quality, group balance, outliers, exclusion recommendations, and downstream readiness.
---

# Dataset Evaluation Skill

Inputs:
- dataset_index.json
- preprocessing_status.csv
- subject_qc_table.csv
- participants.tsv

Outputs:
- dataset_summary.json
- exclusion_recommendations.csv
- report.html
- report.pdf

Rules:
- Do not make clinical diagnosis.
- Separate Include / Manual Review / Exclude.
- Always report thresholds.
- Always preserve subject-level traceability.
12. Pipeline Schema

这是整个系统的核心。

pipeline_id: rsfmri_dpabi_v1
version: 0.1.0
modality: rs-fmri
description: "BIDS-like resting-state fMRI preprocessing using SPM and DPABI"

inputs:
  required:
    - T1w
    - BOLD
  optional:
    - fieldmap
    - participants.tsv

nodes:
  - id: bids_check
    agent: data-inspector
    backend: python
    inputs: ["rawdata"]
    outputs: ["dataset_index.json"]
    parallel_level: project
    gpu_supported: false
    cache: true

  - id: remove_first_volumes
    agent: pipeline-executor
    backend: python
    inputs: ["raw_bold"]
    outputs: ["trimmed_bold"]
    params:
      n_remove: 10
    parallel_level: subject
    gpu_supported: false

  - id: realign
    agent: spm-runner
    backend: spm
    inputs: ["trimmed_bold"]
    outputs: ["realigned_bold", "motion_params"]
    parallel_level: subject
    gpu_supported: false

  - id: normalize
    agent: spm-runner
    backend: spm
    inputs: ["realigned_bold", "T1w"]
    outputs: ["normalized_bold"]
    parallel_level: subject
    gpu_supported: false

  - id: nuisance_regression
    agent: gpu-optimizer
    backend: python-cupy
    inputs: ["normalized_bold", "motion_params"]
    outputs: ["cleaned_bold"]
    parallel_level: subject
    gpu_supported: true
    cpu_fallback: true

  - id: alff
    agent: gpu-optimizer
    backend: python-cupy
    inputs: ["cleaned_bold"]
    outputs: ["alff_map", "falff_map"]
    parallel_level: subject
    gpu_supported: true
    cpu_fallback: true

  - id: qc
    agent: qc-agent
    backend: python
    inputs: ["outputs"]
    outputs: ["subject_qc.json", "qc_figures"]
    parallel_level: subject

  - id: dataset_evaluation
    agent: dataset-evaluator
    backend: python
    inputs: ["subject_qc_table.csv", "participants.tsv"]
    outputs: ["dataset_report.html", "dataset_report.pdf"]
    parallel_level: project
13. 执行状态机

每个 subject × node 都要有状态。

PENDING
READY
RUNNING
SUCCESS
FAILED
SKIPPED
CACHED
RETRYING
NEEDS_REVIEW
EXCLUDED

状态记录：

{
  "run_id": "run_2026_05_01_001",
  "subject": "sub-017",
  "node": "normalization",
  "status": "FAILED",
  "started_at": "2026-05-01T10:32:00",
  "ended_at": "2026-05-01T10:45:22",
  "error_type": "missing_t1",
  "retryable": false,
  "log_path": "outputs/logs/sub-017/normalization.log",
  "outputs": [],
  "recommendation": "manual_review"
}
14. 缓存与断点续跑

每个节点输出：

work/sub-001/normalize/
├── inputs.hash
├── params.hash
├── code_version.txt
├── outputs.json
├── status.json
└── logs/

重跑规则：

输入 hash 变化 → 重跑
参数 hash 变化 → 重跑
节点实现版本变化 → 建议重跑
输出缺失 → 重跑
状态 FAILED → 根据 retryable 决定
状态 SUCCESS 且 hash 未变 → 缓存命中
15. GPU 与并行化方案
15.1 并行化优先级
优先级 1：subject 级并行
优先级 2：session / run 级并行
优先级 3：node 级并行
优先级 4：GPU kernel 级加速

第一版先做：

- 多 subject 并行
- Slurm array
- MATLAB 独立进程
- 每个 subject 独立 work directory
15.2 GPU 优先模块
第一批：
- ALFF / fALFF
- FC matrix
- nuisance regression
- temporal filtering
- ROI correlation

第二批：
- ReHo
- permutation testing
- large-scale statistics

暂缓：
- registration
- normalization
- segmentation
15.3 GPU 节点执行策略
gpu:
  enabled: true
  backend: cupy
  memory_policy: auto_chunk
  fallback: cpu
  validation:
    compare_to_cpu: true
    tolerance: 1e-5
16. 数据集评估方案
16.1 评估维度
1. 数据完整性
2. 预处理成功率
3. 头动质量
4. 配准 / 标准化质量
5. 信号质量
6. 组间 / 站点 / 扫描仪平衡
7. 异常值
8. 排除建议
9. 下游分析准备度
10. 可复现性
16.2 输出分类
Include
Manual Review
Exclude
16.3 数据集评分
Dataset Quality Score: 0-100

数据完整性：20
预处理成功率：20
头动质量：20
配准质量：15
信号质量：15
组间/站点平衡：10

示例：

Total subjects: 120
Successfully preprocessed: 104
Recommended include: 96
Manual review: 8
Recommended exclusion: 16
Dataset quality score: 78 / 100
Rating: Moderate to Good
17. 上下文与日志管理

Claude Code 文档中提到，简单截断上下文会导致 Agent 忘掉关键文件，全量摘要又昂贵且有信息损失，因此采用从轻到重的五步压缩策略：大结果存磁盘、砍掉远古消息、裁剪老工具输出、读时投影、最后才全量摘要。

医学影像场景日志很大，必须借鉴这个策略。

17.1 日志处理
完整日志：存磁盘
上下文中：只放摘要
需要诊断时：按行范围读取
报告中：只放关键错误

结构：

logs/
├── sub-001/
│   ├── matlab_stdout.log
│   ├── matlab_stderr.log
│   ├── spm_error_summary.json
│   └── node_events.jsonl
17.2 大文件策略
NIfTI：不进入上下文，只读 metadata / snapshot / metrics
日志：超过阈值存磁盘，只保留摘要
QC 图：保存文件路径和缩略图
CSV：只读取表头、统计摘要和异常行
18. Hook 系统
18.1 Hook 列表
hooks:
  before_project_create:
    - check_workspace_permission

  before_pipeline_plan:
    - scan_dataset
    - check_required_metadata

  before_pipeline_run:
    - check_disk_space
    - check_matlab_available
    - check_spm_dpabi_paths
    - check_gpu_available
    - require_user_approval_if_overwrite

  before_node_run:
    - validate_node_inputs
    - check_cache
    - allocate_resources

  after_node_run:
    - validate_outputs
    - collect_logs
    - update_state
    - generate_node_qc

  on_node_failure:
    - parse_error
    - match_error_kb
    - decide_retry_or_review

  after_pipeline_run:
    - aggregate_qc
    - run_dataset_evaluation
    - generate_report
    - update_memory

  background_review:
    - summarize_lessons
    - update_error_kb
    - propose_skill_patch
19. 后台复盘与自我改进

借鉴 Hermes 的 Background Review：主流程不阻塞，后台异步总结。Hermes 文档中强调 Background Review 通过独立进程异步运行，负责总结和提炼技能，不影响主对话体验。

你的系统可设计：

每次 pipeline run 结束后：
1. 读取 run_summary.json
2. 读取 failed_subjects.json
3. 总结常见错误
4. 判断是否需要更新 ERROR_KB
5. 判断是否需要新建或修补 Skill
6. 写入 project LESSONS.md
7. 给用户展示“建议学习项”

示例：

## Background Review: run_001

Findings:
- 12 subjects failed normalization.
- 9 failures were caused by missing T1w.
- Current Data Inspector did not detect non-BIDS T1 naming.

Suggested updates:
- Add non-BIDS T1 filename detection.
- Add fallback rule: search anat/T1.nii if sub-xxx_T1w.nii missing.
- Update spm-rsfmri-preprocessing skill.
20. 技术栈建议
前端
React + TypeScript
React Flow：Pipeline DAG
Ant Design / MUI：表单、表格
Niivue：NIfTI 浏览
Plotly / ECharts：QC 图
WebSocket：实时日志
后端
FastAPI
PostgreSQL
Redis
Celery / Dramatiq / Ray
Pydantic
SQLAlchemy
Docker SDK
Slurm wrapper
执行后端
MATLAB
SPM
DPABI / DPARSF
Python
CuPy / PyTorch
Docker
Singularity
Slurm / PBS
存储
PostgreSQL：项目、运行、状态
SQLite：会话归档、本地轻量部署
Filesystem：影像、日志、报告
Object Storage 可选：大规模报告归档
21. 推荐仓库结构
medimg-agent/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ProjectDashboard.tsx
│   │   │   ├── DatasetBrowser.tsx
│   │   │   ├── PipelineBuilder.tsx
│   │   │   ├── RunMonitor.tsx
│   │   │   ├── QCDashboard.tsx
│   │   │   └── ReportCenter.tsx
│   │   └── components/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── runtime/
│   │   ├── tools/
│   │   ├── hooks/
│   │   ├── memory/
│   │   ├── scheduler/
│   │   ├── workflows/
│   │   └── reports/
│   └── pyproject.toml
│
├── agents/
│   ├── orchestrator.md
│   ├── data-inspector.md
│   ├── pipeline-designer.md
│   ├── spm-runner.md
│   ├── dpabi-runner.md
│   ├── scheduler.md
│   ├── gpu-optimizer.md
│   ├── qc-agent.md
│   ├── dataset-evaluator.md
│   ├── error-diagnoser.md
│   └── report-agent.md
│
├── tools/
│   ├── filesystem.py
│   ├── nifti_inspector.py
│   ├── bids_validator.py
│   ├── matlab_runner.py
│   ├── spm_batch_builder.py
│   ├── dpabi_config_builder.py
│   ├── slurm_runner.py
│   ├── gpu_runner.py
│   ├── qc_metrics.py
│   └── report_writer.py
│
├── matlab/
│   ├── spm/
│   │   ├── run_spm_realign.m
│   │   ├── run_spm_normalize.m
│   │   └── run_spm_smooth.m
│   └── dpabi/
│       └── run_dpabi_pipeline.m
│
├── gpu/
│   ├── alff_cupy.py
│   ├── falff_cupy.py
│   ├── fc_matrix_cupy.py
│   └── nuisance_regression_gpu.py
│
├── workflows/
│   ├── rsfmri_dpabi.yaml
│   ├── taskfmri_spm.yaml
│   └── vbm_spm.yaml
│
├── skills/
│   ├── bids-inspection/
│   ├── spm-rsfmri-preprocessing/
│   ├── dpabi-rsfmri-preprocessing/
│   ├── gpu-alff/
│   └── dataset-evaluation/
│
├── memory/
│   ├── global/
│   ├── projects/
│   ├── sessions/
│   └── skills/
│
├── containers/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker-spm
│   ├── Dockerfile.worker-dpabi
│   ├── Dockerfile.worker-gpu
│   └── singularity.def
│
├── specs/
│   ├── pipeline_schema.yaml
│   ├── node_interface.md
│   ├── run_state_machine.md
│   ├── memory_spec.md
│   ├── tool_permission_spec.md
│   └── dataset_evaluation_report.md
│
└── tests/
    ├── unit/
    ├── integration/
    ├── benchmark/
    └── regression/
22. 开发路线图
Phase 0：规范设计

产出：

- pipeline_schema.yaml
- node_interface.md
- run_state_machine.md
- tool_permission_spec.md
- memory_spec.md
- dataset_evaluation_report.md

目标：先把系统骨架定死。

Phase 1：MVP 跑通

功能：

- 项目创建
- BIDS-like 数据扫描
- rs-fMRI pipeline template
- SPM / DPABI wrapper
- subject 级并行
- Run Monitor
- 日志查看
- 基础 QC
- HTML 报告
Phase 2：Agent 化

功能：

- Orchestrator Agent
- Data Inspector Agent
- Pipeline Designer Agent
- SPM / DPABI Agent
- QC Agent
- Error Diagnosis Agent
- Tool-Use Loop
- Plan Mode
- 工具权限系统
Phase 3：数据集评估

功能：

- subject_qc_table.csv
- exclusion recommendation
- group / site balance
- dataset quality score
- dataset evaluation report
Phase 4：GPU 与高性能

功能：

- GPU ALFF / fALFF
- GPU FC matrix
- GPU nuisance regression
- CPU vs GPU benchmark
- Slurm GPU queue
- CPU fallback
Phase 5：长期记忆与 Skill 自进化

功能：

- MEMORY.md / USER.md
- project LESSONS.md
- ERROR_KB.md
- Skill Memory
- Background Review
- Skill patch proposal
23. 最终方案总结

你的项目最终可以定义为：

一个面向医学影像预处理的可视化 Agent 工作流平台，借鉴 Claude Code 的 Tool-Use Loop、Plan Mode、工具权限和 Hook 治理，借鉴 Hermes 的长期记忆、后台复盘、Skill 沉淀和 Plan → Execute → Replan 机制，实现从数据导入、预处理、并行/GPU 加速、QC、数据集评估到报告生成的全流程自动化系统。

第一版不要追求“全自动替代专家”，而是追求：

1. 流程可视化
2. 执行可复现
3. 错误可诊断
4. QC 可追踪
5. 报告可导出
6. 经验可沉淀
7. 加速可验证

这套系统最有价值的地方不是“会聊天”，而是能把医学影像预处理变成一个可审计、可复现、可扩展、会逐步变聪明的工程化平台。