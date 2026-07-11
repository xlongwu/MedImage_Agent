# SPM Sandbox Pipeline Manual Smoke Test

> M6-SPM-SMOKE-E2E | Full SPM sandbox reviewed execution pipeline smoke

**状态**: Manual smoke — requires real MATLAB/SPM. NOT in CI.

---

## 一、前置条件

| 条件 | 检查 |
|------|------|
| MATLAB | `matlab -batch "disp('OK'); exit(0);"` |
| SPM12 | `spm_dir` 指向有效 SPM 根目录 |
| TPM | `{spm_dir}/tpm/TPM.nii` 存在 |
| Env var | `export MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` |
| Backend | `uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000` |
| rawdata | `rawdata_readonly=true` |

---

## 二、project_config

```yaml
project:
  name: spm_sandbox_pipeline_smoke
runtime:
  work_dir: ./outputs/work
  log_dir: ./outputs/logs
  derivatives_dir: ./outputs/derivatives
  report_dir: ./outputs/reports
  matlab_command: matlab
third_party:
  spm_dir: /path/to/spm12
  dpabi_dir: /path/to/dpabi
safety:
  rawdata_readonly: true
  allow_overwrite_derivatives: false
```

---

## 三、Reviewed plan (7 nodes, sandbox-gated)

```json
{
  "pipeline_id": "spm_full_sandbox_smoke",
  "nodes": [
    {"id": "spm_smoke_test", "backend": "matlab-spm", "depends_on": [], "params": {}},
    {"id": "spm_realign_subject", "backend": "matlab-spm", "depends_on": ["spm_smoke_test"],
     "params": {"sandbox_mode": true, "input_bold": "synthetic_bids"}},
    {"id": "spm_slice_timing_subject", "backend": "matlab-spm", "depends_on": ["spm_realign_subject"],
     "params": {"sandbox_mode": true, "input_bold": "synthetic_bids_or_safe_derivatives",
                "allow_derivative_input": true, "tr": 2.0}},
    {"id": "spm_coregister_subject", "backend": "matlab-spm", "depends_on": ["spm_slice_timing_subject"],
     "params": {"sandbox_mode": true, "subject_source": "synthetic_bids",
                "reference_source": "derivatives_mean_functional"}},
    {"id": "spm_segment_subject", "backend": "matlab-spm", "depends_on": ["spm_coregister_subject"],
     "params": {"sandbox_mode": true, "anatomical_source": "coregistered_t1w",
                "tpm_source": "spm_default_tpm"}},
    {"id": "spm_normalize_subject", "backend": "matlab-spm", "depends_on": ["spm_segment_subject"],
     "params": {"sandbox_mode": true, "deformation_source": "segment_deformation_field",
                "functional_source": "sandbox_derivatives"}},
    {"id": "spm_smooth_subject", "backend": "matlab-spm", "depends_on": ["spm_normalize_subject"],
     "params": {"sandbox_mode": true, "normalized_source": "normalize_outputs",
                "fwhm_policy": "bounded_3d", "fwhm": [6, 6, 6]}}
  ]
}
```

---

## 四、Approval

```json
{
  "approved": true, "approved_by": "smoke-tester",
  "approved_nodes": ["spm_smoke_test","spm_realign_subject","spm_slice_timing_subject",
    "spm_coregister_subject","spm_segment_subject","spm_normalize_subject","spm_smooth_subject"],
  "approved_backends": ["matlab-spm"], "rejected_nodes": []
}
```

> ❌ `approved_nodes=["*"]` NOT allowed for MATLAB/SPM.

---

## 五、API call

```bash
curl -s -X POST http://127.0.0.1:8000/api/plans/execute-reviewed \
  -H "Content-Type: application/json" \
  -d '{
    "plan": { ... },
    "approval": { ... },
    "project_config_path": "spm_sandbox_config.yaml",
    "dry_run": false,
    "confirm_execution": true,
    "persist_audit": true,
    "write_pipeline_yaml": true,
    "actor": "spm-full-sandbox-smoke"
  }' | python -m json.tool
```

---

## 六、Expected success

```json
{"ok": true, "status": "EXECUTION_SUBMITTED",
 "execution": {"executor_called": true, "submitted": true},
 "pipeline_yaml": {"written": true},
 "audit": {"persisted": true}}
```

---

## 七、Failure diagnostics

| Status | Cause | Fix |
|--------|-------|-----|
| `REVIEWED_EXECUTION_DISABLED` | env var not set | `export MEDIMAGE_ENABLE_REVIEWED_EXECUTION=1` |
| `CONFIRMATION_REQUIRED` | `confirm_execution` not true | Set `true` |
| `AUDIT_REQUIRED` | `persist_audit` not true | Set `true` |
| `PROJECT_CONFIG_REQUIRED` | missing config path | Provide path |
| `PROJECT_CONFIG_INVALID` | bad YAML | Fix YAML |
| `VALIDATION_FAILED` | unknown node | Check node ids |
| `APPROVAL_GATE_BLOCKED` | wildcard or missing backend | Use explicit node+backend |
| `EXECUTION_POLICY_BLOCKED` | unsafe node | Check sandbox params |
| `SAFE_EXECUTION_POLICY_BLOCKED` | GPU/contract | Remove unsafe nodes |
| `PIPELINE_WRITE_FAILED` | writer error | Check outputs/ permissions |
| `EXECUTION_FAILED` | MATLAB crash | See MATLAB diagnostics below |

### MATLAB/SPM diagnostics

| Code | Severity | Fix |
|------|:---:|------|
| `MATLAB_COMMAND_NOT_FOUND` | ⚠️ | `which matlab` |
| `MATLAB_COMMAND_HAS_ARGUMENTS` | 🔴 | Use bare `matlab` |
| `MATLAB_COMMAND_FORBIDDEN_CHAR` | 🔴 | Remove `;&|` etc |
| `THIRD_PARTY_DIR_NOT_FOUND` | ⚠️ | Check `spm_dir` |
| `SPM_TPM_NOT_FOUND` | 🔴 | `ls {spm_dir}/tpm/TPM.nii` |
| `SPM_SMOOTH_FWHM_INVALID` | 🔴 | FWHM: 3 numbers, 0<each<=12 |

---

## 八、Output artifacts

```text
outputs/work/reviewed_pipelines/    → pipeline YAML
outputs/reports/audit_records/      → audit JSON
outputs/derivatives/rsfmri_preproc/ → realigned, ST-corrected, coregistered,
                                       segmented (c1/c2/c3), normalized (w*),
                                       smoothed (sw*) images
outputs/logs/                       → per-node stdout/stderr
```

---

## 九、rawdata readonly

```bash
git diff data/  # must be empty
```

---

## 十、Cleanup

```bash
rm -rf outputs/work/reviewed_pipelines/*
rm -rf outputs/reports/audit_records/*
rm -rf outputs/logs/*
rm -rf outputs/derivatives/rsfmri_preproc/*
unset MEDIMAGE_ENABLE_REVIEWED_EXECUTION
```

> Do NOT delete `data/` or `rawdata/`.

---

## 十一、Safety boundaries

```
✅ 7 SPM nodes sandbox-gated
✅ explicit node + backend approval
✅ rawdata readonly
❌ DPABI
❌ GPU
❌ GUI/manual
❌ Unrestricted SPM
❌ CI execution
```
