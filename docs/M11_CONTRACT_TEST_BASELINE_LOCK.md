# M11 Contract Test Baseline Lock

> M11-GUI-MODEL-CONTRACT-STABILIZE-T003 | Final baseline after contract + stabilization  
> Status: COMPLETE | Date: 2026-07-11  
> Replaces: `docs/M10_FULL_TEST_BASELINE_LOCK.md` for M11 contract scope

---

## 1. Executive Summary

This document locks the complete test baseline after the M11 real model safety contract implementation and stabilization phases. It records every contract module, every test file, every invariant, and every regression command needed to validate the system before any future real model implementation.

**Current baseline: 2328 passed, 4 skipped. Frontend build: passed.**

**Total M11 contract + stabilization tests: 556. M10 total was 1772 → +556 = 2328.**

---

## 2. Current Baseline Snapshot

| Metric | Value |
|--------|------|
| Total tests | **2328 passed, 4 skipped** |
| Skipped | 4 (CuPy unavailable — GPU benchmark) |
| Frontend build | ✅ Passed |
| Reviewed execution allowlist | **36** (M6:7, M7:20, M8:9, M9:0) |
| GUI/manual allowlist | **0** |
| PyWinAuto loaded | **No** |
| Real model connected | **No** |
| Real GUI automation | **None** |
| M11 contract modules | 5 pure-function modules |
| M11 contract tests | 447 |
| M11 stabilization tests | 109 |

---

## 3. Reviewed Execution Baseline

| Phase | Nodes | Gate Type |
|-------|:---:|------|
| M6 SPM | 7 | Sandbox-gated |
| M7 DPABI | 20 | Metadata/sandbox/report-gated |
| M8 GPU | 9 | Scaffold-gated |
| M9/M10/M11 GUI | **0** | Blocked |
| **Total** | **36** | |

---

## 4. M11 Contract Module Baseline

| Module | Tests | Key Capability |
|------|:---:|------|
| `gui_model_provider_policy.py` | 46 | Only `fixture_only` allowed; 16 blocked providers |
| `gui_model_runtime_isolation.py` | 59 | Only `fixture_only` runtime; 6 blocked runtime types |
| `gui_model_source_policy.py` | 69 | Only `fixture_catalog` source; pure-string path validation |
| `gui_model_input_redaction.py` | 63 | Safe prompt envelope; 12 pattern categories |
| `gui_model_audit_contract.py` | 112 | Metadata-only; recursive forbidden-field scan |
| **Contract total** | **349** | |

All modules are pure-function safety contracts. They do not call inference, load weights, start workers, read/write files, call GUI APIs, or import pywinauto.

---

## 5. M11 Contract Test Baseline

| File | Tests | Category |
|------|:---:|------|
| `test_gui_model_provider_policy_gate.py` | 46 | Provider policy gate |
| `test_gui_model_runtime_isolation_contract.py` | 59 | Runtime isolation contract |
| `test_gui_model_source_policy.py` | 69 | Source/weights policy |
| `test_gui_model_input_redaction_contract.py` | 63 | Input redaction contract |
| `test_gui_model_audit_contract.py` | 112 | Audit metadata contract |
| `test_gui_model_mock_real_boundary.py` | 98 | Boundary integration |
| **Contract tests total** | **447** | |

---

## 6. Stabilization Test Baseline

| File | Tests | Category |
|------|:---:|------|
| `test_gui_model_contract_schema_consistency.py` | 56 | Cross-contract schema consistency |
| `test_gui_model_contract_error_taxonomy.py` | 53 | Error code taxonomy audit |
| **Stabilization total** | **109** | |

**M11 contract + stabilization total: 556 tests.**

---

## 7. Existing GUI/Model Path Baseline

```
Fixture/mock model output (45 static fixtures)
  → validate_and_normalize_model_output()
  → Only safe observation → record_observation
  → Mock adapter route (POST /api/gui-agent/mock-adapter/step)
  → Existing guarded step path (provider/session/action/stop/audit)
  → MockGuiProvider only
```

No real model. No inference. No real provider. No contract module grants execution permission.

---

## 8. Critical Safety Invariants (30)

1. GUI/manual reviewed execution allowlist remains **0**.
2. PyWinAuto remains blocked and unimported.
3. real/desktop/browser/manual providers remain blocked.
4. `provider=mock` remains the only GUI provider path.
5. `fixture_only` remains the only allowed model provider mode.
6. `fixture_only` remains the only allowed runtime mode.
7. `fixture_catalog` remains the only allowed model source.
8. Real model remains disconnected.
9. Inference remains uncalled.
10. Model weights remain unloaded.
11. Worker process remains unstarted.
12. Audit writer remains unimplemented.
13. Audit files remain unwritten.
14. Adapter never sets `provider_call_allowed=true`.
15. Contract modules never set `provider_call_allowed=true`.
16. Contract modules never set `inference_allowed=true`.
17. Only `record_observation` can execute.
18. Tier 1/2/3 remain blocked (40/41 actions).
19. Screenshots remain blocked.
20. Clipboard remains blocked.
21. Mouse/keyboard remain blocked.
22. Network remains blocked.
23. Rawdata remains blocked.
24. Derivatives write remains blocked.
25. Raw prompt/output persistence remains blocked.
26. All contract blocked results fail closed.
27. All allowed contract results grant no execution permission.
28. Mock-real boundary tests pass.
29. GUI reviewed execution blocklist tests pass.
30. Frontend build passes.

---

## 9. Required Regression Command Sets

### Minimal M11 Contract Regression (~2s)
```bash
pytest tests/unit/test_gui_model_provider_policy_gate.py -v
pytest tests/unit/test_gui_model_runtime_isolation_contract.py -v
pytest tests/unit/test_gui_model_source_policy.py -v
pytest tests/unit/test_gui_model_input_redaction_contract.py -v
pytest tests/unit/test_gui_model_audit_contract.py -v
```
**Expected: 349 tests, all pass.**

### Boundary + Stabilization (~2s)
```bash
pytest tests/unit/test_gui_model_mock_real_boundary.py -v
pytest tests/unit/test_gui_model_contract_schema_consistency.py -v
pytest tests/unit/test_gui_model_contract_error_taxonomy.py -v
```
**Expected: 207 tests, all pass.**

### Existing GUI/Model Path Regression (~5s)
```bash
pytest tests/unit/test_gui_agent_mock_adapter_e2e.py -v
pytest tests/unit/test_gui_agent_model_output_validator.py -v
pytest tests/unit/test_gui_reviewed_execution_blocklist.py -v
```
**Expected: 150 tests, all pass.**

### Full Validation (~250s)
```bash
pytest --tb=short
npm --prefix src/frontend run build
```
**Expected: 2328 passed, 4 skipped. Frontend build: passed.**

---

## 10. Regression Severity Classification

### Critical — STOP, do not proceed
- GUI/manual node reaches EXECUTION_SUBMITTED
- PyWinAuto imported or constructed
- Real model provider accepted outside `fixture_only`
- `inference_allowed=true` in any M11 contract result
- `provider_call_allowed=true` in any M11 contract result
- Tier 1/2/3 action executes
- Screenshot/clipboard/mouse/keyboard/network enabled
- Forbidden raw prompt/output persisted

### High — Investigate before proceeding
- Blocked result no longer fail-closed
- Error code prefix/status mismatch
- Path traversal not blocked
- Credential/PHI not blocked
- SPM/DPABI/GPU reviewed execution regression

### Medium — Document and proceed if accepted
- Test count changes without baseline update
- Error taxonomy changes without audit doc update
- Schema changes without consistency doc update

### Low — Normal development
- New tests added with baseline updated
- Documentation-only updates
- New blocked cases added

---

## 11. Expected-Change Policy

| Change | Required Update |
|------|------|
| Test count changes | Update this document and `CURRENT_STATE.md` |
| Contract field changes | Update `M11_CONTRACT_SCHEMA_CONSISTENCY_REVIEW.md` |
| Error code changes | Update `M11_CONTRACT_ERROR_CODE_TAXONOMY_AUDIT.md` |
| Provider/runtime/source mode changes | Open a new reviewed safety phase |
| Real model integration begins | Require new implementation threat review |
| Inference enabled | Require all 8 gate-level tests |
| Action policy expands | Require separate GUI action safety phase |
| Audit writer implemented | Require scoped write + forbidden-field persistence tests |

---

## 12. Future Real-Model Implementation Gate

```
Do NOT implement real inference before ALL of:
  - Provider policy gate tests pass
  - Runtime isolation tests pass
  - Model source/weights policy tests pass
  - Input redaction tests pass
  - Audit metadata contract tests pass
  - Mock-real boundary tests pass
  - Schema consistency tests pass
  - Error taxonomy tests pass
  - GUI reviewed execution blocklist tests pass
  - Full suite (2328+) passes
  - Frontend build passes

Even after all gates: real model implementation must begin
in a separate reviewed phase (M12).
```

---

## 13. Maintenance Checklist

Before any PR touching model contract code:
- [ ] Run: all 5 contract test files (349 tests)
- [ ] Run: boundary + stabilization test files (207 tests)
- [ ] Run: existing GUI/model path tests (150 tests)
- [ ] Run: `pytest --tb=short` (2328 tests)
- [ ] Run: `npm --prefix src/frontend run build`
- [ ] Verify: `pywinauto` not in `sys.modules`
- [ ] Verify: GUI/manual reviewed execution allowlist = 0
- [ ] Verify: No contract result has `provider_call_allowed=true`
- [ ] Verify: No contract result has `inference_allowed=true`
- [ ] Update: `docs/CURRENT_STATE.md` with new test count if changed
- [ ] Update: this baseline document if invariants changed

---

## 14. References

| Document | Content |
|----------|------|
| `docs/M11_REAL_MODEL_SAFETY_CONTRACT_CLOSEOUT.md` | Contract closeout |
| `docs/M11_CONTRACT_SCHEMA_CONSISTENCY_REVIEW.md` | Schema consistency |
| `docs/M11_CONTRACT_ERROR_CODE_TAXONOMY_AUDIT.md` | Error taxonomy |
| `docs/M10_FULL_TEST_BASELINE_LOCK.md` | Previous baseline (superseded for M11) |
