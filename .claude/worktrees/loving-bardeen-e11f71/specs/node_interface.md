# Node Interface

A pipeline node is the smallest executable unit in MedImage Agent.

## Responsibilities

Each node must:

1. Receive structured inputs and parameters.
2. Execute one clearly scoped operation.
3. Write outputs to work/, logs/, derivatives/, or reports/.
4. Write a node result JSON.
5. Write a node state JSON.
6. Preserve stdout and stderr logs.
7. Never modify rawdata/.
8. Never modify third_party/.

## Minimal Node Result

```json
{
  "ok": true,
  "node_id": "spm_smoke_test",
  "backend": "matlab-spm",
  "outputs": [
    "work/spm_smoke_test/smoothed.nii"
  ],
  "metrics": {},
  "errors": []
}
```

## Minimal Node State

```json
{
  "run_id": "run_001",
  "subject": "project",
  "node": "spm_smoke_test",
  "status": "SUCCESS",
  "started_at": "2026-05-01T10:00:00",
  "ended_at": "2026-05-01T10:01:00",
  "log_path": "logs/spm_smoke_test_stdout.log",
  "outputs": [
    "work/spm_smoke_test/result.json",
    "work/spm_smoke_test/smoothed.nii"
  ],
  "errors": []
}
```

## Rules

- A node with missing required outputs must be FAILED.
- A node with MATLAB return code != 0 must be FAILED.
- A node that produces expected outputs and valid result JSON can be SUCCESS.
- A node must not silently succeed.
