# Intent Capture Reference

This reference provides detailed guidance for extracting core intent from feature requests.

---

## Problem Statement Extraction

Parse the feature request to identify:

| Component | Question | Example |
|-----------|----------|---------|
| Pain Point | What problem exists today? | "Users lose settings when switching devices" |
| Impact | Who is affected and how? | "Multi-device users waste time reconfiguring" |
| Opportunity | What value does solving this create? | "Seamless experience increases engagement" |

### Signals of Problem Statements

Look for keywords indicating problems ** NOT EXCLUSIVE** :
- "currently", "today", "right now" → existing state
- "frustrated", "difficult", "time-consuming" → pain
- "need", "want", "would like" → desire

---

## Target Users Identification

Identify WHO benefits from this feature:

| User Type | Indicators | Questions to Ask |
|-----------|------------|------------------|
| Primary | Directly uses the feature | Who performs this action? |
| Secondary | Affected by the feature | Who sees the results? |
| Admin | Configures the feature | Who manages settings? |

### Signals of Target Users

- "users", "developers", "admins" → explicit
- "I want to", "we need" → implicit (ask: who is "we"?)
- Task description → infer actor

---

## Success Criteria Definition

Define measurable outcomes:

| Criterion Type | Format | Example |
|----------------|--------|---------|
| Behavioral | "User can {action}" | "User can switch devices without reconfiguring" |
| Performance | "{metric} < {threshold}" | "Sync completes in < 5 seconds" |
| Quality | "{property} is {state}" | "No data loss during sync" |

### Signals of Success Criteria

- "must", "should", "need to" → requirements
- Numbers, percentages, times → metrics
- "without", "always", "never" → invariants

---

## Ambiguity Detection

Flag vague statements that need clarification:

| Vague Term | Clarifying Question |
|------------|---------------------|
| "fast" | What latency is acceptable? |
| "good" | What specific qualities matter? |
| "proper" | What standards apply? |
| "handle" | What specific behavior is expected? |

When ambiguity is detected, create AMB-### entry and ask user.

---

## Design Preference Capture (D-###)

When a feature has visual, interaction, or UX implications, capture explicit design decisions.

### When to Invoke frontend-design

Trigger `Skill(skill="frontend-design")` when the feature involves:

| Signal | Examples | Design Questions |
|--------|----------|------------------|
| Visual components | "button", "modal", "dashboard" | Colors, spacing, typography |
| Interaction patterns | "toggle", "drag-and-drop", "swipe" | Animation, feedback, states |
| Layout changes | "sidebar", "grid", "responsive" | Breakpoints, positioning |
| User flow | "onboarding", "wizard", "checkout" | Steps, progress, validation |

### Design Decision Format

Capture each decision as D-###:

```markdown
| D-ID | Decision | User Choice | Rationale |
|------|----------|-------------|-----------|
| D-01 | Color scheme for dark mode | System preference with manual override | Accessibility + user control |
| D-02 | Toggle animation style | Smooth 200ms transition | Modern feel without slowdown |
| D-03 | Error state display | Inline with field, red border | Immediate feedback |
```

### Design Decision Types

| Type | Questions to Ask | Downstream Impact |
|------|------------------|-------------------|
| **Visual** | Colors, spacing, sizing, typography | CSS constraints, design tokens |
| **Interaction** | Hover, click, drag behavior | Event handlers, state management |
| **Layout** | Position, responsive behavior | Component structure, breakpoints |
| **Accessibility** | Screen reader, keyboard nav, contrast | ARIA attributes, focus management |
| **Animation** | Timing, easing, transitions | Performance constraints |

### Integration with Downstream Agents

D-### entries become constraints for workers:
- **code-architect** uses D-### to design component structure
- **code-explorer** verifies existing patterns align with D-###
- **Skeptic** checks implementation matches design decisions

### When NOT to Capture Design Decisions

Skip D-### capture when:
- Feature is purely backend/API
- Feature is refactoring without UI changes
- User explicitly states "no design preferences"

In these cases, downstream agents use existing codebase patterns.
