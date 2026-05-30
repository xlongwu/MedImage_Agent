# 下一步行动 (NEXT_ACTIONS)

> M6 Partial Closeout — SPM sandbox reviewed execution

## M5 ✅ | M6 Phase 1-3 ✅ | 712 passed, 4 skipped

## M6 Reviewed Execution Allowlist

| 节点 | 条件 | 状态 |
|------|------|:---:|
| Python-only | — | ✅ |
| `spm_smoke_test` | — | ✅ |
| `spm_realign_subject` | sandbox_mode=true | ✅ |
| `spm_slice_timing_subject` | sandbox_mode=true | ✅ |
| coregister/segment/normalize/smooth | — | ❌ |
| DPABI/GPU/GUI | — | ❌ |

## 推荐 next: M6-T007a — spm_coregister_subject safety contract

保持 M6-T005/006 的 4-phase 节奏：
1. Safety contract (docs)
2. Runner hardening (preflight)
3. Sandbox contract tests
4. Sandbox-only allowlist

不要跳过 contract/runner-hardening/sandbox-tests。
