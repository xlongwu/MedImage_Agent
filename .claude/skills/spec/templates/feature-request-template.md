# Feature Specification Template

## Purpose

This template defines the structure for `{run_dir}/_meta/feature-request.md`, generated during Phase 2 (Spec Formalization). It follows best practices from GitHub's Spec Kit, IEEE 830, and AI agent specification standards.

**Design Principles:**
- Intent is the source of truth (not code)
- Human-readable AND machine-parseable
- Living document that evolves with understanding
- Modular sections for focused agent consumption

---

## Template

```yaml
---
# YAML Frontmatter (Machine-Parseable)
spec_version: "1.0"
run_id: "{RUN_ID}"
feature: "{FEATURE_NAME}"
created_at: "{TIMESTAMP}"
status: "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "BLOCKED"
blocked_by: []  # List of SPEC-### or AMB-### if blocked

# Quick reference for agents
constraint_count: 0
contradiction_count: 0
ambiguity_count: 0
assumption_count: 0

# Boundary summary
boundaries:
  always: []      # Safe actions
  ask_first: []   # High-impact, need confirmation
  never: []       # Hard stops
---
```

```markdown
# Feature Specification: {FEATURE_NAME}

## 1. Intent & Vision

### 1.1 Problem Statement
> What problem are we solving? Why does this matter?

{One paragraph describing the pain point or opportunity}

### 1.2 Target Users
| User Type | Description | Primary Need |
|-----------|-------------|--------------|
| {user_type} | {who they are} | {what they need} |

### 1.3 Success Criteria
How do we know this feature is complete and working?

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| SC-01 | {metric} | {threshold} |
| SC-02 | {metric} | {threshold} |

---

## 2. Scope & Boundaries

### 2.1 In Scope (WILL DO)
- [ ] {deliverable_1}
- [ ] {deliverable_2}
- [ ] {deliverable_3}

### 2.2 Out of Scope (WON'T DO)
- {explicitly_excluded_1}
- {explicitly_excluded_2}

### 2.3 Boundary Definitions

#### Always Do (Safe Actions)
Actions that can be taken without confirmation:
- {safe_action_1}
- {safe_action_2}

#### Ask First (High-Impact)
Actions requiring user confirmation before proceeding:
- {ask_action_1}: {why_confirmation_needed}
- {ask_action_2}: {why_confirmation_needed}

#### Never Do (Hard Stops)
Actions that are explicitly forbidden:
- {forbidden_1}: {why_forbidden}
- {forbidden_2}: {why_forbidden}

---

## 3. Constraints & Requirements

### 3.1 Functional Requirements

| C-ID | Type | Constraint | Priority | Verification |
|------|------|------------|----------|--------------|
| C-01 | REQUIREMENT | {what must be true} | MUST | {how to verify} |
| C-02 | REQUIREMENT | {what must be true} | SHOULD | {how to verify} |

### 3.2 Non-Functional Requirements

| C-ID | Category | Constraint | Target | Verification |
|------|----------|------------|--------|--------------|
| C-03 | Performance | {constraint} | {target} | {how to verify} |
| C-04 | Security | {constraint} | {target} | {how to verify} |
| C-05 | Scalability | {constraint} | {target} | {how to verify} |

### 3.3 Technical Constraints (Limitations)

| C-ID | Limitation | Source | Impact |
|------|------------|--------|--------|
| C-06 | {what cannot be changed} | {platform/code/physics} | {consequence} |

### 3.4 Invariants (Must Always Be True)

| C-ID | Invariant | Rationale | Guard |
|------|-----------|-----------|-------|
| C-07 | {system property} | {why it must hold} | {assertion/check} |

---

## 4. Specification Analysis

### 4.1 Impossibility Check

Patterns evaluated against `reference/impossibility-patterns.md`:

| Pattern | Matched? | Evidence |
|---------|----------|----------|
| PHYS-001 (Persistence vs Volatility) | {YES/NO} | {keywords if matched} |
| CS-001 (CAP Violation) | {YES/NO} | {keywords if matched} |
| SEM-001 (Stateless Memory) | {YES/NO} | {keywords if matched} |

### 4.2 Contradictions Detected

| Issue ID | Pattern | Constraint A | Constraint B | Severity | Resolution |
|----------|---------|--------------|--------------|----------|------------|
| SPEC-01 | {pattern} | C-{N}: {brief} | C-{M}: {brief} | CRITICAL/HIGH | {PENDING/RESOLVED} |

**Resolution Details:**
- SPEC-01: {detailed explanation of contradiction and options}

### 4.3 Ambiguities Detected

| Issue ID | Statement | Problem | Clarification Question |
|----------|-----------|---------|------------------------|
| AMB-01 | "{vague statement}" | {why it's unclear} | {question to ask user} |

---

## 5. Assumptions & Decisions

### 5.1 Explicit Assumptions

| A-ID | Assumption | Basis | Risk if Wrong | Classification |
|------|------------|-------|---------------|----------------|
| A-01 | {what we assume} | {why we assume it} | {consequence} | IMPLICIT/VERIFIED |

### 5.2 Decisions Required

Items that need user input before implementation:

| Decision | Options | Trade-offs | Recommendation |
|----------|---------|------------|----------------|
| D-01: {topic} | A: {option_a}, B: {option_b} | {trade-offs} | {recommendation if any} |

### 5.3 Design Decisions (When Applicable)

Captured via `frontend-design` skill when feature has visual/UX implications:

| D-ID | Decision | User Choice | Rationale |
|------|----------|-------------|-----------|
| D-01 | {design question} | {choice} | {why} |

*Populated when feature has design/UX implications. Downstream agents treat these as constraints.*

---

## 6. Technical Context

### 6.1 Technology Stack
| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| {component} | {tech} | {version} | {constraints} |

### 6.2 Integration Points
| System | Interface | Direction | Data |
|--------|-----------|-----------|------|
| {system} | {API/event/file} | IN/OUT/BOTH | {data type} |

### 6.3 Existing Patterns to Follow
| Pattern | Location | Relevance |
|---------|----------|-----------|
| {pattern_name} | {file:line} | {why relevant} |

---

## 7. Handoff Summary

### Status
| Metric | Value |
|--------|-------|
| Constraints | {N} (REQUIREMENT: {n}, LIMITATION: {n}, INVARIANT: {n}) |
| Contradictions | {N} ({resolved}, {pending}) |
| Ambiguities | {N} |
| Assumptions | {N} |
| Decisions Required | {N} |

### Readiness
- [ ] All contradictions resolved
- [ ] All ambiguities clarified
- [ ] All MUST decisions made
- [ ] Success criteria defined
- [ ] Boundaries established

**Status**: {READY_FOR_SKEPTIC / BLOCKED_ON_RESOLUTION / NEEDS_CLARIFICATION}

{If BLOCKED:}
**Blocking Issues:**
- SPEC-01: {brief}
- AMB-01: {brief}
```

---

## Example

**Feature Request:** `/darwin "Add user preference sync across devices"`

```yaml
---
spec_version: "1.0"
run_id: "0043-user-pref-sync"
feature: "User Preference Sync"
created_at: "2026-01-25T10:30:00Z"
status: "UNDER_REVIEW"
blocked_by: ["AMB-01"]
constraint_count: 5
contradiction_count: 0
ambiguity_count: 1
assumption_count: 2
boundaries:
  always: ["Read preferences", "Write to local storage"]
  ask_first: ["Delete user data", "Change sync frequency"]
  never: ["Store passwords in preferences", "Sync without user consent"]
---
```

```markdown
# Feature Specification: User Preference Sync

## 1. Intent & Vision

### 1.1 Problem Statement
> Users lose their preferences when switching devices. They must reconfigure settings on each device, causing frustration and reducing engagement.

### 1.2 Target Users
| User Type | Description | Primary Need |
|-----------|-------------|--------------|
| Multi-device user | Uses app on phone + desktop | Consistent experience |
| New device migrator | Setting up new device | Quick setup |

### 1.3 Success Criteria
| Criterion | Measurement | Target |
|-----------|-------------|--------|
| SC-01 | Time to sync preferences | < 5 seconds |
| SC-02 | Conflict resolution success | 100% (no data loss) |
| SC-03 | User-reported friction | 0 complaints in first week |

## 2. Scope & Boundaries

### 2.1 In Scope (WILL DO)
- [ ] Sync theme, language, notification preferences
- [ ] Conflict resolution (last-write-wins with timestamp)
- [ ] Offline-first with sync on reconnect

### 2.2 Out of Scope (WON'T DO)
- Account management (separate feature)
- Sync of user-generated content (documents, etc.)
- Cross-app preference sharing

### 2.3 Boundary Definitions

#### Always Do (Safe Actions)
- Read preferences from local storage
- Write preferences to local storage
- Queue sync requests when offline

#### Ask First (High-Impact)
- Delete all user preferences: Irreversible action
- Change sync frequency: Affects battery/bandwidth

#### Never Do (Hard Stops)
- Store passwords in preferences: Security violation
- Sync without user consent: Privacy violation
- Send unencrypted preferences: Security requirement

...
```

---

## Sources

This template incorporates best practices from:
- [GitHub Spec-Driven Development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [Writing Good Specs for AI Agents (Addy Osmani)](https://addyosmani.com/blog/good-spec/)
- [GSA AI Agent Specification Template](https://github.com/GSA-TTS/devCrew_s1/blob/master/docs/templates/AI%20Agent%20Specification%20Template.md)
- IEEE 830 / ISO/IEC/IEEE 29148 standards
