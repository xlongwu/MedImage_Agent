# Diversity Configuration (Population Mode)

Configuration for population mode worker diversity.

---

## When to Use

If mode is `population`, generate diverse worker configurations.

---

## Step 1: Analyze Feature for Diversity Dimensions

- **Keywords**: literal, synonyms, anti-patterns, framework-specific
- **Entry points**: main, types, tests, specific symbols
- **Lenses**: data_flow, error_handling, dependencies, performance

---

## Step 2: Recommend Worker Count

| Complexity | Workers | Model Distribution |
|------------|---------|-------------------|
| Medium | 3 | 2 Opus, 1 Sonnet |
| High | 4 | 2 Opus, 1 Sonnet, 1 Haiku |
| Very High | 5-6 | 2 Opus, 2 Sonnet, 1-2 Haiku |

---

## Step 3: Generate workers.yaml

Write to: `docs/darwin/runs/{RUN_ID}/_meta/workers.yaml`

See `examples/workers-yaml.md` for full example.

---

## Step 4: Present for User Review

Use AskUserQuestion to let user modify the configuration:

```
AskUserQuestion(
  questions=[{
    "question": "Review worker configuration. Proceed with {N} workers?",
    "header": "Workers",
    "multiSelect": false,
    "options": [
      {"label": "Approve configuration", "description": "Proceed with current workers.yaml"},
      {"label": "Modify workers", "description": "I want to adjust keywords, lenses, or count"},
      {"label": "Switch to single-loop", "description": "Use single worker instead"}
    ]
  }]
)
```

---

## Lens Definitions

| Lens | Focus Area | What to Look For |
|------|------------|------------------|
| `data_flow` | Trace data from source to sink | Transformations, mutations, state updates |
| `error_handling` | Find try/catch, error conditions | Unhandled cases, error propagation |
| `dependencies` | Map import graphs | Circular dependencies, coupling |
| `performance` | Find expensive operations | Render triggers, memory leaks, O(n²) |

---

## Keyword Diversity Strategy

Each worker should have distinct keyword sets does not have to limit to 3:

| Worker | Keyword Focus | Example |
|--------|---------------|---------|
| A | Core domain terms | `theme`, `dark`, `mode`, `settings` |
| B | Settings/persistence | `settings`, `localStorage`, `preference` |
| C | Framework/styling | `css`, `variables`, `prefers-color-scheme` |
