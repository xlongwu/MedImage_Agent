# Phases 3-4: Mode Recommendation & Run Scaffolding

This reference covers mode selection and run directory setup.

---

## Phase 3: Mode Recommendation (MANDATORY USER GATE)

### Scope Detection

Use Serena to estimate scope:
```
- Find related symbols: `find_symbol <keywords>`
- Count files likely affected
- Check for cross-cutting concerns
```

### Complexity Heuristics

| Indicator | Single-Loop | Population |
|-----------|-------------|------------|
| Files affected | 1-5 | 6+ |
| New components | 0-2 | 3+ |
| Cross-cutting | No | Yes |
| Integration points | 1-2 | 3+ |
| Risk level | Low-Medium | High |

### Mode Selection

**CRITICAL**: You MUST use AskUserQuestion to get user confirmation before proceeding.

After scope detection, present analysis and get user choice:

```
AskUserQuestion(
  questions=[{
    "question": "Based on analysis (N files, M components, {cross-cutting status}), which mode?",
    "header": "Mode",
    "multiSelect": false,
    "options": [
      {
        "label": "Single-loop (Recommended)" if simple else "Single-loop",
        "description": "One worker, sequential D→E→P. Best for 1-5 files, 0-2 new components."
      },
      {
        "label": "Population (Recommended)" if complex else "Population with N workers",
        "description": "N parallel workers with diverse lenses. Best for 6+ files, 3+ components."
      },
      {
        "label": "Let me decide",
        "description": "Proceed with your recommendation without further input."
      }
    ]
  }]
)
```

**DO NOT proceed to Phase 4 without user confirmation.**

---

## Phase 4: Run Scaffolding

After user confirms mode:

### Step 1: Read Run Sequence

```
Read: docs/darwin/_meta/run-seq.json
Extract: next_run_number
```

### Step 2: Generate Run ID

```
RUN_ID = {padded_run_num}-{SLUG(feature)}
Example: 0001-add-dark-mode-toggle
```

### Step 3: Create Run Directory

```
docs/darwin/runs/{RUN_ID}/
├── _meta/
│   ├── run.json
│   ├── feature-request.md    # Created by SPEC stage
│   ├── principles.md
│   ├── workers.yaml      # Population mode config
│   └── state.yaml        # Per-worker state tracking
├── workers/
│   └── main/             # Single-loop (or A/, B/, ... for population)
├── consolidated/
│   └── spec.md
├── execute/
│   ├── ledger.md
│   └── learnings.md
└── verify/               # Verification outputs
    ├── report.md
    └── gaps.md           # If FIXABLE or BLOCKED
```

### Step 4: Write Run Metadata (`run.json`)

```json
{
  "run_id": "0001-add-dark-mode-toggle",
  "feature": "Add dark mode toggle",
  "mode": "single" | "population",
  "created_at": "ISO timestamp",
  "phase": "ORCHESTRATION",
  "code_root": "src/",
  "constraints": []
}
```

### Step 5: Write Operating Principles (`principles.md`)

```markdown
# Operating Principles for {RUN_ID}

## ETTC Mindset
Evolve specs and plans, not code.

## Zero Hallucination
Every claim requires `file:line` anchor.

## Evidence Grounding
Cite actual command output, not summaries.

## Hazard Tracking
Every H-ID must have mitigation.
```

### Step 6: Update Pointers

- Increment `run-seq.json`
- Update `latest-run.json`
