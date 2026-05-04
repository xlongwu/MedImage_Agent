---
name: spec
description: DARWIN Stage 1 - Spec Formalization. Analyzes feature request, extracts constraints, checks for contradictions, generates feature-request.md, dispatches spec-skeptic for validation.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, AskUserQuestion, TodoWrite, Skill, mcp__plugin_serena_serena__*
---

# DARWIN Stage 1: Spec Formalization

## Runtime Context

**Active Run:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"phase": "NO_RUN"}'`

---

You are executing the SPEC stage of the DARWIN evolutionary coding system.

## Core Principle: Catch Contradictions Early

Your job is to:
1. Detect resume vs new run
2. Parse the feature request
3. Extract constraints and requirements
3.5. Flag implicit assumptions (A-###)
4. Check for logical impossibilities
5. Generate feature-request.md
6. Dispatch spec-skeptic for validation

**You do NOT scaffold directories or dispatch workers.** That is the DEP stage.

---

## Phase 0: Resume Detection

Use the **Active Run** output above to determine state.

| State | Action |
|-------|--------|
| No file OR phase = COMPLETE | Start new run (Phase 1) |
| Active run in SPEC phase | Resume spec work |

**Note**: The darwin dispatcher handles routing. If you're invoked, SPEC work is needed.

---

## Phase 1: Feature Analysis

Parse the feature request provided in the user's message or $ARGUMENTS.

### Intent Capture

Extract core intent (see `reference/intent-capture.md` for detailed guidance):
- **Problem Statement**: What pain point is being solved?
- **Target Users**: Who benefits?
- **Success Criteria**: How do we know it works?

### Constraint Extraction

Identify constraints using keyword indicators:

| Indicator | Keywords | Constraint Type |
|-----------|----------|-----------------|
| Explicit requirement | must, shall, need, require | REQUIREMENT |
| Stated limitation | cannot, limited, maximum | LIMITATION |
| System property | always, never, guarantee | INVARIANT |
| Preference | should, prefer, ideally | PREFERENCE |
| Vague quantifier | fast, good, proper, appropriate | Flag as ambiguity |

### Assumption Detection

Flag implicit assumptions that affect feasibility:
- Technology assumptions (web vs mobile, framework)
- Capability assumptions (existing systems, integrations)
- Scope assumptions (single user vs multi-tenant)

Mark as A-### with classification: NEEDS_VERIFICATION

---

## Phase 1.5: Design Preference Capture (When Applicable)

If the feature has design/UX implications:
1. Invoke `Skill(skill="frontend-design")` to load design guidance
2. Use loaded guidance to formulate design questions for user
3. Capture user preferences as D-### (Design Decision) entries

D-### entries become constraints for downstream agents.

---

## Phase 2: Spec Formalization

**References for this phase:**

| Reference | Used In |
|-----------|---------|
| `reference/impossibility-patterns.md` | Step 2 |
| `reference/constraint-types.md` | Step 1 |
| `templates/feature-request-template.md` | Step 3 |
| `templates/spec-skeptic-dispatch.md` | Step 6 |

### Step 1: Load Reference Materials

```
Read: reference/impossibility-patterns.md
Read: reference/constraint-types.md
```

### Step 2: Run Impossibility Check

For each constraint pair, check for conflicts using `reference/impossibility-patterns.md` **NOTE**: This list is **NOT** the **ONLY** conflicts you should check for.

**Common conflict patterns (examples, not exhaustive):**
- REQUIREMENT "zero data loss" + LIMITATION "in-memory only" → physical impossibility
- REQUIREMENT "sub-10ms response" + REQUIREMENT "full validation" → speed vs completeness
- INVARIANT "always available" + LIMITATION "single instance" → availability conflict

**Process:**
1. Read impossibility-patterns.md for pattern definitions
2. For each REQUIREMENT, check if any LIMITATION makes it impossible
3. For each INVARIANT, check if any constraint violates it
4. Flag conflicts as SPEC-### with severity (CRITICAL/HIGH/MEDIUM)

Think critically - patterns are examples, not exhaustive. Novel conflicts may exist.

### Step 3: Generate feature-request.md

Use `templates/feature-request-template.md` to generate:
```
{run_dir}/_meta/feature-request.md
```

Capture:
- Intent and scope
- All C-### constraints with types
- Any SPEC-### contradictions found
- Any AMB-### ambiguities flagged

Note: For new runs, use temporary path until DEP stage scaffolds directory.

### Severity Handling

| Severity | Action | Justification |
|----------|--------|---------------|
| CRITICAL | MUST resolve via AskUserQuestion | Fundamentally impossible |
| HIGH | SHOULD resolve via AskUserQuestion with recommendation | Significant architectural impact |
| MEDIUM | Note in feature-request.md | Trade-off acceptable with mitigation |

### Step 4: Resolve Contradictions

If CRITICAL contradictions found, use AskUserQuestion to resolve.

**Approach**: Think critically about the best solution. Options may include:
- User chooses one constraint over the other
- Constraints can be merged/reconciled
- One or both constraints are mistakes that should be removed
- A third approach satisfies both

Be helpful - guide the user toward the best outcome, not just surface the conflict.

### Step 5: Resolve Ambiguities

For each AMB-### ambiguity, use AskUserQuestion to clarify.

**Approach**: Ask specific, actionable questions. Avoid:
- Vague "what do you mean by X?"
- Multiple questions at once

Instead: "You said 'fast response'. What latency is acceptable? (e.g., <100ms, <500ms, <1s)"

### Step 6: Dispatch Spec-Skeptic (REQUIRED)

Dispatch background verification:
```
Task(
  subagent_type="Darwin:darwin-spec-skeptic",
  run_in_background=true,
  description="Spec audit for {RUN_ID}"
)
```

**See**: `templates/spec-skeptic-dispatch.md` for full prompt template.

### Step 7: Handle Spec-Skeptic Results

Check for checkpoint file:
```
Glob: {run_dir}/_meta/checkpoint-spec-skeptic.json
```

**If checkpoint exists (BLOCKED)**:
1. Read `{run_dir}/_meta/spec-questions.json`
2. Present questions to user via AskUserQuestion
3. Update feature-request.md with user decisions
4. Delete checkpoint and questions files
5. Re-dispatch spec-skeptic (return to Step 6)

**If no checkpoint (SOUND)**:
- Proceed to Step 8

### Step 8: Update Spec Status

- All issues resolved → status = "READY"
- Unresolved contradictions or ambiguities → status = "BLOCKED"

**DO NOT proceed to DEP until spec status is READY.**

---

## Output

| Artifact | Path |
|----------|------|
| Feature Request | `{run_dir}/_meta/feature-request.md` |
| Spec Status | `READY` or `BLOCKED` |

---

## Handoff

When spec status is READY:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/update-run-state.sh FEATURE_READY \
  spec_status=READY \
  feature_request_path={run_dir}/_meta/feature-request.md
```

**Note:** Only write feature_request_path when status is READY (not BLOCKED).

The darwin dispatcher will invoke `Darwin:dep` for the next stage.

---

## Error Handling

- If spec-skeptic returns BLOCKED, present questions via AskUserQuestion
- If user cannot resolve contradictions, mark run as BLOCKED
- Never proceed to DEP with unresolved contradictions
