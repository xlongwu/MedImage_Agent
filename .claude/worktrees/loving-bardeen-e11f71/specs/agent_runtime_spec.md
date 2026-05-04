# Agent Runtime Specification

This document defines the MVP Agent Runtime for MedImage Agent.

## Design Inspiration

The MVP runtime borrows two architecture ideas:

1. **Claude Code-like execution control**:
   - Tool-use loop
   - Plan Mode before Execute Mode
   - Tool permission metadata
   - Hooks before and after tool execution

2. **Hermes-like long-running agent foundation**:
   - Agent specs
   - Memory-ready structure
   - Background review-ready structure
   - Skill-ready structure

## Scope

The MVP supports:

- deterministic orchestrator agent
- plan generation
- explicit approval before execution
- tool registry
- tool permission registry
- hook manager
- pipeline execution as a tool
- agent run summary

The MVP does not support:

- real LLM API
- autonomous tool selection
- natural language planning
- multi-agent communication
- UI
- database
- background review
- memory mutation
- GPU execution
- parallel execution

## Modes

### Plan Mode

Plan Mode is read-only.

Allowed actions:

- read project config
- read pipeline YAML
- validate pipeline
- inspect expected outputs
- estimate affected paths
- generate plan.json

Forbidden actions:

- run MATLAB
- write derivatives
- run pipeline
- delete files
- overwrite outputs

### Execute Mode

Execute Mode can run the approved plan.

Requirements:

- an existing plan.json
- approval flag set to true
- tool permissions checked
- pre-run hooks passed
- post-run hooks executed

## Agent Run Outputs

```text
work/agent_runs/{agent_run_id}/plan.json
work/agent_runs/{agent_run_id}/agent_summary.json
```

## Safety Rules

- Never execute a pipeline without explicit approval.
- Never modify rawdata.
- Never delete files.
- Never overwrite derivatives unless explicitly configured.
- Always write logs and summaries.
- Always preserve the original pipeline summary.
