# Verify Dispatch Template

This template is used to dispatch the `darwin-verify` subagent for adversarial post-implementation verification.

---

## When to Use

After Execute completes (outputs `<promise>ALL_BATCHES_COMPLETE</promise>`) and the Stop hook allows exit.

---

## Prerequisites

1. **Confirm Execute completion**
   - Execute skill output `<promise>ALL_BATCHES_COMPLETE</promise>`
   - Ledger shows `status: "COMPLETE"`

2. **Locate run files**
   ```
   Read: docs/darwin/_meta/latest-run.json
   Extract: run_id, run_dir
   ```

3. **Verify spec and ledger exist**
   ```
   Confirm: {run_dir}/consolidated/spec.md exists
   Confirm: {run_dir}/execute/ledger.md exists (status: COMPLETE)
   ```

---

## Task Tool Parameters

| Parameter | Value |
|-----------|-------|
| subagent_type | `Darwin:darwin-verify` |
| model | `sonnet` (spec-blind generation requires reasoning) |
| description | `Verify implementation for {run_id}` |

---

## Prompt Template

```
You are an adversarial verifier for DARWIN run {run_id}.

## Critical Constraint
Generate tests from spec BEFORE reading implementation code.
This prevents implementation bias.

## Run Context
- **Run ID**: {run_id}
- **Run Directory**: {run_dir}
- **Feature Request**: {run_dir}/_meta/feature-request.md (USER INTENT)
- **Spec Path**: {run_dir}/consolidated/spec.md (IMPLEMENTATION PLAN)
- **Ledger Path**: {run_dir}/execute/ledger.md
- **Learnings Path**: {run_dir}/execute/learnings.md
- **Test Output**: src/__tests__/verify/{run_id}/

## Your Task

1. **Phase 1**: Read spec.md (NO CODE ACCESS)
   - Extract all tasks with DoD criteria
   - Extract all H-IDs with mitigation claims
   - Build TestMatrix

2. **Phase 2**: Generate tests (STILL NO CODE ACCESS)
   - DoD tests: 1+ per task
   - Hazard attack tests: 1+ per H-ID
   - Edge cases: 3-5 per component
   - Integration: 1 E2E smoke test

3. **Phase 3**: NOW read implementation
   - Read ledger.md for file paths
   - Detect test framework from package.json
   - **Symbol Reconciliation (CRITICAL)**: Use Serena tools to discover actual APIs
     - `get_symbols_overview` on each implementation file
     - `find_symbol` with `include_info=true` for method signatures
     - Build reconciliation table: spec-claimed → actual-implemented
     - Adjust test method names/signatures to match reality
     - Do NOT adjust tests for missing symbols (these may be DoD failures)
   - Write tests to src/__tests__/verify/{run_id}/

4. **Phase 4**: Execute tests
   - Run existing suite first (regression)
   - Run generated tests
   - Capture ALL output

5. **Phase 5**: Report & Classify
   - Write {run_dir}/verify/report.md
   - Classify failures (DoD miss, hazard gap, edge gap, etc.)
   - If failures: Write {run_dir}/verify/gaps.md
   - Output verdict

## Verdicts
- VERIFIED: All pass → `<promise>VERIFICATION_COMPLETE</promise>`
- FIXABLE: 1-3 failures → Generate gaps.md
- BLOCKED: >3 OR regression → Escalate
- RFI: Spec ambiguity → Request clarification

## SUPPLEMENTAL: Evidence Mirroring
Always paste actual test output, not summaries.

## SUPPLEMENTAL: Symbol Reconciliation Protocol
When adjusting Phase 2 tests for actual implementation:

1. For each implementation file, run:
   - `get_symbols_overview(relative_path="...", depth=1)` to see exports
   - `find_symbol(name_path_pattern="ClassName", ..., include_info=true)` for signatures

2. Build reconciliation table before writing any test files:
   | Spec Claimed | Actual Found | Match? | Adjustment |
   |--------------|--------------|--------|------------|
   | calculate() | calculateDelay() | NO | Change name |

3. Adjust test CODE (not test INTENT) to call actual APIs
4. If symbol missing entirely: keep test as-is (potential DoD failure)
```

---

## After Dispatch

Review the verification output at `{run_dir}/verify/report.md`.

### On VERIFIED
```markdown
Verification complete. All tests passed.

Run status: VERIFIED
Next: Mark run as complete in _meta/latest-run.json
```

### On FIXABLE
```markdown
Verification found {N} fixable issues.
Report: {run_dir}/verify/report.md
Gaps: {run_dir}/verify/gaps.md

Next: Start a new `/darwin` session to address gaps.
```

### On BLOCKED
```markdown
Verification blocked with {N} failures.
Report: {run_dir}/verify/report.md
Gaps: {run_dir}/verify/gaps.md

Next: Review gaps and start a new `/darwin` session.
```

### On RFI
```markdown
Specification ambiguity detected.
Questions listed in: {run_dir}/verify/report.md

Next: Clarify requirements, then start a new `/darwin` session.
```

