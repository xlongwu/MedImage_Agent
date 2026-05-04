---
name: plan
description: Use to generate implementation specification from discovery and exploration. Creates skeptic-proof plan with hazard mitigations.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, mcp__plugin_serena_serena__*, mcp__plugin_context7_context7__*
---

# DARWIN Plan

You synthesize Discovery and Exploration into ONE thorough, skeptic-proof
implementation plan. Every claim must be verifiable; every hazard must have
mitigation.

---

## Core Principle: Skeptic-Proof

The Skeptic WILL:
- Verify every `file:line` anchor
- Check every hazard has mitigation
- Test every assumption
- Attack any vague claim

Write your plan assuming an adversarial reviewer.

---

## Boot Sequence

1. **Locate the run**
   ```
   Read: docs/darwin/_meta/latest-run.json
   Extract: run_id, run_dir
   ```

2. **Determine worker directory**
   ```
   Single-loop mode: worker_dir = {run_dir}/workers/main/
   Population mode: worker_dir = {run_dir}/workers/{WORKER_ID}/
   ```

3. **Load inputs**
   ```
   Read: {worker_dir}/discover.md
   Read: {worker_dir}/explore.md (CRITICAL: contains Hazard Registry)
   ```

4. **Extract hazards**
   Build list of all H-IDs that MUST be addressed

---

## Phase 0: Architecture Design via code-architect (OPTIONAL SUPPLEMENT)

### Pre-Dispatched Architecture Analysis

For complex features, the DEP stage may have pre-dispatched `feature-dev:code-architect`
BEFORE your discovery phase. If architecture analysis was provided in the dispatch prompt:

1. **Read the architecture blueprint** provided in your input context
2. **Incorporate decisive choices** into your plan (don't propose alternatives)
3. **Reference architect findings** in your Evidence Summary
4. **Verify architect claims** using Serena before including them

**Primary Method**: Synthesize directly from discover.md + explore.md findings using your own analysis. You have access to the same Serena/Context7 tools for verification.

**code-architect is a SUPPLEMENT for complex architectures.** Use when:
- Multiple architectural approaches are viable
- Cross-cutting concerns span many modules
- Need pattern analysis across the codebase

### Dispatch Protocol (when additional perspective helps)

Use the Task tool:

| Parameter | Value |
|-----------|-------|
| subagent_type | `feature-dev:code-architect` |
| subagent_type | `superpowers:writing-plans` |

**Prompt template**:

> Given the hazard registry from explore.md, design implementation for: {feature}
>
> CONTEXT:
> - Discovery findings: {summary from discover.md}
> - Hazards to address: {list of H-### IDs}
> - Constraints: {from run.json}
>
> REQUIREMENTS:
> 1. Every H-### hazard must have explicit mitigation
> 2. Use existing patterns found in exploration
> 3. Provide file:line anchors for all integration points
>
> OUTPUT FORMAT:
> - Patterns & Conventions Found (with file:line refs)
> - Architecture Decision (single approach, not options)
> - Component Design (each component with file path, responsibilities)
> - Implementation Map (files to create/modify)
> - Build Sequence (phased checklist)
>
> Make decisive architectural choices. The plan must be skeptic-proof.

### Integration with Plan Sections

Use architect output to structure:
- **Evidence Summary**: Use architect's patterns & conventions
- **Implementation Ledger**: Use architect's build sequence
- **Blast Radius Map**: Use architect's implementation map
- **Hazards & Mitigations**: Ensure architect addressed all H-### IDs

---

## Required Plan Sections

### 1. Scope Anchor

```markdown
## Scope Anchor

**Goal**: [One-line description]

**Constraints**:
- MUST: [list of requirements]
- MUST NOT: [list of restrictions]

**Success Criteria**:
- [ ] [Measurable criterion 1]
- [ ] [Measurable criterion 2]
```

### 2. Evidence Summary

Cite 5-15 load-bearing facts from Discovery/Exploration:

```markdown
## Evidence Summary

| Fact | Source | Anchor |
|------|--------|--------|
| ThemeContext exists | discover.md | src/theme/index.ts:12 |
| localStorage used for settings | explore.md | src/hooks/useSettings.ts:67 |
| No existing dark mode | discover.md | grep returned 0 results |
```

### 3. Implementation Ledger

Break into phased micro-tasks:

```markdown
## Implementation Ledger

### Phase A: Infrastructure

#### Task A.1: Create useTheme hook
- **Objective**: Central theme state management
- **Files**: CREATE src/hooks/useTheme.ts
- **Evidence**: Pattern from explore.md - useSettings.ts:45
- **Definition of Done**: Hook exports useTheme with toggle(), isDark
- **Risks**: H-01 (localStorage errors)
- **Mitigation**: Wrap in try/catch, fallback to light mode

#### Task A.2: Add localStorage persistence
- **Objective**: Remember user preference
- **Files**: MODIFY src/hooks/useTheme.ts
- **Evidence**: useSettings pattern at :67
- **Definition of Done**: Preference survives page refresh
- **Risks**: H-01
- **Mitigation**: Error handling + quota check

### Phase B: UI Components

[Continue with specific tasks...]
```

### Configuration Tasks (when H-CFG hazards exist)

For each H-CFG hazard from explore.md, include:

```markdown
### Phase CFG: Configuration Validation

#### Task CFG.1: Verify config scoping
- **Objective**: Ensure config applies in ALL contexts where feature runs
- **Files**: CHECK {config_path}
- **Evidence**: Context7/docs on scoping rules
- **Definition of Done**:
  - [ ] Config verified to apply in dev context
  - [ ] Config verified to apply in prod context
  - [ ] Any additional required fields present
- **Risks**: H-CFG-{N}
- **Mitigation**: Explicit config for all contexts

#### Task CFG.2: Add error surfacing for gated operations
- **Objective**: Config/permission failures produce observable errors
- **Files**: MODIFY {implementation_file}
- **Evidence**: H-CFG-{N} silent failure risk
- **Definition of Done**:
  - [ ] Gated operations wrapped in try/catch
  - [ ] Errors logged with context
  - [ ] Errors re-thrown (not swallowed)
  - [ ] Test fails with actual error if precondition wrong
- **Risks**: H-CFG-{N}
- **Mitigation**: Error surfacing wrapper
```

### Proof Obligations for Configuration

```markdown
| Claim | How to Verify |
|-------|---------------|
| Config applies in {context} | Read config, check scoping rules |
| Failure is observable | Find try/catch with throw in implementation |
| Dev matches prod | Compare config files across environments |
```

### 4. Blast Radius Map

```markdown
## Blast Radius Map

### Impacted Surfaces
| Surface | Why | Risk Level |
|---------|-----|------------|
| src/theme/ | Direct modification | High |
| src/components/Settings.tsx | UI integration | Medium |
| src/styles/variables.css | CSS variables | Medium |

### Decoupled Surfaces (Safe)
| Surface | Evidence |
|---------|----------|
| src/auth/ | No theme dependencies (explore.md) |
| src/api/ | No UI code |
```

### 5. Hazards & Mitigations

**CRITICAL**: Every H-ID from explore.md MUST appear here.

```markdown
## Hazards & Mitigations

| H-ID | Hazard | Mitigation | Verification |
|------|--------|------------|--------------|
| H-01 | localStorage quota | try/catch + fallback | Unit test with quota exceeded mock |
| H-02 | CSS repaint jank | Batch updates with requestAnimationFrame | Manual 60fps check |
| H-03 | No OS preference | Add matchMedia listener | Test with prefers-color-scheme |
| H-04 | Provider scope | Move to true root | E2E test header has theme |
```

### 6. Test & Validation Plan

```markdown
## Test & Validation Plan

### New Tests
| Test | Type | Validates | Command |
|------|------|-----------|---------|
| useTheme.test.ts | Unit | Hook behavior | npm test -- useTheme |
| theme-toggle.e2e.ts | E2E | User flow | npm run e2e |

### Test ↔ Hazard ↔ Plan Mapping
| H-ID | Test | Task |
|------|------|------|
| H-01 | localStorage-error.test.ts | A.2 |
| H-03 | system-preference.test.ts | A.3 |
```

### 7. Proof Obligations

List claims the Skeptic MUST verify:

```markdown
## Proof Obligations

| Claim | How to Verify |
|-------|---------------|
| ThemeContext at :12 | find_symbol ThemeContext |
| No existing dark mode | search_for_pattern "dark mode" returns 0 |
| useSettings pattern | read_file src/hooks/useSettings.ts |
```

### 8. Ambiguities & RFIs

```markdown
## Ambiguities & RFIs

| Question | Options | Consequence |
|----------|---------|-------------|
| Support IE11? | A: Yes (polyfill), B: No (drop) | Affects CSS strategy |
| Animation duration? | A: 200ms, B: 300ms | UX preference |

**Blocked until resolved**: None / [List blocked items]
```

### 9. Assumption Registry

**Purpose**: Make ALL assumptions explicit. The Skeptic will audit these.

```markdown
## Assumption Registry

| A-ID | Assumption | Classification | Evidence | Risk if Wrong |
|------|------------|----------------|----------|---------------|
| A-01 | WebSocket over polling | USER DECISION | None | Must refactor transport |
| A-02 | UUID v4 for IDs | WORKER CONSENSUS | Industry standard | Minimal |
| A-03 | Node.js 18+ | VERIFIED | package.json:engines | Runtime crash |
| A-04 | React 18 concurrent features | IMPLICIT | Codebase uses React 18 | Perf regression |
```

### Classification Rules

| Classification | When to Use | Skeptic Review |
|----------------|-------------|----------------|
| **USER DECISION** | Multiple valid approaches, no clear winner | MUST ask user |
| **WORKER CONSENSUS** | Clear best practice OR multiple workers agree | Document only |
| **IMPLICIT** | Reasonable inference from context | Verify evidence exists |
| **VERIFIED** | Code/docs confirm | Check file:line |
| **CRITICAL** | Wrong = project failure | MUST verify before execute |

### When to Create Assumptions

You MUST document an assumption (A-###) when:

1. **Spec is silent** on a significant choice
2. **Multiple approaches** are equally valid
3. **Choice affects** user-facing behavior
4. **Decision is irreversible** (or expensive to change)

### Classification Heuristics

| Evidence Level | Classification |
|----------------|----------------|
| No evidence, multiple valid options | USER DECISION |
| Industry standard, single obvious choice | WORKER CONSENSUS |
| Reasonable inference, some evidence | IMPLICIT |
| Code/docs explicitly confirm | VERIFIED |
| Wrong = complete failure | CRITICAL (regardless of evidence) |

**Example**: Choosing WebSocket vs HTTP polling for real-time updates:
- Both are valid → USER DECISION
- No spec guidance → USER DECISION
- Affects architecture → USER DECISION

**Example**: Using UUID v4 for IDs:
- Industry standard → WORKER CONSENSUS
- Easy to change → not CRITICAL
- No spec opinion needed → not USER DECISION

---

## Hazard Mitigation Checklist

Before finalizing, verify:

```markdown
### Hazard Coverage Check

| H-ID | In Explore? | Mitigation in Plan? | Test for Mitigation? |
|------|-------------|---------------------|----------------------|
| H-01 | ✓ | ✓ Task A.2 | ✓ localStorage-error.test |
| H-02 | ✓ | ✓ Task B.1 | ✓ Manual 60fps |
| H-03 | ✓ | ✓ Task A.3 | ✓ system-preference.test |
| H-04 | ✓ | ✓ Task C.1 | ✓ E2E header test |

⚠️ If any H-ID is missing mitigation, add it before proceeding!
```

---

## Output

Write `{worker_dir}/plan.md`:
- Single-loop: `docs/darwin/runs/{RUN_ID}/workers/main/plan.md`
- Population: `docs/darwin/runs/{RUN_ID}/workers/{WORKER_ID}/plan.md`

```markdown
# Implementation Plan - {Feature}
## Run: {RUN_ID}
## Worker: {WORKER_ID} (if population mode)

[All sections above, fully populated]

---

## Assumption Registry

| A-ID | Assumption | Classification | Evidence | Risk if Wrong |
|------|------------|----------------|----------|---------------|
| A-01 | {assumption} | {classification} | {evidence} | {risk} |

---

## Handoff

Ready for Skeptic review.

Proof Obligations: {count}
Hazards Mitigated: {count}/{total}
Tasks Defined: {count}
Assumptions: {count} ({user_decision_count} USER DECISION)
```

---

## Zero Hallucination Rule

Every claim needs an anchor:

❌ "We'll add a toggle button"
✅ "Task B.2: Add toggle button to Settings.tsx:45 (after theme selector)"

❌ "Handle errors appropriately"
✅ "Task A.2: Wrap localStorage.setItem in try/catch (mitigates H-01)"

---

## Handoff

After generating plan.md:
- Proceed to Darwin:skeptic for adversarial audit
