# Skeptic Dispatch Template

This template is used to dispatch the `darwin-skeptic` subagent for adversarial plan auditing.

---

## When to Use

After plan.md is written (workers/main/plan.md for single-loop, or workers/{ID}/plan.md for population mode).

---

## Prerequisites

**Verify files exist** (do NOT read content into orchestrator context):
```
Glob: docs/darwin/runs/{RUN_ID}/workers/main/plan*.md
Glob: docs/darwin/runs/{RUN_ID}/workers/main/explore.md
```

Determine `{plan_file}`:
- Iteration 0: `plan.md`
- Iteration N: `plan-r{N}.md`

---

## Task Tool Parameters

| Parameter | Value |
|-----------|-------|
| subagent_type | `darwin-skeptic` |
| run_in_background | `true` |
| description | `Skeptic audit iteration {N}` |

---

## Prompt Template

**DO NOT paste file contents.** Skeptic reads files itself using Serena tools.

```
You are a skeptic auditor. You have NOT seen how this plan was created.


## Documents to Audit (Read these yourself)
- Plan: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/{plan_file}
- Hazard Registry: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/explore.md

Use `mcp__plugin_serena_serena__read_file` to read these documents.
The plan is probably WRONG. Read it to know what claims to verify against actual code.

## Your Task
1. Read plan and explore documents (to identify claims)
2. Extract testable claims: file:line refs, symbol names, API signatures
3. Use Serena (find_symbol, search_for_pattern) to verify each claim
4. Track issues with SK-### IDs
5. Output critique with verdict

## Output
Write to: docs/darwin/runs/{RUN_ID}/workers/{worker_dir}/critique-{N}.md

Include machine-readable verdict block at END of file:
```yaml
---
verdict: SOUND | UNSOUND | PROVISIONAL
issues_count: {number}
kill_list_count: {number}
plan_audited: {plan_file}
---
```

Follow darwin-skeptic protocol:
- Phase 1: Claim Extraction (from documents you read)
- Phase 2: Dialectical Protocol (verify via Serena tools)
- Phase 2.5: Confidence-Based Filtering (≥80% for Kill List)
- Phase 2.6: Attack E - Configuration Validity
- Phase 3: Hazard Audit
- Phase 4: Generate Critique with verdict

## SUPPLEMENTAL: Verification Discipline
- Run the command. Read the output. THEN make claim.
- The plan/explore documents guide WHERE to search, not WHAT to believe.
- NO completion claims without fresh verification evidence.

## SUPPLEMENTAL: Confidence Scoring
- 90-100%: Direct code contradiction → Kill List
- 70-90%: Semantic mismatch → SUSPICIOUS
- 50-70%: Contextual issues → Ambiguity
- <50%: Speculation → Ignore
```

---

## After Dispatch

Review the critique output at `docs/darwin/runs/{RUN_ID}/workers/main/critique-{N}.md`.

**Skeptic is the SOLE VERDICT AUTHORITY.** Only Skeptic produces SOUND/UNSOUND verdicts. Revise produces defense + revised plan, but NEVER produces verdicts.

| Verdict | Action |
|---------|--------|
| **SOUND** | Copy accepted plan to `workers/main/plan-final.md`, then to `consolidated/spec.md` |
| **UNSOUND** or **PROVISIONAL** | Dispatch `darwin-revise` (see `templates/revise-dispatch.md`), then re-dispatch Skeptic |

**Critical**: After Revise completes, ALWAYS re-dispatch Skeptic. The copy to plan-final.md happens ONLY here, after Skeptic returns SOUND.
