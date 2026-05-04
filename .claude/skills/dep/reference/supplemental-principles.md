# Supplemental Principles for Dispatch Prompts

These principles are embedded in worker dispatch prompts based on feature type.

---

## Always Include: Verification Discipline

From superpowers:verification-before-completion:

```markdown
## SUPPLEMENTAL: Verification Discipline

From superpowers:verification-before-completion:
- Run the command. Read the output. THEN claim the result.
- NO completion claims without fresh verification evidence.
- If you didn't see the output, you can't claim it passed.
- Evidence before assertions, always.
```

---

## For Complex Features: Deep Tracing Principles

Add when: `is_complex = len(workers) > 2 or estimated_files > 5`

From feature-dev:code-explorer and feature-dev:code-architect:

```markdown
## SUPPLEMENTAL: Deep Tracing Principles

From feature-dev:code-explorer:
- Follow call chains from entry to output
- Trace data transformations at each step
- Map abstraction layers (presentation → business logic → data)
- Document interfaces between components
- Prefer direct tool use over nested agents

From feature-dev:code-architect:
- Make decisive architectural choices (not multiple options)
- Provide complete implementation blueprint
- Include file paths, function names, concrete steps
- Design for the requirement, not hypothetical futures
```

---

## For UI Features: Aesthetic Guidelines

Add when: `is_ui_feature = any(kw in feature.lower() for kw in ["ui", "component", "frontend", "button", "form", "modal", "dialog", "toggle", "theme", "style", "css"])`

From frontend-design principles:

```markdown
## SUPPLEMENTAL: Aesthetic Guidelines

From frontend-design principles:
- Typography: Choose distinctive fonts, not system defaults
- Color & Theme: Build cohesive palettes with intent
- Motion: Prefer CSS transitions, staggered reveals
- Spatial Composition: Use asymmetry, overlap, negative space
- Avoid: Generic AI aesthetics, centered everything, system fonts
- Every UI decision should have design rationale
```

---

## Feature Type Detection Logic

```python
# Feature type detection for supplemental embedding
is_complex = len(workers) > 2 or estimated_files > 5
is_ui_feature = any(kw in feature.lower() for kw in [
    "ui", "component", "frontend", "button", "form",
    "modal", "dialog", "toggle", "theme", "style", "css"
])
```

---

## Embedding Template

```markdown
{Always include supplemental_verification}

{If is_complex, add supplemental_tracing}

{If is_ui_feature, add supplemental_aesthetic}
```
