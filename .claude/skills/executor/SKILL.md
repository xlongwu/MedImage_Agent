---
name: executor
description: DARWIN Stage 3 - Ledger Building + Execute. Transforms golden spec into ledger, invokes TDD execution with Ralph-style batch enforcement.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, AskUserQuestion, TodoWrite, Skill, mcp__plugin_serena_serena__*
---

# DARWIN Stage 3: Ledger + Execute

## Runtime Context

**Active Run:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"status": "No active run"}'`

---

You are executing the EXECUTOR stage of the DARWIN evolutionary coding system.

## Core Principle: Transform and Delegate

Your job is to:
1. Check for unconfirmed USER DECISION items
2. Invoke ledger-builder to transform spec → ledger
3. Invoke execute skill for TDD implementation
4. Wait for completion promise

**You NEVER write implementation code.** The Execute skill handles all implementation.

---

## Reference Index

| Reference | Read When |
|-----------|-----------|
| `templates/golden-spec-gate.md` | Phase 10 - checking USER DECISION items |

---

## Phase 10: Ledger Building

### Pre-Check: Golden Spec Gate

Before building ledger, check for unconfirmed USER DECISION assumptions:

```bash
grep "USER DECISION" {run_dir}/consolidated/spec.md
```

**If found**: Present via AskUserQuestion using `templates/golden-spec-gate.md`
**If not found**: Proceed directly to ledger building.

### Why Separate Ledger?

| Document | Purpose | Content |
|----------|---------|---------|
| **Spec** (`consolidated/spec.md`) | Complete blueprint | Context, rationale, hazards |
| **Ledger** (`execute/ledger.md`) | Detailed Execution queue | Checkboxes, verifications |

The spec is for PLANNING. The ledger is for EXECUTION.

### Invoke Ledger Builder

```
Skill(
  skill="Darwin:ledger-builder"
)
```

The ledger-builder skill will:
1. Read `{run_dir}/consolidated/spec.md`
2. Transform into execution ledger
3. Write `{run_dir}/execute/ledger.md`
4. Write `{run_dir}/execute/learnings.md`

### Verify Ledger

After ledger-builder completes:
- Check ledger.md has batches matching spec phases
- Check each task has verification command
- Check batch gates are present

---

## Phase 11: Execute (TDD + Ralph Loop)

### Invoke Execute

```
Skill(
  skill="Darwin:execute"
)
```

**CRITICAL**: Do NOT implement code yourself. The Execute skill handles all implementation.

### What Execute Does

The Execute skill will:
1. Load ledger.md and learnings.md
2. Process tasks batch by batch using TDD discipline
3. For each task: Write test → Run (fail) → Implement → Run (pass) → Check box
4. Stop hook enforces batch completion
5. Output `<promise>ALL_BATCHES_COMPLETE</promise>` when done

### Stop Hook Enforcement

The stop hook provides HARD enforcement:

| Condition | Hook Response |
|-----------|---------------|
| Tasks unchecked in batch | Block exit, continue loop |
| Tasks done, gate unchecked | Block, prompt gate verification |
| Batch complete, more remain | Block, prompt next batch |
| All batches, final gate unchecked | Block, prompt final verification |
| `<promise>ALL_BATCHES_COMPLETE</promise>` | Verify ledger, allow exit |
| `<promise>BLOCKED_ON_T{X}.{Y}</promise>` | Allow exit, escalate to user |

### Learnings Persistence

Each task iteration:
- Reads learnings file (patterns, failures)
- Optionally appends ONE learning
- Max 50 entries (oldest trimmed)

---

## Output

| Artifact | Path |
|----------|------|
| Ledger | `{run_dir}/execute/ledger.md` (all tasks checked) |
| Learnings | `{run_dir}/execute/learnings.md` |
| Implementation | Source files modified per ledger |

---

## Handoff

When Execute outputs `<promise>ALL_BATCHES_COMPLETE</promise>`:

1. **Update run state**:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/executor/scripts/update-run-state.sh EXECUTE_COMPLETE
```

2. The darwin dispatcher will then invoke `Darwin:verify` for Stage 4.

---

## If Blocked

When Execute outputs `<promise>BLOCKED_ON_T{X}.{Y}</promise>`:

1. Read learnings file for blocked task context
2. Present to user:
```
AskUserQuestion(
  questions=[{
    "question": "Task T{X}.{Y} is blocked. How would you like to proceed?",
    "header": "Blocked",
    "options": [
      {"label": "Clarify and retry", "description": "Provide clarification, then re-invoke execute"},
      {"label": "Skip task", "description": "Mark task as skipped, continue with remaining tasks"},
      {"label": "End run", "description": "Stop execution, escalate for manual resolution"}
    ]
  }]
)
```
3. Act on user response

---

## Error Handling

- If ledger-builder fails, check spec format
- Never proceed to verify with unchecked tasks
