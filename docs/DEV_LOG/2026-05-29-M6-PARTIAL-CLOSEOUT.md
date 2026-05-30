# M6 Partial Closeout — 2026-05-29

> SPM smoke + realign + slice timing sandbox reviewed execution

## M6 完成阶段

M6-T001 → M6-T006d + fix: 16 tasks + 2 fixes 完成
712 passed, 4 skipped

## 已开放

| 节点 | 条件 |
|------|------|
| `spm_smoke_test` | MATLAB/SPM 环境验证 |
| `spm_realign_subject` | sandbox_mode=true |
| `spm_slice_timing_subject` | sandbox_mode=true + path validation |

## 仍阻断

spm_coregister / segment / normalize / smooth / DPABI / GPU / GUI

## 推荐 next

M6-T007a: spm_coregister_subject safety contract (4-phase)
