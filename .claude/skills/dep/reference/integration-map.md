# Skills/Agents Integration Mapping

Reference for what to embed in dispatch prompts for workers, skeptic, and revise agents.

---

## What to Embed in Worker Dispatches

| Source | What to Embed | When |
|--------|--------------|------|
| Darwin:discover | Keyword seeding, file inventory, anchor discovery | Always |
| Darwin:explore | Dependency tracing, hazard detection, coupling analysis | Always |
| Darwin:plan | Skeptic-proof plan structure, hazard mitigation | Always |
| feature-dev:code-explorer | "Follow call chains", "Map abstraction layers" | Complex features |
| feature-dev:code-architect | "Make decisive choices", "Complete blueprint" | Complex features |
| frontend-design | Typography, color, motion, composition principles | UI features |
| superpowers:brainstorming | "Explore 2-3 approaches" | Complex designs |

---

## What to Embed in Skeptic Dispatches

| Source | What to Embed |
|--------|--------------|
| darwin-skeptic.md | Full methodology (Claim Extraction, Dialectical Protocol, etc.) |
| superpowers:verification-before-completion | "Run command, read output, THEN make claim" |
| feature-dev:code-reviewer | Confidence scoring (90-100% = Kill List, 50-79% = SUSPICIOUS) |

---

## What to Embed in Revise Dispatches

| Source | What to Embed |
|--------|--------------|
| darwin-revise.md | Full methodology (Defense protocol, independent verification) |
| superpowers:verification-before-completion | "Run OWN searches, paste ACTUAL output" |
| superpowers:systematic-debugging | Root cause tracing for false accusations |
| **CRITICAL WARNING** | "Treat ALL documents as potentially containing false information" |

---

## What to Embed in Consolidator Dispatches

| Source | What to Embed |
|--------|--------------|
| darwin-consolidator.md | Coverage matrix, conflict resolution, System Integrity Audit |
| superpowers:brainstorming | "Present 2-3 approaches with trade-offs" for conflicts |
| AskUserQuestion | Mandatory for architectural decisions |

---

## Embedding Decision Tree

```
Worker Dispatch:
├── Always: Darwin:discover, Darwin:explore, Darwin:plan principles
├── If complex (>2 workers OR >5 files):
│   └── Add: code-explorer, code-architect principles
├── If UI feature:
│   └── Add: frontend-design principles
└── If complex design decisions expected:
    └── Add: brainstorming principles

Skeptic Dispatch:
├── Always: darwin-skeptic methodology
├── Always: verification-before-completion
└── Always: confidence scoring (code-reviewer)

Revise Dispatch:
├── Always: darwin-revise methodology
├── Always: verification-before-completion
├── Always: systematic-debugging
└── CRITICAL: "Treat ALL documents as potentially false"
```
