# Consolidator Dispatch Template

This template is used to dispatch the `darwin-consolidator` subagent to synthesize multiple worker plans into one golden specification.

---

## When to Use

Population mode - after all workers have reached SOUND verdict and have `plan-final.md` files.

---

## Task Tool Parameters

| Parameter | Value |
|-----------|-------|
| subagent_type | `darwin-consolidator` |
| model | `sonnet` |
| description | `Consolidate DARWIN worker plans` |

---

## Prompt Template

Paste all worker outputs into this template:

```
You are the consolidator. Synthesize multiple worker plans into one golden spec.


## Worker Outputs

### Worker A
[PASTE workers/A/plan-final.md]
[PASTE workers/A/explore.md hazard section]

### Worker B
[PASTE workers/B/plan-final.md]
[PASTE workers/B/explore.md hazard section]

[Continue for all workers...]

## Your Task
1. Build coverage matrix
2. Identify consensus items (HIGH confidence)
3. Resolve conflicts (verify with code or ask user)
4. Consolidate hazards
5. System Integrity Audit (Birth/Life/Death)
6. Synthesize implementation tasks
7. Generate golden spec.md

## SUPPLEMENTAL: Brainstorming for Conflicts
- For architectural conflicts, present 2-3 approaches with trade-offs
- Use AskUserQuestion for decisions
- Don't make architectural decisions without user input

## Output
Write to: docs/darwin/runs/{RUN_ID}/consolidated/spec.md
```

---

## After Dispatch

Proceed to **Consolidator Review Gate** (see `templates/consolidator-review-gate.md`).

The orchestrator MUST present decisions to user before proceeding to Execute.
