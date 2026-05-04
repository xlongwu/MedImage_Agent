# Learnings File Format

Template for `{run_dir}/execute/learnings.md`.

---

## Purpose

Persist critical discoveries and failures across fresh agent invocations.
Each agent reads this at boot and appends ONE learning (if significant).

**Rules**:
- Append-only during execution
- Maximum 50 entries
- When exceeded, remove oldest entry
- Include failures explicitly

---

## Initial Template

```markdown
# Execution Learnings - {Feature Name}

> Append-only log read by each fresh agent.
> Max 50 entries. Oldest removed when limit exceeded.
> Format: `[Task-ID] Learning or failure`

---

## Log

<!-- Entries added during execution -->
```

---

## Entry Format

```
[T{batch}.{num}] {Brief learning or failure description}
```

### Success Learnings

```
[T1.3] Test command: npm test -- --testPathPattern={file}
[T2.1] EventStore requires await initialize() before use
[T2.4] PriorityQueue uses min-heap (lower number = higher priority)
[T3.2] Circuit breaker halfOpenLimit is constructor param, not setter
```

### Failure Entries

```
[T2.3] FAILED: Assumed max-heap, actually min-heap
[T2.3] RETRY: Fixed comparison, tests pass now
[T3.5] FAILED: Missing async/await on enqueue
[T3.5] RETRY: Added await, TypeError resolved
```

### Batch Gate Entries

```
[B1-GATE] Batch 1 complete. 5/5 tasks, tsc passes, tests pass.
[B2-GATE] Batch 2 complete. 8/8 tasks, all verified.
```

---

## When to Add Entry

**ADD** an entry when:
- You discover a non-obvious pattern
- A test command differs from expected
- You fix a failure (document what was wrong)
- A batch gate passes
- You find a project-specific convention

**DON'T ADD** for:
- Routine task completion
- Obvious operations
- Redundant information already in log

---

## Reading Protocol (Boot Sequence)

Each fresh agent should:

1. Read learnings file
2. Scan for failures on current/upcoming tasks
3. Note any patterns relevant to current work
4. Proceed with awareness of past discoveries

---

## Writing Protocol

After task completion:

1. Did you discover something non-obvious? If no, skip.
2. Is it already in learnings? If yes, skip.
3. If adding: append ONE line in format `[T{id}] {learning}`
4. If file exceeds 50 entries: remove oldest (top) entry

---

## Example Complete File

```markdown
# Execution Learnings - Task Queue System

> Append-only log read by each fresh agent.
> Max 50 entries. Oldest removed when limit exceeded.
> Format: `[Task-ID] Learning or failure`

---

## Log

[T1.2] Branded types need `as const` for literal inference
[T1.5] Barrel exports must use `export * from` not `export { }`
[B1-GATE] Batch 1 complete. 5/5 tasks, tsc passes.
[T2.1] DomainEvent needs protected constructor for inheritance
[T2.3] FAILED: Forgot to make Event.version readonly
[T2.3] RETRY: Added readonly modifier, tests pass
[T2.4] Job state machine: PENDING -> SCHEDULED requires explicit transition
[B2-GATE] Batch 2 complete. 8/8 tasks, domain tests pass.
[T3.1] EventStore.append() is async - always await
[T3.3] FAILED: Heap comparison was inverted (max vs min)
[T3.3] RETRY: Fixed to min-heap, priority ordering correct
[T3.5] DeadLetterQueue needs separate storage from main queue
[B3-GATE] Batch 3 complete. 10/10 tasks, infra tests pass.
[T4.1] Command handlers receive dependencies via factory
[T4.5] FAILED: Query handler was mutating state
```

---

## Maintenance

### Trimming Old Entries

When adding entry #51:
1. Count existing entries after `## Log`
2. Remove oldest entry (first after `## Log`)
3. Append new entry

Max 50 entries maintained.

---

## Integration with Execute

The Execute skill references learnings at:
1. Boot (read full file)
2. Task start (check for failures on this task)
3. Task end (optionally append learning)
4. Batch gate (append gate entry)
