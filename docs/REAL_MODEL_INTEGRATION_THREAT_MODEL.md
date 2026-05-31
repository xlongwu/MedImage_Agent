# Real Model Integration Threat Model

> M11-GUI-MODEL-T001 | Threat model for real fine-tuned GUI Agent integration  
> Status: DESIGN | Date: 2026-07-11  
> Feeds into: M11-GUI-MODEL-T002 (runtime isolation), T003 (provider gate), T004 (input design)

---

## 1. Executive Summary

This document models the threats introduced by connecting a **real fine-tuned GUI Agent model** to the existing adapter/guard pipeline. Currently, all model outputs come from static mock fixtures — deterministic, reviewed, and incapable of generating novel unsafe outputs. A real model introduces **every** risk that mock fixtures were designed to exclude: hallucinated actions, prompt injection, data exfiltration, resource exhaustion, supply-chain compromise, and adapter/guard bypass.

**This document does not implement real model integration.** It defines the threat surface and required safety controls that must be in place before any inference code is written.

---

## 2. Current Safety Baseline

| Metric | Value |
|--------|------|
| Reviewed execution allowlist | 36 (M6:7, M7:20, M8:9, M9:0) |
| GUI/manual allowlist | 0 |
| pytest | 1772 passed, 4 skipped |
| Frontend build | Passed |
| Allowed GUI/model path | fixture → adapter → `record_observation` → guard → MockGuiProvider |
| Real model connected | No |
| Inference called | No |
| PyWinAuto enabled | No |

The current system is safe because:
- Model outputs are **static fixtures** — they cannot hallucinate novel unsafe actions.
- The adapter validates every fixture output deterministically.
- The guard pipeline authorizes every action independently.
- No code path exists that calls `model.generate()` or `model.predict()`.

A real model removes the static-fixture assumption. **Every novel model output must be treated as untrusted data.**

---

## 3. Scope and Non-Goals

### Scope

- Model the full threat surface of real fine-tuned GUI Agent integration.
- Identify new risks beyond those covered by mock fixture integration.
- Define required safety controls before any implementation.
- Preserve the current `record_observation`-only guard baseline.

### Non-Goals

- Implementing real model integration — no inference, no weights, no API calls.
- Enabling PyWinAuto or any real GUI provider.
- Opening new action types beyond `record_observation`.
- Adding arbitrary raw model output routes.
- Modifying the existing guard, adapter, or provider behavior.

---

## 4. Threat Surface Inventory

| Surface | Mock Fixture Risk | Real Model Risk |
|---------|:---:|:---:|
| Model runtime | None (no runtime) | **HIGH** — arbitrary code execution, deserialization |
| Model weights | None | **HIGH** — supply-chain, backdoor, integrity |
| Tokenizer / processor | None | **MEDIUM** — remote code, unsafe parsing |
| Input prompt | None (static) | **HIGH** — prompt injection, PHI leakage |
| UI context in prompt | None | **HIGH** — adversarial UI text |
| Model output | Static, reviewed | **HIGH** — hallucination, bypass, unsafe actions |
| Adapter normalization | Deterministic | **MEDIUM** — model may craft adversarial normalized shapes |
| Guard submission | Safe by construction | **HIGH** — model may attempt to bypass guard |
| Audit/logging | None | **HIGH** — chain-of-thought, PII, credentials |
| Cache/temp files | None | **MEDIUM** — inference cache leakage |
| Network access | None | **HIGH** — remote provider data exfiltration |
| GPU/CPU resources | None | **HIGH** — denial of service, resource exhaustion |
| Third-party provider | None | **CRITICAL** — data exfiltration to external API |
| Local model server | None | **HIGH** — insecure endpoint exposure |

---

## 5. Model Runtime Risks

### 5.1 Unsafe Deserialization
Model weights are typically loaded via `torch.load()` or `safetensors`. `torch.load()` with `weights_only=False` (the default in older PyTorch) can execute arbitrary Python code embedded in pickle files.

**Required:** `weights_only=True` or `safetensors` format only. `trust_remote_code=False` for HuggingFace models.

### 5.2 Arbitrary Model Path
A misconfigured model path pointing to an attacker-controlled directory could load a malicious checkpoint.

**Required:** Model path must be a fixed, reviewed, scoped directory. No user-controlled or environment-variable-controlled path loading.

### 5.3 Resource Exhaustion
Inference without resource limits can consume all available CPU/GPU memory, block other workloads, or cause OOM kills.

**Required:** Per-inference memory budget, GPU VRAM budget, CPU time timeout, maximum tokens limit, batch size limit.

### 5.4 Logging / Caching
Model runtimes often log prompts and outputs to disk or cache them in temp directories. This can leak PHI, credentials, subject IDs, and file paths.

**Required:** No persistent prompt/output logging. No inference cache in shared or unscoped directories. Temp files scoped to `outputs/work/gui_agent/inference/`.

---

## 6. Model Input Risks

### 6.1 Prompt Content
The prompt sent to the model may contain:
- User instructions (trusted, scoped)
- UI-visible text (untrusted — may contain adversarial instructions)
- Terminal output (untrusted)
- File paths (may leak data locations)
- Subject IDs (PHI)
- Previous model actions (may compound errors)

**Required:**
- Prompt input must be minimized — only essential context.
- UI text must be summarized, not passed verbatim.
- No raw screenshots, no clipboard contents, no file paths, no credentials in prompts.
- Subject IDs must be redacted or tokenized.

### 6.2 System Instructions
The model's system prompt is a powerful control surface. If the model can modify its own system prompt or if a malicious UI text influences it, the model may act outside its authorized scope.

**Required:** System instructions must be immutable at inference time. Model must not be able to modify system prompt. UI text must not be treated as system instruction.

---

## 7. Model Output Risks

### 7.1 Hallucinated Actions
The model may propose actions that are not in the 41-action taxonomy — or actions that are in the taxonomy but unsafe (Tier 1/2/3).

**Required:** Every model output must pass through `validate_and_normalize_model_output()`. Unknown actions → `MODEL_ACTION_REJECTED`. Tier 1/2/3 actions → `MODEL_ACTION_REJECTED`.

### 7.2 Adversarial Normalized Shapes
A sophisticated model (or prompt injection) might craft output that looks like a valid normalized action but contains unsafe fields (e.g., `action_type=record_observation` but `uses_screenshot=true`).

**Required:** The action declaration validator (`validate_gui_action_declaration()`) must be the authoritative check on every field. The adapter normalizes; the guard validates.

### 7.3 Confidence / Rationale Override
A model may output high confidence for an unsafe action, or provide a rationale that appears to justify bypassing policy.

**Required:** Confidence does not override policy. Rationale does not override policy. These are metadata fields, not authorization tokens.

### 7.4 Multi-Action Plans
The model may propose executing multiple steps in sequence, potentially hiding an unsafe step among safe ones.

**Required:** Multi-action plans → `multi_action_plan_blocked`. Single action per model output invocation.

---

## 8. Prompt / UI Injection Risks

### 8.1 UI-Originated Instructions
MATLAB, SPM, DPABI GUI labels, terminal output, browser content, and error messages may contain text like:
- "Click Run to proceed"
- "Ignore previous instructions"
- "Use pywinauto directly"
- "Disable safety checks"
- "Set approved=true"

**Required:**
- UI text is always untrusted.
- The model may summarize UI text but must not follow UI-originated instructions as authority.
- Adapter must reject outputs that cite UI text as justification for unsafe actions.
- Policy override keywords in raw model output → `policy_override_attempt`.

### 8.2 Prompt Injection via User Instruction
Even the user's instruction could contain injection if it includes pasted UI text, terminal output, or web content.

**Required:** User instruction field must be scoped. Pasting large UI text blocks must be prevented or sanitized.

### 8.3 Chain-of-Thought Manipulation
If the model's chain-of-thought is exposed and later fed back as context, adversarial outputs can compound.

**Required:** Chain-of-thought must not be stored. Must not be fed back as prompt context in subsequent inference calls.

---

## 9. Data Privacy Risks

| Data Type | Risk | Mitigation |
|------|:---:|------|
| PHI / subject IDs | Exposure in prompts, outputs, logs | Redact or tokenize |
| File paths | Exposure of rawdata locations | Redact from prompts |
| Medical images | Exposure in screenshots or model context | No raw screenshots in v1 |
| Credentials / tokens | Exposure if passed in prompts | Never include in prompts |
| Clipboard contents | Exposure if model-accessible | Block clipboard access |
| Chain-of-thought | Persistent storage of reasoning | Never store |
| Audit metadata | May contain PII if not sanitized | Redaction required before persistence |

**Required:** No raw chain-of-thought logging. No raw screenshots. No clipboard. No credentials in any log or audit record. PHI must be redacted before persistence.

---

## 10. Resource and Availability Risks

| Risk | Impact | Mitigation |
|------|:---:|------|
| CPU exhaustion | System unresponsive | Per-inference CPU time timeout |
| GPU VRAM exhaustion | OOM, crash | VRAM budget, CPU fallback |
| Memory exhaustion | OOM, swap thrash | Per-inference memory budget |
| Disk exhaustion | Inference cache fills disk | Scoped temp directory, size limit |
| Network exhaustion | Remote provider stalls | Local timeout, fallback to mock |
| Concurrent inference | Resource contention | Single inference at a time (v1) |

**Required:** Timeout, memory budget, VRAM budget, no network by default, single-concurrency for v1.

---

## 11. Supply-Chain and Model-Weight Risks

| Risk | Mitigation |
|------|------|
| Backdoored model weights | Model must be from reviewed source; hash verification required |
| Malicious tokenizer | `trust_remote_code=False`; reviewed tokenizer configuration |
| Compromised HuggingFace repo | Pinned commit hash; local mirror preferred |
| Model format vulnerability | `safetensors` only; no pickle-based loading |

**Required:** Model source must be reviewed. Weights must be hash-verified. `trust_remote_code=False`. `safetensors` format only.

---

## 12. Remote Model Provider Risks

If the model runs on a remote provider (OpenAI API, local LLM server, etc.):

| Risk | Mitigation |
|------|------|
| Data exfiltration to provider | No PHI/credentials in prompts; minimize context |
| Provider logging | Review provider data retention policy |
| Provider API key leakage | Key stored in env var only; never in code or logs |
| Provider downtime | Local mock fallback required |
| Provider model change | Pinned model version; no auto-upgrade |

**Required:** Remote provider must be explicitly gated. Local-only by default for v1. API key must never appear in logs, audit records, or prompts.

---

## 13. Local Model Provider Risks

| Risk | Mitigation |
|------|------|
| Insecure local server endpoint | Localhost binding only; no external network interface |
| Server process escalation | Run as dedicated low-privilege user |
| Model file access | Scoped to model directory only |
| Log file leakage | Scoped log directory; no prompt/output logging |

**Required:** Localhost only. Dedicated user. No external network binding. Scoped file access.

---

## 14. Adapter / Guard Bypass Risks

| Attempt | Blocked By |
|------|------|
| Model calls provider directly | `_provider()` gate in `gui_agent.py` |
| Model calls `/api/gui-agent/step` directly | Route-level guard: session + action validators |
| Model sets `provider=pywinauto` | Provider policy gate → `GUI_GUARD_REAL_PROVIDER_DISABLED` |
| Model sets `approved=true` | Adapter rejection: `approval_override_blocked` |
| Model emits raw coordinates | Adapter rejection: `raw_coordinate_click_blocked` |
| Model emits multi-action plan | Adapter rejection: `multi_action_plan_blocked` |
| Model emits Tier 1/2/3 action | Action validator → `GUI_GUARD_ACTION_TIER_BLOCKED` |
| Model emits screenshot request | Adapter rejection: `screenshot_request_blocked` |
| Route accepts arbitrary raw model output | Current route uses `fixture_id` only |

**Required:** Real model integration must not expose provider directly. Must not expose `approved` flag. Must not submit rejected outputs. Must route through the same adapter→guard→provider path as mock fixtures.

---

## 15. Audit and Logging Risks

| Risk | Mitigation |
|------|------|
| Chain-of-thought in audit | Never stored |
| PHI in audit metadata | Redaction required |
| Prompt in audit | Not stored; only `model_output_id` referenced |
| Inference timing side-channel | Not a concern for v1 |
| Audit file path traversal | Scoped audit directory |

**Required:** Audit must follow `GuiAuditRecord` schema. No raw model output in persistent audit. Only `model_output_id`, `adapter_decision`, `adapter_rejection_reason`, `guard_result`, `audit_id`.

---

## 16. Required Safety Controls (Pre-Implementation)

1. **Model provider policy gate** — allowlist of permitted model sources; no remote by default.
2. **Model runtime sandbox** — `weights_only=True`, `trust_remote_code=False`, `safetensors` only.
3. **Resource budgets** — CPU timeout, memory budget, VRAM budget, max tokens, single concurrency.
4. **Network disabled by default** — no remote provider, no external API calls.
5. **Prompt input minimization** — only essential context; no raw UI text, no screenshots, no clipboard.
6. **Prompt sanitization** — redact PHI, file paths, credentials before prompt construction.
7. **Output validation** — every model output must pass `validate_and_normalize_model_output()`.
8. **Existing GUI guard** — provider/session/action/stop/audit guards remain active.
9. **Audit metadata** — follow `GuiAuditRecord` schema; no chain-of-thought, no prompt, no PII.
10. **Sensitive data redaction** — PHI, credentials, paths redacted before any persistence.
11. **No chain-of-thought logging** — reasoning traces never stored or fed back as context.
12. **Regression tests** — all 1772 existing tests must continue to pass.
13. **Model-output fixture tests** — mock fixtures must remain as regression baseline.
14. **No real provider** — PyWinAuto and real providers remain blocked.
15. **No action expansion** — only `record_observation` remains executable.

---

## 17. Non-Negotiable Invariants

```
1. No real model without model-runtime threat model approval.
2. No model inference without sandbox controls.
3. No model direct provider access — model output must go through adapter→guard.
4. No model direct PyWinAuto access — PyWinAuto remains blocked.
5. No model direct /api/gui-agent/step access unless through fixture-like adapter route.
6. No provider selection from model output.
7. No approved=true from model output.
8. No screenshot in v1.
9. No clipboard in v1.
10. No mouse/keyboard in v1.
11. No network action in v1.
12. No file paths in v1.
13. No rawdata/derivatives access in v1.
14. Only record_observation remains executable (1 of 41 actions).
15. GUI/manual reviewed execution allowlist remains 0.
16. All 1772 existing tests must pass.
17. Frontend build must pass.
18. PyWinAuto module must not be imported outside its sandboxed test.
```

---

## 18. Future Implementation Roadmap

```
M11-GUI-MODEL-T002: Model runtime isolation design
  - Sandboxing requirements, resource budgets, network policy
  - Local vs remote model architecture

M11-GUI-MODEL-T003: Model provider policy gate design
  - Model source allowlist, remote provider gating
  - API key and credential handling

M11-GUI-MODEL-T004: Inference input minimization and redaction design
  - Prompt construction constraints
  - UI context sanitization rules

M11-GUI-MODEL-T005: Model-output audit metadata persistence design
  - Persistent audit records for model-derived actions
  - Redaction and retention policies

M11-GUI-MODEL-T006: Mock-real model boundary tests
  - Test that mock fixtures still pass after real model infrastructure is added
  - Test that real model output follows the same adapter→guard→provider path

M11-GUI-MODEL-CLOSEOUT: Real model integration design closeout
```

### Hard Constraints

```
Do NOT connect a real model before T002/T003/T004 are implemented and reviewed.
Do NOT write inference code before threat model is approved.
Do NOT enable PyWinAuto.
Do NOT enable screenshots, clipboard, mouse, keyboard, network.
Do NOT open GUI/manual reviewed execution allowlist.
Do NOT expand beyond record_observation.
```

---

## 19. Acceptance Criteria Before Any Real Model Code

1. This threat model is reviewed and approved.
2. Model runtime isolation design (T002) is complete.
3. Model provider policy gate design (T003) is complete.
4. Inference input design (T004) is complete.
5. Audit metadata persistence design (T005) is complete.
6. Mock-real model boundary tests (T006) are designed.
7. All 1772 existing tests pass.
8. All 17 non-negotiable invariants are verified.
9. PyWinAuto remains blocked.
10. GUI/manual reviewed execution allowlist remains 0.
11. SPM (7), DPABI (20), GPU (9) allowlists unaffected.

---

## 20. References

| Document | Content |
|----------|---------|
| `docs/M10_FULL_TEST_BASELINE_LOCK.md` | Current test baseline and invariants |
| `docs/M10_GUI_AGENT_MOCK_INTEGRATION_CLOSEOUT.md` | Mock integration closeout |
| `docs/M10_GUI_AGENT_ADAPTER_PHASE_CLOSEOUT.md` | Adapter phase closeout |
| `docs/NORMALIZED_GUI_ACTION_SCHEMA.md` | Normalized action schema |
| `docs/M9_GUI_AGENT_API_GUARD_CLOSEOUT.md` | Guard phase closeout |
| `docs/M6_M9_SAFETY_ARCHITECTURE_REVIEW.md` | Cross-phase safety architecture |
