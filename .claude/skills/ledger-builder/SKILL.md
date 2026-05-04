---
name: ledger-builder
description: Transform golden spec into execution ledger. Mechanical extraction with batch gates and verification commands.
disable-model-invocation: false
allowed-tools: Read, Write, Grep, Glob, mcp__plugin_serena_serena__*
---

# DARWIN Ledger Builder

## Runtime Context

**Active Run:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"status": "No active run"}'`

---

## Purpose

Transform the golden spec into an execution ledger that **preserves
behavioral requirements** from the spec.

**This is a FAITHFUL transformation that retains implementation guidance.**

---

## Input

**Golden Spec**: `{run_dir}/consolidated/spec.md`

The spec contains:
- Implementation phases (your batches)
- Task definitions with files, DoD, hazard mitigations
- Context and rationale (IGNORE for ledger)

---

## Output

**Execution Ledger**: `{run_dir}/execute/ledger.md`
**Learnings File**: `{run_dir}/execute/learnings.md`

---

## Reference Index

| Reference | Read When |
|-----------|-----------|
| `templates/ledger-format.md` | Writing ledger structure (AUTHORITATIVE) |
| `templates/learnings-format.md` | Initializing learnings file (AUTHORITATIVE) |
| `templates/verification-patterns.md` | Generating verification commands |

---

## Extraction Protocol

### Step 1: Read Spec Structure

```
Read: {run_dir}/consolidated/spec.md
Extract:
  - Phase headings (## Phase N: Name)
  - Task definitions (### Task X.Y: Title)
  - For each task: files, DoD, mitigates
```

### Step 2: Generate Verification Commands

For each task, generate verification that **tests behavior when possible**.

#### Verification Strategy

| DoD Type | Verification Approach |
|----------|----------------------|
| Behavioral (class works, method returns X) | Run code, assert behavior |
| Has existing/planned tests | Reference the test |
| Simple (file exists, config valid) | Structural check |

#### Key Principle

**If DoD describes behavior, verification must test behavior.**

- DoD says "class has method X" → Verify: import and call method
- DoD says "constructor sets property" → Verify: instantiate, check property
- DoD says "test passes" → Verify: run the test

The execute agent has agency to iterate however it wants. The verification command is the **final gate check** that determines if DoD is truly achieved.

See: `templates/verification-patterns.md` for language-specific guidance.

### Step 3: Create Batch Gates

Each phase becomes a batch with a gate:

```markdown
## Batch N: {Phase Name}

[Tasks...]

**Batch Gate**:
- [ ] All tasks checked
- [ ] `tsc --noEmit` passes (if TypeScript)
- [ ] `npm test -- --testPathPattern="{phase_pattern}"` passes
```

### Step 4: Write Ledger

Use template: `templates/ledger-format.md`

### Step 5: Initialize Learnings

Create empty learnings file with header.

---

## Ledger Format

**See**: `templates/ledger-format.md` (AUTHORITATIVE)

Key elements:
- YAML frontmatter with 8 fields
- Batch sections matching spec phases
- Enhanced task format preserving spec fields:
  - Objective, DoD (multi-line), Evidence, Mitigation
  - Verify command (behavioral when possible)
- Batch gates with build + test commands
- Final gate with full suite

**See**: `templates/verification-patterns.md` for verification command guidance.

---

## Learnings File Format

**See**: `templates/learnings-format.md` (AUTHORITATIVE)

Key elements:
- Append-only log
- Max 50 entries (oldest trimmed)
- Format: `[Task-ID] Learning` or `[BN-GATE] Batch complete`

---

## Task Extraction Rules

### Preserving Spec Structure

The spec (from plan phase) contains these fields per task:

```
#### Task A.1: {Title}
- **Objective**: {description}
- **Files**: {CREATE|MODIFY} {path}
- **Evidence**: {pattern or file:line from exploration}
- **Definition of Done**: {criteria - may be multi-line}
- **Risks**: {H-ID list}
- **Mitigation**: {how to address risks}
```

**PRESERVE ALL FIELDS** in ledger. Do not strip to single-line DoD.

### Field Mapping

| Spec Field | Ledger Field | Action |
|------------|--------------|--------|
| Task title | Title | Copy |
| Files | Operation + Path | Copy |
| Objective | Objective | Copy |
| Definition of Done | DoD | Copy (multi-line OK) |
| Evidence | Evidence | Copy |
| Risks | Mitigates | Copy |
| Mitigation | Mitigation | Copy |
| (generated) | Verify | Generate behavioral command |

### Handling Missing Fields

| Missing Field | Default |
|---------------|---------|
| Objective | Derive from task title |
| Evidence | "See spec" |
| DoD | "Task implemented per spec" |
| Mitigates | "none" |
| Mitigation | "N/A" |
| Verify | Generate from DoD |

---

## Batch Size Guidelines

| Spec Phase Size | Ledger Handling |
|-----------------|-----------------|
| 1-5 tasks | Single batch |
| 6-10 tasks | Single batch (acceptable) |
| 11-20 tasks | Consider splitting at natural boundaries |
| 20+ tasks | Split into sub-batches |

**Natural split boundaries**:
- Different directories (e.g., `domain/events/` vs `domain/job/`)
- Different concerns (e.g., types vs implementations)
- Dependency boundaries

---

## Example Transformation

### Spec Input (excerpt)

```markdown
## Phase 2: Domain Layer

### Task 2.1: Create Event Base Class
- **Objective**: Abstract base for all domain events
- **Files**: CREATE src/domain/events/event.ts
- **Evidence**: Event sourcing pattern from explore.md
- **Definition of Done**:
  - Exports abstract DomainEvent class
  - Constructor accepts (id: string, version: number)
  - Has readonly id, timestamp, version properties
- **Risks**: H-A-003
- **Mitigation**: Validate id is non-empty, version >= 0

### Task 2.2: Create Job Events
- **Objective**: Concrete events for job lifecycle
- **Files**: CREATE src/domain/events/job-events.ts
- **Evidence**: Extends DomainEvent pattern
- **Definition of Done**:
  - Exports JobCreatedEvent, JobStartedEvent, JobCompletedEvent
  - Each extends DomainEvent
- **Risks**: H-A-003, H-A-004
- **Mitigation**: Include job ID in all events
```

### Ledger Output

```markdown
## Batch 2: Domain Layer (2 tasks)

- [ ] **T2.1: Create Event Base Class** | CREATE src/domain/events/event.ts
  - Objective: Abstract base for all domain events
  - DoD:
    - Exports abstract DomainEvent class
    - Constructor accepts (id: string, version: number)
    - Has readonly id, timestamp, version properties
  - Evidence: Event sourcing pattern from explore.md
  - Verify: Class instantiates, properties accessible
  - Mitigates: H-A-003
  - Mitigation: Validate id is non-empty, version >= 0

- [ ] **T2.2: Create Job Events** | CREATE src/domain/events/job-events.ts
  - Objective: Concrete events for job lifecycle
  - DoD:
    - Exports JobCreatedEvent, JobStartedEvent, JobCompletedEvent
    - Each extends DomainEvent
  - Evidence: Extends DomainEvent pattern
  - Verify: Events can be instantiated and extend DomainEvent
  - Mitigates: H-A-003, H-A-004
  - Mitigation: Include job ID in all events

**Batch 2 Gate**:
- [ ] All tasks above checked
- [ ] Build passes
- [ ] Domain tests pass
```

---

## Invocation

Called by executor stage after consolidation phase:

```
After consolidated spec is written:
1. Invoke Darwin:ledger-builder skill
2. Input: run_dir path
3. Output: ledger.md + learnings.md created
4. Proceed to Execute phase
```

---

## Red Flags (STOP)

- Stripping multi-line DoD to single line
- Using structural verification when DoD describes behavior
- Omitting Evidence/Mitigation that exists in spec
- Inventing tasks not in spec
- Skipping verification command generation
- Creating batches that don't match spec phases
