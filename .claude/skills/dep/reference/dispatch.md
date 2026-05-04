# Phases 5-7: Pre-Dispatch, Diversity, Worker Dispatch

This reference covers 3P agent evaluation and worker dispatch protocols.

---

## Phase 5: Pre-Dispatch 3P Agents (Optional)

**See also**: `reference/pre-dispatch-agents.md` for detailed evaluation criteria.

Before dispatching DARWIN workers, evaluate if 3rd-party agents should run first:

| Condition | Agent to Dispatch |
|-----------|-------------------|
| Complex codebase (10+ files) | `feature-dev:code-architect` |
| Unknown patterns | `feature-dev:code-explorer` |
| UI feature | Embed frontend-design principles |

Feed results into worker dispatch prompts as additional context.

---

## Phase 6: Diversity Configuration (Population Mode Only)

**See also**: `reference/diversity-config.md` for configuration details.

If mode is `population`:

1. **Analyze feature** for diversity dimensions:
   - Keywords: Different terminology for the same concept
   - Entry points: Different starting points in codebase
   - Lenses: data_flow, control_flow, state_changes, error_paths

2. **Recommend worker count** (3-6 based on complexity)

3. **Generate `workers.yaml`** (see `examples/workers-yaml.md`)

4. **Present for user review** via AskUserQuestion

---

## Phase 7: Worker Dispatch

After scaffolding complete:

### Single-Loop Mode

Dispatch darwin-worker agent with ID="main".

**See**: `templates/worker-dispatch.md` for the full prompt template.

Core parameters:
- Worker ID: `main`
- Keywords: derived from feature request
- Entry Point: detected from codebase
- Lens: `data_flow` (default)
- Run Directory: `docs/darwin/runs/{RUN_ID}`
- Project Path: `{project_path}`

**Output files** (MUST use exact names):
- `workers/main/discover.md` ← NOT "discovery.md"
- `workers/main/explore.md` ← NOT "exploration.md"
- `workers/main/plan.md`

Wait for worker completion, then proceed to Phase 8 (Skeptic Dispatch).

### Population Mode

```markdown
## Run Scaffolded: {RUN_ID}

Worker configuration saved to: docs/darwin/runs/{RUN_ID}/_meta/workers.yaml

Proceeding to dispatch workers in parallel...
```

**See**: `templates/worker-dispatch.md` for worker dispatch protocol.

**CRITICAL**: Dispatch ALL workers in a single message with multiple Task calls for parallel execution.

Each worker receives:
- Unique worker ID (A, B, C, ...)
- Different keywords from diversity config
- Different entry point
- Different lens

Wait for all workers to complete, then proceed to Phase 8.
