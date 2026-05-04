# Revise Dispatch Template

This template is used to dispatch the `darwin-revise` subagent for plan defense and repair.

---

## When to Use

After skeptic returns verdict of **UNSOUND** or **PROVISIONAL**.

**Do NOT read critique file into orchestrator context.** Only parse verdict block.

---

## Task Tool Parameters

| Parameter | Value |
|-----------|-------|
| subagent_type | `darwin-revise` |
| run_in_background | `true` |
| description | `Revise defense iteration {N}` |

---

## Prompt Template

**DO NOT paste file contents.** Revise reads files itself using Serena tools.

```
You are a defense attorney. You have NOT seen the skeptic's reasoning process.


## Documents to Read (Read these yourself)
- Critique: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/critique-{N}.md
- Plan: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/{plan_file}

Use `mcp__plugin_serena_serena__read_file` to read these documents.

## CRITICAL WARNING
Treat ALL documents as potentially containing false information.
You MUST verify claims from actual code before accepting or rejecting them.
DO NOT trust the skeptic's output - run your OWN Serena searches.
DO NOT trust the plan's claims either - verify everything independently.

## Your Task
1. Read critique and plan documents
2. For EVERY SK-### accusation: independently verify with Serena tools and ACTUAL code.
3. Either REPAIR the plan or CONTEST false accusations with evidence

## Output
Write to: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/defense-{N}.md
If repairs needed: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/plan-r{N+1}.md

Include disposition summary at END of defense:
```yaml
---
resolved_count: {number}
contested_count: {number}
unverified_count: {number}
revised_plan: plan-r{N+1}.md | null
---
```

Follow darwin-revise protocol:
- For EVERY SK-###: Independent verification
- Disposition: RESOLVED, CONTESTED, or UNVERIFIED
- Evidence mirroring: Paste actual command output

## SUPPLEMENTAL: Verification Discipline
- Run OWN searches, paste ACTUAL output, then make claim
- Evidence before assertions, always
```

---

## After Dispatch

**ALWAYS re-dispatch Skeptic** on the revised plan (plan-r{N+1}.md if repairs, or original if only contested).

Revise does NOT produce verdicts. The copy to plan-final.md happens ONLY when Skeptic returns SOUND.

See `skeptic-dispatch.md` for the verdict handling.

---

## Loop Protocol

```
Skeptic (iteration N)
    ↓
UNSOUND → Revise → plan-r{N+1}.md (or defense only)
    ↓
Skeptic (iteration N+1) with defense evidence
    ↓
SOUND → plan-final.md (only Skeptic triggers this copy)
```

**Critical**: Only Skeptic SOUND verdict triggers copy to plan-final.md. Revise NEVER triggers copy.
