---
name: discover
description: Use for breadth-first exploration of codebase. Maps file inventory, entry points, and surfaces relevant to the feature. Uses stochastic keyword seeding with Serena memory integration.
allowed-tools: Read, Write, Bash, Glob, Grep, Task, mcp__plugin_serena_serena__*, mcp__plugin_context7_context7__*
---

# DARWIN Discover

## Runtime Context

**Active Run:**
!`cat docs/darwin/_meta/latest-run.json 2>/dev/null || echo '{"phase": "NO_RUN"}'`

**Package:**
!`jq -r '"\(.name)@\(.version)"' package.json 2>/dev/null || echo "No package.json"`

---

You perform breadth-first mapping of the codebase to surface all areas relevant
to the feature. This is the foundation for deeper exploration.

---

## Core Principle: Stochastic Seeding

Generate diverse search strategies to avoid tunnel vision. NEVER CUT CORNERS:
- **Literal**: Exact terms from feature request
- **Synonyms**: Related terms that might be used in code
- **Anti-seeds**: Edge cases, error conditions, negations
- **Framework-specific**: Terms from relevant frameworks

---

## Boot Sequence

1. **Locate the run**
   ```
   Read: docs/darwin/_meta/latest-run.json
   Extract: run_id, run_dir
   ```

2. **Load run metadata**
   ```
   Read: {run_dir}/_meta/run.json
   Extract: feature, code_root, constraints, mode (single/population)
   ```

3. **Determine worker directory**
   ```
   Single-loop mode: worker_dir = {run_dir}/workers/main/
   Population mode: worker_dir = {run_dir}/workers/{WORKER_ID}/
   ```

4. **Load worker config (if population mode)**
   ```
   Read: {run_dir}/_meta/workers.yaml
   Extract: keywords, entry_point, lens for THIS worker
   ```

5. **Load Serena memories** (CRITICAL for intelligent seeding)
   ```
   list_memories: Get all available memories
   read_memory: Load relevant memories based on feature domain
   ```

   Look for memories about:
   - Architecture patterns used in this codebase
   - Naming conventions and terminology
   - Key modules and their responsibilities
   - Previous learnings from similar features
   - Known hazards or gotchas

---

## Phase 0: Memory-Informed Context

**Before generating keywords**, extract intelligence from Serena memories.

### Memory is a HINT, not TRUTH

**Memory can be stale or incorrect.** Treat it as:
- Starting points for exploration (not final answers)
- Hypotheses to verify (not facts to trust)
- Suggestions to expand keywords (not replacements for search)

**NEVER**:
- Skip code verification because memory says something exists
- Trust memory locations without checking (files move, code changes)
- Assume memory terminology is still current

**ALWAYS**:
- Verify memory claims against actual code
- Search for BOTH memory terms AND generic terms
- Flag contradictions between memory and code

### Memory Analysis Format

```markdown
## Project Intelligence (from Serena Memory) - UNVERIFIED

### Architecture Hints (to verify)
- {patterns discovered in previous sessions} -> VERIFY
- {module boundaries and responsibilities} -> VERIFY

### Terminology Suggestions (to confirm)
- Memory says: "{term}" for {concept} -> CHECK if still used
- Domain vocabulary: {list} -> SEARCH both memory terms AND alternatives

### Suggested Surface Areas (to explore)
- {module}: claimed to handle {responsibility} -> VERIFY exists
```

**Use this intelligence to**:
1. EXPAND keyword list (add memory terms, don't replace generic ones)
2. PRIORITIZE search order (check memory locations first, then broaden)
3. CREATE verification checklist (confirm or refute memory claims)
4. IDENTIFY potential staleness (flag for memory update if wrong)

---

## Phase 1: Intelligent Keyword Generation

Generate 7-12 search keywords informed by memory + feature request:

| Type | Keywords | Source |
|------|----------|--------|
| Literal | {direct terms from feature} | Feature request |
| Project Terms | {equivalent terms from memory} | Serena memory |
| Synonyms | {related terms} | Domain knowledge |
| Anti-seeds | {error, fail, edge, exception} | Standard |
| Framework | {framework-specific terms} | Memory + package.json |
| Integration | {related modules from memory} | Serena memory |

**Example**: See `examples/keyword-generation.md` for complete walkthrough.

### No Memory Available?

If no relevant memories exist:
1. Note this in the discovery report
2. Use standard keyword generation
3. Flag "Project terminology unknown" as a risk
4. Plan to write memory after exploration

---

## Phase 2: Mandatory Anchors

Always check these entry points:

1. **Package manifest**
   ```
   Read: package.json (or equivalent)
   Extract: dependencies, scripts, main entry
   ```

2. **Application entry**
   ```
   Find: main entry point (index.ts, App.tsx, activate(), etc.)
   Note: file:line for bootstrap logic
   ```

3. **Type definitions**
   ```
   Search: Type/interface files related to feature
   Note: Existing types that might need extension
   ```

---

## Phase 3: Surface Inventory

For each keyword, run searches and catalog findings:

### Using Serena

```
search_for_pattern: keyword
find_symbol: keyword (for symbols)
```

### Catalog Format

| File | Relevance | Anchor |
|------|-----------|--------|
| src/theme/index.ts | High - theme context | :12 ThemeProvider |

| Symbol | Type | Location | Relevance |
|--------|------|----------|-----------|
| ThemeContext | Context | src/theme/index.ts:12 | High |

| Package | Version | Purpose |
|---------|---------|---------|
| styled-components | ^5.3.0 | CSS-in-JS theming |

---

## Phase 3.5: Deep Exploration (OPTIONAL SUPPLEMENT)

**Primary Method**: Direct Serena tools (`find_symbol`, `search_for_pattern`, `read_file`) + Context7 queries remain the core approach. Always use these first.

**code-explorer supplement**: For complex surface areas where direct tools are insufficient.

**Pre-dispatch check**: If DEP's Pre-Dispatch phase already ran code-explorer, check for results
in `{run_dir}/_meta/pre-dispatch/` before dispatching again.

**See**: `reference/code-explorer-usage.md` for dispatch protocol and integration.

**When to use**:
- High-relevance items need deeper tracing
- Complex dependency chains span multiple layers
- Surface inventory from direct tools is incomplete

---

## Phase 4: Context7 Integration

Query relevant documentation:

```
resolve-library-id: For each framework/library found
query-docs: "How to implement {feature} in {framework}"
```

Document findings:

| Framework | Pattern | Reference |
|-----------|---------|-----------|
| React | useContext for theme | Context7: /facebook/react |

---

## Phase 4.5: Configuration System Intelligence

**Trigger**: When discovery finds configuration files, permission systems, or gated APIs.

### Detection Patterns

| Pattern | File Indicators | Code Indicators |
|---------|-----------------|-----------------|
| Permission/Capability | capability files, manifests | API authorization calls |
| Environment Config | .env, config.{env}.* | `process.env`, conditional imports |
| Feature Gating | feature flag files | `if (feature.enabled)` patterns |
| Security Boundaries | CORS config, CSP headers | Security-related API calls |

### Query Pattern

When a config system is found:
```
resolve-library-id: {framework_or_system}
query-docs: "configuration scope", "dev vs production", "failure behavior"
```

### Document in Discovery

| System | Config Location | Governs What |
|--------|-----------------|--------------|
| {name} | {file:line} | {what it controls} |

**Handoff to Explore**: Flag for H-CFG hazard analysis:
- Each config system found (for scoping questions)
- Each gated API (for failure mode questions)
- Any dev/prod differences noticed

---

## Phase 5: Generate Output

Write `{worker_dir}/discover.md`:
- Single-loop: `docs/darwin/runs/{RUN_ID}/workers/main/discover.md`
- Population: `docs/darwin/runs/{RUN_ID}/workers/{WORKER_ID}/discover.md`

**Template**: `templates/discovery-report.md`

**Required sections**:
- Memory-Informed Context (verified claims only)
- Search Strategy (all keyword types with sources)
- Mandatory Anchors (package, entry, types)
- Surface Inventory (High/Medium/Low relevance)
- Framework Patterns (Context7 findings)
- Configuration Systems (if found)
- Initial Observations
- Handoff to Explore (3-5 priority areas)

---

## Zero Hallucination Rule

**CRITICAL**: Every claim must have a `file:line` anchor.

| Bad | Good |
|-----|------|
| "There's a theme system" | "ThemeContext exists at src/theme/index.ts:12" |
| "Settings are persisted" | "localStorage.setItem called at src/hooks/useSettings.ts:67" |

---

## Phase 6: Memory Write-Back

**CRITICAL**: Verify claims with Context7 before writing to memory.

**Templates**: `templates/memory-writeback.md`

### Steps

1. **Correct Stale Memory** - Fix incorrect claims found during verification
   ```
   edit_memory: {stale_memory_name}
   ```

2. **Verify Before Writing** - Cross-check with Context7 and code
   - API claims: Query Context7 for accuracy
   - Pattern claims: Verify with find_symbol/read_file
   - ONLY write verified information

3. **Write New Learnings** - Verified discoveries only
   ```
   write_memory: darwin-{feature-slug}-discovery.md
   ```
   Include: terminology, architecture, surface areas, integration points, gotchas

4. **Flag Uncertain Claims** - Mark unverified items explicitly
   ```markdown
   ## Unverified (needs confirmation)
   - {claim} - could not verify, may be stale
   ```

---

## Handoff

After generating discover.md, continue to `Darwin:explore` protocol

Workers execute the full D→E→P sequence before returning to the DEP orchestrator.
