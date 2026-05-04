# code-explorer Usage in Discovery

This document details when and how to use the `feature-dev:code-explorer` agent as a supplement to direct Serena tools during discovery.

---

## Primary vs Supplement

| Approach | Tools | When to Use |
|----------|-------|-------------|
| **Primary** | Serena: `find_symbol`, `search_for_pattern`, `read_file` + Context7 | Always - this is the default |
| **Supplement** | `feature-dev:code-explorer` agent | Complex cases where direct tools are insufficient |

**code-explorer is a SUPPLEMENT, not a replacement.** Always exhaust direct Serena tools first.

---

## When to Dispatch code-explorer

| Condition | Use code-explorer? |
|-----------|-------------------|
| Simple symbol lookup | No - use `find_symbol` |
| Pattern search in known files | No - use `search_for_pattern` |
| High-relevance item needs deeper tracing | **Yes** |
| Complex dependency chains span multiple layers | **Yes** |
| Surface inventory from direct tools is incomplete | **Yes** |
| Need to understand architectural patterns | **Yes** |
| Call chain crosses 5+ files | **Yes** |

---

## Dispatch Protocol

Use the Task tool with these parameters:

| Parameter | Value |
|-----------|-------|
| subagent_type | `feature-dev:code-explorer` |

### Prompt Template

```
Analyze: {surface_area}
Keywords: {keywords from Phase 1}
Entry point: {entry_point}

Trace through the code comprehensively and return:
1. Entry points with file:line references
2. Step-by-step execution flow
3. Key components and their responsibilities
4. List of 5-10 essential files to read

Focus on understanding architecture patterns that will inform the implementation plan.
```

### Example Dispatch

```
Task(
  subagent_type="feature-dev:code-explorer",
  prompt="""
Analyze: Theme system and settings persistence
Keywords: ThemeContext, useSettings, localStorage, dark, light
Entry point: src/theme/index.ts

Trace through the code comprehensively and return:
1. Entry points with file:line references
2. Step-by-step execution flow
3. Key components and their responsibilities
4. List of 5-10 essential files to read

Focus on understanding architecture patterns that will inform the implementation plan.
"""
)
```

---

## Integration with Surface Inventory

After code-explorer returns, merge findings into Surface Inventory:

### Merge Protocol

1. **Add discovered symbols** to Symbol table
   - Include `file:line` from explorer results
   - Mark source as "code-explorer"

2. **Add traced files** to Files table
   - Categorize by relevance (High/Medium/Low)
   - Note why each file matters

3. **Flag hazard indicators** for Explore phase
   - Cross-cutting concerns
   - Circular dependencies
   - Hidden side effects
   - Global state mutations

### Example Merge

```markdown
### Surface Inventory (after code-explorer merge)

#### Symbols Discovered
| Symbol | Type | Location | Source |
|--------|------|----------|--------|
| ThemeContext | Context | src/theme/index.ts:12 | Direct search |
| useTheme | Hook | src/theme/hooks.ts:34 | code-explorer |
| persistTheme | Function | src/theme/persist.ts:8 | code-explorer |

#### Additional Hazard Indicators (for Explore)
- Circular: ThemeContext <-> useSettings (flagged by code-explorer)
- Global state: localStorage modified in multiple places
```

---

## What code-explorer Provides

The agent traces execution paths and returns:

1. **Entry points** - Where execution begins
2. **Execution flow** - Step-by-step path through code
3. **Components** - Key classes/functions and responsibilities
4. **File list** - Essential files to understand the feature
5. **Architecture patterns** - Design patterns in use
6. **Coupling points** - Where components interact

---

## What code-explorer Does NOT Provide

- Hazard assessment (that's Explore phase)
- Implementation recommendations (that's Plan phase)
- Testing strategy (that's Execute phase)

Use code-explorer for **understanding**, not **decision-making**.
