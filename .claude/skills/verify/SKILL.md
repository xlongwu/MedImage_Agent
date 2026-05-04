---
name: verify
description: DARWIN Stage 4 - Adversarial Verification. Dispatches darwin-verify agent to test implementation against spec. No feedback loop - ends with verdict.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, AskUserQuestion, TodoWrite, mcp__plugin_serena_serena__*, mcp__plugin_context7_context7__*
---

# DARWIN Stage 4: Verification

## Runtime Context

**Active Run:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"status": "No active run"}'`

**Feature Request Path:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null | grep -o '"feature_request_path"[^,}]*' | cut -d'"' -f4 || echo "No feature request path"`

**Spec Path:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null | grep -o '"spec_path"[^,}]*' | cut -d'"' -f4 || echo "No spec path"`

---

You are executing the VERIFY stage of the DARWIN evolutionary coding system.

## Core Principle: Adversarial Testing

The darwin-verify agent generates tests from the specification BEFORE reading implementation code. This prevents implementation bias.

| Execute Verification | darwin-verify |
|---------------------|---------------|
| Existence checking | Behavioral verification |
| Saw implementation | Spec-blind test generation |
| Per-task commands | DoD + Hazard + Edge + Integration |

---

## Dispatch Verification

**See:** `templates/verify-dispatch.md` (AUTHORITATIVE) for dispatch format.

```
Task(
  subagent_type="Darwin:darwin-verify",
  prompt="..."  // Build from templates/verify-dispatch.md
)
```

### Test Categories

darwin-verify generates tests by category:

| Category | Description | Count |
|----------|-------------|-------|
| **SC** | Success criteria from feature-request.md | Per SC-### |
| **Constraint** | Constraint validation | Per C-### |
| **DoD** | 1+ test per task Definition of Done | Per task |
| **Hazard** | 1+ attack test per H-ID mitigation | Per hazard |
| **Edge** | 3-5 scenarios per component | Per component |
| **Integration** | E2E smoke test | 1 |
| **Regression** | Existing test suite | All |

### Verdict Handling

darwin-verify outputs one of:

| Verdict | Condition | Action |
|---------|-----------|--------|
| **VERIFIED** | All tests pass | Run complete. Success! |
| **FIXABLE** | 1-3 failures, clear fixes, no regression | Output report + gaps. Recommend new session. |
| **BLOCKED** | >3 failures OR regression OR unclear | Output report + gaps. Escalate to user. |
| **RFI** | Spec ambiguity found | Output questions. User clarifies. |

**See:** `templates/gaps-format.md` (AUTHORITATIVE) for gap report structure.

---

## Output

| Artifact | Path |
|----------|------|
| Verify Report | `{run_dir}/verify/report.md` |
| Gaps (if FIXABLE/BLOCKED) | `{run_dir}/verify/gaps.md` |
| Test Files | `src/__tests__/verify/{run_id}/` |

---

## Handoff (Terminal Stage)

This is the final stage. No feedback loop.

### VERIFIED

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/verify/scripts/update-verdict.sh VERIFIED
```

Output: "Run complete. All verification tests passed."

### FIXABLE

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/verify/scripts/update-verdict.sh FIXABLE "{run_dir}/verify/gaps.md"
```

Output: Report with specific fixes. Recommend: "Start a new `/darwin` session with the gaps as input."

### BLOCKED

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/verify/scripts/update-verdict.sh BLOCKED "{run_dir}/verify/gaps.md"
```

Output: Report with blockers. Escalate to user for resolution.

### RFI

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/verify/scripts/update-verdict.sh RFI
```

Output: Questions for user. Recommend: "Clarify requirements and start a new `/darwin` session."

---

## Design Decision: No Feedback Loop

Each `/darwin` session is self-contained. We explicitly do NOT loop back to earlier stages because:

1. **Context accumulation** - Looping risks hitting context limits
2. **Complex state tracking** - Avoid unbounded execution
3. **Clean sessions** - Each run is atomic and reviewable

Gaps become input to a **new `/darwin` session**.

**Note:** The completeness audit (Phase 4.5 in darwin-verify) IS allowed to loop internally within the verification phase. This is different from stage-to-stage feedback loops.