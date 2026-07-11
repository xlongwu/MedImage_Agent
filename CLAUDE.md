# CLAUDE.md

Claude Code users must read `AGENTS.md` first. `AGENTS.md` is the
authoritative repository rulebook for architecture, safety, Git, validation,
and documentation lifecycle. If this file conflicts with `AGENTS.md`,
`AGENTS.md` wins.

## Claude Code Workflow Notes

- Start by reading the target files and the relevant anchors named in the task.
- For multi-file work, present a short plan before editing when the human has
  not already provided an execution plan.
- Keep edits limited to the files required by the current task.
- Do not work concurrently with another agent on the same task unless the human
  explicitly coordinates ownership.
- Use `docs/临时任务/` only as temporary handoff space. Completed handoffs should
  be removed after durable information is migrated to the correct long-term
  document.

For architecture rules, safety boundaries, test commands, frontend validation,
and completion reporting, follow `AGENTS.md`. This file does not duplicate
those rules.
