# Keyword Generation Example

Demonstrates intelligent keyword generation using Serena memory + feature request.

---

## Feature Request

> "Add dark mode toggle"

---

## Memory Context (Assumed)

From Serena memory consulted:

```markdown
# From architecture memory:
- "Project uses 'appearance' not 'theme' in settings"
- "All UI state flows through AppContext"

# From style_conventions memory:
- "CSS uses design tokens in tokens.css"
- "Color variables follow --color-{semantic}-{variant} pattern"

# From project_overview memory:
- "Settings stored in localStorage under 'user-prefs'"
```

---

## Generated Keywords

| Type | Keywords | Source | Rationale |
|------|----------|--------|-----------|
| **Literal** | dark, mode, toggle | Feature request | Direct terms from the request |
| **Project Terms** | appearance, AppContext, tokens | Serena memory | Project-specific terminology |
| **Synonyms** | light, color, palette, style, scheme | Domain knowledge | Related concepts |
| **Anti-seeds** | invalid, error, fallback, unsupported | Standard | Edge cases and error handling |
| **Framework** | useContext, useState, localStorage | Memory + deps | React patterns, storage |
| **Integration** | settings, preferences, UserConfig, user-prefs | Serena memory | Related modules and storage keys |

---

## Search Strategy Generated

```markdown
### Phase 1: Memory-informed searches (higher confidence)
1. Search "appearance" (memory says this is the term used)
2. Search "AppContext" (memory says state flows through here)
3. Search "tokens" (memory says CSS uses design tokens)

### Phase 2: Literal feature terms
4. Search "dark"
5. Search "mode"
6. Search "toggle"

### Phase 3: Framework patterns
7. Search "useContext.*theme" or "useContext.*appearance"
8. Search "localStorage.*pref"

### Phase 4: Integration points
9. Search "settings"
10. Search "UserConfig"

### Phase 5: Anti-seeds (edge cases)
11. Search "fallback.*color" or "default.*theme"
12. Search "unsupported.*theme"
```

---

## Memory Verification Checklist

Before trusting memory, verify each claim:

| Memory Claim | Verification Method | Status |
|--------------|---------------------|--------|
| Uses "appearance" not "theme" | `grep -r "appearance" src/` | PENDING |
| State flows through AppContext | `find_symbol AppContext` | PENDING |
| Design tokens in tokens.css | `ls src/**/tokens.css` | PENDING |
| Colors use --color-{semantic}-{variant} | Read tokens.css | PENDING |
| Settings in localStorage user-prefs | `grep "user-prefs" src/` | PENDING |

---

## No Memory Example

If no relevant memories exist:

| Type | Keywords | Source |
|------|----------|--------|
| Literal | dark, mode, toggle | Feature request |
| Synonyms | light, color, palette, style, theme | Domain knowledge |
| Anti-seeds | invalid, error, fallback, default | Standard |
| Framework | useState, useEffect, localStorage, CSS | Common patterns |
| Integration | settings, preferences, config | Generic |

**Note**: Without memory, more generic terms are used. Flag "Project terminology unknown" as a risk in discovery report.

---

## Output

The final keyword list for Phase 3 searches:

```
dark, mode, toggle, appearance, AppContext, tokens,
light, color, palette, style, scheme, useContext,
useState, localStorage, settings, preferences,
UserConfig, user-prefs, invalid, error, fallback,
unsupported, default
```

Total: 22 keywords (7-12 recommended, but memory expanded the list)
