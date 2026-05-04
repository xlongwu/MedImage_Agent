# Context Requirements

Reference for understanding when to use Skills (shared context) vs Agents (fresh context).

---

## Skill vs Agent Decision Table

| Phase | Type | Context | Dispatch Method |
|-------|------|---------|-----------------|
| Discover | Skill | Main (shared) | Skill tool → `Darwin:discover` |
| Explore | Skill | Main (shared) | Skill tool → `Darwin:explore` |
| Plan | Skill | Main (shared) | Skill tool → `Darwin:plan` |
| **Skeptic** | **Subagent** | **Fresh** | Task tool → `darwin-skeptic` agent |
| **Revise** | **Subagent** | **Fresh** | Task tool → `darwin-revise` agent |
| **Worker** | **Subagent** | **Fresh** | Task tool → `darwin-worker` agent |
| **Consolidator** | **Subagent** | **Fresh** | Task tool → `darwin-consolidator` agent |
| Execute | Skill | Main (shared) | Skill tool → `Darwin:execute` |

---

## Why Fresh Context Matters

### Skeptic Isolation
- **Cannot be biased** by seeing how the plan was reasoned
- Sees only: plan.md + explore.md + source code
- Does NOT see: Worker's discovery notes, reasoning process, intermediate findings

### Revise Independence
- **Must independently verify** (cannot trust skeptic's search results)
- Sees only: critique-{N}.md + plan.md + source code
- Does NOT see: Skeptic's reasoning process, Skeptic's tool output

### Worker Stochastic Independence
- **Cannot see other workers' work** (prevents convergence bias)
- Each worker has: Different keywords, entry points, lenses
- Produces: Diverse perspectives that consolidator synthesizes

---

## Shared Context (Skills) - When It's OK

Use **Skill tool** when:
- Sequential phases that build on each other (D→E→P)
- Accumulated findings improve next phase
- No adversarial relationship needed
- Same perspective is acceptable

Examples:
- Discover → Explore (exploration builds on discovery)
- Plan → Execute (execution follows plan)

---

## Fresh Context (Agents) - When Required

Use **Task tool** when:
- Adversarial validation needed
- Independent verification required
- Multiple parallel perspectives wanted
- Bias from previous phases would be harmful

Examples:
- Skeptic (must not see how plan was created)
- Revise (must not trust skeptic's searches)
- Workers (must not see each other's findings)

---

## Integration Points

- **Serena**: Use for initial scope detection (`find_symbol`, `search_for_pattern`)
- **Context7**: Query relevant documentation for the feature domain
- **Custom Subagents**: In agents/ directory for fresh-context phases
