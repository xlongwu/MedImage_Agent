# Example workers.yaml

This is an example configuration for population mode workers.

---

## Full Example

```yaml
workers:
  A:
    id: "A"
    model: "opus"
    keywords:
      - "theme"
      - "dark"
      - "light"
      - "color"
      - "palette"
    entry_point: "src/theme/index.ts"
    lens: "data_flow"
    description: "Trace data flow from toggle to rendering"

  B:
    id: "B"
    model: "opus"
    keywords:
      - "appearance"
      - "settings"
      - "preference"
      - "persistence"
      - "localStorage"
      - "synchronization"
    entry_point: "src/hooks/useSettings.ts"
    lens: "error_handling"
    description: "Identify error conditions and edge cases"

  C:
    id: "C"
    model: "sonnet"
    keywords:
      - "stylesheet"
      - "css"
      - "variables"
      - "media query"
      - "prefers-color-scheme"
      - "system preference"
    entry_point: "src/styles/variables.css"
    lens: "performance"
    description: "Analyze rendering performance and CSS optimization"

diversity_config:
  total_workers: 3
  recommended_models:
    - model: "opus"
      count: 2
      reason: "Complex feature requires deep exploration"
    - model: "sonnet"
      count: 1
      reason: "Cost optimization for performance lens"
```

---

## Schema Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workers` | object | Yes | Map of worker ID to worker config |
| `workers.{ID}.id` | string | Yes | Worker identifier (A, B, C, etc.) |
| `workers.{ID}.model` | string | Yes | Model to use (opus, sonnet, haiku) |
| `workers.{ID}.keywords` | array | Yes | Search keywords for this worker |
| `workers.{ID}.entry_point` | string | Yes | Starting file for exploration |
| `workers.{ID}.lens` | string | Yes | Analysis lens (data_flow, error_handling, dependencies, performance) |
| `workers.{ID}.description` | string | No | Human-readable description of worker's focus |
| `diversity_config` | object | No | Metadata about worker distribution |

---

## Lens Options

| Lens | Purpose |
|------|---------|
| `data_flow` | Trace data transformations, state mutations |
| `error_handling` | Find error conditions, unhandled cases |
| `dependencies` | Map import graphs, identify coupling |
| `performance` | Find expensive operations, optimize renders |

---

## Model Selection Guidelines

| Model | When to Use | Cost |
|-------|-------------|------|
| `opus` | Complex reasoning, deep analysis | Highest |
| `sonnet` | Balanced capability/cost | Medium |
| `haiku` | Simple tasks, cost optimization | Lowest |

Recommended distribution:
- 2/3 opus for complex exploration
- 1/3 sonnet for cost-effective coverage
- haiku for very large populations (5+ workers)
