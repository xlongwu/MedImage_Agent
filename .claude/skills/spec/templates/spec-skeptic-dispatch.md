# Spec Skeptic Dispatch Template

This template dispatches `darwin-spec-skeptic` to audit feature-request.md BEFORE worker dispatch.

---

## When to Use

After Phase 2 (Spec Formalization) creates `feature-request.md`.

---

## Prerequisites

**Verify files exist** (do NOT read content into orchestrator context):

```
Glob: docs/darwin/runs/{RUN_ID}/_meta/feature-request.md
```

If feature-request.md doesn't exist, Phase 2 was not completed correctly.

---

## Task Tool Parameters

| Parameter | Value |
|-----------|-------|
| subagent_type | `Darwin:darwin-spec-skeptic` |
| run_in_background | `true` |
| description | `Spec audit for {RUN_ID}` |

---

## Prompt Template

```
You are a spec skeptic. You audit feature specifications for contradictions BEFORE workers start.

## Documents to Audit (Read these yourself)
- Spec: docs/darwin/runs/{RUN_ID}/_meta/feature-request.md
- Impossibility Patterns: skills/spec/reference/impossibility-patterns.md
- Constraint Types: skills/spec/reference/constraint-types.md

Use `mcp__plugin_serena_serena__read_file` to read these documents.

## Your Task
1. Extract all C-### constraints from feature-request.md
2. Check for REQUIREMENT vs LIMITATION conflicts using impossibility-patterns.md
3. Search codebase for feasibility evidence
4. Flag any ambiguities (AMB-###)
5. Output audit report with verdict
6. If BLOCKED: Generate question manifest for user resolution

## Output Files
1. docs/darwin/runs/{RUN_ID}/_meta/spec-audit.md (full report)
2. If BLOCKED: docs/darwin/runs/{RUN_ID}/_meta/checkpoint-spec-skeptic.json (gate file)
3. If BLOCKED: docs/darwin/runs/{RUN_ID}/_meta/spec-questions.json (questions for user)

## CRITICAL: Question Manifest Format

When BLOCKED, you MUST write spec-questions.json so the orchestrator can present
questions to the user WITHOUT reading your full audit report.

Format:
{
  "status": "BLOCKED",
  "questions": [
    {
      "issue_id": "SPEC-01",
      "question": "Contradiction: Zero data loss (C-01) conflicts with in-memory storage (C-03)",
      "header": "Persistence",
      "options": [
        {"label": "Add persistence layer", "description": "Store to disk/database, satisfies C-01"},
        {"label": "Accept data loss", "description": "Relax C-01, keep in-memory architecture"},
        {"label": "Use hybrid approach", "description": "Describe alternative solution"}
      ]
    },
    {
      "issue_id": "AMB-01",
      "question": "What latency is acceptable for 'fast' responses?",
      "header": "Performance",
      "options": [
        {"label": "< 100ms", "description": "Sub-100ms p99 latency"},
        {"label": "< 500ms", "description": "Half-second acceptable"},
        {"label": "Custom", "description": "Specify target latency"}
      ]
    }
  ]
}

Each question MUST be self-contained - user can answer without reading spec-audit.md.
```

---

## Orchestrator Question Handling

When checkpoint exists, read spec-questions.json and present to user:

```python
# Pseudo-code for orchestrator
questions_json = read("spec-questions.json")
for q in questions_json["questions"]:
    AskUserQuestion(
        questions=[{
            "question": q["question"],
            "header": q["header"],
            "multiSelect": False,
            "options": [
                {"label": opt["label"], "description": opt["description"]}
                for opt in q["options"]
            ]
        }]
    )
```

### Handling User Responses

After user answers:
1. **Update feature-request.md** with user's decision
2. **Delete checkpoint file** to unblock
3. **Delete spec-questions.json** (consumed)
4. **Proceed to Handoff (FEATURE_READY)**

If user chooses "Custom" or "Other": Ask follow-up for specifics.

---

## Context Management

| File | Orchestrator Reads? | Purpose |
|------|---------------------|---------|
| spec-audit.md | NO | Full report for user reference |
| checkpoint-spec-skeptic.json | EXISTS check only | Gate detection |
| spec-questions.json | YES (small) | Question content for AskUserQuestion |

This keeps orchestrator context light while enabling intelligent user interaction.

---

## Example Flow

```
1. Phase 2 completes → feature-request.md exists
2. Orchestrator dispatches darwin-spec-skeptic (background)
3. Spec-skeptic finds SPEC-01 contradiction
4. Spec-skeptic writes:
   - spec-audit.md (full report)
   - checkpoint-spec-skeptic.json (gate)
   - spec-questions.json (questions)
5. Orchestrator sees checkpoint, reads spec-questions.json
6. Orchestrator calls AskUserQuestion with SPEC-01 options
7. User chooses "Add persistence layer"
8. Orchestrator updates feature-request.md with decision
9. Orchestrator deletes checkpoint + questions files
10. Orchestrator proceeds to Handoff (FEATURE_READY)
```
