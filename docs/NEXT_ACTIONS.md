# 下一步行动 (NEXT_ACTIONS)

> M6 Early Sandbox Closeout — 741 passed, 4 skipped

## M6 SPM Early Sandbox: 4 nodes allowed, 3 blocked

| Allowed | Blocked |
|---------|---------|
| spm_smoke_test | spm_segment_subject |
| spm_realign (sandbox) | spm_normalize_subject |
| spm_slice_timing (sandbox) | spm_smooth_subject |
| spm_coregister (sandbox) | DPABI/GPU/GUI |

## Recommended next: M6-T008a — spm_segment_subject safety contract

4-phase rhythm: contract → hardening → tests → allowlist.
Do NOT skip to normalize/smooth or DPABI.
