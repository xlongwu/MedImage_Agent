# 下一步行动 (NEXT_ACTIONS)

> 最后更新：2026-05-29 — M6-T004c 完成

## M5 状态：✅ 全部完成

## M6 状态：🔴 SPM/DPABI Execution Safety — Phase 2 进行中

M6-T001 至 M6-T004c 已完成。`spm_smoke_test` 是唯一可通过 reviewed execution 的 SPM 节点。

## 当前 allowlist 状态

| 类别 | 节点 | 状态 |
|------|------|:---:|
| Python-only | data_inspection, motion_qc, ... | ✅ 允许 |
| SPM smoke | `spm_smoke_test` | ✅ 允许 (M6-T004b) |
| SPM subject | spm_realign, spm_slice_timing, ... | ❌ 阻断 |
| DPABI execution | dpabi_subject_*, dpabi_sandbox_* | ❌ 阻断 |
| GPU | gpu_* | ❌ 阻断 |
| GUI/manual | gui_* | ❌ 阻断 |

## 推荐 next action: M6-T005 — spm_realign_subject sandbox

在独立 sandbox 环境中验证 `spm_realign_subject` 可安全进入 reviewed execution。

**前置**:
- M6-T004a/b/c 已完成 (spm_smoke_test 验证)
- MATLAB command safety guard 就绪
- node + backend approval 就绪

**不做**:
- 不直接在生产环境开放
- 不绕过 sandbox
- 不开放其他 subject-level SPM

## M6 进度

```
✅ M6-T001: SPM/DPABI safety review
✅ M6-T002a: MATLAB command safety guard
✅ M6-T003: node + backend approval
✅ M6-T004a: SPM smoke safety preflight
✅ M6-T004b: spm_smoke_test allowlist
✅ M6-T004c: SPM smoke manual guide
⬜ M6-T005: spm_realign sandbox ← 推荐 next
⬜ M6-T006: SPM pipeline (coreg→segment→normalize→smooth)
⬜ M6-T007: DPABI contract/capability allowlist
⬜ M6-T008: DPABI sandbox
⬜ M6-T009: DPABI subject execution
⬜ M6-T010: GUI Agent design
```
