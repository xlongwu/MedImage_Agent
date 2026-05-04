# Verification Gaps Report

> This report documents gaps found during verification of run {run_id}.
> To address these gaps, start a new `/darwin` session with this file as context.

---

## Run Context

| Field | Value |
|-------|-------|
| Run ID | {run_id} |
| Feature | {feature_name} |
| Feature Request | `{run_dir}/_meta/feature-request.md` |
| Spec | `{run_dir}/consolidated/spec.md` |
| Learnings | `{run_dir}/execute/learnings.md` |
| Verification Date | {timestamp} |
| Verdict | {FIXABLE | BLOCKED} |

---

## Coverage Summary

| Category | Tested | Passed | Failed | Coverage |
|----------|--------|--------|--------|----------|
| Success Criteria (SC) | {n} | {n} | {n} | {%} |
| Constraints (C) | {n} | {n} | {n} | {%} |
| Task DoD | {n} | {n} | {n} | {%} |
| Hazard Mitigations | {n} | {n} | {n} | {%} |
| Edge Cases | {n} | {n} | {n} | {%} |
| Integration | {n} | {n} | {n} | {%} |
| Regression | {n} | {n} | {n} | {%} |

**Total Gaps:** {N}

---

## Gaps

### V-01: {Brief Title}

**Category:** {SC Failure | Constraint Violation | DoD Miss | Hazard Unmitigated | Edge Gap}
**Traces to:** {feature-request.md SC-01 | spec.md T2.3 | spec.md H-CFG-01}
**Severity:** {CRITICAL | HIGH | MEDIUM}

**What was expected:**
{From feature-request.md or spec.md - quote the requirement}

**What happened:**
```
{Actual test output - Evidence Mirroring - paste full output}
```

**Gap description:**
{Clear explanation of the discrepancy}

**Suggested fix:**
{Specific, actionable fix if known}
{Confidence: X%}

---

## Key Learnings from This Run

Reference: `{run_dir}/execute/learnings.md`

Relevant learnings for gap resolution:
- {learning_1 if relevant to gaps}
- {learning_2 if relevant to gaps}

---

## Suggested Next Steps

**For FIXABLE verdict:**
```
/darwin "Fix verification gaps from {run_id}: {1-sentence summary of gaps}"
```
Attach this file as context. The gaps are minor and have clear fixes.

**For BLOCKED verdict:**
1. Review the gaps above carefully
2. Consider if spec needs revision
3. Then:
```
/darwin "Address verification blockers from {run_id}: {1-sentence summary}"
```

---

## Completeness Certification

This verification achieved:
- SC Coverage: {n}/{total} ({%})
- Constraint Coverage: {n}/{total} ({%})
- DoD Coverage: {n}/{total} ({%})
- Hazard Coverage: {n}/{total} ({%})

Completeness audit passed: {YES/NO}
