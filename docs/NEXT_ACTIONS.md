# 下一步行动 (NEXT_ACTIONS)

> M8 GPU Phase — COMPLETE 🎉 (36 total reviewed execution nodes)

## M6: 7 SPM | M7: 20 DPABI | M8: 9 GPU

## Next: M9-GUI-T001 GUI/manual node inventory and threat model — ✅ COMPLETE (2026-07-11)

See `docs/GUI_MANUAL_AGENT_THREAT_MODEL.md` for the full threat model and inventory.

**Key findings:**
- 0 GUI/manual nodes in NODE_REGISTRY or reviewed execution allowlist
- GUI Agent subsystem (`gui_agent.py`) exists as a standalone system outside reviewed execution
- Mock provider is default; pywinauto provider can perform real desktop click/type/screenshot
- GUI agent API is LIVE (`main.py:55` — `app.include_router(gui_agent_router)`)
- Current reviewed execution correctly blocks all GUI/manual nodes (plan_adapter + approval_gate)
- Safety gap: GUI agent API bypasses the 12-gate reviewed execution pipeline

## M9-GUI-T002：GUI approval and HITL design — ✅ COMPLETE (2026-07-11)

See `docs/GUI_MANUAL_APPROVAL_HITL_DESIGN.md` for the full design.

**Key design decisions:**
- Three-layer approval model: Session → Action-Plan → Per-Action
- `approved=true` boolean insufficient for real desktop control
- Provider policy: mock default safe / pywinauto requires `MEDIMAGE_GUI_AGENT_REAL_PROVIDER=1`
- Integration recommendation: Option B Phase 1 (add equivalent 12-gate guard to GUI agent API)
- Per-action confirmation for Tier 2/3 actions with semantic approval text
- Suggested HIGH_RISK_BACKENDS expansion to include `gui`, `manual`, `desktop`, `browser`
- Human-in-the-loop requires structured Action Plan display + emergency abort

## M9-GUI-T003：GUI action taxonomy and sandbox contract — ✅ COMPLETE (2026-07-11)

See `docs/GUI_ACTION_TAXONOMY_AND_SANDBOX_CONTRACT.md` for the full taxonomy and contracts.

**Key deliverables:**
- 29 actions classified into 4 tiers with 14 dimension fields each
- Full Sandbox Declaration Schema (23 fields + validation rules)
- Full Action Declaration Schema (22 fields)
- 5 standalone policy contracts: Screenshot, Clipboard, File/Path, Network, External App/Window
- 22 permanently blocked actions with required future contract specifications
- `classify_gui_action()` and `validate_gui_session_declaration()` pseudocode
- 25 test benchmarks defined for M9-GUI-T004

## M9-GUI-T004：GUI blocklist tests — ✅ COMPLETE (2026-07-11)

New test file: `tests/unit/test_gui_reviewed_execution_blocklist.py` — 38 tests covering:
- Plan Adapter GUI blocklist (12 tests): gui_* prefix, backend=gui/gui-agent/manual/desktop/browser, mock/pywinauto providers
- Approval Gate (6 tests): manual_required, wildcard, backend-only, boolean-only, multiple manual, regression
- Execute-Reviewed API (11 tests): policy blocked, executor_called=false, all blocked backends, wildcard, backends-only, regression
- Tool Catalog (5 tests): gui_* fallback contract, manual_required=true, requires_approval, required fields, non-gui not affected
- Safety gap (1 test): /api/gui-agent/* bypass still exists
- Regression (3 tests): SPM sandbox, DPABI metadata, GPU contract all still work

Total: 1192 passed, 4 skipped. Frontend build: passed.

## M9-GUI-T005：Read-only observation contract — ✅ COMPLETE (2026-07-11)

See `docs/GUI_READ_ONLY_OBSERVATION_CONTRACT.md` for the full contract.

**Key deliverables:**
- 7 Tier 0 read-only actions formally contracted
- Mock provider: safe by default, CI-allowed, no real screenshot/desktop access
- Real provider: still blocked, design-only, requires future 7-gate guard
- Screenshot policy: 4-level (disabled→ephemeral_only→persist_redacted→persist_raw=blocked)
- Sensitive data policy: UI text untrusted, must redact before persistence, no following UI instructions
- Session Declaration: 24 fields + 13 rejection conditions
- Action Declaration: 22 fields + 9 rejection conditions
- Audit: 17 required fields + 5 prohibited fields
- Stop conditions: 11 automatic stop triggers
- 16 future test benchmarks defined

## M9-GUI-T006：Manual-only smoke guide — ✅ COMPLETE (2026-07-11)

See `docs/GUI_MANUAL_SMOKE_GUIDE.md` for the full manual smoke guide.

**Key deliverables:**
- 36-item manual smoke checklist covering all M9 security components
- 7 automated verification steps (all GUI-related test suites)
- 5 manual code inspection steps (MockGuiProvider, PyWinAuto, tool_catalog, approval_gate, bypass)
- 7 failure diagnostic scenarios with specific investigation + remediation steps
- Full cleanup guide + environment variable cleanup
- Printable/copiable checklist for human operators

## M9-GUI-CLOSEOUT：Phase Closeout — ✅ COMPLETE (2026-07-11)

See `docs/M9_GUI_MANUAL_PHASE_CLOSEOUT.md` for the full phase closeout.

**M9 GUI/manual Agent Phase: COMPLETE 🎉**

7 tasks delivered:
- T001: Threat model and inventory (7 attack surfaces, 5 safety gaps)
- T002: Three-layer approval + HITL design (Session → Action-Plan → Per-Action)
- T003: 29-action taxonomy + 5 standalone policy contracts + classification rules
- T004: 38 automated blocklist tests (executor_called=false locked)
- T005: Read-only observation contract (7 Tier 0 actions, 4-level screenshot policy)
- T006: 36-item manual smoke guide with failure diagnostics
- CLOSEOUT: Phase summary + 20 acceptance criteria for future real-provider work

**Allowlist: 36 total (M6:7 / M7:20 / M8:9 / M9:0)**
**No code modified except test file (T004).**
**No GUI execution opened.**

## M6–M9 Safety Architecture Review — ✅ COMPLETE (2026-07-11)

See `docs/M6_M9_SAFETY_ARCHITECTURE_REVIEW.md` for the full cross-phase safety architecture review.

Covers:
- Phase-by-phase safety model (M6 SPM → M7 DPABI → M8 GPU → M9 GUI)
- Risk model comparison across all four capability types
- Why M6–M8 can be allowlisted vs. why M9 remains blocked
- `/api/gui-agent/*` bypass: the #1 priority gap for next phase
- Fine-tuned GUI Agent integration architecture (model → adapter → guard layers → provider)
- 12 future GUI guard layers + 12 non-negotiable safety invariants
- Recommended roadmap: guard implementation → mock-only testing → real-provider gating

## M9-GUI-GUARD-T001：API Guard Design — ✅ COMPLETE (2026-07-11)

See `docs/GUI_AGENT_API_GUARD_DESIGN.md` for the full guard design.

Key deliverables:
- 14-layer guard pipeline design (Schema → Session → Provider → Target → Action → Tier → File → Screenshot → Clipboard → Network → Approval → Audit → Stop → Token)
- 13 structured error codes (GUI_GUARD_PROVIDER_BLOCKED, GUI_GUARD_ACTION_TIER_BLOCKED, etc.)
- Standardised error response schema
- Provider policy gate: mock-only by default; PyWinAuto blocked unconditionally
- Action tier classifier: 29 actions mapped to 4 tiers with block/pass/confirm rules
- session declaration validator: 23 fields, 13 rejection conditions
- action declaration validator: 22 fields, 9 rejection conditions
- approval/HITL integration: session → action-plan → per-action; approved=true deprecated
- audit log: 17 required fields, 4 prohibited fields, sensitive-data redaction
- stop-condition checker: 12 conditions, implementation phases
- Emergency abort: client + server + automated layers; abort token design
- Mock-only rollout: 6-phase implementation plan (T002–T006 + CLOSEOUT)
- Fine-tuned GUI Agent path: Model → Action Adapter → Schema → Guard → Provider
- 25 future test benchmarks

## M9-GUI-GUARD-T002：Provider Policy Gate — ✅ IMPLEMENTED (2026-07-11)

Implemented the first layer of the 14-layer GUI Agent API guard. Production code changed: YES (3 files).

**Production files:**
- `src/backend/app/runtime/gui_agent_guard.py` (NEW) — `GuiGuardResult` dataclass + `validate_gui_provider_policy()`
- `src/backend/app/api/gui_agent_routes.py` (MODIFIED) — route-level gate on session creation
- `src/backend/app/runtime/gui_agent.py` (MODIFIED) — runtime-level defense in `_provider()`

**Test file:**
- `tests/unit/test_gui_agent_provider_policy_gate.py` (NEW) — 43 tests

**Behavior:**
- Only `provider="mock"` returns `ok=true`, `provider_call_allowed=true`
- `provider="pywinauto"` / `"real"` / `"desktop"` / `"browser"` / `"manual"` → HTTP 403 + structured error
- `approved=true` does NOT bypass the gate
- `MEDIMAGE_GUI_AGENT_REAL_PROVIDER=1` alone does NOT bypass
- PyWinAuto provider is never constructed
- Mock sessions and steps continue to work (no regression)
- Reviewed execution GUI blocklist: 38/38 still pass
- SPM/DPABI/GPU allowlists: unchanged
- Full test suite: 1235 passed, 4 skipped

## M9-GUI-GUARD-T003：Session Declaration Validator — ✅ IMPLEMENTED (2026-07-11)

Implemented the session declaration validator (Layer 2 of the 14-layer guard pipeline). Production code changed: YES (3 files).

**Production files:**
- `src/backend/app/runtime/gui_agent_guard.py` (MODIFIED) — `validate_gui_session_declaration()`, new error codes
- `src/backend/app/api/gui_agent_routes.py` (MODIFIED) — `_guard_session()` integration in POST session
- `src/backend/app/api/models.py` (MODIFIED) — `GuiAgentSessionRequest` extended with 18 session declaration fields (safe defaults for backward compat)

**Test file:**
- `tests/unit/test_gui_agent_session_declaration_validator.py` (NEW) — 54 tests

**Validated fields (18):** gui_sandbox_mode, provider, target_application, target_window, allowed_action_tiers, file_scope, allow_rawdata_access, allow_derivatives_write, screenshot_policy, clipboard_policy, network_policy, external_app_policy, duration_limit_seconds, step_limit, human_present, emergency_abort_enabled, audit_log_required, redaction_policy

**Blocked cases:** Tier 1/2/3, screenshot!=disabled, clipboard!=disabled, network!=disabled, rawdata/derivatives access, invalid file_scope, human_present=false, emergency_abort=false, audit_log_required=false, limits exceeded

**Full test suite: 1289 passed, 4 skipped. T002 regression: 43/43. T004 regression: 38/38.**

## M9-GUI-GUARD-T004：Action Validator + Tier Classifier — ✅ IMPLEMENTED (2026-07-11)

Implemented the action declaration validator + tier classifier (Layers 5-6 of the 14-layer guard pipeline). Production code changed: YES (3 files).

**Production files:**
- `src/backend/app/runtime/gui_agent_guard.py` (MODIFIED) — action taxonomy (29 actions, 4 tiers), `classify_gui_action_tier()`, `validate_gui_action_declaration()`, 10 new error codes
- `src/backend/app/api/gui_agent_routes.py` (MODIFIED) — `_guard_action()` integration in POST step
- `src/backend/app/api/models.py` (MODIFIED) — `GuiAgentStepRequest` extended with 13 action declaration fields

**Test file:**
- `tests/unit/test_gui_agent_action_declaration_validator.py` (NEW) — 52 tests

**T004 policy:** Only `action_type=record_observation` with `provider=mock` passes. All other 28 actions blocked. Tier 0 actions that aren't record_observation blocked as `GUI_GUARD_ACTION_NOT_ALLOWED`. Tier 1/2/3 blocked. Usage flags (screenshot/clipboard/keyboard/mouse/network) blocked. Path/side-effect/confirmation violations blocked.

**Full test suite: 1341 passed, 4 skipped. T002/T003/T004 regressions all passed.**

## M9-GUI-GUARD-T005：Audit Log + Stop-Condition Checker — ✅ IMPLEMENTED (2026-07-11)

Implemented audit pre-create + stop-condition checker (Layers 12-13 of the 14-layer guard pipeline). Production code changed: YES (3 files).

**Production files:**
- `src/backend/app/runtime/gui_agent_guard.py` (MODIFIED) — `GuiAuditRecord` dataclass, `create_gui_audit_record()`, `validate_gui_stop_conditions()`, 7 new error codes
- `src/backend/app/runtime/gui_agent.py` (MODIFIED) — session state extended with `_created_at_ts`, `step_count`, and all session declaration fields; step_count increments on every step
- `src/backend/app/api/gui_agent_routes.py` (MODIFIED) — stop-condition check + audit pre-create in POST step before provider call

**Test file:**
- `tests/unit/test_gui_agent_audit_and_stop_conditions.py` (NEW) — 38 tests

**T005 checkpoint order:** stop-condition check → audit pre-create → provider call. Audit record attached to response as `audit` field. Blocked steps get audit record with `audit_id` in error detail. step_limit exceeded, duration exceeded, emergency abort all blocked with structured errors.

**Full test suite: 1379 passed, 4 skipped. T002/T003/T004/T005 regressions all passed.**

## M9-GUI-GUARD-T006：Guarded API Integration Tests — ✅ COMPLETE (2026-07-11)

62 end-to-end integration tests. No production code changed.

**Full suite: 1441 passed, 4 skipped.**

## M9-GUI-GUARD-CLOSEOUT：Guard Phase Closeout — ✅ COMPLETE (2026-07-11)

See `docs/M9_GUI_AGENT_API_GUARD_CLOSEOUT.md` for the full closeout.

**M9 GUI Agent API Guard Phase: COMPLETE 🎉**

`/api/gui-agent/*` transformed from known bypass → mock-only guarded API. 6 guard layers implemented, 4 production files modified, 249 new tests. Only `mock + valid session + record_observation` reaches provider. PyWinAuto permanently blocked.

## M10-GUI-AGENT-T001：Action Adapter Design — ✅ COMPLETE (2026-07-11)

See `docs/FINE_TUNED_GUI_AGENT_ACTION_ADAPTER_DESIGN.md`.

Design covers: 6 model output classes, Normalized GUI Action Schema, rejection policy (22 categories), prompt injection handling, model-output validator (14 checks), guard/audit integration, mock-only rollout (5-phase plan).

## M10-GUI-AGENT-T002：Normalized Action Schema — ✅ COMPLETE (2026-07-11)

See `docs/NORMALIZED_GUI_ACTION_SCHEMA.md`. Formal data contract: raw model output envelope, normalized action envelope, rejection result schema (21 reasons), adapter decision schema, audit metadata schema, mapping to `GuiAgentStepRequest`. **Action taxonomy count corrected: 41 actions (7+6+6+22), not 29.** 34 test benchmarks for T003 validator.

## M10-GUI-AGENT-T003：Model-Output Validator — ✅ IMPLEMENTED (2026-07-11)

New module: `src/backend/app/runtime/gui_agent_model_adapter.py` — pure functions, no provider/API/GUI calls. 58 tests.

**Key behavior:** Only safe observation → record_observation passes. 21 rejection reasons active. Provider selection, approved=true, screenshots, clipboard, keyboard, mouse, network, credentials, shell commands, policy override, raw coordinates, multi-action plans all blocked. `provider_call_allowed=false` at adapter stage.

**Full suite: 1499 passed, 4 skipped.**

## M10-GUI-AGENT-T004：Adapter/Guard Compatibility Tests — ✅ COMPLETE (2026-07-11)

79 tests: normalized action → guard compatibility (20), adapter safety flags (9), rejected output isolation (8), rejection categories (16), no sensitive logging (8), API smoke (4), regression (14). No production code changed.

**Full suite: 1578 passed, 4 skipped.**

## M10-GUI-AGENT-CLOSEOUT：Adapter Phase Closeout — ✅ COMPLETE (2026-07-11)

See `docs/M10_GUI_AGENT_ADAPTER_PHASE_CLOSEOUT.md`. 4 tasks + closeout: adapter validated, schema defined, 137 tests, 21+ rejection reasons. No real model connected. No execution opened beyond mock-only `record_observation`.

## M10-GUI-AGENT-MOCK-T001：Mock Adapter API Design — ✅ COMPLETE (2026-07-11)

See `docs/MOCK_MODEL_ADAPTER_API_DESIGN.md`. Architecture, request/response schemas, adapter→guard flow, rejection flow, audit metadata, error codes, 25 future test benchmarks.

## M10-GUI-AGENT-MOCK-T002：Mock Fixtures — ✅ IMPLEMENTED (2026-07-11)

45 fixtures across 9 categories, 32 tests. Module: `gui_agent_mock_model_fixtures.py`. Safe observation fixtures → record_observation. All rejection fixtures → MODEL_ACTION_REJECTED with expected reasons verified.

**Full suite: 1610 passed, 4 skipped.**

## M10-GUI-AGENT-MOCK-T003：Mock Adapter API Route — ✅ IMPLEMENTED (2026-07-11)

2 new routes: `GET /api/gui-agent/mock-adapter/fixtures` + `POST /api/gui-agent/mock-adapter/step`. Fixture → adapter → dry-run/guard submission. 32 API tests. **1642 passed, 4 skipped.**

## M10-GUI-AGENT-MOCK-T004：Adapter-to-Guard E2E Tests — ✅ COMPLETE (2026-07-11)

54 end-to-end tests: fixture catalog (6), dry-run (4), safe submit (12), rejection e2e (6 + 10 parametrized), request validation (5), guard failure (5), non-call (3), regression (6). **1696 passed, 4 skipped.**

## M10-GUI-AGENT-MOCK-CLOSEOUT：Mock Integration Phase Closeout — ✅ COMPLETE (2026-07-11)

See `docs/M10_GUI_AGENT_MOCK_INTEGRATION_CLOSEOUT.md`. 4 tasks + closeout: 45 fixtures, 2 API routes, 118 tests, complete fixture→adapter→guard→provider chain verified. No real model. No PyWinAuto. No execution opened beyond mock-only `record_observation`.

## M10-GUI-AGENT-STABILIZE-T001：Error Code Audit — ✅ COMPLETE (2026-07-11)

Audited 55 codes across 3 layers. 44 response consistency tests. 7 inconsistencies found (all low-severity, security-safe). Document: `docs/GUI_AGENT_ADAPTER_ERROR_CODE_AUDIT.md`. **1740 passed, 4 skipped.**

## M10-GUI-AGENT-STABILIZE-T002：Schema Consistency Review — ✅ COMPLETE (2026-07-11)

2 response schema fixes (safety flags added to fixture-not-found and session-required). 32 consistency tests. All 6 response types now share uniform 5-field safety flags. 5 remaining inconsistencies accepted as intentional design. **1772 passed, 4 skipped.**

## M10-GUI-AGENT-STABILIZE-T003：Full Test Baseline Lock — ✅ COMPLETE (2026-07-11)

See `docs/M10_FULL_TEST_BASELINE_LOCK.md`. 1772 passed, 4 skipped. 25 safety invariants documented. Minimal, adapter, mock, schema, and full regression commands defined. 4-tier regression severity classification. Expected-change policy for all future modifications.

## M11-GUI-MODEL-T001：Real Model Threat Model — ✅ COMPLETE (2026-07-11)

See `docs/REAL_MODEL_INTEGRATION_THREAT_MODEL.md`. 15 threat surfaces modeled (runtime, weights, input, output, injection, privacy, supply-chain, bypass, audit). 17 non-negotiable invariants. 15 required safety controls. 6-phase implementation roadmap.

**M10 Stabilization Phase: COMPLETE 🎉**  
## M11-GUI-MODEL-T002：Runtime Isolation Design — ✅ COMPLETE (2026-07-11)

See `docs/MODEL_RUNTIME_ISOLATION_DESIGN.md`. 7-layer isolation architecture, 15 error codes, resource budgets, filesystem/network/cache policies, prompt input/output boundaries, 20 required test benchmarks.

## M11-GUI-MODEL-T003：Model Provider Policy Gate Design — ✅ COMPLETE (2026-07-11)

See `docs/MODEL_PROVIDER_POLICY_GATE_DESIGN.md`. 8 provider types, 20-step gate pipeline, 15 error codes, provider declaration schema. Only `fixture_only` allowed. All real/remote/external providers blocked.

## M11-GUI-MODEL-T004：Input Minimization Design — ✅ COMPLETE (2026-07-11)

See `docs/MODEL_INFERENCE_INPUT_REDACTION_DESIGN.md`. 5 allowed input classes, 20 blocked categories, redaction policy, prompt envelope schema, UI context/user instruction minimization, 14 error codes.

## M11-GUI-MODEL-T005：Audit Metadata Persistence Design — ✅ COMPLETE (2026-07-11)

See `docs/MODEL_OUTPUT_AUDIT_METADATA_PERSISTENCE_DESIGN.md`. 15 audit events, unified 6-section schema, 19 forbidden fields, scoped path/retention/cleanup policies, fail-closed audit failure policy, 9 error codes.

## M11-GUI-MODEL-T006：Mock-Real Boundary Tests Design — ✅ COMPLETE (2026-07-11)

See `docs/MOCK_REAL_BOUNDARY_TESTS_DESIGN.md`. ~120 tests across 10 categories, 7 future test files planned, 15-item acceptance gate for real model implementation.

## M11-GUI-MODEL-CLOSEOUT：Design Phase Closeout — ✅ COMPLETE (2026-07-11)

See `docs/M11_REAL_MODEL_INTEGRATION_DESIGN_CLOSEOUT.md`. 6 tasks + closeout: 7 design documents, 0 implementation. Real model not connected. Inference not called. 18 non-negotiable invariants documented. 10 required gates before any real model code.

**M11 Real Model Integration Design Phase: COMPLETE 🎉**  
## M11-GUI-MODEL-CONTRACT-T001：Provider Policy Gate — ✅ IMPLEMENTED (2026-07-11)

New module: `src/backend/app/runtime/gui_model_provider_policy.py`. 46 tests. Only `fixture_only` allowed. 6 real provider types + 10 blocked names. 11 policy deviation checks. No inference, no model loading, no pywinauto. **1818 passed, 4 skipped.**

## M11-GUI-MODEL-CONTRACT-T002：Runtime Isolation Contract — ✅ IMPLEMENTED (2026-07-11)

New module: `src/backend/app/runtime/gui_model_runtime_isolation.py`. 59 tests. Only `fixture_only` allowed. 6 real runtime types + 31 policy deviation checks. No worker, no inference, no pywinauto. **1877 passed, 4 skipped.**

## M11-GUI-MODEL-CONTRACT-T003：Model Source Policy — ✅ IMPLEMENTED (2026-07-11)

New module: `src/backend/app/runtime/gui_model_source_policy.py`. 69 tests. Only `fixture_catalog` allowed. 7 blocked source types, 9 path scope validations (pure string, no filesystem). No torch/transformers/safetensors imports. **1946 passed, 4 skipped.**

## M11-GUI-MODEL-CONTRACT-T004：Input Redaction Contract — ✅ IMPLEMENTED (2026-07-11)

New module: `src/backend/app/runtime/gui_model_input_redaction.py`. 63 tests. Safe minimal prompt envelope allowed. 7 raw input types blocked. 12 pattern categories detected (credentials, paths, injection, coordinates, chain-of-thought). No inference, no pywinauto. **2009 passed, 4 skipped.**

## M11-GUI-MODEL-CONTRACT-T005：Audit Metadata Contract — ✅ IMPLEMENTED (2026-07-11)

New module: `src/backend/app/runtime/gui_model_audit_contract.py`. 112 tests. 15 event types accepted. 31 forbidden fields blocked. Scoped audit path policy, metadata semantics, retention 1-30 days. No file writes, no pywinauto. **2121 passed, 4 skipped.**

**M11 Contract Implementation Phase: COMPLETE with T001–T005 🎉**  
## M11-GUI-MODEL-CONTRACT-T006：Mock-Real Boundary Tests — ✅ IMPLEMENTED (2026-07-11)

98 integration tests. 5-contract chain verified. Fixture→adapter→guard→provider path locked. 16 real providers, 6 real runtimes, 7 real sources → all blocked. Input/audit sensitive boundaries blocked. No pywinauto/torch/transformers/safetensors imports. **2219 passed, 4 skipped.**

**M11 Contract Implementation Phase: COMPLETE with T001–T006 🎉**  
## M11-CONTRACT-CLOSEOUT：Safety Contract Phase Closeout — ✅ COMPLETE (2026-07-11)

See `docs/M11_REAL_MODEL_SAFETY_CONTRACT_CLOSEOUT.md`. 5 contracts + 447 tests. 2219 passed, 4 skipped. No real model, no inference, no audit writer. 21 non-negotiable invariants.

**M11 Real Model Contract Phase: COMPLETE 🎉**  
## M11-GUI-MODEL-CONTRACT-STABILIZE-T001：Schema Consistency Review — ✅ COMPLETE (2026-07-11)

See `docs/M11_CONTRACT_SCHEMA_CONSISTENCY_REVIEW.md`. 5 contracts reviewed, 4 findings (all intentional), 56 consistency tests. No permission leaks. All contracts side-effect free. **2275 passed, 4 skipped.**

## M11-GUI-MODEL-CONTRACT-STABILIZE-T002：Error Code Taxonomy Audit — ✅ COMPLETE (2026-07-11)

See `docs/M11_CONTRACT_ERROR_CODE_TAXONOMY_AUDIT.md`. 84 codes across 5 contracts. 13 categories mapped. 6 cross-contract equivalence groups. 4-tier severity classification. 53 taxonomy tests. **2328 passed, 4 skipped.**

## M11-GUI-MODEL-CONTRACT-STABILIZE-T003：Test Baseline Lock — ✅ COMPLETE (2026-07-11)

See `docs/M11_CONTRACT_TEST_BASELINE_LOCK.md`. 2328 passed, 4 skipped. 30 invariants. 4 regression command sets. 4-tier severity classification. Expected-change policy. Future implementation gate defined.

**M11 Contract Stabilization Phase: COMPLETE 🎉**  
## M11-GUI-MODEL-RELEASE-CHECKPOINT：Release Checkpoint — ✅ COMPLETE (2026-07-11)

See `docs/M11_FIXTURE_ONLY_GUI_MODEL_RELEASE_CHECKPOINT.md`. 2328 passed, 4 skipped. 24 invariants. 12 exit criteria for future real model phase. Fixture-only path frozen as release baseline.

**M11: COMPLETE 🎉 (Design → Contract → Stabilization → Release Checkpoint)**  
**Next: M12-GUI-MODEL-IMPL-T001 (implementation threat review) — awaiting user decision.**
