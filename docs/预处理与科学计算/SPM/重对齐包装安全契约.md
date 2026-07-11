# SPM Realign Wrapper Safety Contract

**Status:** Contract design only — NOT IMPLEMENTED.
**Version:** v1.0-draft
**Date:** 2026-06-18

---

## 1. Scope

This document defines the **future** safety and implementation contract for an
SPM realignment wrapper node (`spm_realign_subject`).  No real MATLAB/SPM
execution is implemented in the current release (`v0.3.0-rc1`).  All sections
below describe a contract to be implemented in a later release.

The project remains a **research engineering tool**, not a clinical diagnostic
system.  The wrapper must:

- Never modify rawdata.
- Only write to approved derivatives/output directories under the project runtime tree.
- Require Approval Gate and persisted audit before actual execution.
- Never accept arbitrary user-supplied paths or MATLAB code.
- Never silently overwrite existing derivatives.

---

## 2. Non-Goals

This contract explicitly excludes:

- No MATLAB execution in the current release.
- No real SPM preprocessing execution.
- No DPABI execution.
- No full preprocessing pipeline (slice timing, normalization, smoothing).
- No clinical interpretation or diagnosis.
- No automatic subject exclusion based on motion metrics.
- No rawdata modification.
- No silent overwrite of existing derivative files.
- No LLM-generated MATLAB scripts.
- No user-supplied MATLAB code.

---

## 3. Future Node Identity

| Field | Value |
|---|---|
| **Node ID** | `spm_realign_subject` |
| **Backend** | `matlab-spm` |
| **Risk level** | `high` |
| **Requires approval** | `true` |
| **Executable** | `false` (until explicitly enabled) |
| **Manual required** | `true` (until env + approval gates mature) |
| **Parallel level** | `subject` |
| **Inputs** | BOLD NIfTI, optional BOLD sidecar JSON |
| **Outputs** | Realigned BOLD (`r<sub>_bold.nii`), mean/reference BOLD, motion parameter text file (`rp_*.txt`), stdout/stderr logs, provenance JSON, node state JSON |
| **Tags** | `spm`, `matlab`, `rsfmri`, `realign`, `motion` |

Current metadata in `src/backend/app/runtime/tool_catalog.py` already defines
this node with `backend: matlab-spm`, `requires_approval: True`, and
`risk_level: high`.  It is NOT in the safe execution allowlist.

---

## 4. Preconditions

Before real execution is allowed, ALL of the following must be satisfied:

1. Project exists and is persisted in the dashboard store.
2. Project context resolves (`project_config.yaml`, `rawdata_dir`).
3. A reviewed plan exists with a valid `reviewed_plan_id`.
4. The plan passes `validate_plan()` (validator).
5. The plan passes `adapt_reviewed_plan()` (adapter).
6. BOLD Reference Readiness status is not `blocked`.
7. `rawdata_dir` is confirmed read-only (`copy_mode: reference`).
8. Output root is not inside `rawdata_dir`.
9. MATLAB executable path is configured in desktop config.
10. SPM path is configured in desktop config or project config.
11. Environment health check passes.
12. Approval Gate explicitly approves `spm_realign_subject`.
13. An audit record is persisted BEFORE execution.
14. The safe allowlist in `execute_reviewed_routes.py` explicitly includes
    this node (currently it does NOT — it is blocked as SPM).
15. User has acknowledged external MATLAB/SPM execution.

---

## 5. Inputs

**Allowed inputs** (discovered, never user-supplied):

- BOLD NIfTI path: discovered from project metadata, import records, or
  dataset index path.
- BOLD sidecar JSON path: same-stem companion file.
- Subject ID / session ID: derived from BIDS folder structure.
- `project_config_path`: path to the validated project config YAML.
- Node params: from the reviewed plan dict.

**Disallowed inputs:**

- Arbitrary user-supplied absolute paths.
- Paths outside authorized project roots.
- Output paths inside `rawdata_dir`.
- Shell snippets or command strings.
- MATLAB code provided by user or LLM.
- Planner-generated commands.

---

## 6. Parameters

Future allowed parameter schema:

```json
{
  "quality": 0.9,
  "separation_mm": 4,
  "fwhm_mm": 5,
  "register_to_mean": true,
  "estimate_reslice": true,
  "interpolation": 2,
  "wrap": [0, 0, 0],
  "weight_image": null
}
```

Rules:

- All params must be validated against a strict Pydantic schema.
- Unknown params are rejected or ignored with an explicit warning.
- All params must be recorded in the provenance JSON.
- LLM/planner cannot inject arbitrary MATLAB script parameters.
- Defaults must be explicit and versioned in the node metadata.

---

## 7. Outputs

Expected output manifest for a successful realignment:

| Output | Path Pattern | Required |
|---|---|---|
| Realigned BOLD | `<derivatives>/spm_realign/<sub>/<ses>/r<sub>_bold.nii` | Yes |
| Mean / reference BOLD | `<derivatives>/spm_realign/<sub>/<ses>/mean<sub>_bold.nii` | Yes |
| Motion parameters | `<derivatives>/spm_realign/<sub>/<ses>/rp_<sub>_bold.txt` | Yes |
| Node state JSON | `<work>/states/<run_id>/<sub>/spm_realign_subject.json` | Yes |
| Stdout log | `<work>/logs/<run_id>/<sub>/spm_realign_stdout.log` | Yes |
| Stderr log | `<work>/logs/<run_id>/<sub>/spm_realign_stderr.log` | Yes |
| Provenance JSON | `<work>/states/<run_id>/<sub>/spm_realign_provenance.json` | Yes |
| QC summary placeholder | `<reports>/spm_realign/<sub>/qc_summary.json` | Future |

Rules:

- All outputs must be under `derivatives/`, `work/`, or `reports/` inside the
  project output root.
- Outputs must not overwrite existing files unless explicit overwrite approval
  is present in the approval record.
- Output manifest must include `exists`, `size_bytes`, `modified_at`, and
  `checksum` where feasible.
- Missing expected outputs should mark the node as `FAILED` with a clear error
  listing which outputs are absent.

---

## 8. Dry-Run Contract

The dry-run path (`POST /api/plans/execute-reviewed` with `dry_run: true`)
must:

- Validate inputs (BOLD path exists, sidecar readable).
- Validate output paths (not in rawdata, writable, no conflicts).
- Validate MATLAB/SPM environment availability if configured.
- Validate approval requirements.
- Validate parameter schema.
- Predict output paths as a manifest.
- Return a command preview as descriptive text only (NOT an executable shell
  command).
- NOT execute MATLAB or SPM.
- NOT create files or directories.
- NOT update run state as successful execution.

---

## 9. Execution Contract

The real execution path (`dry_run: false`) must:

1. Require `MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1`.
2. Require `confirm_execution: true`.
3. Require `persist_audit: true`.
4. Require `write_pipeline_yaml: true`.
5. Pass all preconditions (section 4).
6. Pass Approval Gate for `spm_realign_subject` specifically.
7. Create a `run_link` record BEFORE spawning MATLAB.
8. Create a node state JSON record BEFORE spawning MATLAB (status: `RUNNING`).
9. Spawn MATLAB in non-interactive mode with a pre-defined batch script.
10. Capture stdout and stderr to log files.
11. Impose a configurable timeout.
12. After MATLAB returns, verify expected outputs exist.
13. Write provenance JSON.
14. Update node state JSON with final status.
15. Update run summary and trigger artifact discovery.
16. On failure: update node state to `FAILED`, capture errors, never continue
    silently.
17. On timeout: kill MATLAB process, mark node `FAILED` with timeout error.

---

## 10. Approval Gate Requirements

The approval record for `spm_realign_subject` must include:

| Field | Description |
|---|---|
| `approved` | Must be `true` |
| `approved_by` | Non-empty identifier string |
| `approval_timestamp` | ISO-8601 timestamp |
| `node_id` | `"spm_realign_subject"` |
| `subject_scope` | List of subject IDs approved for realignment |
| `external_tool_acknowledgement` | Explicit confirmation of MATLAB/SPM execution |
| `rawdata_read_only_confirmation` | Confirmation that rawdata will not be modified |
| `output_directory_confirmation` | Confirmed output root path |
| `overwrite_policy` | Explicit policy for existing files |
| `risk_acknowledgement` | Acknowledged risk of external tool execution |
| `reviewed_plan_hash` | Hash of the reviewed plan |
| `project_id` | Current project |
| `reviewed_plan_id` | Persisted plan identity |

These fields follow the pattern established in `src/backend/app/planner/approval_gate.py`.

---

## 11. Audit Requirements

The audit record must include:

- `project_id`, `reviewed_plan_id`, `run_id`, `node_id`
- `subject_id` / `session_id` for each subject processed
- All node parameters (as applied)
- Input paths and SHA-256 checksums where feasible
- Predicted output paths (from dry-run)
- Actual output paths (after execution)
- MATLAB version string (if detectable)
- SPM version string (if detectable)
- Command template identifier (NOT raw command)
- Stdout/stderr log paths
- MATLAB return code
- Start/end timestamps
- Status (`SUCCESS`, `FAILED`, `TIMEOUT`)
- Errors and warnings

This follows the pattern in `src/backend/app/planner/audit_record.py`.

---

## 12. Environment Detection

Required environment checks (separate from execution):

- MATLAB executable path resolution (from desktop config or system PATH).
- SPM directory existence and `spm.m` verification.
- Non-interactive MATLAB invocation test (`matlab -batch "disp('ok'); exit"`).
- SPM version query via MATLAB if safe.
- Writable output root (not rawdata, not system directory).
- Rawdata read-only confirmation.

Environment detection must use existing `environment_check` node or a new
dedicated health-check endpoint.  It must never execute SPM pipelines.

---

## 13. Path Safety Rules

- No arbitrary path input from user, LLM, or planner.
- No writing under `rawdata_dir` or any path that resolves into it.
- No resolving symlinks into rawdata for output directories.
- No shell concatenation or string-building of MATLAB commands.
- No user-provided MATLAB code or script fragments.
- Output root must be project-scoped: `derivatives/`, `work/`, or `reports/`
  under the project directory.
- Output paths must be normalized, resolved, and validated against the project
  output roots.
- Input paths must be discovered (via image sources, dataset index, or BIDS
  structure), never user-supplied.
- Log files must be under `work/logs/<run_id>/`.

These rules follow the existing `src/backend/app/runtime/path_safety.py` pattern.

---

## 14. Failure Modes

| Failure | Status | Message | Next Action |
|---|---|---|---|
| MATLAB not found | `BLOCKED` | "MATLAB executable not found" | Configure MATLAB path in desktop settings |
| SPM not found | `BLOCKED` | "SPM directory not found or spm.m missing" | Configure SPM path in desktop config |
| BOLD input missing | `BLOCKED` | "BOLD NIfTI not found for subject" | Verify rawdata and dataset index |
| BOLD unreadable | `FAILED` | "Cannot read BOLD NIfTI" | Check file permissions and corruption |
| Invalid params | `BLOCKED` | "Parameter validation failed" | Fix params in reviewed plan |
| Approval missing | `BLOCKED` | "Approval gate blocked" | Complete approval for this node |
| Audit write failure | `BLOCKED` | "Cannot persist audit record" | Check audit directory permissions |
| Output path conflict | `BLOCKED` | "Output path already exists" | Set overwrite policy or clear outputs |
| MATLAB non-zero exit | `FAILED` | "MATLAB returned code N" | Inspect stderr log |
| Expected output missing | `FAILED` | "Output file X was not produced" | Inspect MATLAB logs |
| Partial outputs | `FAILED` | "Only N of M expected outputs exist" | Inspect logs, consider retry |
| Timeout | `FAILED` | "Realignment exceeded timeout" | Increase timeout or check input size |
| Permission error | `BLOCKED` | "Cannot write to output directory" | Check output directory permissions |
| Log write failure | `WARNING` | "Cannot write log file" | Node continues but logs missing |

Every failure returns a structured status, a user-facing message, and a
concrete next action.  No failure is silent.

---

## 15. Provenance and Reproducibility

Required provenance record:

```json
{
  "software": {
    "matlab_version": "R2023b",
    "spm_version": "12.7771",
    "wrapper_version": "0.1.0"
  },
  "params": { "quality": 0.9, "fwhm_mm": 5 },
  "inputs": {
    "bold_path": "<path>",
    "bold_sha256": "<hash>",
    "sidecar_path": "<path>"
  },
  "outputs": {
    "realigned_bold": { "path": "<path>", "sha256": "<hash>", "size_bytes": 12345 },
    "mean_bold": { "path": "<path>", "sha256": "<hash>", "size_bytes": 6789 },
    "motion_params": { "path": "<path>", "sha256": "<hash>" }
  },
  "command_template_id": "spm_realign_v1",
  "run_id": "<run_id>",
  "node_id": "spm_realign_subject",
  "started_at": "2026-...",
  "ended_at": "2026-...",
  "platform": { "os": "Windows", "hostname": "..." }
}
```

`command_template_id` references a known, versioned template — never raw MATLAB
commands.

---

## 16. Frontend UX Contract

Future UI behaviour for `spm_realign_subject`:

- **Status display**: clearly shows "SPM Realign" is a high-risk external
  execution node.
- **Environment readiness**: shows MATLAB/SPM availability from health check.
- **Required approvals**: approval gate section with all required fields.
- **Subject scope**: user selects which subjects to realign.
- **Dry-run preview**: predicted output paths and expected artifact manifest.
- **Post-execution**: realigned BOLD path, motion params path, log files
  previewable through existing run artifacts panel.
- **Failure messages**: clear error with next action from the failure modes
  table.
- **Research-only notice**: prominent warning that this is not a clinical tool.
- **No execute button**: until backend reports node is implementation-ready
  and environment checks pass.

---

## 17. Test Matrix

### Contract tests

- Node metadata: `requires_approval: true`, `risk_level: high`, `backend: matlab-spm`
- Node is NOT executable before implementation
- Node is NOT in safe allowlist before implementation
- Plan containing `spm_realign_subject` validates but execution is blocked
- Dry-run does not create files or directories

### Path safety tests

- Output path inside rawdata → rejected
- Path traversal in output → rejected
- Symlink escape into rawdata → rejected
- Arbitrary input path → rejected

### Approval / audit tests

- Missing approval → blocked
- Missing audit → blocked
- Approval scope mismatch → blocked
- Audit write failure prevents execution

### Environment tests

- MATLAB missing → blocked with clear message
- SPM missing → blocked
- Invalid MATLAB path → blocked
- Version query gracefully handles failure

### Execution tests (future implementation)

- Synthetic BOLD realign smoke test behind explicit env flag
- Stdout/stderr captured to log files
- All expected outputs verified (exist, size > 0)
- Partial output failure marks node FAILED
- Timeout is honoured and node marked FAILED
- Cancellation terminates MATLAB process

### Artifact / observability tests

- Motion parameter file (`rp_*.txt`) is discovered as run artifact
- Logs are previewable through existing artifact preview
- Provenance JSON is previewable
- Run detail shows failure status when output is missing
- Rawdata unchanged before/after (snapshot comparison)

---

## 18. Recommended Implementation Order

| Phase | Step | Description |
|---|---|---|
| 1 | Contract doc | This document |
| 2 | Metadata only | Ensure `spm_realign_subject` is registered in tool catalog but NOT executable |
| 3 | Env check | Extend `environment_check` node to report MATLAB/SPM availability |
| 4 | Param schema | Add strict Pydantic schema for realign params |
| 5 | Dry-run planner | Implement dry-run that predicts output manifest without executing |
| 6 | Approval UI | Extend frontend approval gate for external SPM nodes |
| 7 | Audit extension | Add realign-specific fields to audit record |
| 8 | Wrapper template | Implement safe MATLAB batch script template (versioned, not user-supplied) |
| 9 | Synthetic smoke | Local smoke test behind `MEDIMAGE_MATLAB_ENABLED=1` |
| 10 | External BIDS smoke | External BIDS smoke behind explicit env flag |
| 11 | Safe allowlist | Add node to safe allowlist ONLY after all tests pass |
| 12 | Output integration | Connect outputs to Motion QC Readiness and Motion Metrics Draft |

---

## 19. Open Questions

These decisions are deferred to the implementation phase:

- **MATLAB invocation method**: `-batch` vs `-r` vs `-nodesktop -nosplash`?
- **SPM batch script generation**: pre-written `.m` file in `matlab/` directory
  vs dynamically generated from template?
- **Output derivatives layout**: `<derivatives>/spm_realign/<sub>/<ses>/` vs
  flat structure?
- **Subject/session batching**: one MATLAB call per subject vs batch processing?
- **Timeout default**: what timeout is reasonable for realignment (depends on
  input size)?
- **Overwrite policy**: fail on conflict vs append timestamp?
- **SPM version support**: SPM12 only vs SPM8/12 compatibility?
- **Standalone SPM**: support for compiled SPM without MATLAB license?
- **Desktop packaging**: how to include MATLAB-dependent workflows in the
  PyInstaller + Electron desktop release?

---

## 20. Completion Criteria for Future Implementation

Before `spm_realign_subject` can be enabled for real execution:

- [ ] This contract document is reviewed and approved.
- [ ] All safety tests in the test matrix pass.
- [ ] Approval Gate explicitly covers `spm_realign_subject`.
- [ ] Audit record is written before execution and all required fields present.
- [ ] Dry-run predicts output manifest without creating files.
- [ ] Real execution captures stdout/stderr to log files.
- [ ] All expected outputs are verified after execution.
- [ ] Run artifacts are discoverable and previewable.
- [ ] Motion parameter file is picked up by Motion QC Readiness.
- [ ] Motion Metrics Draft can parse the generated `rp_*.txt`.
- [ ] Rawdata unchanged before/after (snapshot test passes).
- [ ] Documentation updated with user-facing non-clinical warning.
- [ ] Environment health endpoint reports MATLAB/SPM status.
- [ ] Desktop packaging build still succeeds without MATLAB on the build machine.

---

*End of contract document.  This document describes future behaviour only.
No real SPM realignment execution exists in the current release.*
