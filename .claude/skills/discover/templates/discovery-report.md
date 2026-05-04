# Discovery Report Template

Use this template when generating `{worker_dir}/discover.md` in Phase 5.

---

## Output Locations

- **Single-loop**: `docs/darwin/runs/{RUN_ID}/workers/main/discover.md`
- **Population**: `docs/darwin/runs/{RUN_ID}/workers/{WORKER_ID}/discover.md`

---

## Template

```markdown
# Discovery Report - {Feature}
## Run: {RUN_ID}
## Worker: {WORKER_ID} (if population mode)

### Memory-Informed Context

**Memories Consulted**:
- {memory_name}: {key insight used}

**Memory Verification Results**:
| Memory Claim | Status | Evidence |
|--------------|--------|----------|
| "{term}" used for X | VERIFIED | Found at src/config.ts:23 |
| Module Y handles Z | VERIFIED | Confirmed via find_symbol |
| Pattern P is standard | STALE | Now uses Pattern Q (src/new.ts:1) |
| File at path/old.ts | MOVED | Now at path/new/location.ts |

**Memory Corrections Needed**:
- {memory_name}: Update "{old_claim}" -> "{new_reality}"
- {memory_name}: Remove reference to {deleted_thing}

**Intelligence Applied (verified only)**:
- Used "{project_term}" - confirmed still in use
- Searched {module} - verified it handles {responsibility}

### Search Strategy

Keywords used:
- Literal: {list}
- Project Terms: {list} (from memory)
- Synonyms: {list}
- Anti-seeds: {list}
- Framework: {list}
- Integration: {list} (from memory)

### Mandatory Anchors

| Anchor | Location | Notes |
|--------|----------|-------|
| Package manifest | package.json | Dependencies: {list} |
| Entry point | src/index.ts:15 | Bootstrap at line 15 |
| Type definitions | src/types/ | Theme types exist |

### Surface Inventory

#### High Relevance
| Item | Type | Location | Why |
|------|------|----------|-----|
| ThemeContext | Context | src/theme/index.ts:12 | Existing theme system |

#### Medium Relevance
| Item | Type | Location | Why |
|------|------|----------|-----|
| useSettings | Hook | src/hooks/useSettings.ts:45 | Settings pattern to follow |

#### Low Relevance (but noted)
| Item | Type | Location | Why |
|------|------|----------|-----|
| OldColorPicker | Component | src/legacy/colors.tsx:1 | Deprecated, avoid |

### Framework Patterns

| Pattern | Source | Applicability |
|---------|--------|---------------|
| ThemeProvider pattern | Context7 | High - matches existing |

### Configuration Systems Found (if any)

| System | Config Location | Governs What | Query Needed |
|--------|-----------------|--------------|--------------|
| {name} | {file:line} | {what it controls} | {Context7 query} |

### APIs That May Be Gated (if any)

| API | Likely Requires | How to Verify |
|-----|-----------------|---------------|
| {api_call} | {config/permission} | {check method} |

### Initial Observations

- {observation with file:line anchor}
- {observation with file:line anchor}
- {observation with file:line anchor}

### Handoff to Explore

Key areas for depth exploration:
1. {path} - {reason}
2. {path} - {reason}
3. {path} - {reason}
```

---

## Section Requirements

### Memory-Informed Context
- **MUST** include verification status for all memory claims used
- **MUST** list corrections needed (if any)
- Only cite **verified** intelligence in "Applied" section

### Search Strategy
- **MUST** include all 6 keyword categories
- Note source of each category (Feature request, Serena memory, Standard, etc.)

### Mandatory Anchors
- **MUST** check: package manifest, entry point, type definitions
- Include `file:line` references where possible

### Surface Inventory
- Categorize by relevance (High/Medium/Low)
- **EVERY** item needs `file:line` location
- Include "Why" column explaining relevance

### Framework Patterns
- Document Context7 queries made
- Note applicability to this feature

### Configuration Systems (if found)
- Flag for H-CFG hazard analysis in Explore phase
- Note dev/prod differences if observed

### Handoff to Explore
- List 3-5 specific paths for depth exploration
- Prioritize by relevance
