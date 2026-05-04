---
name: darwin
description: Start evolutionary coding workflow. Dispatches to stage-skills based on run state.
argument-hint: Feature description (e.g., "Add dark mode toggle")
allowed-tools: Read, Write, Bash, Skill, AskUserQuestion, TodoWrite, mcp__plugin_serena_serena__activate_project
---

# DARWIN Dispatcher

You are the main entry point for the DARWIN evolutionary coding system.

## Usage

```
/darwin "Add dark mode toggle"
/darwin "Implement user authentication with JWT"
/darwin "Refactor database layer to support multiple backends"
```

## What DARWIN Does

DARWIN is an evolutionary approach to feature development that:

1. **SPEC** - Formalizes requirements, catches contradictions early, surfaces user intent
2. **DEP** - Discovers codebase, Explores dependencies, Plans implementation
3. **EXECUTOR** - Builds ledger, executes with TDD discipline
4. **VERIFY** - Adversarial testing against specification

---

## Step 0: Activate Serena (REQUIRED)

Before detecting state, activate Serena for this session:

```
mcp__plugin_serena_serena__activate_project(project="{current_project}")
```

---

## State Detection

Read the current run state:

```bash
cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"phase": "NO_RUN"}'
```

Extract the phase value for state machine routing:

```bash
jq -r '.phase // "NO_RUN"'
```

---

## State Machine

| State | Action |
|-------|--------|
| **NO_RUN** | Invoke `Darwin:spec` with feature request |
| **FEATURE_READY** | Invoke `Darwin:dep` |
| **DEP_COMPLETE** | Offer /compact, then invoke `Darwin:executor` |
| **EXECUTE_COMPLETE** | Invoke `Darwin:verify` |
| **COMPLETE (VERIFIED)** | Success! Output summary. |
| **COMPLETE (FIXABLE)** | Output report + fixes. Recommend new session. |
| **COMPLETE (BLOCKED)** | Output blockers. Escalate to user. |
| **COMPLETE (RFI)** | Output questions. User clarifies, starts new session. |

---

## Stage Invocation

Use the Skill tool to invoke the appropriate stage:

### New Run (NO_RUN)
```
Skill(skill="Darwin:spec")
```
Pass the feature request from $ARGUMENTS.

### After Spec (FEATURE_READY)
```
Skill(skill="Darwin:dep")
```

### After DEP (DEP_COMPLETE)
First, offer context reset:
```
AskUserQuestion:
  question: "DEP complete. Recommend context reset before execution."
  options:
    - "/compact (recommended)"
    - "/clear"
    - "Continue"
```

Then:
```
Skill(skill="Darwin:executor")
```

### After Execute (EXECUTE_COMPLETE)
```
Skill(skill="Darwin:verify")
```

---

## Feature Request

**Feature**: $ARGUMENTS

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `/darwin "feature"` | Full workflow |
| `/darwin-discover` | Just discover phase |
| `/darwin-explore` | Just explore phase |
| `/darwin-plan` | Just plan phase |
| `/darwin-skeptic` | Audit current plan |
| `/darwin-worker` | Run D-E-P in sequence |

---

## Key Principles

1. **Zero Hallucination**: Every claim needs `file:line` anchor
2. **Hazard Tracking**: Every H-ID must have mitigation
3. **Code is King**: Revise agent verifies skeptic claims against actual code
4. **TDD Discipline**: No production code without failing test first
5. **Evidence Before Claims**: Verify, then assert

---

## Run Directory

All artifacts are saved to:
```
docs/darwin/runs/<run-id>/
├── _meta/
│   ├── run.json
│   ├── feature-request.md
│   ├── workers.yaml (population mode)
│   └── state.yaml (population mode)
├── workers/
│   └── main/ (or A/, B/, C/, D/)
├── consolidated/
│   └── spec.md
├── execute/
│   └── ledger.md
└── verify/
    └── report.md
```

---

## Proceed

Now detect state and invoke the appropriate stage skill.
