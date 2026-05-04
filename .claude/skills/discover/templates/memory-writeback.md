# Memory Write-Back Protocol

After discovery completes, update Serena memory with verified learnings.

---

## Step 1: Correct Stale Memory

If discovery found incorrect claims in existing memories:

```
edit_memory: {stale_memory_name}
```

### What to Fix

- Update moved file paths
- Correct outdated terminology
- Remove references to deleted code
- Update changed patterns

### Example Correction

```
Memory says: "Auth logic in src/auth/login.ts"
Reality: File moved to src/features/auth/login.ts

Action:
edit_memory("architecture")
  needle: "src/auth/login.ts"
  repl: "src/features/auth/login.ts"
  mode: "literal"
```

---

## Step 1.5: Context7 Verification (BEFORE WRITING NEW MEMORY)

**CRITICAL**: Verify claims using Context7 before writing to memory.

### For API/Feature Claims

Example claim: "ES2020 supports structuredClone"

```
mcp__plugin_context7_context7__resolve-library-id: Get library ID
mcp__plugin_context7_context7__query-docs: Query specific feature
```

Cross-check against project's target version (from tsconfig.json or package.json).

### Example Verification

```
Claim to write: "ES2020 supports structuredClone"
Verification: query-docs("structuredClone availability MDN")
Result: "structuredClone is ES2022+"
Action: Do NOT write this claim, or write corrected version
```

### For Pattern Claims

Example: "uses singleton pattern"

- Verify with `find_symbol` or `read_file`
- Include `file:line` evidence
- Only write if independently confirmed

**ONLY write verified information to memory.** This prevents memory corruption that can mislead future sessions.

---

## Step 2: Write New Learnings

```
write_memory: darwin-{feature-slug}-discovery.md
```

### Template

```markdown
# Discovery Learnings: {Feature}
## Verified: {date}

## Terminology (verified against code)
- "{term}" means {meaning} - verified at {file:line}
- {component} is called {project_name} - verified at {file:line}

## Architecture (verified against code)
- {pattern} is used for {purpose} - see {file:line}
- {module} depends on {dependencies} - traced via find_referencing_symbols

## Surface Areas (verified)
- {area}: {responsibility} - entry point at {file:line}

## Integration Points (verified)
- {component} -> {component} via {mechanism} - see {file:line}

## Gotchas (current as of {date})
- {warning} - still true, verified at {file:line}
```

### Key Requirements

1. **Every claim needs `file:line` anchor**
2. **Include verification date** (memories age)
3. **Separate verified from uncertain**
4. **Be specific** - future sessions need actionable info

---

## Step 3: Flag Uncertain Claims

If something couldn't be verified but seems likely:

```markdown
## Unverified (needs confirmation)
- {claim} - could not verify, may be stale
- {hypothesis} - based on pattern, not confirmed
```

This ensures future sessions know what's trusted vs uncertain.

---

## Memory Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature discovery | `darwin-{slug}-discovery.md` | `darwin-dark-mode-discovery.md` |
| Architecture update | `architecture` | Append to existing |
| Project conventions | `style_conventions` | Append to existing |

---

## Do NOT Write

- Unverified claims
- Speculation without evidence
- Temporary workarounds (session-specific)
- Personal preferences vs project patterns
