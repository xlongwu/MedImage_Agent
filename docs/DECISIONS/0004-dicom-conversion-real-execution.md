# ADR-004: DICOM 转换真实执行路线

## Status
Accepted (2026-06-14) — previously Proposed. Public execute endpoint exists in `api/execute_reviewed_routes.py`, feature-flagged frontend UI in `DicomConversionExecutePanel.tsx`, and safety contracts are in place. Dry-run only was an earlier transitional state; real execution is the intended target.

## Context
当前 DICOM 转换仅支持 dry-run（生成映射预览，不创建文件）。FunRaw/T1Raw 数据（1104 DICOM 验证通过）需要通过 dcm2niix 转换为 NIfTI 格式才能进入完整预处理链。已完成的准备工作：
- 安全合同：`dicom_conversion_safety.py`
- 执行服务：`dicom_conversion_execution.py` (69KB)
- 审批门设计：`dicom_conversion_approval.py`
- 发布就绪检查：`dicom_conversion_release_readiness.py`
- 前端面板：`DicomConversionExecutePanel.tsx`, `DicomConversionReviewPanel.tsx`
- 12+ 相关 schema / 服务文件

两种可选方案：

1. **独立安全沙箱执行** — dcm2niix 在独立子进程中运行，受限文件系统访问
2. **集成到 Pipeline Runtime** — DICOM 转换作为特殊 preprocessing 节点

## Decision
**采用 Option 1：独立安全沙箱执行，通过专用 API endpoint 和前端面板交互。**

理由：
1. dcm2niix 是 C 编译的本机二进制，不应与 Python pipeline 共享进程空间
2. 安全边界更清晰：独立子进程 + 受限文件系统访问
3. 已有完整的安全合同、审批门、审计设计（12+ 文件），只需执行
4. 前端面板已就绪
5. 遵循现有安全架构（Approval Gate + Audit Record + Sandbox）

## Consequences

### 正面
- 解锁真实 DICOM → NIfTI 转换能力
- FunRaw/T1Raw 数据可直接进入完整预处理链
- 安全边界独立，不影响现有 Python/SPM 执行
- 不修改 pipeline_executor.py 或 Approval Gate 核心逻辑

### 负面
- 引入外部依赖（dcm2niix），需管理版本和安装
- 新增独立执行路径，需要独立监控和错误处理
- dcm2niix 行为因版本/平台而异，需充分测试

### 风险缓解
- dcm2niix 版本锁定（通过 Docker 或 bundled binary）
- 转换输出指纹验证（SHA256）
- 转换前 dry-run 预览，转换后 BIDS 验证
- 参考文档: `docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md`

## 相关文档
- `docs/DICOM_TO_NIFTI_EXECUTION_WRAPPER_CONTRACT.md`
- `docs/DICOM_CONVERSION_APPROVAL_GATE_DESIGN.md`
- `docs/DICOM_CONVERSION_RELEASE_HARDENING.md`
- `docs/architecture.md` — 安全边界与 Pipeline Runtime

---
*创建于：2026-06-14*
