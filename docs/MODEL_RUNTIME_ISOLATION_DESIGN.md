# Model Runtime Isolation Design

> M11-GUI-MODEL-T002 | Runtime isolation for real fine-tuned GUI Agent inference  
> Status: DESIGN | Date: 2026-07-11  
> Depends on: M11-GUI-MODEL-T001 (real model threat model)  
> Feeds into: M11-GUI-MODEL-T003 (provider policy gate)

---

## 1. Executive Summary

This document defines the runtime isolation architecture for future real fine-tuned GUI Agent inference. It specifies how model loading, inference execution, and output handling must be sandboxed to prevent the 15 threat surfaces identified in M11-GUI-MODEL-T001 from materializing when real model code is eventually introduced.

**Every boundary defined here is a requirement, not a suggestion.** The current mock-fixture system is safe precisely because no inference runtime exists. Adding one without these controls would open every threat surface simultaneously.

---

## 2. Current Safety Baseline

| Metric | Value |
|--------|------|
| Reviewed execution allowlist | 36 (M6:7, M7:20, M8:9, M9:0) |
| GUI/manual allowlist | 0 |
| pytest | 1772 passed, 4 skipped |
| Allowed GUI/model path | fixture → adapter → `record_observation` → guard → MockGuiProvider |
| Real model connected | No |
| Inference called | No |
| PyWinAuto enabled | No |

---

## 3. Scope and Non-Goals

### Scope

- Design runtime isolation boundaries for future real model inference.
- Define model source, weight loading, tokenizer, filesystem, network, cache, resource, and output policies.
- Define prompt input minimization and redaction requirements.
- Define error codes and failure modes.
- Preserve current mock-only `record_observation` baseline.

### Non-Goals

- Implementing inference runtime, loading model weights, or connecting any LLM/VLM.
- Enabling PyWinAuto or real GUI provider.
- Opening new action types beyond `record_observation`.
- Adding arbitrary raw model output routes.

---

## 4. Runtime Isolation Architecture

```
Model Request
  │
  ▼
┌──────────────────────────────────────┐
│  Layer 1: Model Provider Policy Gate │  ← source allowlist, remote gating
├──────────────────────────────────────┤
│  Layer 2: Runtime Sandbox Declaration│  ← resource budget, filesystem scope
├──────────────────────────────────────┤
│  Layer 3: Input Minimizer / Redactor │  ← prompt construction, PHI stripping
├──────────────────────────────────────┤
│  Layer 4: Isolated Inference Worker  │  ← separate process, no provider access
├──────────────────────────────────────┤
│  Layer 5: Output Envelope            │  ← raw model output only, untrusted
├──────────────────────────────────────┤
│  Layer 6: validate_and_normalize_    │  ← existing adapter
│           model_output()             │
├──────────────────────────────────────┤
│  Layer 7: Existing GUI Guard Pipeline│  ← provider/session/action/stop/audit
└──────────────────────────────────────┘
  │
  ▼
MockGuiProvider (only provider reachable)
```

**Critical invariants:**
- The inference worker must not access provider, PyWinAuto, or `/api/gui-agent/step`.
- The inference worker must not set `provider_call_allowed`, `approved`, or session fields.
- The inference worker output is untrusted data — the adapter and guard are the sole authorities.

---

## 5. Model Source Policy

### Allowed (future, after explicit approval)

| Source | Conditions |
|--------|------|
| Local pinned model directory | Checksum verified, version pinned |
| Local safetensors weights | Hash-verified, from reviewed artifact |
| Local tokenizer files | From same artifact, `trust_remote_code=False` |
| Offline model artifact | Immutable, checksum in project config |
| Allowlisted provider config | Explicit provider ID, reviewed credentials handling |

### Blocked (permanent or until dedicated phase)

| Source | Reason |
|--------|------|
| Arbitrary model path | Path traversal, supply-chain risk |
| Remote code repository | `trust_remote_code` must be false |
| Unverified HuggingFace repo | Pinned commit required; local mirror preferred |
| Pickle-only checkpoint (.pt/.pth) | Arbitrary code execution risk |
| Runtime-downloaded weights | Network attack surface |
| User-supplied model path | Cannot trust user input |
| Network-loaded model | Network must be disabled by default |

### Required Config

```json
{
  "model_runtime_sandbox": true,
  "model_source": "local_allowlisted",
  "model_id": "gui_agent_v1",
  "model_dir": "models/gui_agent/v1/",
  "weights_format": "safetensors",
  "weights_only": true,
  "trust_remote_code": false,
  "checksum_required": true,
  "network_access": "disabled"
}
```

---

## 6. Model Weight Loading Policy

| Requirement | Rationale |
|------|------|
| `safetensors` format only | No pickle deserialization; safe by design |
| `weights_only=True` (PyTorch 2.0+) | Blocks arbitrary code in pickle |
| `trust_remote_code=False` | Blocks remote code execution from HuggingFace configs |
| No `torch.load()` with default pickle | Must be explicitly blocked |
| Model files scoped to `model_dir` only | No traversal, no symlinks, no rawdata paths |
| Checksum verification before load | Prevents tampered or corrupted weights |
| No runtime download | Model must be pre-staged and verified |

---

## 7. Tokenizer / Processor Policy

| Requirement | Rationale |
|------|------|
| Tokenizer files from same allowlisted artifact | Supply-chain consistency |
| No remote tokenizer download at runtime | Network must be disabled |
| No custom processor code unless reviewed | `trust_remote_code` covers tokenizers too |
| No execution of repository-provided Python | Tokenizer configs can contain code execution hooks |
| Tokenizer output scoped to memory only | No disk caching of tokenized prompts |

---

## 8. Local Model Runtime Isolation

```
┌──────────────────────────────────────────────┐
│          Isolated Inference Worker            │
│                                               │
│  Allowed:                                      │
│    ✓ Read model_dir (scoped)                   │
│    ✓ Write temp_dir (scoped)                   │
│    ✓ Write cache_dir (scoped, optional)        │
│    ✓ Receive structured input envelope         │
│    ✓ Return structured output envelope         │
│                                               │
│  Blocked:                                      │
│    ✗ Access provider (MockGuiProvider, etc.)   │
│    ✗ Import PyWinAuto / pywinauto              │
│    ✗ Import GUI automation (pyautogui, etc.)   │
│    ✗ Read rawdata / derivatives                │
│    ✗ Write rawdata / derivatives               │
│    ✗ Access network (default disabled)         │
│    ✗ Access filesystem outside scoped dirs     │
│    ✗ Call /api/gui-agent/* routes              │
│    ✗ Set provider_call_allowed                 │
│    ✗ Set approved=true                         │
│    ✗ Access clipboard, screenshots, mouse/kb   │
└──────────────────────────────────────────────┘
```

**Implementation notes:**
- Worker should be a separate Python subprocess with restricted imports.
- `sys.path` must not include provider or route modules.
- Output must be serialized as Raw Model Output Envelope only.

---

## 9. Remote Model Provider Isolation

If a remote provider is used in a future phase:

| Requirement | Rationale |
|------|------|
| Explicit provider allowlist | No arbitrary API endpoints |
| No PHI in prompts | Redact before sending |
| No raw screenshots in prompts | Not included in v1 |
| No clipboard contents in prompts | Not accessible |
| No credentials in prompts | Never in prompt construction |
| No rawdata paths in prompts unless redacted | Tokenize or strip |
| Request logging disabled or minimized | Provider may retain logs |
| Data retention policy reviewed | Legal/privacy requirement |
| Network egress allowlist | Only permitted provider endpoints |
| Timeout and retry limits | Prevent hanging on network |
| API key in env var only | Never in code, logs, or prompts |

**Default:** Remote provider **disabled**. Requires explicit future phase with dedicated threat model review.

---

## 10. Network Policy

| Rule | v1 Default | Future |
|------|:---:|------|
| Network access for local model | **Disabled** | May allow for remote provider after dedicated phase |
| Arbitrary outbound HTTP | **Blocked** | Permanent |
| Downloading weights at runtime | **Blocked** | Permanent |
| Telemetry / analytics | **Blocked** | Permanent |
| Upload of any data | **Blocked** | Permanent |
| Screenshot / clipboard / rawdata upload | **Blocked** | Permanent |

---

## 11. Filesystem Policy

### Read-Only

| Directory | Purpose | Conditions |
|------|------|------|
| `models/gui_agent/<version>/` | Model weights, tokenizer, config | Allowlisted, checksum-verified |
| `outputs/work/gui_agent/model_runtime/<run_id>/` | Scoped model runtime work dir | Created per run, cleaned up |

### Read/Write

| Directory | Purpose | Conditions |
|------|------|------|
| `outputs/work/gui_agent/model_runtime/<run_id>/temp/` | Transient inference artifacts | Auto-cleaned after run |
| `outputs/work/gui_agent/model_runtime/<run_id>/cache/` | Optional inference cache | Size-limited, no PII |

### Blocked

| Path | Reason |
|------|------|
| `rawdata/` | Permanent invariant |
| `data/` | Permanent invariant |
| `derivatives/` | Permanent invariant |
| `~/`, `/home/`, `Desktop`, `Downloads` | User data access |
| Arbitrary absolute paths | Path traversal |
| Symlinks escaping model_dir | Traversal |
| `..` in any path | Traversal |
| `outputs/reports/` | Only audit metadata may write here via guard |

---

## 12. Cache / Temp Directory Policy

| Policy | Detail |
|------|------|
| Cache directory | Scoped to `outputs/work/gui_agent/model_runtime/<run_id>/cache/` |
| Temp directory | Scoped to `outputs/work/gui_agent/model_runtime/<run_id>/temp/` |
| Cache must not contain prompts with PHI | Redact before caching |
| Cache must not contain raw screenshots | Not included in v1 |
| Cache must not contain clipboard | Not accessible |
| Cache must not contain credentials | Never in prompts |
| Auto-cleanup | After model run completes or on error |
| Size limit | configurable, default 512 MB |

---

## 13. Resource Budget Policy

| Resource | Default Limit | Notes |
|------|:---:|------|
| Max inference timeout (soft) | 30 seconds | Graceful termination |
| Hard timeout | 60 seconds | Force kill |
| Max memory | 4096 MB | Per-inference allocation |
| Max GPU memory | Disabled by default | Requires explicit GPU enablement |
| Max input characters | 8192 | Bounded prompt length |
| Max output characters | 4096 | Bounded response length |
| Max concurrent model jobs | 1 | Single worker for v1 |
| Queue limit | 10 | Bounded pending requests |

**Note:** GPU memory budget reuses concepts from M8 `gpu_safety.py` but does not enable real GPU inference in this design phase.

---

## 14. Concurrency and Queue Policy

| Policy | v1 |
|------|:---:|
| Concurrent inference | 1 (single worker) |
| Pending queue | FIFO, max 10 |
| Queue overflow | Reject with `MODEL_RUNTIME_QUEUE_FULL` |
| Worker reuse | New worker per inference (stateless) |
| Worker timeout | Hard kill after `hard_timeout_seconds` |

---

## 15. Prompt Input Boundary

### What the prompt may contain (after sanitization)

- Scoped user instruction (max 256 chars)
- Summarized UI context (no verbatim UI text)
- Previous action summary (no chain-of-thought)
- Task objective (from session)

### What the prompt must not contain

- Raw UI text (verbatim window titles, control labels)
- Raw screenshots or image data
- Clipboard contents
- Credentials, API keys, tokens
- PHI (subject IDs, names, dates)
- Rawdata file paths
- Session declaration fields (provider, approved, policies)
- Chain-of-thought from previous inferences
- Any text including "ignore safety", "disable guard", "use pywinauto", "approved=true"

### Input Minimization Rules

- Max prompt length: 8192 characters
- UI context: summarized only (max 512 chars)
- Previous actions: action_type only (no parameters, no rationale)
- File paths: never included
- Subject IDs: redacted or tokenized

---

## 16. Output Boundary

### What the model may output

```json
{
  "model_output_id": "model_out_001",
  "source": "fine_tuned_gui_agent",
  "raw_text": "observe current state",
  "raw_json": null,
  "observed_context_summary": "User asked for observation.",
  "timestamp": "2026-07-11T00:00:00Z"
}
```

### What the model must not output

- `provider` field (rejected: `provider_selection_blocked`)
- `approved=true` (rejected: `approval_override_blocked`)
- `provider_call_allowed=true` (adapter never grants this)
- Session declaration fields
- Raw coordinates
- Multi-action plans
- Shell commands
- File paths
- Credentials

### Post-Output Validation

Every model output must pass through `validate_and_normalize_model_output()`:
- Unknown actions → `MODEL_ACTION_REJECTED`
- Tier 1/2/3 actions → `MODEL_ACTION_REJECTED`
- Ambiguous/injection/policy-override text → `MODEL_ACTION_REJECTED`
- Safe observation → `record_observation` → guard → MockGuiProvider

---

## 17. Logging and Audit Policy

### Must NOT be logged

- Chain-of-thought
- Raw model prompts
- Raw model outputs (only `model_output_id` referenced)
- Raw screenshots
- Clipboard contents
- Credentials, API keys, tokens, passwords
- PHI, subject IDs, patient data
- Model weights or configuration secrets

### Must be logged

| Field | Source |
|------|------|
| `model_output_id` | Inference worker |
| `model_id` / `model_version` | Inference worker |
| `inference_timestamp` | Inference worker |
| `inference_duration_ms` | Inference worker |
| `adapter_decision` | Adapter |
| `adapter_rejection_reason` | Adapter (if rejected) |
| `guard_result` | Guard |
| `audit_id` | Guard (`create_gui_audit_record`) |

---

## 18. Error Codes and Failure Modes

| Error Code | Condition |
|------|------|
| `MODEL_RUNTIME_DISABLED` | Model runtime feature flag not enabled |
| `MODEL_PROVIDER_NOT_ALLOWED` | Provider not in source allowlist |
| `MODEL_SOURCE_NOT_ALLOWED` | Model source not allowlisted |
| `MODEL_CHECKSUM_MISMATCH` | Weight checksum verification failed |
| `MODEL_TRUST_REMOTE_CODE_BLOCKED` | `trust_remote_code=true` rejected |
| `MODEL_WEIGHTS_FORMAT_BLOCKED` | Non-safetensors format rejected |
| `MODEL_PATH_SCOPE_BLOCKED` | Model path outside allowed scope |
| `MODEL_NETWORK_BLOCKED` | Network access attempted |
| `MODEL_TIMEOUT` | Inference exceeded soft/hard timeout |
| `MODEL_MEMORY_BUDGET_EXCEEDED` | Memory allocation exceeded budget |
| `MODEL_GPU_BUDGET_EXCEEDED` | GPU VRAM exceeded budget |
| `MODEL_OUTPUT_INVALID` | Output failed schema validation |
| `MODEL_OUTPUT_REJECTED` | Output rejected by adapter |
| `MODEL_AUDIT_REQUIRED` | Audit record creation failed |
| `MODEL_RUNTIME_QUEUE_FULL` | Inference queue at capacity |

All errors must:
- Not expose internal model state
- Not expose prompt or output content
- Return structured response with `provider_call_allowed=false`
- Never call provider

---

## 19. Required Tests Before Implementation

| Test | Category |
|------|------|
| Provider policy blocks unknown provider | Gate |
| Model path traversal blocked | Filesystem |
| Rawdata model path blocked | Filesystem |
| Derivatives model path blocked | Filesystem |
| `trust_remote_code` blocked | Weights |
| Pickle checkpoint blocked | Weights |
| Safetensors allowed | Weights |
| Checksum required and verified | Weights |
| Network disabled for local inference | Network |
| Timeout enforced | Resources |
| Memory budget enforced | Resources |
| Single concurrency enforced | Concurrency |
| Output cannot set provider | Output boundary |
| Output cannot set `approved=true` | Output boundary |
| Output cannot set `provider_call_allowed` | Output boundary |
| Inference worker cannot call provider | Isolation |
| Inference worker cannot import PyWinAuto | Isolation |
| Adapter rejection works with real output | Integration |
| Existing guard tests pass (1772) | Regression |
| PyWinAuto not imported | Regression |

---

## 20. Future Implementation Roadmap

```
M11-GUI-MODEL-T003: Model provider policy gate design
  → Source allowlist, remote provider gating, credential handling

M11-GUI-MODEL-T004: Inference input minimization and redaction design
  → Prompt construction constraints, UI context sanitization

M11-GUI-MODEL-T005: Model-output audit metadata persistence design
  → Persistent audit records, redaction policies

M11-GUI-MODEL-T006: Mock-real model boundary tests
  → Mock fixtures still pass; real model output follows same path

M11-GUI-MODEL-CLOSEOUT: Real model integration design closeout
```

### Hard Constraints

```
Do NOT implement inference before T002/T003/T004/T005 are reviewed.
Do NOT load model weights before sandbox controls exist.
Do NOT enable PyWinAuto.
Do NOT enable screenshots, clipboard, mouse, keyboard, network.
Do NOT open GUI/manual reviewed execution allowlist.
Do NOT expand beyond record_observation.
```

---

## 21. References

| Document | Content |
|----------|---------|
| `docs/REAL_MODEL_INTEGRATION_THREAT_MODEL.md` | 15 threat surfaces, 17 invariants |
| `docs/M10_FULL_TEST_BASELINE_LOCK.md` | Current test baseline |
| `docs/M10_GUI_AGENT_MOCK_INTEGRATION_CLOSEOUT.md` | Mock integration closeout |
| `docs/NORMALIZED_GUI_ACTION_SCHEMA.md` | Normalized action schema |
| `docs/M9_GUI_AGENT_API_GUARD_CLOSEOUT.md` | Guard phase closeout |
