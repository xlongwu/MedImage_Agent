# Golden Spec Gate Template

This template handles final assumption confirmation before ledger building.

---

## When to Use

After Phase 9 (Context Reset Gate), BEFORE Phase 10 (Ledger Building).

Only triggers if unconfirmed USER DECISION assumptions exist in spec.md.

---

## Prerequisites

**Check for USER DECISION assumptions**:

```
Grep: "USER DECISION" {run_dir}/consolidated/spec.md
OR
Grep: "USER DECISION" {run_dir}/workers/main/plan-final.md (single-loop)
```

If no matches → Skip this gate, proceed to Phase 10 (Ledger Building).

---

## Protocol

### Step 1: Extract Unconfirmed Assumptions

From spec.md or plan-final.md, find all assumptions marked USER DECISION:

```markdown
| A-ID | Assumption | Classification | Evidence |
|------|------------|----------------|----------|
| A-01 | WebSocket over polling | USER DECISION | None |
| A-04 | Dark mode default off | USER DECISION | None |
```

### Step 2: Build Question Set

For EACH USER DECISION assumption, prepare AskUserQuestion:

```
AskUserQuestion(
  questions=[
    {
      "question": "A-01: Should we use WebSocket or HTTP polling for real-time updates?",
      "header": "Transport",
      "multiSelect": false,
      "options": [
        {"label": "WebSocket (Recommended)", "description": "Bidirectional, lower latency, slightly more complex"},
        {"label": "HTTP Polling", "description": "Simpler, more firewall-friendly, higher latency"},
        {"label": "Long Polling", "description": "Middle ground, moderate complexity"}
      ]
    },
    {
      "question": "A-04: What should the default theme be?",
      "header": "UI Default",
      "multiSelect": false,
      "options": [
        {"label": "Light mode", "description": "Traditional default, good for accessibility"},
        {"label": "Dark mode", "description": "Modern preference, easier on eyes"},
        {"label": "System preference", "description": "Follow OS setting"}
      ]
    }
  ]
)
```

**CRITICAL**: Batch related questions (max 4 per call). Don't overwhelm user.

### Step 3: Record Decisions

After user responds, update spec.md:

**Before:**
```markdown
| A-01 | WebSocket over polling | USER DECISION | None |
```

**After:**
```markdown
| A-01 | WebSocket transport | USER CONFIRMED | Gate confirmation 2026-01-25 |
```

### Step 4: Update Resolution Log

Add to spec.md Resolution Log:

```markdown
### Gate Confirmations

| A-ID | Question | User Choice | Timestamp |
|------|----------|-------------|-----------|
| A-01 | Transport type | WebSocket | 2026-01-25T14:30:00Z |
| A-04 | Default theme | System preference | 2026-01-25T14:30:15Z |
```

---

## Skip Conditions

Skip this gate if:

1. **No USER DECISION assumptions** - All assumptions were verified or implicit
2. **Single-loop mode with no ambiguity** - Simple feature with clear approach
3. **User explicitly declined** - Previous prompt asked "confirm assumptions?" → user said "just proceed"

---

## Error Handling

If user chooses "Other" for any question:

1. Ask follow-up: "Please describe your preferred approach for {assumption}"
2. Record free-text response
3. Mark as USER CONFIRMED with custom value

---

## Context Efficiency

This gate runs AFTER context reset, so orchestrator has fresh context.

**DO NOT** re-read entire spec.md. Only:
1. Grep for USER DECISION lines
2. Parse the assumption table rows
3. Present questions
4. Update specific lines

---

## Integration with Orchestrator

This gate is checked at the START of Phase 10 (Ledger Building):

```markdown
## Phase 10: Ledger Building

**Pre-check**: Golden Spec Gate (Conditional)

1. Grep for "USER DECISION" in spec
2. If found: Present via AskUserQuestion (see templates/golden-spec-gate.md)
3. Update spec with confirmations
4. Continue with ledger building...
```

**Skip if**: No USER DECISION assumptions found
