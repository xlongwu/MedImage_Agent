# 阶段九：RC2 功能冻结、证据收敛与 Windows 发布验证

> 状态：In Progress — G9-0/G9-1 收敛中，G9-3 已有源码级证据
> 任务模式：Release and Packaging Mode；真实数据链路同时适用 Scientific Validation Mode。
> 目标版本：`v0.6.0-rc2`。

## 主线

1. 同步 `PROJECT_STATE.md`、能力矩阵和阶段七/八状态。
2. 冻结 `main` 的执行路径、科学算法和能力等级。
3. 从候选提交重新构建 Windows 打包应用。
4. 使用 `data/DemoData` 的 `Sub_001`、`Sub_002`、`Sub_003` 运行真实多受试者 E2E。
5. 验证正常退出、强制终止、重启恢复、失败受试者隔离和经审批的局部重试。
6. 固化远端 CI、构建、运行、产物、rawdata 不变性和版本一致性证据。
7. 所有关卡通过后发布 `v0.6.0-rc2`；任一关卡失败则保持 `rc1`，不得带病打标。

## 当前证据快照（2026-07-16）

- Windows 源码全量后端：`4108 passed, 16 skipped`。
- 前端：format、typecheck、`238` tests、production build 全部通过。
- DemoData 三被试：6 个 DICOM 序列转换为 6 个 NIfTI/JSON 对；rawdata
  1,104 个文件、总大小和指纹前后不变。
- reviewed gateway 源码 E2E：三被试产生 21 个原生空间预处理 NIfTI，
  ALFF/fALFF 使用 `gpu-cupy`；恢复复跑复用转换登记，转换审计未重写。
- 上述证据不替代 G9-2 打包应用、G9-4 完整退出/崩溃/恢复矩阵或 G9-5
  exact-SHA 远端 CI。

详细范围、风险、证据与关卡见[阶段九总体计划](阶段九_RC2发布收敛总体计划.md)。

## 冻结规则

冻结期间只接受发布阻塞修复、测试、证据和文档修正。以下改动必须退出 RC2 主线并重新立项：

- 新执行入口或 Runner；
- 科学公式、默认参数或能力等级升级；
- 新公共 API 或持久化契约；
- 新的必选依赖；
- 开启 MATLAB、SPM、DPABI、真实 GUI 自动化或外部命令执行；
- 任何 rawdata 写入或安全门控弱化。
