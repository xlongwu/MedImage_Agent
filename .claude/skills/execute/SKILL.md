---
name: execute
description: Execute ledger tasks using TDD discipline with Ralph-style loop. Iterate each task until DoD passes, then proceed batch by batch.
disable-model-invocation: false
skills:
  - superpowers:test-driven-development
  - superpowers:verification-before-completion
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__plugin_serena_serena__*, mcp__plugin_context7_context7__*
---

# DARWIN Execute

## Core Principle: TDD Until DoD Passes

**Each task is a TDD loop.** You iterate on a task until its Definition of Done (DoD) verification passes. Only then do you check the box and move to the next task.

This is NOT "implement once and hope" - this is disciplined iteration until perfection.

---

## How This Works

```
1. Read ledger.md and learnings.md
2. Find current batch, find first unchecked task `- [ ]`
3. TDD LOOP for this task:
   a. Write/verify test exists for DoD
   b. Implement the task
   c. Run verification command
   d. If FAIL → analyze, fix, goto (b)
   e. If PASS → check box, log learning
4. Repeat for all tasks in batch
5. Verify batch gate
6. Proceed to next batch (or complete)
```

**Completion promise**: `<promise>ALL_BATCHES_COMPLETE</promise>`

**Key insight**: You iterate internally until DoD passes. No external feedback loop needed - TDD discipline handles failures at the task level.

---

## Boot Sequence

1. **Locate run state**
   ```
   Read: docs/darwin/_meta/latest-run.json
   Extract: run_id, run_dir
   ```

2. **Load execution files**
   ```
   Read: {run_dir}/execute/ledger.md
   Read: {run_dir}/execute/learnings.md
   ```

3. **Find current position**
   - Parse YAML frontmatter for `current_batch`
   - Find first unchecked `- [ ]` in that batch
   - If batch complete, check batch gate

4. **Check for relevant learnings**
   - Scan learnings for current task ID
   - Note any failures or patterns

---

## Task Execution Protocol

For each unchecked task `- [ ] **T{X}.{Y}: {Title}**`:

### 1. Read Task Details

Extract from ledger:
- **Objective** - What this task achieves (context)
- **DoD** - Definition of Done (your success criteria, may be multi-line)
- **Evidence** - Patterns/examples from codebase exploration (implementation hints)
- **Verify** - Command that proves DoD is met
- **Mitigates** - Hazard IDs this task addresses
- **Mitigation** - How to address the hazards (implementation guidance)

**Use these fields BEFORE implementing:**
- Evidence shows existing patterns to follow
- Mitigation tells you HOW to address the risks
- Objective clarifies intent when DoD is ambiguous

**If Mitigates contains H-CFG**: Read `reference/tdd-gated-operations.md` and apply error-surfacing test pattern before TDD loop.

### 2. TDD Loop (Iterate Until DoD Passes)

```
attempt = 0
while True:
    attempt += 1

    # Step A: Ensure test exists
    If DoD requires behavior, verify test exists or write one

    # Step B: Implement
    Create or modify the specified file
    Follow DoD criteria exactly
    If task mitigates a hazard, ensure mitigation is present

    # Step C: Run Verification
    Run the Verify command from ledger

    # Step D: Check result
    if verification PASSES:
        break  # Exit loop, proceed to check box

    if attempt >= 3:
        Log: [T{X}.{Y}] STUCK after 3 attempts
        Check if spec is unclear
        If truly stuck: output <promise>BLOCKED_ON_T{X}.{Y}</promise>
        break

    # Step E: Analyze and fix
    Log: [T{X}.{Y}] FAILED attempt {attempt}: {reason}
    Diagnose: What went wrong?
    Fix: Adjust implementation
    # Loop back to Step B
```

**Critical**: Do NOT check the box until verification PASSES. The TDD loop ensures you iterate until DoD is achieved.

### 3. Check the Box (Only After Verification Passes)

Edit ledger.md: change `- [ ]` to `- [x]` for this task

### 4. Append Learning

Document what you learned:
```
[T{X}.{Y}] {Brief learning - especially if you had to iterate}
```

---

## Batch Gate Protocol

When all tasks in a batch are checked:

### 1. Verify Gate Conditions
Run each command in the batch gate:
```bash
tsc --noEmit           # Must exit 0
npm test -- --testPathPattern="{pattern}"  # Must pass
```

### 2. Check Gate Boxes
Edit ledger.md: check all gate conditions

### 3. Log Batch Completion
Append to learnings:
```
[B{N}-GATE] Batch {N} complete. {X}/{X} tasks, tests pass.
```

### 4. Update Frontmatter
Edit `current_batch: {N}` to `current_batch: {N+1}`

### 5. Proceed or Complete
- If more batches: continue to next batch
- If all batches done: proceed to Final Gate

---

## Final Gate Protocol

When all batches complete:

### 1. Run Final Checks
```bash
npm test              # Full test suite
tsc --noEmit          # All types
npm run lint          # If available
```

### 2. Check Final Gate Boxes
Edit ledger.md: check all final gate conditions

### 3. Update Status
Edit frontmatter: `status: "COMPLETE"`

### 4. Output Completion Promise
```
<promise>ALL_BATCHES_COMPLETE</promise>
```

The Stop hook will verify and allow exit.

---

## Failure Handling

### Task Verification Fails (Handled by TDD Loop)

Failures are handled INSIDE the TDD loop for each task:
1. **Do NOT check the box** - loop continues
2. **Investigate**: What's wrong? Use systematic-debugging discipline
3. **Fix**: Adjust implementation based on diagnosis
4. **Re-verify**: Run verification again (loop iteration)
5. **Log each attempt**: `[T{X}.{Y}] FAILED attempt {N}: {reason}`
6. **After success, log resolution**: `[T{X}.{Y}] RESOLVED: {what fixed it}`

The TDD loop ensures you CANNOT proceed until DoD passes.

### Batch Gate Fails

1. **Identify failing condition** - which gate check failed?
2. **Find root cause** - which task's code is broken?
3. **Fix the task** - may need to uncheck box, re-enter TDD loop
4. **Re-run gate checks**

### Stuck > 5 Attempts (Escalation)

If the TDD loop hits 5 attempts without progress:
1. Log pattern in learnings: `[T{X}.{Y}] STUCK: {pattern observed}`
2. Check if spec is unclear or DoD is impossible
3. Output: `<promise>BLOCKED_ON_T{X}.{Y}</promise>`
   - Stop hook will escalate to user
   - User intervention required to clarify spec or adjust DoD

---

## Learnings Protocol

### Read at Boot
Scan for:
- Failures on tasks you're about to do
- Patterns in current module/batch
- Project conventions

### Write Sparingly
Only add when:
- You discover non-obvious pattern
- You fix a failure (document cause)
- Batch gate passes

### Format
```
[T{batch}.{num}] Brief description
[B{N}-GATE] Batch {N} complete. X/X tasks.
```

### Trimming Priority

When removing oldest entry to make room (>50 entries):
- If oldest is a task learning `[T{X}.{Y}]`, remove it
- If oldest is a batch gate `[B{N}-GATE]`, check second-oldest
  - If second-oldest is a task learning, remove that instead (preserve gate)
  - If all gates, remove oldest gate

---

## File Editing Rules

### Checking Boxes
Use exact replacement:
```
Old: - [ ] **T1.3: Create config types**
New: - [x] **T1.3: Create config types**
```

### Updating Frontmatter
```yaml
# Before
current_batch: 1

# After
current_batch: 2
```

### Appending Learnings
Add to end of Log section, before any closing markers.

---

## Red Flags (STOP)

- Checking box BEFORE verification passes
- Skipping tasks within a batch
- Proceeding to next batch without gate verification
- Ignoring failures (must log and fix)
- Modifying spec or ledger structure
- Claiming completion without Final Gate

---

## Integration Points

### Serena (Optional)
Use for semantic verification:
- `find_symbol` - Verify exports exist
- `find_referencing_symbols` - Check integration

### Context7 (When Needed)
If task involves external APIs:
- Verify API signatures before implementing
- Document in learnings if API differs from expected

---

## Stop Hook Behavior

The `darwin-execute-stop.sh` hook:

1. **Checks for completion promise**
   - `ALL_BATCHES_COMPLETE` → verifies ledger, allows exit
   - `BLOCKED_ON_T{X}.{Y}` → escalates to user, allows exit

2. **Counts unchecked tasks in current batch**
   - If unchecked remain → blocks exit, continues loop

3. **Verifies batch gate**
   - If gate not checked → blocks exit

You cannot exit until:
- All tasks checked AND batch gate verified, OR
- You output a valid promise

---

## Example Session

```
[Boot]
Read ledger.md: Batch 2, current_batch=2
Read learnings.md: [T2.1] DomainEvent needs protected constructor
Find first unchecked: T2.3: Create Job Events

[Execute T2.3]
Read DoD: Exports JobCreatedEvent, JobStartedEvent, JobCompletedEvent
Implement: Create src/domain/events/job-events.ts
Run verify: grep -E "export.*(class) Job(Created|Started|Completed)Event" src/domain/events/job-events.ts
Output: export class JobCreatedEvent... (3 matches)
Check box: - [x] **T2.3: Create Job Events**

[Continue to T2.4, T2.5...]

[Batch 2 Gate]
Run: tsc --noEmit → exits 0
Run: npm test -- --testPathPattern="domain" → PASS
Check gate boxes
Append: [B2-GATE] Batch 2 complete. 8/8 tasks, tests pass.
Update: current_batch: 3

[Continue batches...]

[Final Gate]
Run: npm test → PASS
Run: tsc --noEmit → exits 0
Check final gate boxes
Update: status: "COMPLETE"
Output: <promise>ALL_BATCHES_COMPLETE</promise>

[Exit allowed by Stop hook]
```
