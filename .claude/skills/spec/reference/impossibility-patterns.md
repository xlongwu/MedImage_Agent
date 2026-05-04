# Impossibility Pattern Library

## Purpose

Detect mutually exclusive requirements BEFORE worker dispatch. When both columns of a pattern match the feature request, flag for user resolution.

---

## Pattern Categories

### PHYS: Data Persistence vs Volatility

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| PHYS-001 | "zero data loss", "no data loss", "persist all", "durable" | "in-memory only", "memory-only", "no persistence", "ephemeral storage" | CRITICAL | Choose: persistence layer OR accept data loss |
| PHYS-002 | "survive restart", "crash-safe", "fault-tolerant" | "stateless", "no state", "ephemeral" | CRITICAL | Choose: state persistence OR stateless design |
| PHYS-003 | "offline-first", "work offline" | "real-time sync", "always connected", "live updates required" | HIGH | Choose: offline capability OR require connection |

### CS: CAP Theorem & Distributed Systems

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| CS-001 | "always consistent", "strong consistency", "ACID" | "always available", "100% uptime", "never fail" | CRITICAL | CAP theorem: Choose consistency OR availability during partition |
| CS-002 | "exactly-once delivery", "exactly once" | "at-least-once", "retry on failure" (without dedup) | HIGH | Need idempotency/deduplication for exactly-once with retries |
| CS-003 | "globally ordered", "total ordering" | "low latency", "sub-10ms", "real-time" | HIGH | Global ordering adds latency; choose one priority |

### SEM: Semantic Contradictions

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| SEM-001 | "stateless", "no server state" | "remember", "persist preferences", "save session" | CRITICAL | Stateless cannot remember; need client-side or external storage |
| SEM-002 | "immutable", "never change" | "update", "modify", "edit" | HIGH | Immutable data cannot be updated; use versioning or replacement |
| SEM-003 | "synchronous", "blocking", "wait for result" | "non-blocking", "async-first", "fire-and-forget" | MEDIUM | Choose execution model |

### PERF: Performance Trade-offs

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| PERF-001 | "real-time", "sub-100ms", "instant" | "comprehensive validation", "full audit", "deep analysis" | HIGH | Thorough validation takes time; define acceptable latency |
| PERF-002 | "unlimited scale", "infinite users" | "single instance", "no horizontal scaling", "monolith" | HIGH | Unlimited scale requires distribution |
| PERF-003 | "minimal memory", "low footprint" | "cache everything", "preload all", "keep in memory" | MEDIUM | Memory constraints conflict with aggressive caching |

### SEC: Security vs Accessibility

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| SEC-001 | "public API", "open access", "no auth required" | "secure", "authenticated only", "authorized users" | HIGH | Define which endpoints need auth vs public |
| SEC-002 | "zero trust", "verify everything" | "trusted internal", "skip validation internally" | HIGH | Choose trust boundary model |
| SEC-003 | "anonymous", "no tracking", "privacy-first" | "personalized", "user history", "recommendations" | MEDIUM | Personalization requires some user data |

### RES: Resource Constraints

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| RES-001 | "never delete", "keep forever", "full history" | "limited storage", "quota", "bounded" | HIGH | Infinite retention requires infinite storage |
| RES-002 | "no external dependencies", "self-contained" | "use {specific service}", "integrate with {API}" | MEDIUM | External service is a dependency |
| RES-003 | "browser-only", "client-side only" | "server processing", "backend required" | MEDIUM | Some operations require server |

### IMPL: Implementation Conflicts

| ID | Pattern A | Pattern B | Severity | Resolution |
|----|-----------|-----------|----------|------------|
| IMPL-001 | "backwards compatible", "no breaking changes" | "complete redesign", "greenfield", "start fresh" | HIGH | Compatibility constrains redesign |
| IMPL-002 | "single file", "no new files" | "modular", "separate concerns", "microservices" | MEDIUM | Modularity requires multiple files |
| IMPL-003 | "no new dependencies", "vendored only" | "use {library}", "integrate {framework}" | MEDIUM | New library is a dependency |

---

## Pattern Maintenance

### Adding New Patterns

When a new impossibility is discovered during a DARWIN run:

1. Document the contradiction in `learnings.md`
2. Extract the keyword patterns
3. Add to appropriate category above
4. Assign severity based on:
   - CRITICAL: Fundamentally impossible (laws of physics/CS)
   - HIGH: Requires significant architectural change
   - MEDIUM: Trade-off, may be acceptable with compromise

### Pattern Quality Criteria

Good patterns are:
- **Falsifiable**: Clear when they match vs don't match
- **Actionable**: Resolution path is clear
- **Evidence-based**: Derived from actual failures

Avoid patterns that are:
- Too broad (match everything)
- Too specific (match only one case)
- Subjective (depend on interpretation)
