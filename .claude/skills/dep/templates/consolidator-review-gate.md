# Consolidator Review Gate

**MANDATORY USER GATE** - Must present decisions to user before Execute.

After consolidator writes spec.md, orchestrator MUST present decisions to user.

---

## Step 1: Read spec.md and extract Resolution Log

```
Read: docs/darwin/runs/{RUN_ID}/consolidated/spec.md
Extract: "Resolution Log" section with all conflict resolutions
Extract: "Assumptions" section with decisions made
```

---

## Step 2: Present to user via AskUserQuestion

```
AskUserQuestion(
  questions=[{
    "question": "The consolidator resolved {N} conflicts. Review and approve?",
    "header": "Review",
    "multiSelect": false,
    "options": [
      {
        "label": "Approve all resolutions",
        "description": "Proceed with the consolidated spec as-is"
      },
      {
        "label": "Review conflicts individually",
        "description": "I want to review each conflict and make my own decisions"
      },
      {
        "label": "Reject and re-run consolidation",
        "description": "The resolutions don't look right, try again with different approach"
      }
    ]
  }]
)
```

---

## Step 3: If "Review conflicts individually"

For each unresolved or contested item in the Resolution Log:

```
AskUserQuestion(
  questions=[{
    "question": "Conflict: {topic}. Worker A: {approach_A}. Worker B: {approach_B}. Which approach?",
    "header": "{topic}",
    "multiSelect": false,
    "options": [
      {"label": "Worker A approach", "description": "{trade-offs_A}"},
      {"label": "Worker B approach", "description": "{trade-offs_B}"},
      {"label": "Hybrid approach", "description": "Combine elements from both"}
    ]
  }]
)
```

---

## Step 4: Update spec.md with user decisions

- Change "Method" column from "Analysis" to "User Decision"
- Record the user's chosen approach in the Resolution Log

---

## Step 5: Proceed to Execute

Only after user approves, invoke `Darwin:execute` skill.
