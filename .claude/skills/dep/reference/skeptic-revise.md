# Phases 8-9: Skeptic-Revise Loops & Context Reset

This reference covers adversarial plan validation and context management.

---

## Phase 8: Skeptic-Revise Loops (CRITICAL - Fresh Context Required)

**IMPORTANT**: Skills share context. Subagents have fresh context.

For phases requiring isolation (Skeptic, Revise, Workers), you MUST dispatch custom subagents via the Task tool, NOT invoke skills.

**See**: `reference/context-requirements.md` for full context isolation rationale.

### Context Hygiene Protocol

**Orchestrator MUST NOT read file contents.** This prevents context bloat.

| Action | Allowed | Not Allowed |
|--------|---------|-------------|
| Verify file exists | `Glob`, `ls` | - |
| Check verdict | Parse YAML block only | Read full critique |
| Handoff context | File paths | File contents |

**Agents read files themselves** using Serena tools. They achieve full document awareness without bloating orchestrator context.

**Background execution**: Use `run_in_background=true` for Skeptic and Revise. Poll for output files or use TaskOutput to check completion.

---

### Single-Loop: Skeptic-Revise Loop

1. **Dispatch darwin-skeptic subagent** (run_in_background=true)
   **See**: `templates/skeptic-dispatch.md`

2. **Parse verdict** (YAML block at end of critique-{N}.md only)
   - If SOUND: proceed to step 4
   - If UNSOUND/PROVISIONAL: continue to step 3

3. **Dispatch darwin-revise subagent** (run_in_background=true)
   **See**: `templates/revise-dispatch.md`
   Then re-dispatch Skeptic on revised plan (loop back to step 1)

4. **When verdict is SOUND**:
   - Copy accepted plan to `workers/main/plan-final.md`
   - Copy to `consolidated/spec.md` for Execute phase

5. **Consolidator Review Gate (MANDATORY)**
   **See**: `templates/consolidator-review-gate.md`

---

### Population: Per-Worker Loops + Consolidation

**See**: `reference/state-machine.md` for state tracking format.

1. **Dispatch ALL workers in parallel** (single message, multiple Task calls)
   **See**: `templates/worker-dispatch.md`

2. **Per-worker Skeptic-Revise loops** (complete independently)
   - Each worker loops: Skeptic → UNSOUND? → Revise → Skeptic → ... → SOUND
   - Update `state.yaml` after each dispatch

3. **Wait for all workers to reach SOUND**

4. **Dispatch Consolidator**
   **See**: `templates/consolidator-dispatch.md`

5. **Consolidator Review Gate (MANDATORY)**
   **See**: `templates/consolidator-review-gate.md`

6. **After user approves**, proceed to Context Reset Gate

---

## Phase 9: Context Reset Gate

**MANDATORY**: After spec is approved (SOUND verdict or consolidation approval), offer context reset.

The orchestrator has accumulated significant context from D-E-P phases, Skeptic-Revise loops, and consolidation. Before execution, offer to reset for a cleaner implementation context.

```
AskUserQuestion(
  questions=[{
    "question": "Spec approved. Ready for execution. How would you like to manage context?",
    "header": "Context",
    "multiSelect": false,
    "options": [
      {
        "label": "Clear and continue (Recommended)",
        "description": "Full context reset. Start fresh for implementation. Use /clear."
      },
      {
        "label": "Compact and continue",
        "description": "Summarize context, keep key info. Use /compact."
      },
      {
        "label": "Continue without reset",
        "description": "Keep full context. Use if you need to reference earlier discussion."
      }
    ]
  }]
)
```

### Handling User Choice

- **If user chooses clear**: Output `/clear` instruction and stop. User will restart with `/darwin execute`.
- **If user chooses compact**: Output `/compact` and wait for compaction, then proceed to Phase 10.
- **If user chooses continue**: Proceed directly to Phase 10.
