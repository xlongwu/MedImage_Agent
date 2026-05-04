---
name: skill-review
description: This skill should be used when reviewing Claude Code plugins, creating skills, writing agents, or implementing hooks. Use when the user asks to "review a skill", "create a plugin", "write an agent", "implement a hook", "check plugin quality", or needs guidance on plugin component authoring and review.
---

# Plugin Component Review

Comprehensive guide for writing and reviewing Claude Code plugin components (skills, agents, hooks).

## Contents

- Quick Reference
- Review Process (4 phases)
- Component-Specific Rules
- Additional Resources

---

## Quick Reference

| Component | Description Location | Writing Style | Key Limits |
|-----------|---------------------|---------------|------------|
| **Skill** | Frontmatter `description` | Imperative/infinitive | SKILL.md < 500 lines |
| **Agent** | Frontmatter `description` | Second person ("You are...") | Description < 5,000 chars |
| **Hook** | In `hooks.json` | N/A (JSON config) | Timeout: 60s command, 30s prompt |

### Description Format

| Component | Format | Example |
|-----------|--------|---------|
| **Skill** | Third-person + triggers | "This skill should be used when the user asks to..." |
| **Agent** | Third-person + examples | "Use this agent when... `<example>` blocks" |

---

## Review Process

### Phase 1: Pre-Review

Before examining the component, establish context.

#### 1.1 Flow Tracing

Trace the component's role in the larger workflow:
- What invokes this component?
- What does it output?
- Who consumes that output?

```
Upstream → [THIS COMPONENT] → Downstream
```

#### 1.2 Empirical Evidence

Read working examples before prescribing patterns:
- Find similar components in the same plugin
- Check how they handle the same patterns
- Note what works vs what you'd change

**Principle:** Evidence over theory. Check what similar components actually do.

#### 1.3 Identify Design Decisions

Search for explicit design decisions that might conflict:
```bash
grep -r "Design Decision" path/to/plugin/
grep -r "FORBIDDEN\|NOT\|NEVER" path/to/plugin/
```

---

### Phase 2: Structure Check

Verify the component follows structural requirements.

#### 2.1 Progressive Disclosure

| Level | What | When Loaded |
|-------|------|-------------|
| 1. Metadata | name + description | Always (system prompt) |
| 2. SKILL.md body | Core instructions | When skill triggers |
| 3. References | Detailed docs | When explicitly read |

**Rule:** SKILL.md body under 500 lines. Move detailed content to `references/`.

#### 2.2 Reference Depth

Keep references **one level deep** from SKILL.md.

```markdown
# BAD: Too deep (Claude may only read first 100 lines)
SKILL.md → advanced.md → details.md → actual-info.md

# GOOD: One level deep
SKILL.md → reference/patterns.md
SKILL.md → reference/api-docs.md
```

#### 2.3 File Organization

```
skill-name/
├── SKILL.md           # Core instructions (required)
├── references/        # Detailed docs (loaded as needed)
├── templates/         # Format definitions (AUTHORITATIVE)
├── scripts/           # Deterministic operations
└── assets/            # Output resources (not loaded into context)
```

**Key distinction:**
- `references/` = loaded into context when needed
- `assets/` = used in output, never loaded into context

---

### Phase 3: Content Check

Verify content quality and discoverability.

#### 3.1 Description Quality (CSO)

**Claude Search Optimization** determines if the component gets discovered.

| Rule | Why |
|------|-----|
| Third-person format | Injected into system prompt |
| Trigger phrases, not workflow summaries | Summaries cause Claude to skip body |
| Specific key terms | Enables discovery from 100+ components |
| Technology-agnostic problems | Broader applicability |

```yaml
# BAD: Workflow summary (Claude may skip body)
description: Use when executing plans - dispatches subagent per task with review between tasks

# GOOD: Trigger conditions only
description: This skill should be used when executing implementation plans with independent tasks
```

#### 3.2 Writing Style

| Component | Style | Example |
|-----------|-------|---------|
| **Skills** | Imperative/infinitive | "Extract fields from input" |
| **Agents** | Second person | "You are a code reviewer..." |

```markdown
# BAD (skill): Second person
You should validate the input before processing.

# GOOD (skill): Imperative
Validate input before processing.
```

#### 3.3 Degrees of Freedom

Match specificity to task fragility:

| Freedom | When | Example |
|---------|------|---------|
| **High** | Multiple valid approaches | Code review process |
| **Medium** | Preferred pattern exists | Report generation template |
| **Low** | Fragile/critical operations | Database migration script |

**Principle:** Narrow bridge with cliffs = low freedom. Open field = high freedom.

#### 3.4 Template Authority

Templates define FORMAT. SKILL.md references, never duplicates.

```markdown
# BAD: Duplicating template content
## Output Format
The report should have:
- Section A with fields X, Y, Z
- Section B with tables...
[entire format duplicated]

# GOOD: Reference with AUTHORITATIVE marker
## Output Format

**See:** `templates/report-format.md` (AUTHORITATIVE)

Key sections: A, B, C
```

**Merge rule:** If reference is always loaded AND combined < 500 lines, merge. If conditionally loaded, keep separate.

---

### Phase 4: Verification

Verify correctness and consistency.

#### 4.1 TDD for Documentation

Apply RED-GREEN-REFACTOR to skills:

1. **RED:** Run pressure scenario WITHOUT skill, document baseline failures
2. **GREEN:** Write minimal skill addressing those failures
3. **REFACTOR:** Find new rationalizations, add counters, re-test

**Iron Law:** No skill without a failing test first.

#### 4.2 Cross-Reference Check

Before finalizing changes:
```bash
# Search for all references to changed concepts
grep -r "concept-name" path/to/plugin/

# Check for naming consistency
grep -r "fixes\.md" path/  # vs
grep -r "gaps\.md" path/   # same file?
```

#### 4.3 Consistency Check

| Check | How |
|-------|-----|
| One canonical name | Search for variants |
| Design decisions propagated | All references updated or deleted |
| No stale references | grep for removed files/concepts |
| README structure updated | Check if structure section is current |

#### 4.4 Completeness Gate

Before finalizing:

```markdown
<completeness_check>
99.99% confident that:
- [ ] All referenced files exist
- [ ] No orphaned reference files
- [ ] Consistent naming throughout
- [ ] Design decisions documented
- [ ] Line count under limits
</completeness_check>
```

---

## Component-Specific Rules

### Skills

**Key patterns:** D1-D5, O1-O7, S1, S3-S6, T1-T5

| Requirement | Value |
|-------------|-------|
| SKILL.md body | < 500 lines |
| Description | Third-person, < 1024 chars |
| Name | 64 chars max, gerunds preferred |

**State ownership:** Skills extract their own state via runtime context:
```markdown
## Runtime Context

**Current State:**
!`cat path/to/state.json 2>/dev/null || echo '{}'`
```

**Script encapsulation:** Deterministic operations belong in scripts:
```bash
# GOOD: Script call
bash ${CLAUDE_PLUGIN_ROOT}/scripts/update-state.sh NEW_STATE

# BAD: Inline shell
jq '.phase = "NEW_STATE"' state.json > tmp.json && mv tmp.json state.json
```

### Agents

**Key patterns:** D6, S2, A1-A4

| Requirement | Value |
|-------------|-------|
| Description | < 5,000 chars with `<example>` blocks |
| Name | 3-50 chars, lowercase + hyphens |
| Model | `inherit` recommended |

**Description format:**
```markdown
Use this agent when [conditions]. Examples:

<example>
Context: [Scenario]
user: "[Request]"
assistant: "[Response using agent]"
<commentary>
[Why this agent triggers]
</commentary>
</example>
```

**Model selection:**
- `inherit` - Same as parent (default)
- `haiku` - Fast, economical
- `sonnet` - Balanced
- `opus` - Most capable

**Color semantics:**
- Blue/cyan: Analysis, review
- Green: Success-oriented
- Yellow: Caution, validation
- Red: Critical, security

**Tools restriction:** Limit to minimum needed (principle of least privilege).

### Hooks

**Key patterns:** H1-H6

| Requirement | Value |
|-------------|-------|
| Command timeout | 60s default |
| Prompt timeout | 30s default |
| Lifecycle | Load at session start, require restart for changes |

**Hook types:**
- **Prompt-based:** Context-aware decisions, flexible
- **Command:** Deterministic checks, fast

**Matcher patterns:**
```json
"matcher": "Write"           // Exact match
"matcher": "Write|Edit"      // Multiple tools
"matcher": "*"               // All tools
"matcher": "mcp__.*"         // Regex
```

**Phase-specific hooks:** One hook per phase when completion criteria differ.

**Security:**
- Validate all inputs
- Check for path traversal (`..`)
- Quote all bash variables
- Never trust tool input without validation

---

## Additional Resources

### Reference Files

**See:** `references/patterns.md` (AUTHORITATIVE) - Complete 50-pattern catalog with evidence

**See:** `references/checklists.md` - Pre/during/post review checklists

**See:** `references/anti-patterns.md` - Common mistakes with fixes

**See:** `references/limits.md` - All character/line limits

### Templates

**See:** `templates/skill-review-template.md` - Skill review checklist

**See:** `templates/agent-review-template.md` - Agent review checklist

### Scripts

**See:** `scripts/validate-skill.sh` - Basic skill validation

---

## Quick Decision Guide

```
Creating/reviewing component?
    │
    ├─► Skill? → Third-person description, imperative body, <500 lines
    │
    ├─► Agent? → Second-person body, <example> blocks in description
    │
    └─► Hook? → Prompt for complex logic, command for deterministic
```

---

## Evidence Sources

All patterns in this skill are backed by evidence from:

| Source | Authority |
|--------|-----------|
| anthropic-best-practices.md | Official Anthropic documentation |
| superpowers:writing-skills | TDD methodology for skills |
| plugin-dev:skill-development | Plugin structure reference |
| plugin-dev:agent-development | Agent authoring reference |
| plugin-dev:hook-development | Hook implementation reference |

**See:** `references/patterns.md` for complete evidence mapping.
