# TDD for Gated Operations

Detailed protocol for implementing code that depends on external conditions (config, permissions, network, environment).

---

## The Problem Pattern

Many APIs fail silently or with unhelpful errors when preconditions aren't met:

| Failure Mode | Symptom | Real Cause |
|--------------|---------|------------|
| Silent no-op | API returns undefined/null | Config not applied |
| Generic error | "Request failed" | Permission denied |
| Empty result | [] or {} returned | Query missing required scope |
| Works in dev | Passes locally, fails in CI | Environment mismatch |
| Swallowed exception | No error, but feature broken | Try/catch hiding real issue |

**These failures are HARD TO DEBUG** because the error doesn't surface the root cause.

---

## The Solution: Error-Surfacing Test FIRST

Before writing the happy-path test, write a test that will **surface the actual error** if preconditions fail.

### Pattern: Wrap Gated Operations

```typescript
// Pattern: Wrap gated operations to surface failures
async function safeGatedOperation() {
  try {
    return await gatewayAPI();
  } catch (error) {
    console.error('Gated operation failed:', error);
    console.error('Stack:', error.stack);
    throw error;  // Re-throw so test fails with ACTUAL error
  }
}
```

```python
# Python equivalent
async def safe_gated_operation():
    try:
        return await gateway_api()
    except Exception as error:
        print(f"Gated operation failed: {error}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise so test fails with ACTUAL error
```

### Why This Works

1. **Without wrapper**: Test fails with generic assertion error
2. **With wrapper**: Test fails AND logs the ACTUAL error (config missing, permission denied, etc.)

---

## TDD Sequence for Gated Code

### 1. RED (Error Surfacing)

```typescript
// test/theme.test.ts
describe('Theme persistence', () => {
  it('should save theme to localStorage', async () => {
    // Wrap in error-surfacing handler
    try {
      const result = await saveThemePreference('dark');
      expect(result).toBe(true);
    } catch (error) {
      console.error('Theme save failed - check localStorage availability');
      console.error('Error:', error);
      throw error;
    }
  });
});
```

**Run test**: If precondition is wrong, you see WHY in the output.

### 2. GREEN (Fix Preconditions)

If test revealed config/permission issue:
1. Fix the precondition (add config, grant permission, etc.)
2. Implement the actual feature logic
3. Test passes with correct preconditions

### 3. REFACTOR

- Keep error surfacing in place (it's observability, not debug code)
- Clean up implementation
- Consider promoting error surfacing to production logging

---

## Common Gated Operations

| Operation Type | Common Preconditions | Error Surfacing Strategy |
|----------------|---------------------|-------------------------|
| localStorage | Browser context, not SSR | Check `typeof window !== 'undefined'` |
| fetch/API calls | Network available, CORS configured | Log response status + body |
| File system | Path exists, permissions | Log ENOENT/EACCES specifically |
| Environment vars | Variable defined | Log which var is missing |
| Database | Connection string, schema | Log connection error details |
| Auth tokens | Token valid, not expired | Log token decode error |

---

## H-CFG Hazard Mitigation

For any H-CFG (configuration hazard) in the spec:

### Mitigation Table Template

| H-ID | Operation | Precondition | Error Surfacing | Test File |
|------|-----------|--------------|-----------------|-----------|
| H-CFG-01 | localStorage.setItem | Browser context | try/catch with console.error | theme.test.ts:15 |
| H-CFG-02 | API.fetchUser | Auth token valid | Log response.status + body | user.test.ts:42 |
| H-CFG-03 | fs.readFile | File exists | Log ENOENT with path | config.test.ts:8 |

### Rule

**No gated operation without error surfacing wrapper.**

If you find yourself writing code that calls an external API, permission-gated feature, or environment-dependent operation:

1. STOP
2. Write error-surfacing test FIRST
3. Verify test fails correctly if precondition is missing
4. Then implement

---

## Error Surfacing vs Production Logging

| Phase | Error Surfacing | Production Logging |
|-------|-----------------|-------------------|
| Test | console.error + throw | N/A |
| Dev | console.error + throw | logger.error + throw |
| Prod | N/A | logger.error + graceful fallback |

**Error surfacing is for debugging during development.** In production, you may want graceful degradation instead of throwing.

---

## Integration with Ledger

Document in ledger under Current Task Details:

```markdown
**Gated Operations**:
- localStorage.setItem: Error surfacing at theme.test.ts:15
- H-CFG-01 mitigation: try/catch at useTheme.ts:34

**Precondition Verification**:
- localStorage available: Verified in browser context
- SSR check added: typeof window !== 'undefined' at useTheme.ts:12
```
