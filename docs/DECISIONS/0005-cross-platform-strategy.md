# ADR-005: 跨平台策略

## Status
Accepted (2026-06-14) — previously Proposed. Current v0.5 ships Windows-only Electron + PyInstaller packaging, which aligns with the phased approach: Windows first, macOS/Linux as future milestones.

## Context
当前仅支持 Windows 打包（Electron + PyInstaller）。用户群体主要是神经影像研究者，macOS 和 Linux 在学术界占有相当比例。项目 Roadmap 提到 "macOS/Linux 打包" 作为未来目标。

两种可选方案：

1. **Web 优先 + PWA** — 专注 Web 体验 + Docker 部署 + PWA
2. **全平台原生桌面** — 维护三套 Electron 打包

## Decision
**分阶段：v0.6-0.7 专注 Web + Docker 部署，v0.8+ 评估 macOS Electron 打包，长期 PWA。**

理由：
1. Web 应用天然跨平台，Docker 解决后端依赖
2. Electron 跨平台打包维护成本高（独立 CI、测试、签名）
3. PWA 提供接近原生体验，且无需应用商店审核
4. MATLAB/SPM 依赖限制了真正的"全平台"——Windows 仍是主要目标
5. 团队资源应聚焦核心功能而非打包工程

## Consequences

### 正面
- Web + Docker 降低用户入门门槛
- PWA 减少桌面端打包维护负担
- 团队可聚焦核心功能而非打包工程

### 负面
- 纯 Web 模式需要用户自行启动后端（或使用 Docker）
- PWA 文件系统访问能力受限
- 延迟 macOS/Linux 原生桌面体验

## 相关文档
- `docs/architecture.md` — 桌面打包边界
- `docs/DESKTOP_APP_PACKAGING.md`

---
*创建于：2026-06-14*
