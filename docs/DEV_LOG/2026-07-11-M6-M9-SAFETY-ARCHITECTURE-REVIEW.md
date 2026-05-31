# M6–M9 Overall Safety Architecture Review

**Date:** 2026-07-11

**Status:** COMPLETE

## Summary

Completed the cross-phase M6–M9 safety architecture review. Created `docs/M6_M9_SAFETY_ARCHITECTURE_REVIEW.md` consolidating the safety posture, reviewed execution baseline, risk model comparison, bypass analysis, fine-tuned agent integration architecture, guard layer requirements, non-negotiable invariants, and recommended roadmap.

## Key Findings

### Allowlist Baseline

| Phase | Nodes | Gate Mechanism |
|-------|:---:|------|
| M6 SPM | 7 | Sandbox-gated |
| M7 DPABI | 20 | Sandbox/metadata/report-gated |
| M8 GPU | 9 | Sandbox scaffold (no real CUDA) |
| M9 GUI | **0** | Blocked — design only |

### Risk Model Comparison

- **SPM/DPABI**: runtime/path/subprocess/output-scope risks — resolved by sandbox contracts
- **GPU**: resource/device/memory/scaffold risks — resolved by scaffold-only + no CUDA
- **GUI/manual**: human interaction, external app control, sensitive data, screenshots, clipboard, prompt injection, unattended control — **requires fundamentally different safety model**

### Why M9 Remains Blocked

GUI content is untrusted. Screenshots expose PHI. Mouse/keyboard actions are irreversible. Clipboard access is high-risk. The agent can encounter prompt injection in any visible UI text. These risks cannot be mitigated by the sandbox-gating model used for M6–M8.

### #1 Priority Gap

`/api/gui-agent/*` remains an un-gated API surface outside the reviewed execution pipeline. Future work must add an equivalent 12-gate guard before any real provider enablement.

### Architecture for Fine-Tuned GUI Agent

Recommended: model outputs structured intent/actions through a normalized adapter, NOT raw mouse coordinates. Provider never directly exposed to the model. All actions routed through 12 guard layers before reaching Mock or real provider.

### Roadmap

Guard implementation (M9-GUI-GUARD-T001–T006) → mock-only testing → real-provider gating. 12 non-negotiable safety invariants documented.

## Documents Created/Modified

- **Created:** `docs/M6_M9_SAFETY_ARCHITECTURE_REVIEW.md`
- **Created:** `docs/DEV_LOG/2026-07-11-M6-M9-SAFETY-ARCHITECTURE-REVIEW.md` (this file)
- **Modified:** `docs/CURRENT_STATE.md`
- **Modified:** `docs/NEXT_ACTIONS.md`
- **Modified:** `docs/TASK_BACKLOG.md`
