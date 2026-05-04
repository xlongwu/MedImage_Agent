# Constraint Flow & Registry

This reference covers constraint lifecycle and registry formats. For constraint TYPE definitions (REQUIREMENT, LIMITATION, INVARIANT, PREFERENCE), see SKILL.md Phase 1.

---

## Constraint Sources

| Source | Reliability | Verification Method |
|--------|-------------|---------------------|
| **User-stated** | HIGH | Direct from feature request |
| **Code-discovered** | HIGH | Verified via file:line reference |
| **Documentation** | HIGH | Context7 or official docs |
| **Inferred** | MEDIUM | Logical deduction from context |
| **Assumed** | LOW | No direct evidence, flag for review |

---

## Constraint Registry Format

```markdown
## Constraint Registry

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-01 | REQUIREMENT | Zero data loss | feature-request.md | YES | User stated |
| C-02 | LIMITATION | In-memory volatile | src/store.ts:45 | YES | Code comment |
| C-03 | INVARIANT | Event IDs unique | src/events/base.ts:12 | YES | UUID generation |
| C-04 | PREFERENCE | Async-first | CLAUDE.md:34 | YES | Project convention |
| C-05 | REQUIREMENT | Sub-100ms response | feature-request.md | YES | User stated |
| C-06 | LIMITATION | No external deps | run.json | YES | Orchestrator constraint |
```

---

## Cross-Phase Constraint Flow

```
Phase 2 (Spec Formalization)
    ↓ Extract initial C-### from feature request
    ↓ Write to feature-request.md

Phase 3 (Spec Skeptic)
    ↓ Validate C-### compatibility
    ↓ Flag REQUIREMENT vs LIMITATION conflicts

Phase 8 (Worker Explore)
    ↓ Discover new C-### from code
    ↓ Cross-reference with feature-request.md C-###
    ↓ Mark conflicts as H-CFG hazards

Phase 10 (Consolidator)
    ↓ Merge C-### from all workers
    ↓ Detect cross-worker contradictions
    ↓ Resolve before plan synthesis
```

---

## Constraint Verification Status

| Status | Meaning | Action |
|--------|---------|--------|
| **YES** | Verified via evidence | None needed |
| **NO** | Not yet verified | Must verify before execute |
| **INHERITED** | From feature-request.md | Already verified in Phase 2 |
| **CONFLICT** | Contradicts another constraint | Must resolve before proceed |
| **ASSUMED** | No evidence, believed true | Flag for skeptic review |

---

## Usage in Other Phases

### In Hazard Registry (H-###)

When a constraint conflict is discovered, it becomes a hazard:

```markdown
| H-ID | Category | Hazard | Evidence | C-IDs |
|------|----------|--------|----------|-------|
| H-CFG-01 | Constraint | REQ vs LIM conflict | C-01 vs C-02 | C-01, C-02 |
```

### In Assumption Registry (A-###)

When a constraint's source is ASSUMED, it should also appear as an assumption:

```markdown
| A-ID | Assumption | Source | C-ID |
|------|------------|--------|------|
| A-01 | Node.js 18+ available | Assumed | C-07 |
```

### In Implementation Tasks

Tasks reference which constraints they satisfy:

```markdown
#### Task A.1: Add persistence layer
- **Ensures**: C-01 (zero data loss)
- **Removes**: C-02 (in-memory limitation no longer applies)
```
