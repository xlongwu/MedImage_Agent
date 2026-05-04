# Per-Worker State Machine (Population Mode)

Each worker has its own independent Skeptic-Revise loop. The orchestrator tracks state for EACH worker.

---

## State Flow Diagram

```
PHASE 1: Parallel D→E→P (All workers start together)
├── Worker A (model=opus) → workers/A/plan.md
├── Worker B (model=opus) → workers/B/plan.md
└── Worker C (model=sonnet) → workers/C/plan.md
    [Wait for ALL workers to complete D→E→P]

PHASE 2: Per-Worker Skeptic-Revise Loops (Complete Independently)
Each worker loops independently until SOUND:
  Skeptic → UNSOUND? → Revise → Skeptic → ... → SOUND → DONE

[Wait for ALL worker loops to complete]

PHASE 3: Consolidator (if population mode)
└── Reads all workers/*/plan-final.md → consolidated/spec.md → User decisions

PHASE 4: Execute
└── Darwin:execute reads consolidated/spec.md, writes execute/ledger.md
```

---

## State Tracking File

Write state to `docs/darwin/runs/{RUN_ID}/_meta/state.yaml`:

```yaml
# State tracking for per-worker loops
workers:
  A:
    status: "done"  # discovering | exploring | planning | skeptic | revise | done
    iteration: 2
    verdict: "SOUND"
    current_plan: "workers/A/plan-r2.md"
    # When done, copy to workers/A/plan-final.md
  B:
    status: "revise"
    iteration: 1
    verdict: "UNSOUND"
    blocking_issues: ["SK-01", "SK-03"]
    current_plan: "workers/B/plan-r1.md"
  C:
    status: "done"
    iteration: 0
    verdict: "SOUND"
    current_plan: "workers/C/plan.md"
    # When done, copy to workers/C/plan-final.md
```

---

## Worker Status Values

| Status | Description |
|--------|-------------|
| `discovering` | Running Darwin:discover phase |
| `exploring` | Running Darwin:explore phase |
| `planning` | Running Darwin:plan phase |
| `skeptic` | Waiting for skeptic audit |
| `revise` | Revise agent working on defense |
| `done` | Reached SOUND verdict, plan-final.md created |

---

## Orchestrator Loop Logic

The orchestrator manages worker state until all workers reach SOUND verdict:

**Loop Protocol**:

1. For each worker needing skeptic audit:
   - Use the Task tool to dispatch `darwin-skeptic` agent with `model: haiku`
   - Read the critique output, update worker state
   - If verdict is SOUND → mark worker as done
   - If UNSOUND → mark worker as needs_revise

2. For each worker needing revision:
   - Use the Task tool to dispatch `darwin-revise` agent with `model: sonnet`
   - Increment worker iteration counter
   - Mark worker as needs_skeptic for next round

3. Continue until all workers reach SOUND verdict

4. When all workers done → dispatch consolidator

---

## State Update Protocol

After each subagent dispatch:

```yaml
# Update state.yaml
workers:
  {WORKER_ID}:
    status: {new_status}
    iteration: {current_iteration}
    verdict: {SOUND | UNSOUND | null}
    current_plan: "workers/{WORKER_ID}/plan{-r{N}}.md"
    blocking_issues: [{SK-### list if UNSOUND}]
```

When worker reaches SOUND:
```bash
# Copy to final
cp workers/{WORKER_ID}/{current_plan} workers/{WORKER_ID}/plan-final.md
```
