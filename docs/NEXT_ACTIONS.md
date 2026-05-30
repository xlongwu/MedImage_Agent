# 下一步行动 (NEXT_ACTIONS)

> 最后更新：2026-05-29 — M6-T001 完成

## M5 状态：✅ 全部完成

M1 / M2 / M3 / M5 全部闭环。550 passed, 4 skipped。

## M6 状态：🔴 SPM/DPABI Execution Safety

M6-T001 审计完成。SPM/DPABI **仍被阻断** — 未开放任何 subject-level MATLAB execution。

## 推荐 next action: M6-T002 — MATLAB command safety hardening

**目标**: 对 `matlab_command`、`spm_dir`、`dpabi_dir` 做白名单校验。

**范围**:
- 新增 `matlab_command` 白名单 (只允许 `matlab` 或受控绝对路径)
- 校验 `spm_dir`/`dpabi_dir` 不可逃逸工作目录
- 增强 `spm_*_runner.py` 的 path safety
- 不影响当前 M5 gate 逻辑

**允许修改**:
- `src/backend/app/tools/matlab_runner.py` (新增校验)
- `src/backend/app/tools/spm_*_runner.py` (增强 path safety)
- `tests/unit/test_spm_*.py` (新增测试)

**禁止**:
- 不开放 SPM/DPABI subject-level execution
- 不修改 executor / node_registry
- 不修改 M5 gate

## M6 完整路线

```text
✅ M6-T001: safety review (done)
⬜ M6-T002: MATLAB command safety hardening ← recommended next
⬜ M6-T003: node-level + backend-level approval
⬜ M6-T004: spm_smoke_test into safe allowlist
⬜ M6-T005: spm_realign + slice_timing subject-level
⬜ M6-T006: spm_coregister → segment → normalize → smooth
⬜ M6-T007: DPABI contract/capability into allowlist
⬜ M6-T008: DPABI sandbox smoke
⬜ M6-T009: DPABI subject execution
⬜ M6-T010: GUI Agent design
```
