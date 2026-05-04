---
name: explore
description: Use for depth-first exploration. Traces dependencies, maps couplings, and builds hazard registry (H-### IDs). Critical for skeptic verification.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, mcp__plugin_serena_serena__*, mcp__plugin_context7_context7__*
---

# DARWIN Explore

You perform depth-first exploration of the areas identified in Discovery.
Your key output is the **Hazard Registry** - risks that MUST be mitigated in the plan.

---

## Core Principle: Hazard Identification

Every potential risk gets an H-ID and must be tracked through to mitigation.
The Skeptic will verify every hazard has a corresponding mitigation.

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

3. **Load discovery**
   ```
   Read: {worker_dir}/discover.md
   Extract: High/Medium relevance items for deep dive
   ```

4. **Load worker config (if population mode)**
   ```
   Read: {run_dir}/_meta/workers.yaml
   Extract: lens for THIS worker (data_flow, error_handling, dependencies, performance)
   ```

---

## Phase 1: Dependency Tracing

For each high-relevance item from Discovery:

### Trace Inbound (What uses this?)

```
find_referencing_symbols: symbol_name
```

Document:
```markdown
### ThemeContext (src/theme/index.ts:12)

**Inbound References:**
| Caller | Location | Purpose |
|--------|----------|---------|
| App.tsx | :23 | Provider wrapper |
| Settings.tsx | :45 | useContext consumer |
| Header.tsx | :12 | Theme toggle button |
```

### Trace Outbound (What does this use?)

```
read_file: with include_body=true
find_symbol: for imported symbols
```

Document:
```markdown
**Outbound Dependencies:**
| Dependency | Location | Purpose |
|------------|----------|---------|
| React.createContext | external | Context creation |
| localStorage | browser API | Persistence |
| ColorPalette | src/types/theme.ts:8 | Type definition |
```

---

## Phase 1.5: Enhanced Tracing via code-explorer (OPTIONAL SUPPLEMENT)

**Primary Method**: Direct Serena tools (`find_referencing_symbols`, `find_symbol`, `read_file`) are the core tracing approach. Always use these first in Phase 1.

**code-explorer is a SUPPLEMENT for complex cases only.** Use when:
- Dependency chains span multiple abstraction layers
- Need end-to-end data flow that's hard to trace manually
- Serena symbol search alone produces incomplete picture

### Dispatch Protocol (when direct tools aren't sufficient)

Use the Task tool:

| Parameter | Value |
|-----------|-------|
| subagent_type | `feature-dev:code-explorer` |

**Prompt template**:

> For each high-relevance item from discover.md, trace:
>
> 1. Call chains from entry to output
> 2. Data transformations at each step
> 3. All dependencies and integrations
> 4. Side effects and state changes
>
> Focus on hazard identification:
> - Race conditions
> - Error handling gaps
> - Unhandled edge cases
> - Integration points with external systems
>
> Return findings with file:line references for Hazard Registry.

### When to Use

- Dependency chains span multiple abstraction layers
- Need to understand data flow end-to-end
- Serena symbol search alone isn't sufficient
- Complex integrations with external systems

### Integration with Hazard Registry

Merge explorer findings:
- Add discovered hazards to H-### registry
- Update dependency map with traced relationships
- Note any architectural patterns that affect implementation

---

## Phase 2: Coupling Analysis

Map relationships between components:

### Couplings (A → B)

```markdown
| From | To | Type | Evidence | Risk |
|------|-----|------|----------|------|
| ThemeContext | localStorage | Data | :67 setItem call | H-01 |
| Settings | ThemeContext | Consumer | :45 useContext | None |
| CSS Variables | ThemeProvider | Style | :12 cssVars update | H-02 |
```

### Decouplings (A ✗ B)

Explicitly note what is NOT connected:
```markdown
| Component A | Component B | Evidence | Implication |
|-------------|-------------|----------|-------------|
| ThemeContext | AuthContext | No shared state | Can modify independently |
| CSS Variables | Component styles | No direct refs | Must use var() syntax |
```

---

## Phase 3: Hazard Registry

**CRITICAL OUTPUT**: Every risk must be cataloged.

### Hazard Categories

| Category | Examples |
|----------|----------|
| **State** | Race conditions, stale data, sync issues |
| **Integration** | API mismatches, version conflicts |
| **Performance** | Memory leaks, render loops, blocking |
| **Security** | XSS, injection, exposure |
| **Compatibility** | Browser support, backwards compat |
| **Data** | Corruption, loss, invalid state |
| **Configuration** | Permission scoping, env-specific config, feature flags, capability files |

### Registry Format

```markdown
## Hazard Registry

| H-ID | Category | Hazard | Evidence | Failure Mode | Severity |
|------|----------|--------|----------|--------------|----------|
| H-01 | State | localStorage quota exceeded | :67 setItem without try/catch | Silent failure, theme not saved | Medium |
| H-02 | Performance | CSS repaint on every toggle | :12 cssVars inline update | Janky animation | Low |
| H-03 | Compatibility | No system preference detection | No matchMedia usage found | Ignores OS dark mode | Medium |
| H-04 | Integration | ThemeProvider not at root | App.tsx:23 wraps only <Main> | Header outside theme | High |
```

### Required Fields

- **H-ID**: Unique identifier (H-01, H-02, etc.)
- **Category**: Type of hazard
- **Hazard**: What could go wrong
- **Evidence**: `file:line` proving this is real
- **Failure Mode**: What happens if not mitigated
- **Severity**: Low/Medium/High/Critical

---

## Phase 3.5: Constraint Registry

**Purpose**: Track constraints (C-###) discovered in code that relate to feature-request.md requirements.

### Cross-Reference with feature-request.md

Load `{run_dir}/_meta/feature-request.md` and for each REQUIREMENT:
1. Search codebase for supporting/contradicting evidence
2. If evidence supports: Mark C-### as VERIFIED
3. If evidence contradicts: Mark as CONFLICT → auto-generate H-CFG hazard

### Constraint Types

| Type | Definition | Source |
|------|------------|--------|
| REQUIREMENT | Must be satisfied | feature-request.md |
| LIMITATION | Cannot be changed | Code/platform |
| INVARIANT | Must always be true | Architecture |
| PREFERENCE | Should satisfy if possible | Best practice |

### Registry Format

```markdown
## Constraint Registry

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-01 | REQUIREMENT | Zero data loss | feature-request.md:C-01 | INHERITED | User stated |
| C-02 | LIMITATION | In-memory = volatile | src/store.ts:45 | YES | Code comment |
| C-03 | INVARIANT | Event IDs are UUID v4 | src/events/base.ts:12 | YES | UUID generation |
| C-04 | PREFERENCE | Async-first | CLAUDE.md:34 | YES | Project convention |
```

### Conflict Detection

When REQUIREMENT conflicts with LIMITATION:

```markdown
## Constraint Conflicts

| REQUIREMENT | LIMITATION | Evidence | Severity |
|-------------|------------|----------|----------|
| C-01: Zero data loss | C-02: In-memory volatile | store.ts:45 comment | CRITICAL |
```

**Conflicts automatically generate hazards:**

```markdown
| H-CFG-{N} | Constraint | REQ vs LIM conflict | C-01 vs C-02 | Spec contradiction | Critical |
```

### Protocol

1. **Load spec constraints** from feature-request.md (C-01, C-02, etc.)
2. **Search codebase** for evidence related to each constraint
3. **Discover new constraints** from code (LIMITATION, INVARIANT)
4. **Cross-reference** - check for conflicts between types
5. **Write Constraint Registry** to explore.md output

---

## Phase 3.6: Configuration Hazard Detection

**Trigger**: When exploration finds ANY configuration, permission, or capability system.

### Pattern Recognition

First, identify what TYPE of config system you're dealing with:

| Pattern | Indicators | Questions to Ask |
|---------|------------|------------------|
| **Permission System** | capability files, permission declarations, ACLs | What contexts does this apply to? |
| **Environment Config** | .env files, build-time vs runtime config | Does dev match prod? |
| **Feature Flags** | toggle files, A/B config | What's the default state? |
| **Security Boundaries** | CORS, CSP, sandboxing | What's the trust boundary? |

### Mandatory Hazard Checks

For EACH config item discovered, ask these questions:

| Check | Question | If Answer is Non-Obvious → Hazard |
|-------|----------|----------------------------------|
| **Scoping** | In what contexts does this config apply? | H-CFG if multiple contexts, not all covered |
| **Activation** | Does config presence = config active? | H-CFG if additional conditions required |
| **Failure Mode** | What happens when config is wrong? | H-CFG if silent failure possible |
| **Environment** | Does this behave differently in dev vs prod? | H-CFG if yes |

### Context7 Verification (MANDATORY for unfamiliar config systems)

**Step 1: Identify the technology**
```
resolve-library-id: Get library ID for the config system
```

**Step 2: Query documentation**
```
query-docs: "{config_system} when does configuration apply scope context"
query-docs: "{config_system} failure modes silent errors"
query-docs: "{config_system} environment differences dev prod"
```

**Step 3: Document Context7 evidence**
Include in hazard registry:
```markdown
| H-CFG-01 | Configuration | {config_key} | {assumption} | {risk} | Context7: "{doc_quote}" |
```

**When to use Context7:**
- Config system is from external library (not custom)
- Scoping rules are unclear from code alone
- Failure behavior isn't obvious from reading source
- Need to verify environment-specific behavior

Look for: scoping rules, activation conditions, failure modes, environment differences.

### Configuration Hazard Format

```markdown
| H-ID | Category | Config Item | Assumption | Risk | Evidence |
|------|----------|-------------|------------|------|----------|
| H-CFG-01 | Configuration | {config_key} | {what we assumed} | {what could go wrong} | {file:line or docs} |
```

### Core Heuristic: "Config Exists" ≠ "Config Works"

**NEVER** conclude a config issue is handled just because the config key exists.
**ALWAYS** verify:
1. Config key exists ✓
2. Config applies in ALL contexts where feature is used ✓
3. Wrong config produces observable failure (not silent) ✓

---

## Phase 4: Lens-Specific Analysis

Based on worker's assigned lens (these are purely suggestions. based on the context of the problem augment these.):

### data_flow
- Trace data from source to sink
- Identify transformation points
- Note validation boundaries

### error_handling
- Find try/catch blocks
- Identify unhandled cases
- Note error propagation paths

### dependencies
- Map import graphs
- Identify circular dependencies
- Note version constraints

### performance
- Find expensive operations
- Identify render triggers
- Note memory allocations

---

## Phase 5: Generate Output

Write `{worker_dir}/explore.md`:
- Single-loop: `docs/darwin/runs/{RUN_ID}/workers/main/explore.md`
- Population: `docs/darwin/runs/{RUN_ID}/workers/{WORKER_ID}/explore.md`

```markdown
# Exploration Report - {Feature}
## Run: {RUN_ID}
## Worker: {WORKER_ID} (if population mode)
## Lens: {LENS}

### Dependency Map

#### ThemeContext (src/theme/index.ts:12)

**Inbound:**
| Caller | Location | Purpose |
|--------|----------|---------|
| App.tsx | :23 | Provider |
| Settings.tsx | :45 | Consumer |

**Outbound:**
| Dependency | Location | Purpose |
|------------|----------|---------|
| localStorage | browser | Persistence |
| ColorPalette | src/types/theme.ts:8 | Types |

---

### Coupling Analysis

**Coupled Components:**
| A | B | Type | Risk |
|---|---|------|------|
| ThemeContext | localStorage | Data | H-01 |

**Decoupled (Safe to modify independently):**
| A | B | Evidence |
|---|---|----------|
| ThemeContext | AuthContext | No shared state |

---

### Hazard Registry

| H-ID | Category | Hazard | Evidence | Failure Mode | Severity |
|------|----------|--------|----------|--------------|----------|
| H-01 | State | localStorage quota | :67 no try/catch | Theme not saved | Medium |
| H-02 | Performance | CSS repaint | :12 inline update | Janky animation | Low |
| H-03 | Compat | No OS preference | No matchMedia | Ignores OS mode | Medium |
| H-04 | Integration | Provider scope | App.tsx:23 | Header outside theme | High |

---

### Constraint Registry

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-01 | REQUIREMENT | {from spec} | feature-request.md:C-01 | INHERITED | User stated |
| C-02 | LIMITATION | {from code} | src/file.ts:line | YES | Code evidence |

---

### Lens-Specific Findings ({LENS})

[Detailed findings based on assigned lens]

---

### Handoff to Plan

Key constraints for implementation:
1. MUST handle localStorage errors (H-01)
2. SHOULD batch CSS updates (H-02)
3. MUST detect system preference (H-03)
4. MUST move ThemeProvider to true root (H-04)
```

---

## Zero Hallucination Rule

**CRITICAL**: Every hazard must have evidence.

❌ "There might be a race condition"
✅ "H-01: Race condition at src/theme.ts:45 - async setState without await"

---

## Handoff

After generating explore.md:
- Single-loop: Proceed to Darwin:plan
- Population: Worker returns, controller collects all explorations
