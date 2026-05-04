# Worker Dispatch Template

This template is used to dispatch `darwin-worker` subagents for population mode parallel exploration.

---

## When to Use

Population mode - after workers.yaml is confirmed by user.

---

## Prerequisites

1. **Read worker configuration**
   ```
   Read: docs/darwin/runs/{RUN_ID}/_meta/workers.yaml
   ```

---

## Parallel Dispatch (CRITICAL)

**All Task tool calls MUST go in ONE message for parallel execution.**

For each worker from workers.yaml, use the Task tool. Example for 3 workers:

**Worker A** - Task tool parameters:
- subagent_type: `darwin-worker` (or `general-purpose`)
- model: `opus`
- description: `DARWIN Worker A exploration`
- prompt: (see template below with Worker ID=A, Keywords=[theme, dark, light, color, palette], Entry Point=src/theme/index.ts, Lens=data_flow)

**Worker B** - Task tool parameters:
- subagent_type: `darwin-worker` (or `general-purpose`)
- model: `opus`
- description: `DARWIN Worker B exploration`
- prompt: (same template, different keywords/lens/entry_point per workers.yaml)

**Worker C** - Task tool parameters:
- subagent_type: `darwin-worker` (or `general-purpose`)
- model: `sonnet`
- description: `DARWIN Worker C exploration`
- prompt: (same template, different keywords/lens/entry_point per workers.yaml)

---

## Basic Worker Prompt Template

```
You are Population Worker {ID}. You have NOT seen other workers' findings.

## Your Parameters
Worker ID: {ID}
Keywords: {keywords}
Entry Point: {entry_point}
Lens: {lens}
Run Directory: docs/darwin/runs/{RUN_ID}

## Your Task
1. Discover - breadth-first exploration with your keywords
2. Explore - depth-first tracing with your lens
3. Plan - implementation spec

## Output Files (EXACT NAMES REQUIRED)
Write to docs/darwin/runs/{RUN_ID}/workers/{ID}/:
- discover.md   ← CORRECT (NOT "discovery.md")
- explore.md    ← CORRECT (NOT "exploration.md")
- plan.md
```

---

## Detailed Worker Dispatch Construction

### Step 1: Gather Run Metadata

```
Read: docs/darwin/runs/{RUN_ID}/_meta/run.json
Extract: project_path (from code_root or inferred from cwd)
Read: docs/darwin/runs/{RUN_ID}/_meta/workers.yaml
```

### Step 2: Determine Feature Type

| Condition | Check | If True |
|-----------|-------|---------|
| Complex feature | workers > 2 OR estimated_files > 5 | Add `supplemental_tracing` |
| UI feature | feature involves visual/interactive elements (e.g., ui, component, frontend, button, form, modal, dialog, toggle, theme, style, css) | Add `supplemental_aesthetic` |
| Always | - | Add `supplemental_verification` |

### Step 3: Construct Supplemental Principles

**For ALL dispatches (always include):**
```markdown
## SUPPLEMENTAL: Verification Discipline

From superpowers:verification-before-completion:
- Run the command. Read the output. THEN claim the result.
- NO completion claims without fresh verification evidence.
- If you didn't see the output, you can't claim it passed.
- Evidence before assertions, always.
```

**For complex features (is_complex=True), ADD:**
```markdown
## SUPPLEMENTAL: Deep Tracing Principles

From feature-dev:code-explorer:
- Follow call chains from entry to output
- Trace data transformations at each step
- Map abstraction layers (presentation → business logic → data)
- Document interfaces between components
- Prefer direct tool use over nested agents

From feature-dev:code-architect:
- Make decisive architectural choices (not multiple options)
- Provide complete implementation blueprint
- Include file paths, function names, concrete steps
- Design for the requirement, not hypothetical futures
```

**For UI features (is_ui_feature=True), ADD:**
```markdown
## SUPPLEMENTAL: Aesthetic Guidelines

From frontend-design principles:
- Typography: Choose distinctive fonts, not system defaults
- Color & Theme: Build cohesive palettes with intent
- Motion: Prefer CSS transitions, staggered reveals
- Spatial Composition: Use asymmetry, overlap, negative space
- Avoid: Generic AI aesthetics, centered everything, system fonts
- Every UI decision should have design rationale
```

### Step 4: Full Prompt Template

For each worker, use the Task tool with these parameters:

| Parameter | Value |
|-----------|-------|
| subagent_type | `darwin-worker` |
| model | From workers.yaml (opus/sonnet/haiku) |
| description | `DARWIN Worker {worker.id}` |

**Full prompt template**:

```
## Your Assignment
Worker ID: {worker.id}
Keywords: {worker.keywords}
Entry Point: {worker.entry_point}
Lens: {worker.lens}
Run Directory: docs/darwin/runs/{RUN_ID}
Project Path: {project_path}

## Your Task
Execute the full D→E→P methodology using your preloaded skills:
1. Darwin:discover - generate discover.md
2. Darwin:explore - generate explore.md
3. Darwin:plan - generate plan.md

## Output Files (EXACT NAMES REQUIRED)
Write to docs/darwin/runs/{RUN_ID}/workers/{worker.id}/:
- discover.md   ← CORRECT (NOT "discovery.md")
- explore.md    ← CORRECT (NOT "exploration.md")
- plan.md

{Include supplemental_verification - always}
{Include supplemental_tracing - if is_complex}
{Include supplemental_aesthetic - if is_ui_feature}

## Zero Hallucination
Every claim needs file:line anchor. Memory is HINTS, not TRUTH.
```

### Step 5: Parallel Dispatch

**CRITICAL**: Dispatch ALL workers in a SINGLE message for parallel execution.

For each worker in workers.yaml, include a Task tool call in your response:
- subagent_type: `darwin-worker`
- model: worker.model (from workers.yaml)
- description: `DARWIN Worker {worker.id}`
- prompt: Constructed from Step 4 template with worker's parameters

All Task calls must be in ONE response to enable parallel execution.

---

## After Worker Dispatch

1. **Wait for all workers to complete**

2. **Dispatch Skeptic for EACH worker's plan**

   Can also be parallel - use Task tool for each worker:
   - Task: description=`Skeptic audit Worker A`, prompt=[skeptic methodology + workers/A/plan.md]
   - Task: description=`Skeptic audit Worker B`, prompt=[skeptic methodology + workers/B/plan.md]
   - (continue for all workers...)
   - Output: workers/{ID}/critique-{N}.md

3. **Dispatch Revise for each critique (as needed)**

4. **Proceed to Consolidator** (see `templates/consolidator-dispatch.md`)
