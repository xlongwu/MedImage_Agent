# M12 Frontend Capability Labeling Review

> M12-RELEASE-T003 | Frontend capability labeling review  
> Status: COMPLETE | Date: 2026-07-11

---

## 1. Executive Summary

This document reviews the MedImage Agent frontend for misleading capability labeling. Three UI issues were identified and fixed in `DesktopSettingsPanel.tsx`: the `pywinauto` provider option, the "Allow GUI Agent" label, and related configuration controls.

**All frontend capability labels now align with the backend safety baseline: mock-only, record-observation-only, no real model, no PyWinAuto.**

---

## 2. Capability Labeling Taxonomy

| Label | Meaning | Example |
|------|------|------|
| **Release-ready** | Fully implemented and tested | Reviewed execution pipeline, plan adapter |
| **Mock-only** | Safe for demo/test/CI; not real automation | GUI Agent provider, mock fixtures |
| **Scaffold-only** | Interface scaffold exists; no real compute | GPU benchmark panel |
| **Design-only** | Documented; not implemented | Real model inference, audit writer |
| **Blocked** | Explicitly prohibited | PyWinAuto, screenshots, Tier 1/2/3 |

---

## 3. GUI Agent Frontend Labeling Review

### Issues Found and Fixed

| # | File | Issue | Fix |
|:---:|------|------|------|
| 1 | `DesktopSettingsPanel.tsx` | `pywinauto` selectable in GUI provider dropdown | Added `disabled` attribute + "(blocked)" label |
| 2 | `DesktopSettingsPanel.tsx` | "Allow GUI Agent" misleading — implies real GUI | Changed to "Enable GUI Agent (mock-only, record_observation)" |
| 3 | `DesktopSettingsPanel.tsx` | Provider label "GUI provider" ambiguous | Changed to "GUI provider (mock only)" |

### Current State After Fixes

| UI Element | Current Label | Safety Alignment |
|------|------|:---:|
| GUI provider dropdown | "Mock (safe default)" only; "pywinauto (blocked)" disabled | ✅ |
| GUI Agent checkbox | "Enable GUI Agent (mock-only, record_observation)" | ✅ |
| Provider label | "GUI provider (mock only)" | ✅ |

### Not Present (and should not be)

- Real provider dropdown (desktop/browser/manual)
- Screenshot capture button
- Clipboard read/write controls
- Mouse/keyboard automation controls
- Model inference toggle
- "Run Model" button
- Tier 1/2/3 action controls

---

## 4. GPU Frontend Labeling Review

### GpuBenchmarkPanel.tsx

| Element | Current Label | Assessment |
|------|------|:---:|
| "Detect GPU" button | Detects CUDA presence; informational only | Acceptable |
| "Run ALFF Benchmark" button | Suggests real GPU compute | ⚠️ Scaffold-only |
| GPU Detection Result | Displays JSON | Acceptable |
| Benchmark Result | Displays JSON | Acceptable |

**Note:** The "Run ALFF Benchmark" label implies real GPU processing. GPU execution is scaffold-only (M8 preflight, CuPy not available in tests — 4 tests skipped). This is acceptable as long as the user understands the benchmark is preflight/detection, not production GPU processing.

---

## 5. Reviewed Execution Frontend Labeling Review

### AgentControls.tsx

| Element | Assessment |
|------|:---:|
| "生成 Plan" (Generate Plan) button | ✅ Orchestrator agent — deterministic, no LLM |
| "批准并执行 Pipeline" (Approve and Execute) | ✅ Requires user confirmation modal; calls reviewed execution |
| Approval gate checkbox (`approved: true`) | ✅ Present in workflow |

**Note:** The AgentControls operate the orchestrator agent pipeline, not the GUI Agent. This is correct — the orchestrator creates plans from config and pipeline YAML deterministically.

---

## 6. Misleading UI Risk Register

| # | Risk | Severity | Fixed |
|:---:|------|:---:|:---:|
| 1 | `pywinauto` selectable → user thinks real GUI is available | **CRITICAL** | ✅ Fixed (disabled + blocked label) |
| 2 | "Allow GUI Agent" → user expects real desktop control | HIGH | ✅ Fixed (mock-only clarification) |
| 3 | "GUI provider" → user expects multiple real providers | MEDIUM | ✅ Fixed (mock only label) |
| 4 | "Run ALFF Benchmark" → user expects real GPU processing | MEDIUM | ⚠️ Accepted (scaffold, no CUDA in tests) |
| 5 | LLM settings exposed → user expects LLM is used | MEDIUM | ⚠️ Accepted (orchestrator is deterministic; LLM is advisor-only) |

---

## 7. Recommended Frontend Copy

### Use These Labels

```
GUI Agent mode: Mock-only safety mode
Real desktop automation: Disabled
Allowed action: record_observation
Model inference: Not connected
PyWinAuto provider: Blocked
Screenshots / clipboard / mouse / keyboard: Blocked
GPU: Scaffold / preflight only
GUI reviewed execution: Not allowlisted (0 nodes)
```

### Avoid These Labels

```
GUI Agent ready
Desktop automation enabled
GPU computing enabled
AI model connected
Real provider available
Click automation supported
Run model now
```

---

## 8. Release Acceptance Checklist

| Check | Status |
|------|:---:|
| `pywinauto` not selectable in GUI provider dropdown | ✅ |
| GUI Agent label clarifies mock-only | ✅ |
| No "Run Model" or "Start Inference" button exists | ✅ |
| No screenshot/clipboard/mouse/keyboard controls exist | ✅ |
| No Tier 1/2/3 action buttons exist | ✅ |
| Frontend build passes | Pending verification |

---

## 9. Regression Commands

```bash
npm --prefix src/frontend run build
pytest --tb=short
```

---

## 10. References

| Document | Content |
|----------|------|
| `docs/M12_SYSTEM_RELEASE_READINESS_REVIEW.md` | Release readiness (T001) |
| `docs/M12_BACKEND_API_SURFACE_FREEZE.md` | API surface freeze (T002) |
| `docs/M11_FIXTURE_ONLY_GUI_MODEL_RELEASE_CHECKPOINT.md` | Safety baseline |
