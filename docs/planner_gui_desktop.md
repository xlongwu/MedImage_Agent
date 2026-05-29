# Planner, GUI Agent, and Desktop v0.3 Alpha Baseline

This document records the implemented v0.3 alpha baseline for the next development track.

## Planner API

- `POST /api/planner/draft`: creates a disease/task-aware pipeline draft.
- `POST /api/planner/validate`: validates a draft against the pipeline schema and node registry.
- `POST /api/planner/execute`: executes a validated plan through the deterministic runtime; `approved=true` is required only when external SPM/DPABI/GUI-style backends are present.
- `GET /api/planner/history`: lists stored planner drafts and executions.

The planner is advice-only by default. It never lets the LLM directly execute tools or modify data. If LLM configuration is absent, deterministic fallback maps downstream tasks such as ALFF/fALFF, ReHo, and functional connectivity to existing pipeline templates. When `MEDIMAGE_LLM_MOCK_RESPONSE` or an OpenAI-compatible provider is configured, the LLM must return a JSON object that passes path and schema validation before execution is considered.

Planner smoke examples:

```bash
python -m src.backend.app.tools.run_planner_smoke_cli
python -m src.backend.app.tools.run_planner_smoke_cli --mock-llm-pipeline examples/pipeline_rsfmri_reho.yaml
```

## GUI Agent API

- `GET /api/gui-agent/sessions`
- `POST /api/gui-agent/sessions`
- `POST /api/gui-agent/sessions/{session_id}/step`
- `GET /api/gui-agent/sessions/{session_id}/screenshot`
- `POST /api/gui-agent/sessions/{session_id}/abort`

The default provider is `mock`: it records intended SPM/DPABI GUI actions and audit artifacts without controlling the desktop. The Windows-first `pywinauto` provider is optional and requires explicit approval before real GUI actions or screenshots. Every session writes `session.json`, screenshot artifacts, and a `replay_steps.py` audit script.

## Desktop Shell

The desktop baseline uses Electron + React. The Electron main process can start the local FastAPI backend and exposes `MEDIMAGE_API_BASE_URL` to the renderer. Development entry points live under `src/frontend/electron/`.

Desktop configuration endpoints:

- `GET /api/desktop/config`
- `POST /api/desktop/config`
- `GET /api/desktop/health`

The React advanced mode includes a Desktop Settings panel for local paths, LLM provider settings, GPU mode, and GUI Agent provider/approval. API keys are redacted in API responses and are not written back in plaintext by the settings endpoint.

Electron smoke checks:

```bash
cd src/frontend
npm run build
npm run desktop:check
```

## External SPM/DPABI Smoke Package

The external smoke workflow is the handoff point for research teams that have
real MATLAB, SPM, or DPABI installed. It is intentionally separate from normal
CI: default commands generate a manual verification package and do not launch
MATLAB. Real smoke execution requires explicit approval.

```bash
python -m src.backend.app.tools.run_external_smoke_cli --target all --mode preflight
python -m src.backend.app.tools.run_external_smoke_cli --target all --mode manual_package
python -m src.backend.app.tools.run_external_smoke_cli --target all --mode approved_smoke --approve --approved-by local-user --dpabi-function y_Smooth
```

Artifacts are written to `outputs/reports/external_smoke/`, including a
checklist, approval template, command sheet, MATLAB script snapshots, diagnostic
report, and machine-readable `external_smoke_result.json`. Rawdata remains
read-only. `DPARSF_run`, `DPARSFA_run`, and DPABI GUI batch execution remain
forbidden; DPABI smoke is limited to environment checks and allowlisted
single-function wrappers.

The same package is available through the local API and desktop UI:

- `GET /api/external-smoke/status`
- `POST /api/external-smoke/run`

The desktop Advanced Mode system tab shows an External SPM / DPABI Smoke panel
that can run preflight or manual-package generation without launching MATLAB.
The panel only launches real smoke checks when `approved_smoke` is selected and
the request explicitly sets `approved=true`.

## Import Diagnostics

The desktop Advanced Mode system tab also includes an Import Diagnostics panel.
It turns the current NIfTI/BIDS discovery layer into a reviewable validation
surface for research handoff:

- `GET /api/images/manifest`: returns discovered image sources, subject IDs,
  sequence labels, source paths, voxel spacing, dimensions, warnings, and the
  generated manifest path under `outputs/reports/image_sources/`.
- `GET /api/images/validation`: rebuilds the validation report for a project,
  returns the full issue list, report paths, manifest path, and inline Markdown
  `report_text` for UI review.
- `GET /api/datasets/imports`: returns the recorded import roots for a project,
  including dataset ID, type, timestamp, path, and whether the path currently
  exists on disk.
- `POST /api/datasets/diagnostics/package`: writes a handoff package under
  `outputs/reports/import_diagnostics/{project_id}/` with a combined Markdown
  report and JSON payload covering validation, manifest, imports, and artifact
  paths. A ZIP archive is generated alongside the report so the package can be
  attached to a manual MATLAB/SPM/DPABI smoke record without collecting raw
  images. `CHECKSUMS.sha256` records SHA256 hashes for the packaged diagnostic
  artifacts. The API response also includes safety flags such as
  `rawdata_not_bundled`, `read_only_validation`, and `diagnostics_only`.
  When DICOM import roots are present, the package also includes the
  metadata-only DICOM preflight report and JSON under `artifacts/`, with hashed
  UIDs and no raw DICOM payload.
- `GET /api/datasets/diagnostics/package/latest`: returns the latest generated
  handoff package metadata and report text so the desktop UI can recover the
  package after refresh or app restart.
- `POST /api/datasets/diagnostics/package/verify`: verifies the handoff ZIP
  entries against `CHECKSUMS.sha256` and reports missing or mismatched files.
- `GET /api/datasets/dicom/preflight`: scans `.dcm`/`.ima` files from a
  registered import root or explicit path, reads DICOM headers only with
  `stop_before_pixels=True`, and writes a metadata-only JSON/Markdown report
  under `outputs/reports/dicom_preflight/{project_id}/`. Raw Study/Series UIDs
  are hashed in outputs and sample file paths are written relative to the scan
  root when possible.

The panel supports a project ID field and a one-click revalidation action. It
shows validation issue severity, code, subject/session/sequence scope, file
path, imported root history, full JSON payloads, and the rendered Markdown
report text. It can also generate an Import Diagnostics handoff package for
manual review. Report, JSON, manifest, checksum, handoff folder, and handoff
ZIP paths can be opened through the Electron preload bridge; the renderer does
not receive direct Node access. The UI can also verify the package checksum
manifest before attaching it to a manual smoke record. This is still read-only
validation: imported roots are scanned, rawdata is never modified or bundled,
and all generated diagnostics stay under `outputs/reports/`.

Expected manual handoff flow:

```bash
python -m pytest tests/api/test_dashboard_api.py -q
python -m src.backend.app.tools.run_dicom_preflight_cli --project-id brain-tumor-study --path data/DemoData --max-files 2000
python -m src.backend.app.tools.run_import_diagnostics_cli --project-id brain-tumor-study --mode all
python -m src.backend.app.tools.run_import_diagnostics_cli --project-id brain-tumor-study --import-path data/DemoData --dataset-type dicom --mode all
cd src/frontend
npm run build
```

`data/DemoData` is treated as a read-only real DICOM sample root. The CLI
can first run a metadata-only DICOM preflight, then register the path, record a
file inventory, generate the handoff ZIP, and verify its checksums without
copying DICOM files into the package.

Then open Advanced Mode -> System Status -> Import Diagnostics, refresh the
project, and attach the displayed Markdown report plus manifest path to the
manual smoke record when testing real MATLAB/SPM/DPABI environments.

## Dependency Policy

Core requirements stay small. Optional capabilities are listed in `requirements-optional.txt`; Electron dependencies are in `src/frontend/package.json`.
