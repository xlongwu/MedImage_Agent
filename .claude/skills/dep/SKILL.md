---
name: dep
description: Use after SPEC stage completes (FEATURE_READY state). Orchestrates codebase exploration through worker dispatch, skeptic-revise loops, and plan consolidation.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, AskUserQuestion, TodoWrite, Skill, mcp__plugin_serena_serena__*
---

# DARWIN Stage 2: DEP + Skeptic-Revise + Consolidation

## Runtime Context

**Active Run:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"phase": "NO_RUN"}'`

---

You are executing the DEP stage of the DARWIN evolutionary coding system.

## Core Principle: Orchestrate, Don't Implement

**You NEVER write implementation code.** Your job is to:
1. Recommend mode (single-loop vs population)
2. Scaffold the run directory
3. Dispatch workers for D-E-P phases
4. Run skeptic-revise loops until SOUND
5. Consolidate into golden spec

| Phase | Tool | Who Does Work |
|-------|------|---------------|
| D-E-P | Task (darwin-worker) | Worker agent |
| Skeptic | Task (darwin-skeptic) | Skeptic agent |
| Revise | Task (darwin-revise) | Revise agent |
| Consolidate | Task (darwin-consolidator) | Consolidator agent |

If you find yourself reading source files to make edits, **STOP**.

---

## Phase 0: State Verification (CRITICAL)

Use the **Active Run** output above to verify SPEC stage completed.

| State | Action |
|-------|--------|
| `FEATURE_READY` | Proceed to Mode Recommendation |
| `NO_RUN` | Error - "SPEC stage required. Run /darwin first." |
| `DEP_COMPLETE` | Error - "DEP already complete. Proceed to executor." |
| Other | Error - "Unexpected state: {state}. Check latest-run.json." |

**DO NOT proceed without valid state.**

---

## Mode Recommendation (MANDATORY USER GATE)

Use Serena for scope detection:
```
mcp__plugin_serena_serena__find_symbol(symbol="...")
mcp__plugin_serena_serena__search_for_pattern(pattern="...")
```

| Indicator | Single-Loop | Population |
|-----------|-------------|------------|
| Files affected | 1-5 | 6+ |
| New components | 0-2 | 3+ |
| Cross-cutting | No | Yes |

**Present mode options via AskUserQuestion.**

**DO NOT proceed to Run Scaffolding without user confirmation.**

**Details**: `reference/scaffolding.md`

---

## Run Scaffolding

1. Generate run ID from `docs/darwin/_meta/run-seq.json`
2. Create directory structure:
   ```
   docs/darwin/runs/{run_id}/
   ├── _meta/
   │   ├── run.json
   │   ├── principles.md
   │   ├── workers.yaml (population mode)
   │   └── state.yaml (population mode)
   ├── workers/
   │   └── main/ (or A/, B/, C/, D/)
   ├── consolidated/
   └── execute/
   ```
3. Update `docs/darwin/_meta/latest-run.json`

**Details**: `reference/scaffolding.md`

---

## Pre-Dispatch 3P Agents (Optional)

Evaluate if `feature-dev:code-architect` or `feature-dev:code-explorer` should run first.

**Details**: `reference/dispatch.md` and `reference/pre-dispatch-agents.md`

---

## Diversity Configuration (Population Mode Only)

Generate `workers.yaml` with diverse:
- Keywords (different search terms)
- Entry points (different starting files)
- Lenses (different perspectives)

Present for user review via AskUserQuestion.

**Details**: `reference/dispatch.md` and `reference/diversity-config.md`
**Example**: `examples/workers-yaml.md`

---

## Worker Dispatch

**Single-loop**: Dispatch darwin-worker with ID="main".
**Population**: Dispatch all workers in parallel (single message, multiple Task calls).

```
Task(
  subagent_type="Darwin:darwin-worker",
  prompt="...",  // See templates/worker-dispatch.md
  run_in_background=true  // Population mode
)
```

**Output files** (MUST use exact names):
- `workers/{id}/discover.md`
- `workers/{id}/explore.md`
- `workers/{id}/plan.md`

**Details**: `reference/dispatch.md` and `templates/worker-dispatch.md`

---

## Skeptic-Revise Loops (FRESH CONTEXT REQUIRED)

### Context Hygiene Rule

**Orchestrator MUST NOT read file contents.** Only parse verdict blocks.
Agents read files themselves using Serena tools.

### Single-Loop Mode

1. Dispatch darwin-skeptic (background)
2. Parse verdict from YAML block only
3. If UNSOUND, dispatch darwin-revise
4. Loop until SOUND
5. Copy to plan-final.md and consolidated/spec.md

### Population Mode

1. Per-worker skeptic-revise loops (parallel)
2. Track state in state.yaml
3. When all workers SOUND, dispatch consolidator
4. Consolidator merges into consolidated/spec.md

**Details**: `reference/skeptic-revise.md` and `reference/context-requirements.md`

---

## Context Reset Gate (MANDATORY USER GATE)

Before proceeding to executor, offer context reset:

```
AskUserQuestion:
  question: "DEP phase complete. Ready for execution. How would you like to proceed?"
  options:
    - "/compact - Compress context (recommended)"
    - "/clear - Fresh context for execution"
    - "Continue in current session"
```

This prevents context rot before execution.

**Both modes require Consolidator Review Gate before proceeding.**

**Details**: `reference/skeptic-revise.md` and `templates/consolidator-review-gate.md`

---

## Output

| Artifact | Path |
|----------|------|
| Worker plans | `{run_dir}/workers/{id}/plan.md` |
| Final plans | `{run_dir}/workers/{id}/plan-final.md` |
| Golden spec | `{run_dir}/consolidated/spec.md` |

---

## Handoff

When golden spec is ready and user has chosen context strategy:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/update-run-state.sh DEP_COMPLETE spec_path={run_dir}/consolidated/spec.md
```

The darwin dispatcher will invoke `Darwin:executor` for the next stage.

---

## Error Handling

- If worker fails, allow retry with same worker ID
- If skeptic-revise exceeds 5 iterations, escalate to user
- If consolidator conflicts unresolvable, present to user
- Never proceed to executor with unresolved USER DECISION items
