# Pre-Dispatch 3P Agents

Before dispatching DARWIN workers, evaluate if 3rd-party agents should run first to provide architectural context.

---

## When to Dispatch

| Condition | Action | Agent to Dispatch |
|-----------|--------|-------------------|
| Complex existing codebase (10+ files) | Get architecture analysis | `feature-dev:code-architect` |
| Not sure where to start | Get deep exploration | `feature-dev:code-explorer` |
| UI/UX feature detected | Note for worker embedding | (embed frontend-design principles) |

---

## Dispatching feature-dev:code-architect

Use when complex existing codebase needs architecture mapping before workers explore.

```
Task(
  subagent_type="feature-dev:code-architect",
  model="sonnet",
  description="Analyze architecture for {feature}",
  prompt="Analyze the existing architecture relevant to {feature}.
         Map: entry points, data flow, abstraction layers, integration points.
         Return: Architecture blueprint with key files and patterns."
)
```

---

## Dispatching feature-dev:code-explorer

Use when unknown patterns or unfamiliar framework needs deep exploration.

```
Task(
  subagent_type="feature-dev:code-explorer",
  model="sonnet",
  description="Explore codebase for {feature}",
  prompt="Explore the codebase for patterns related to {feature}.
         Trace call chains, map dependencies, identify existing solutions.
         Return: Key files, patterns found, integration recommendations."
)
```

---

## Feeding Results to Workers

Pass pre-dispatch results into worker dispatch prompts as additional context:

```markdown
## Pre-Exploration Findings

The following architecture analysis was performed before your exploration:
{paste code-architect or code-explorer results}

Use these findings to inform your discovery and exploration.
```

---

## Decision Flow

```
Feature Request
    ↓
Scope Analysis (Phase 1)
    ↓
10+ files OR unfamiliar framework?
    ├── Yes → Dispatch code-architect/code-explorer
    │         ↓
    │         Feed results to workers
    │         ↓
    │         Worker Dispatch
    │
    └── No → Worker Dispatch directly
```
