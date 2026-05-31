# Mock-Real Boundary Tests Design

> M11-GUI-MODEL-T006 | Test matrix for fixture-only → real model transition  
> Status: DESIGN | Date: 2026-07-11  
> Depends on: M11-GUI-MODEL-T001 through T005  
> Feeds into: M11-GUI-MODEL-CLOSEOUT

---

## 1. Executive Summary

This document defines the complete test matrix that must exist **before** any real model implementation code is added to the MedImage Agent. Currently, all model outputs come from static mock fixtures. Transitioning to a real fine-tuned GUI Agent requires proving that every real-model capability remains blocked until explicitly opened — and that mock-fixture safety is not compromised by the infrastructure changes needed to support real inference.

**This document designs ~120 tests across 10 categories. No tests are implemented in this task.**

---

## 2. Current Safety Baseline

| Metric | Value |
|--------|------|
| Reviewed execution allowlist | 36 (GUI: 0) |
| pytest | 1772 passed, 4 skipped |
| Allowed model path | fixture → adapter → `record_observation` → guard → MockGuiProvider |
| Real model | Not connected |

---

## 3. Scope and Non-Goals

### Scope
- Design a complete test matrix for the mock-to-real transition.
- Define boundary tests for provider gate, runtime, weights, network, input, output, adapter, audit.
- Define acceptance gates that must pass before real model code is added.

### Non-Goals
- Implementing tests — this is test design only.
- Enabling real models, inference, PyWinAuto, or new GUI actions.

---

## 4. Boundary Test Philosophy

```
Mock fixture safety ≠ real model safety.

Before real model code exists:
  → Boundary tests assert every real-model capability is BLOCKED.

During real model implementation:
  → Turn design-only boundaries into FAILING tests first.
  → Implement minimal code to make them pass.
  → Never relax action policy while doing so.

Every new real-model capability must be:
  → Behind an explicit policy gate.
  → Backed by a dedicated test suite.
  → Tested for regression against the mock baseline.
```

**Core principles:** Fail closed. No implicit enablement. No env-var-only gates. No `approved=true` bypass. No arbitrary model paths. No network by default. No raw persistence. No direct provider access.

---

## 5. Mock-Only Baseline Tests (12, must always pass)

| # | Test | Current File |
|:---:|------|------|
| 1 | Fixture catalog returns only metadata (no raw_text) | `test_gui_agent_mock_adapter_api_route.py` |
| 2 | Safe fixture dry-run does not call provider | `test_gui_agent_mock_adapter_e2e.py` |
| 3 | Safe fixture submit uses guarded step path | `test_gui_agent_mock_adapter_e2e.py` |
| 4 | Safe fixture submit reaches MockGuiProvider only | `test_gui_agent_mock_adapter_e2e.py` |
| 5 | Rejected fixture not submitted to guard | `test_gui_agent_mock_adapter_e2e.py` |
| 6 | Rejected fixture does not call provider | `test_gui_agent_mock_adapter_e2e.py` |
| 7 | Adapter `provider_call_allowed_by_adapter=false` | `test_gui_agent_schema_consistency.py` |
| 8 | Guard success `provider_call_allowed_by_guard=true` | `test_gui_agent_schema_consistency.py` |
| 9 | All 6 response types have safety flags | `test_gui_agent_schema_consistency.py` |
| 10 | No sensitive data in any response | `test_gui_agent_schema_consistency.py` |
| 11 | Fixture integrity (45 fixtures) | `test_gui_agent_mock_model_fixtures.py` |
| 12 | Adapter validation (58 tests) | `test_gui_agent_model_output_validator.py` |

---

## 6. Provider Policy Boundary Tests (20, design → future implementation)

| # | Test |
|:---:|------|
| 1 | `fixture_only` allowed |
| 2 | Missing `provider_type` → `MODEL_PROVIDER_MISSING` |
| 3 | Unknown `provider_type` → `MODEL_PROVIDER_UNKNOWN` |
| 4 | `local_allowlisted` → blocked in current phase |
| 5 | `local_untrusted` → blocked |
| 6 | `remote_disabled` → blocked |
| 7 | `remote_allowlisted_future` → blocked |
| 8 | `remote_untrusted` → blocked |
| 9 | `external_tool_provider` → blocked |
| 10 | `openai` provider → blocked |
| 11 | `huggingface` provider → blocked |
| 12 | `ollama` / `vllm` / `transformers` → blocked |
| 13 | `pywinauto` provider → blocked |
| 14 | `custom_http` provider → blocked |
| 15 | `approved=true` ignored by gate |
| 16 | Env var enablement ignored by gate |
| 17 | Provider cannot set `provider_call_allowed=true` |
| 18 | Provider cannot expand action policy |
| 19 | Blocked response has `inference_allowed=false` |
| 20 | All safety flags `false` on blocked |

**Expected:** Only `fixture_only` → `MODEL_PROVIDER_ALLOWED`. Everything else → `MODEL_PROVIDER_BLOCKED`.

---

## 7. Runtime Isolation Boundary Tests (14)

| # | Test |
|:---:|------|
| 1 | Inference disabled by default |
| 2 | `inference_enabled=false` blocks model call |
| 3 | Worker cannot import `pywinauto` |
| 4 | Worker cannot import GUI automation libraries |
| 5 | Worker has no provider access |
| 6 | Worker cannot call `/api/gui-agent/step` |
| 7 | Worker returns Raw Model Output Envelope only |
| 8 | Soft timeout enforced (30s) |
| 9 | Hard timeout enforced (60s) |
| 10 | Memory budget enforced (4096 MB) |
| 11 | GPU disabled by default |
| 12 | Concurrency limit enforced (1 worker) |
| 13 | Queue overflow → `MODEL_RUNTIME_QUEUE_FULL` |
| 14 | Runtime errors → `provider_call_allowed=false` |

---

## 8. Model Source / Weights Boundary Tests (14)

| # | Test |
|:---:|------|
| 1 | `safetensors` allowed (future, after provider approval) |
| 2 | Pickle `.pt`/`.pth` → blocked |
| 3 | `trust_remote_code=true` → `MODEL_TRUST_REMOTE_CODE_BLOCKED` |
| 4 | `weights_only=false` → blocked |
| 5 | Checksum missing → `MODEL_CHECKSUM_REQUIRED` |
| 6 | Checksum mismatch → `MODEL_CHECKSUM_MISMATCH` |
| 7 | `model_dir` traversal → `MODEL_PATH_SCOPE_BLOCKED` |
| 8 | `model_dir` rawdata → blocked |
| 9 | `model_dir` derivatives → blocked |
| 10 | Absolute arbitrary `model_dir` → blocked |
| 11 | Symlink escape → blocked |
| 12 | Runtime weight download → `MODEL_NETWORK_BLOCKED` |
| 13 | User-supplied model path → blocked |
| 14 | Unknown HF repo → blocked |

**Expected:** All real model sources blocked; no weights loaded in current phase.

---

## 9. Network Boundary Tests (9)

| # | Test |
|:---:|------|
| 1 | `network_access=disabled` passes |
| 2 | `network_access=local_only` → blocked |
| 3 | `network_access=unrestricted` → blocked |
| 4 | Arbitrary outbound HTTP → blocked |
| 5 | Runtime weight download → blocked |
| 6 | Telemetry → disabled |
| 7 | Remote provider → disabled |
| 8 | Upload blocked (screenshot, clipboard, rawdata) |
| 9 | Remote API key not logged |

**Expected:** `network_accessed=false` in all current responses.

---

## 10. Input Redaction Boundary Tests (20)

| # | Test |
|:---:|------|
| 1 | Safe bounded summary passes |
| 2 | Input exceeds char limit → `MODEL_INPUT_TOO_LONG` |
| 3 | Raw screenshot → `MODEL_INPUT_CONTAINS_SCREENSHOT` |
| 4 | Screenshot OCR → blocked |
| 5 | Clipboard → `MODEL_INPUT_CONTAINS_CLIPBOARD` |
| 6 | Raw UI text → blocked |
| 7 | Raw terminal output → blocked |
| 8 | Browser DOM → blocked |
| 9 | File contents → blocked |
| 10 | Rawdata path → `MODEL_INPUT_CONTAINS_RAWDATA_PATH` |
| 11 | Derivatives path → `MODEL_INPUT_CONTAINS_DERIVATIVES_PATH` |
| 12 | Absolute path → blocked |
| 13 | PHI → `MODEL_INPUT_CONTAINS_PHI` |
| 14 | API key/token → `MODEL_INPUT_CONTAINS_CREDENTIAL` |
| 15 | "provider=pywinauto" in text → stripped or blocked |
| 16 | "approved=true" in text → stripped or blocked |
| 17 | "ignore safety"/"disable guard" → blocked |
| 18 | "click run" → blocked |
| 19 | Raw coordinates → blocked |
| 20 | Redaction failure → `MODEL_INPUT_REDACTION_FAILED`, inference blocked |

---

## 11. Model Output / Adapter Boundary Tests (16)

| # | Test |
|:---:|------|
| 1 | Safe observation → `record_observation` |
| 2 | Ambiguous intent → `ambiguous_intent` |
| 3 | Raw coordinate click → `raw_coordinate_click_blocked` |
| 4 | Provider selection → `provider_selection_blocked` |
| 5 | `approved=true` → `approval_override_blocked` |
| 6 | Screenshot request → `screenshot_request_blocked` |
| 7 | Clipboard request → `clipboard_request_blocked` |
| 8 | File path → `file_path_blocked` |
| 9 | Rawdata path → `rawdata_path_blocked` |
| 10 | Derivatives → `derivatives_write_blocked` |
| 11 | Network request → `network_request_blocked` |
| 12 | Credential → `credential_request_blocked` |
| 13 | Shell command → `shell_command_blocked` |
| 14 | Tier 1/2/3 → blocked |
| 15 | Confidence does not override |
| 16 | No chain-of-thought logged |

**Expected:** Only `record_observation` → `NORMALIZED_ACTION_READY`. All else → `MODEL_ACTION_REJECTED`.

---

## 12. Audit Metadata Boundary Tests (15)

| # | Test |
|:---:|------|
| 1 | Valid metadata writes to scoped path |
| 2 | Audit path `rawdata/` → blocked |
| 3 | Audit path `derivatives/` → blocked |
| 4 | Path traversal → blocked |
| 5 | Absolute arbitrary path → blocked |
| 6 | User-provided filename → ignored/blocked |
| 7 | Forbidden fields rejected at schema |
| 8 | `raw_text` not persisted |
| 9 | `chain_of_thought` not persisted |
| 10 | `screenshot_bytes` not persisted |
| 11 | `clipboard_contents` not persisted |
| 12 | Credentials not persisted |
| 13 | Adapter mapped metadata → persisted correctly |
| 14 | Adapter rejected metadata → persisted correctly |
| 15 | Audit failure → blocks provider call |

---

## 13. Existing GUI Guard Regression Tests (11)

| # | Test | File |
|:---:|------|------|
| 1 | Provider=mock only | `test_gui_agent_provider_policy_gate.py` |
| 2 | PyWinAuto/real blocked | `test_gui_agent_provider_policy_gate.py` |
| 3 | `approved=true` cannot bypass | `test_gui_agent_provider_policy_gate.py` |
| 4 | Session validator (18 fields) | `test_gui_agent_session_declaration_validator.py` |
| 5 | Action validator (only record_obs) | `test_gui_agent_action_declaration_validator.py` |
| 6 | Tier 1/2/3 blocked | `test_gui_agent_action_declaration_validator.py` |
| 7 | Audit pre-create | `test_gui_agent_audit_and_stop_conditions.py` |
| 8 | Stop conditions | `test_gui_agent_audit_and_stop_conditions.py` |
| 9 | Guarded API integration | `test_gui_agent_guarded_api_integration.py` |
| 10 | Schema consistency | `test_gui_agent_schema_consistency.py` |
| 11 | Error code audit | `test_gui_agent_adapter_error_code_audit.py` |

---

## 14. Reviewed Execution Regression Tests (6)

| # | Test |
|:---:|------|
| 1 | GUI allowlist = 0 |
| 2 | `gui_*` blocked at plan_adapter |
| 3 | `executor_called=false` |
| 4 | SPM allowlist unchanged (7) |
| 5 | DPABI allowlist unchanged (20) |
| 6 | GPU allowlist unchanged (9) |

---

## 15. Non-Call / Isolation Assertions (9)

| # | Assertion |
|:---:|------|
| 1 | `pywinauto` not imported |
| 2 | PyWinAutoGuiProvider not constructed |
| 3 | No GUI automation libraries imported |
| 4 | No mouse function called |
| 5 | No keyboard function called |
| 6 | No clipboard function called |
| 7 | No screenshot function called |
| 8 | No real model inference called |
| 9 | No rawdata/derivatives written |

---

## 16. Acceptance Gate Before Real Model Implementation

```
[ ] All 1772 current tests pass
[ ] Frontend build passes
[ ] Provider policy boundary tests pass (20 tests)
[ ] Runtime isolation boundary tests pass (14 tests)
[ ] Model source/weights boundary tests pass (14 tests)
[ ] Network boundary tests pass (9 tests)
[ ] Input redaction boundary tests pass (20 tests)
[ ] Model output/adapter boundary tests pass (16 tests)
[ ] Audit metadata boundary tests pass (15 tests)
[ ] Existing GUI guard regression tests pass (11 test files)
[ ] Reviewed execution regression tests pass (6 assertions)
[ ] Non-call/isolation assertions pass (9 assertions)
[ ] GUI/manual reviewed execution allowlist remains 0
[ ] PyWinAuto remains blocked
[ ] Only record_observation remains executable
[ ] Real model provider remains disabled
```

**~137 boundary tests (11 existing + ~120 new) + 1772 existing = ~1900 total expected after implementation.**

---

## 17. Future Test File Plan

| File | Tests | Category |
|------|:---:|------|
| `tests/unit/test_gui_model_provider_policy_gate.py` | 20 | Provider gate |
| `tests/unit/test_gui_model_runtime_isolation_contract.py` | 14 | Runtime |
| `tests/unit/test_gui_model_source_policy.py` | 14 | Weights/source |
| `tests/unit/test_gui_model_network_policy.py` | 9 | Network |
| `tests/unit/test_gui_model_input_redaction_contract.py` | 20 | Input |
| `tests/unit/test_gui_model_audit_metadata_contract.py` | 15 | Audit |
| `tests/unit/test_gui_model_mock_real_boundary.py` | ~12 | Boundary integration |
| **Total new** | **~104** | |

---

## 18. Future Implementation Roadmap

```
M11-GUI-MODEL-CLOSEOUT: Real model integration design closeout
```

After closeout, the implementation phase would map each design document to code:
- Provider gate → `gui_model_provider_gate.py`
- Runtime isolation → `gui_model_runtime.py`
- Input redaction → `gui_model_input_minimizer.py`
- Audit persistence → `gui_model_audit_writer.py`

---

## 19. References

| Document | Tests Designed |
|----------|:---:|
| `docs/MODEL_PROVIDER_POLICY_GATE_DESIGN.md` | 20 |
| `docs/MODEL_RUNTIME_ISOLATION_DESIGN.md` | 14 |
| `docs/MODEL_INFERENCE_INPUT_REDACTION_DESIGN.md` | 20 |
| `docs/MODEL_OUTPUT_AUDIT_METADATA_PERSISTENCE_DESIGN.md` | 15 |
| `docs/REAL_MODEL_INTEGRATION_THREAT_MODEL.md` | 17 invariants |
| `docs/M10_FULL_TEST_BASELINE_LOCK.md` | Baseline |
