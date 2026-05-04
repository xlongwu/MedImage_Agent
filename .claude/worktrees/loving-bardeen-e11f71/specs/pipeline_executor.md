# Pipeline Executor

The pipeline executor runs a YAML-defined pipeline.

## Scope

The MVP executor supports:

- sequential execution
- dependency validation
- stop on failure
- node registry
- node state writing
- pipeline summary writing

It does not support:

- parallel execution
- scheduling
- GPU resource allocation
- UI
- database
- real medical image preprocessing

## Execution Rules

1. Load project_config.yaml.
2. Load pipeline YAML.
3. Validate required pipeline fields.
4. Validate all node IDs are unique.
5. Validate dependencies refer to existing node IDs.
6. Execute nodes in YAML order.
7. A node can run only if all dependencies are SUCCESS.
8. If a node fails and stop_on_failure=true, stop the pipeline.
9. Write node state for every attempted node.
10. Write pipeline summary JSON at the end.

## Pipeline Status

- SUCCESS: all nodes succeeded
- FAILED: at least one node failed
- PARTIAL: pipeline stopped after some nodes succeeded and one failed
- INVALID: pipeline YAML is invalid

## Summary Output

```json
{
  "run_id": "run_mvp_001",
  "pipeline_id": "medimage_mvp_pipeline",
  "status": "SUCCESS",
  "nodes_total": 2,
  "nodes_success": 2,
  "nodes_failed": 0,
  "node_states": [
    "work/states/run_mvp_001/environment_check.json",
    "work/states/run_mvp_001/spm_smoke_test.json"
  ],
  "errors": []
}
```
