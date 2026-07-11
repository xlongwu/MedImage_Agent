# API Service Specification

This document defines the MVP FastAPI service for MedImage Agent.

## Goals

Expose existing deterministic CLI/runtime capabilities through HTTP APIs.

The API is intended for a future visual frontend.

## Scope

Supported in MVP:

- health check
- project config inspection
- pipeline listing
- pipeline detail reading
- agent plan creation
- approved agent execution
- agent run summary reading
- dataset evaluation report reading
- safe file reading from allowlisted folders

Unsupported in MVP:

- authentication
- multi-user accounts
- database
- async job queue
- WebSocket streaming
- real LLM calls
- UI
- GPU scheduling
- DPABI pipeline
- production deployment

## Safety Rules

- API must not delete files.
- API must not modify rawdata.
- API must not modify SPM or DPABI source.
- API must not allow arbitrary path traversal.
- API execution requires approved=true.
- API file reading is limited to allowlisted folders.

## Allowlisted Read Folders

```text
examples/
work/
logs/
reports/
memory/
specs/
```

## Endpoints

### GET /health

Returns service status.

### GET /api/project-config

Reads the default project config.

### GET /api/pipelines

Lists YAML files in examples/.

### GET /api/pipelines/{pipeline_name}

Reads and validates a pipeline YAML.

### POST /api/agent/plan

Creates a plan.

### POST /api/agent/execute

Executes an approved plan.

Requires:

```json
{
  "approved": true
}
```

### GET /api/agent-runs/{agent_run_id}

Reads plan, agent_summary, review_summary, and proposed_memory_patch if they exist.

### GET /api/reports/dataset-evaluation

Reads dataset evaluation outputs if they exist.

### GET /api/files/read?path=...

Reads a safe text file from an allowlisted folder.
