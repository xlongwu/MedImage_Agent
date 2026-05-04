---

## Step 32: Release Checklist + Deployment Readiness 闭环

This step implements a release readiness scanner to verify project readiness for demo, handoff, or deployment preparation.

### Quick Start

```bash
# Run release readiness check
python -m backend.app.tools.run_release_readiness_cli

# Or use the frontend release readiness panel
```

### What This Step Does

1. **Project Structure Checks**
   - Required directories exist
   - Required files exist
   - Required specs exist
   - Required tools exist
   - Required frontend components exist
   - Required tests exist

2. **Safety Gate Verification**
   - DPARSF_run / DPARSFA_run blocked in contracts
   - Templates default to approved=false
   - Templates don't contain full pipeline runners
   - Artifact browser rejects path traversal
   - Bundles exclude rawdata and third_party

3. **Readiness Score Calculation**
   - Percentage of passed checks
   - Blockers count (deployment blockers)
   - Warnings count (non-blocking issues)
   - Overall status: READY / WARNING / BLOCKED

4. **Report Generation**
   - YAML checklist
   - JSON readiness data
   - Markdown report

### Readiness Status

| Status | Description |
|--------|-------------|
| READY | No blockers, only minor warnings |
| WARNING | No blockers, meaningful warnings exist |
| BLOCKED | At least one deployment blocker |

### Output Files

```text
work/release/
├── release_checklist.yaml       # YAML checklist
└── release_readiness.json       # JSON readiness data

reports/release/
└── release_readiness_report.md  # Markdown report
```

### Checks Performed

**Structure Checks:**
- backend/app directories
- frontend/src directories
- matlab/, specs/, examples/, tests/unit/
- Key files: README.md, main.py, routes.py, etc.

**Spec Checks:**
- All DPABI specs exist
- Experiment specs exist
- Artifact browser spec exists
- Reproducibility bundle spec exists
- Release readiness spec exists

**Tool Checks:**
- All DPABI tools exist
- Experiment tools exist
- Artifact browser exists
- Reproducibility bundle exists
- Release readiness scanner exists

**Frontend Checks:**
- DpabiPanel exists
- DpabiTemplateWizard exists
- ExperimentPanel exists
- ExperimentDashboard exists
- ArtifactBrowser exists
- ReproducibilityBundle exists

**Safety Checks:**
- DPARSF_run blocked in contracts
- DPARSFA_run blocked in contracts
- Templates default approved=false
- Templates don't contain DPARSF_run
- Bundle safety verified
- Artifact index exists
- Experiment dashboard exists

### API Endpoint

```bash
# Get release readiness
GET /api/release/readiness
```

### Frontend

The "Release Readiness" section provides:

- **Run Check Button** - Execute readiness scan
- **Status Banner** - READY/WARNING/BLOCKED with color
- **Readiness Score** - Percentage of passed checks
- **Stats Grid** - Passed, Blockers, Warnings counts
- **Blockers List** - Deployment blocking issues
- **Warnings List** - Non-blocking issues
- **All Checks List** - Complete check results with severity
- **Safety Guarantees** - Safety check status

### CLI Usage

```bash
# Run release readiness check
python -m backend.app.tools.run_release_readiness_cli
```

### Safety Rules

- **Read-only** - Only scans files, never modifies
- **No pipeline execution** - Pure static analysis
- **No MATLAB launch** - No external tool execution
- **No DPABI execution** - No runtime dependencies
- **No file deletion** - Safe operation
- **No automatic deployment** - Manual review required

### Readiness Score Formula

```
readiness_score = (checks_passed / checks_total) * 100
```

### Status Determination

```python
if blockers > 0:
    status = "BLOCKED"
elif warnings > 0:
    status = "WARNING"
else:
    status = "READY"
```

### Use Cases

- **Pre-deployment Check** - Verify readiness before deployment
- **Demo Preparation** - Ensure all components are functional
- **Handoff Review** - Document project state for handoff
- **CI/CD Integration** - Automated readiness checks
- **Release Gate** - Block releases with critical issues

### Required Safety Guarantees

The scanner verifies:

- ✅ Generated templates default to approved=false
- ✅ DPARSF_run / DPARSFA_run are blocked in wrapper contracts
- ✅ Template library does not promote full pipeline runners
- ✅ Artifact browser rejects path traversal
- ✅ Bundles exclude rawdata and third_party
- ✅ Release scanner itself does not execute pipelines or MATLAB

---

## Step 33: Docker / Local Deployment Profile + Health Check 闭环

This step implements deployment profiles and health checks for local development and Docker demo modes.

### Quick Start

```bash
# Local development mode
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && npm run dev

# Docker demo mode
docker compose -f deploy/docker-compose.demo.yml up --build

# Scan deployment profile
python -m backend.app.tools.run_deployment_profile_cli
```

### What This Step Does

1. **Deployment Profiles**
   - `local_dev` - Local development with uvicorn + npm
   - `docker_demo` - Containerized demo mode
   - Environment variable templates
   - Service definitions

2. **Docker Configuration**
   - Backend Dockerfile (Python 3.11 slim)
   - Frontend Dockerfile (Node 20 + Nginx)
   - Docker Compose demo configuration
   - Nginx reverse proxy config

3. **Health Checks**
   - Backend health endpoint: `GET /api/health`
   - Frontend health endpoint: `GET /health`
   - Docker health checks configured

4. **Deployment Profile Scanner**
   - Validates deployment files exist
   - Checks Docker safety configurations
   - Verifies environment variables
   - Detects forbidden copy patterns
   - Generates deployment report

### Deployment Modes

#### Local Dev (`local_dev`)

```yaml
backend:
  command: uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
  health_url: http://127.0.0.1:8000/api/health

frontend:
  command: cd frontend && npm run dev
  url: http://127.0.0.1:5173
```

**Features:**
- Hot reload for backend and frontend
- MATLAB/SPM/DPABI may be available locally
- Full execution requires approval gates

#### Docker Demo (`docker_demo`)

```yaml
services:
  backend:
    image: medimage-agent-backend
    ports: ["8000:8000"]
    environment:
      MEDIMAGE_MATLAB_ENABLED: "false"
      MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION: "false"

  frontend:
    image: medimage-agent-frontend
    ports: ["5173:80"]
    depends_on: [backend]
```

**Features:**
- MATLAB disabled by default
- DPABI execution disabled by default
- Only read/report/preview/dashboard functions
- Work/reports/logs/examples mounted as volumes
- Third_party not copied into images

### Environment Variables

Create `.env` from `.env.example`:

```bash
# Core
MEDIMAGE_ENV=local_dev
MEDIMAGE_BACKEND_PORT=8000
MEDIMAGE_FRONTEND_PORT=5173

# Runtime directories
MEDIMAGE_WORK_DIR=./work
MEDIMAGE_REPORT_DIR=./reports
MEDIMAGE_LOG_DIR=./logs

# External dependencies (disabled in docker_demo)
MEDIMAGE_MATLAB_ENABLED=false
MEDIMAGE_SPM_DIR=./third_party/spm12
MEDIMAGE_DPABI_DIR=./third_party/DPABI_V8.2_240510

# Safety defaults
MEDIMAGE_ALLOW_FULL_DPABI_EXECUTION=false
MEDIMAGE_ALLOW_DPARSF_RUN=false
MEDIMAGE_ALLOW_DPARSFA_RUN=false
MEDIMAGE_ALLOW_RAWDATA_WRITE=false
MEDIMAGE_SYNTHETIC_ONLY=true
```

### Deployment Files

```text
deploy/
├── local_profile.yaml          # Local dev profile
├── docker-compose.demo.yml     # Docker compose config
├── backend.Dockerfile          # Backend container
├── frontend.Dockerfile         # Frontend container
└── nginx.conf                  # Nginx config

.env.example                    # Environment template
```

### Output Files

```text
work/deployment/
└── deployment_profile.json     # Deployment profile data

reports/deployment/
└── deployment_profile_report.md # Deployment report
```

### Deployment Profile Status

| Status | Description |
|--------|-------------|
| READY | All deployment files present, safety checks pass |
| WARNING | Deployment files present, minor issues detected |
| BLOCKED | Missing required files or safety violations |

### Checks Performed

**File Checks:**
- `.env.example` exists
- `deploy/local_profile.yaml` exists
- `deploy/docker-compose.demo.yml` exists
- `deploy/backend.Dockerfile` exists
- `deploy/frontend.Dockerfile` exists
- `deploy/nginx.conf` exists

**Safety Checks:**
- Dockerfiles don't copy third_party
- Dockerfiles don't copy .git
- Dockerfiles don't copy node_modules
- `.env.example` contains safety defaults
- `docker-compose.demo.yml` disables MATLAB
- `docker-compose.demo.yml` disables DPABI execution

**Environment Checks:**
- Docker CLI available
- Docker Compose available
- Node.js available
- npm available

### API Endpoints

```bash
# Health check
GET /api/health

# Deployment profile
GET /api/deployment/profile
```

### Frontend

The "Deployment Profile" section provides:

- **Scan Button** - Execute deployment profile scan
- **Status Banner** - READY/WARNING/BLOCKED with color
- **Stats Grid** - Passed checks, blockers, warnings
- **Deployment Profiles** - Local dev and Docker demo configs
- **Blockers List** - Critical deployment issues
- **Warnings List** - Non-blocking issues
- **All Checks List** - Complete check results
- **Environment Info** - Platform, Docker, Node versions
- **Safety Guarantees** - Safety check status

### CLI Usage

```bash
# Scan deployment profile
python -m backend.app.tools.run_deployment_profile_cli
```

### Safety Rules

- **No automatic Docker build** - Manual build required
- **No automatic deployment** - Manual deployment required
- **No pipeline execution** - Pure static analysis
- **No MATLAB launch** - Disabled in docker_demo
- **No DPABI execution** - Disabled in docker_demo
- **No rawdata exposure** - Excluded from images
- **No third_party copy** - External dependencies not bundled

### Docker Build (Manual)

```bash
# Build backend
docker build -f deploy/backend.Dockerfile -t medimage-agent-backend .

# Build frontend
docker build -f deploy/frontend.Dockerfile -t medimage-agent-frontend .

# Run with compose
docker compose -f deploy/docker-compose.demo.yml up
```

### Health Check Endpoints

**Backend:**
```bash
curl http://127.0.0.1:8000/api/health
# Returns: {"ok": true, "service": "medimage-agent-api", "status": "healthy"}
```

**Frontend (Nginx):**
```bash
curl http://127.0.0.1:5173/health
# Returns: ok
```

### Use Cases

- **Local Development** - Quick start with hot reload
- **Docker Demo** - Containerized demo without MATLAB
- **CI/CD Integration** - Automated deployment checks
- **Deployment Review** - Validate configuration before deploy
- **Environment Audit** - Check required tools availability

## Step 34: rs-fMRI Core Preprocessing Plan

This step introduces the core rs-fMRI preprocessing protocol.

It defines:

- preprocessing protocol
- step registry
- step schema
- pipeline DAG
- SPM-backed steps
- DPABI-backed steps
- Python QC steps
- GPU candidate steps
- QC metrics
- failure modes
- diagnostic hints
- safety gates

It does not execute preprocessing.

### Run

```bash
python -m backend.app.tools.run_rsfmri_core_plan_cli
```

Expected outputs:

- `work/preprocessing/rsfmri/rsfmri_preprocessing_plan.json`
- `reports/rsfmri/rsfmri_preprocessing_plan_report.md`
- `work/pipeline_runs/run_rsfmri_core_plan_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/preprocessing-plan
```

Refresh:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/preprocessing-plan/refresh
```

### Frontend

Use the **rs-fMRI Core Preprocessing Plan** section to load and refresh the plan.

### Safety

This step:

- does not execute preprocessing
- does not launch MATLAB
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not modify rawdata
- does not delete files

## Step 35: SPM Realignment and Motion QC

This step implements the first real core rs-fMRI preprocessing wrapper.

It supports:

- approved SPM realignment
- synthetic BIDS-like input only
- realigned BOLD output
- mean functional image output
- motion parameter file output
- framewise displacement calculation
- subject-level motion QC
- dataset-level motion QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_spm_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_realign_motion_qc.yaml --approve
```

Expected outputs:

- `derivatives/rsfmri_preproc/sub-001/func/rsub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/meansub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/rp_sub-001_bold.txt`
- `derivatives/rsfmri_preproc/sub-001/func/spm_realign_result.json`
- `derivatives/rsfmri_qc/sub-001/motion_qc.json`
- `derivatives/rsfmri_qc/sub-001/motion_qc.md`
- `reports/rsfmri/motion_qc_summary.json`
- `reports/rsfmri/motion_qc_report.md`
- `work/pipeline_runs/run_rsfmri_spm_realign_motion_qc_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_spm_realign_motion_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use the **rs-fMRI SPM Realignment + Motion QC** section.

### Safety

This step:

- requires approved=true
- only processes synthetic BIDS-like input
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing

## Step 36: SPM Slice Timing Correction and Metadata QC

This step implements SPM slice timing correction for synthetic rs-fMRI data.

It supports:

- approved SPM slice timing correction
- synthetic BIDS-like input only
- BIDS sidecar metadata parsing
- RepetitionTime validation
- SliceTiming validation
- conversion from BIDS SliceTiming to SPM slice order
- subject-level slice timing QC
- dataset-level slice timing QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_spm_slice_timing_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_spm_slice_timing_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_spm_slice_timing.yaml --approve
```

Expected outputs:

- `derivatives/rsfmri_preproc/sub-001/func/sub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/asub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/spm_slice_timing_result.json`
- `derivatives/rsfmri_qc/sub-001/slice_timing_qc.json`
- `derivatives/rsfmri_qc/sub-001/slice_timing_qc.md`
- `reports/rsfmri/slice_timing_qc_summary.json`
- `reports/rsfmri/slice_timing_qc_report.md`
- `work/pipeline_runs/run_rsfmri_spm_slice_timing_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/spm-slice-timing
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/spm-slice-timing/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_spm_slice_timing.yaml",
    "approved": true
  }'
```

### Frontend

Use the **rs-fMRI SPM Slice Timing + Metadata QC** section.

### Safety

This step:

- requires approved=true
- only processes synthetic BIDS-like input
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing

## Step 37: Slice Timing → Realignment → Motion QC Chain

This step connects the first two real rs-fMRI preprocessing wrappers.

It supports:

- approved SPM slice timing correction
- approved SPM realignment using slice timing output
- motion QC
- subject-level chain summary
- dataset-level chain report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_st_realign_motion_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_st_realign_motion_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_st_realign_motion_qc.yaml --approve
```

Expected outputs:

- `derivatives/rsfmri_preproc/sub-001/func/asub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/rasub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/meanasub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/rp_asub-001_bold.txt`
- `derivatives/rsfmri_qc/sub-001/slice_timing_qc.json`
- `derivatives/rsfmri_qc/sub-001/motion_qc.json`
- `reports/rsfmri/st_realign_motion_chain_summary.json`
- `reports/rsfmri/st_realign_motion_chain_report.md`
- `work/pipeline_runs/run_rsfmri_st_realign_motion_qc_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/st-realign-motion-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_st_realign_motion_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use the **rs-fMRI Slice Timing → Realignment → Motion QC** section.

### Safety

This step:

- requires approved=true
- only processes synthetic BIDS-like input
- only allows realignment derivative input from expected slice timing output
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing

## Step 38: SPM Coregistration and Registration QC

This step implements SPM coregistration between the mean functional image and synthetic T1w anatomical image.

It supports:

- approved SPM coregistration
- synthetic BIDS-like input only
- mean functional derivative as reference
- T1w derivative workspace copy as source
- registration QC metrics
- subject-level registration QC
- dataset-level registration QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_coregistration_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_coregistration_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_coregistration_qc.yaml --approve
```

Expected outputs:

- `derivatives/rsfmri_preproc/sub-001/anat/sub-001_T1w.nii`
- `derivatives/rsfmri_preproc/sub-001/anat/coreg_sub-001_T1w.nii`
- `derivatives/rsfmri_preproc/sub-001/anat/spm_coregistration_result.json`
- `derivatives/rsfmri_qc/sub-001/registration_qc.json`
- `derivatives/rsfmri_qc/sub-001/registration_qc.md`
- `reports/rsfmri/registration_qc_summary.json`
- `reports/rsfmri/registration_qc_report.md`
- `work/pipeline_runs/run_rsfmri_coregistration_qc_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/coregistration-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/coregistration-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_coregistration_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use the **rs-fMRI SPM Coregistration + Registration QC** section.

### Safety

This step:

- requires approved=true
- only processes synthetic BIDS-like input
- uses derivative mean functional reference
- copies T1w into derivatives before coregistration
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing

## Step 39: SPM Segmentation and Tissue QC

This step implements SPM segmentation of the coregistered synthetic T1w image.

It supports:

- approved SPM segmentation
- derivative coregistered T1w input only
- GM / WM / CSF tissue probability maps
- deformation field output
- tissue QC metrics
- subject-level tissue QC
- dataset-level tissue QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_segmentation_tissue_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_segmentation_tissue_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_segmentation_tissue_qc.yaml --approve
```

Expected outputs:

- `derivatives/rsfmri_preproc/sub-001/anat/c1coreg_sub-001_T1w.nii`
- `derivatives/rsfmri_preproc/sub-001/anat/c2coreg_sub-001_T1w.nii`
- `derivatives/rsfmri_preproc/sub-001/anat/c3coreg_sub-001_T1w.nii`
- `derivatives/rsfmri_preproc/sub-001/anat/y_coreg_sub-001_T1w.nii`
- `derivatives/rsfmri_preproc/sub-001/anat/spm_segmentation_result.json`
- `derivatives/rsfmri_qc/sub-001/tissue_qc.json`
- `derivatives/rsfmri_qc/sub-001/tissue_qc.md`
- `reports/rsfmri/tissue_qc_summary.json`
- `reports/rsfmri/tissue_qc_report.md`
- `work/pipeline_runs/run_rsfmri_segmentation_tissue_qc_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/segmentation-tissue-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_segmentation_tissue_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use the **rs-fMRI SPM Segmentation + Tissue QC** section.

### Safety

This step:

- requires approved=true
- only processes derivative coregistered T1w input
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing

## Step 40: SPM Normalization and Normalization QC

This step implements SPM normalize write using the deformation field produced by segmentation.

It supports:

- approved SPM normalization
- derivative realigned functional input only
- derivative segmentation deformation field input only
- normalized functional output
- optional normalized mean functional output
- normalization QC metrics
- subject-level normalization QC
- dataset-level normalization QC report
- frontend visualization

It does not run full preprocessing.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_normalization_qc_cli
```

This should fail safely because approval is missing.

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_normalization_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_normalization_qc.yaml --approve
```

Expected outputs:

- `derivatives/rsfmri_preproc/sub-001/func/wrasub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/wmeanasub-001_bold.nii`
- `derivatives/rsfmri_preproc/sub-001/func/spm_normalization_result.json`
- `derivatives/rsfmri_qc/sub-001/normalization_qc.json`
- `derivatives/rsfmri_qc/sub-001/normalization_qc.md`
- `reports/rsfmri/normalization_qc_summary.json`
- `reports/rsfmri/normalization_qc_report.md`
- `work/pipeline_runs/run_rsfmri_normalization_qc_001/summary.json`

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/normalization-qc
```

Run approved:

```bash
curl -X POST http://127.0.0.1:8000/api/rsfmri/normalization-qc/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_config_path": "examples/project_config_dataset.yaml",
    "pipeline_path": "examples/pipeline_rsfmri_normalization_qc.yaml",
    "approved": true
  }'
```

### Frontend

Use the **rs-fMRI SPM Normalization + Normalization QC** section.

### Safety

This step:

- requires approved=true
- only processes derivative functional input
- only uses derivative deformation field input
- does not modify rawdata
- does not run DPABI
- does not call DPARSF_run
- does not call DPARSFA_run
- does not call DPABI GUI
- does not execute full preprocessing

## Step 41: SPM Smoothing and Smoothing QC

This step implements SPM smoothing using the normalized functional image produced by normalization.

It supports: approved SPM smoothing, derivative normalized functional input only, smoothed normalized functional output, smoothing QC metrics, subject-level and dataset-level reports, frontend visualization.

### Run without approval

```bash
python -m backend.app.tools.run_rsfmri_smoothing_qc_cli
```

### Run with approval

```bash
python -m backend.app.tools.run_rsfmri_smoothing_qc_cli examples/project_config_dataset.yaml examples/pipeline_rsfmri_smoothing_qc.yaml --approve
```

Expected outputs: `derivatives/rsfmri_preproc/sub-001/func/swrasub-001_bold.nii`, `spm_smoothing_result.json`, `smoothing_qc.json/.md`, `reports/rsfmri/smoothing_qc_summary.json/.md`.

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/smoothing-qc
curl -X POST http://127.0.0.1:8000/api/rsfmri/smoothing-qc/run -d '{"approved": true}'
```

### Safety

This step: requires approved=true, only processes derivative normalized functional input, does not modify rawdata, does not run DPABI.

## Step 42: Nuisance Regression, Confound Matrix, and DPABI Backend Contract

This step implements nuisance regression design and a Python backend MVP. It supports: Friston24 confound matrix, motion6, intercept and linear trend, Python OLS residualization, subject-level and dataset-level regression QC, DPABI backend contract (no execution), frontend visualization.

### Run

```bash
python -m backend.app.tools.run_rsfmri_nuisance_regression_cli --approve
```

Expected outputs: `derivatives/rsfmri_confounds/sub-001/confounds.tsv/.json/.qc.json`, `derivatives/rsfmri_preproc/sub-001/func/resid_swr*.nii`, `derivatives/rsfmri_qc/sub-001/nuisance_regression_qc.json/.md`, `reports/rsfmri/nuisance_regression_qc_summary.json/.md`, `work/dpabi/contracts/nuisance_regression_backend_contract.json`.

### API

```bash
curl http://127.0.0.1:8000/api/rsfmri/nuisance-regression
curl -X POST http://127.0.0.1:8000/api/rsfmri/nuisance-regression/run -d '{"approved": true}'
```

### Safety: only processes derivative input, does not modify rawdata, does not execute DPABI (contract only).

## Step 43: Temporal Filtering and Filtering QC

Python FFT-based temporal band-pass filtering on nuisance-regressed derivatives. TR from slice timing QC or explicit fallback, default 0.01-0.08 Hz band-pass. Outputs `filt_resid_swr*.nii`, filtering QC JSON/MD, dataset QC report, DPABI contract.

### Run: `python -m backend.app.tools.run_rsfmri_temporal_filtering_cli --approve`
### API: `curl http://127.0.0.1:8000/api/rsfmri/temporal-filtering`
### Safety: only derivative input, no DPABI execution, no rawdata modification.

## Step 44: ALFF / fALFF and QC

Python NumPy ALFF/fALFF. ALFF = mean low-frequency amplitude, fALFF = low-freq mean / non-DC full-spectrum mean. TR from QC or fallback. Outputs `alff.nii`, `falff.nii` in `derivatives/rsfmri_metrics/`. GPU and DPABI contracts without execution.

### Run: `python -m backend.app.tools.run_rsfmri_alff_falff_cli --approve`
### API: `curl http://127.0.0.1:8000/api/rsfmri/alff-falff`
### Safety: only derivative input, no DPABI/GPU execution, no rawdata modification.

## Step 45: ReHo and ReHo QC

Python NumPy ReHo via Kendall's coefficient of concordance (KCC). Neighborhood 7/19/27, default 27. Boundary voxels skipped. Output in `derivatives/rsfmri_metrics/reho.nii`. GPU and DPABI contracts without execution.

### Run: `python -m backend.app.tools.run_rsfmri_reho_cli --approve`
### API: `curl http://127.0.0.1:8000/api/rsfmri/reho`

## Step 46: Functional Connectivity and FC QC

Python NumPy ROI/seed FC. Default: 4 synthetic cuboid ROIs from functional image shape. ROI time series extraction, Pearson correlation matrix, Fisher-z transform. Optional seed-to-voxel map. GPU and DPABI contracts without execution.

### Run: `python -m backend.app.tools.run_rsfmri_functional_connectivity_cli --approve`
### API: `curl http://127.0.0.1:8000/api/rsfmri/functional-connectivity`

## Step 47: Group-level Dataset Summary and Dashboard

Read-only aggregation of all subject-level QC, metrics, pipeline runs, and backend contracts. Auto-discovers subjects from derivatives subdirectories, builds wide metrics CSV, dataset summary JSON, dashboard-ready JSON, pipeline completeness matrix, contracts overview, and Markdown report. No SPM/MATLAB/DPABI/GPU execution.

### Run: `python -m backend.app.tools.run_rsfmri_group_summary_cli`
### API: `curl http://127.0.0.1:8000/api/rsfmri/group-summary`

## Step 48: Dataset Report Exporter

Packages existing synthetic rs-fMRI reports, QC, metrics, contracts, and pipeline summaries into a ZIP report package with SHA256 checksums and manifest. Read-only from derivatives/reports/work, writes only to exports. Excludes .nii/.gz/.mat binary files.

### Run: `python -m backend.app.tools.run_rsfmri_report_exporter_cli`
### API: `curl http://127.0.0.1:8000/api/rsfmri/report-export/latest`

## Step 49: Report Package Validator

Validates exported report packages for integrity: SHA256 checksums, ZIP consistency, required files present, safety flags audit, and forbidden binary content (NIfTI/MAT). Read-only, writes only validation artifacts. Does not repair packages.

### Run: `python -m backend.app.tools.run_rsfmri_report_validator_cli`
### API: `curl http://127.0.0.1:8000/api/rsfmri/report-validator/latest`

## Step 50: Project Release Readiness Check

Audits project structure, specs, backend tools, runtime registry, pipelines, CLI, API, frontend, tests, docs, safety boundaries, and report packages. Reports PASS/WARNING/FAIL status with category breakdown.

### Run: `python -m backend.app.tools.run_release_readiness_cli`
### API: `curl http://127.0.0.1:8000/api/release-readiness`

## Step 51: Documentation Cleanup

Creates docs/ directory with architecture overview, user guide, developer guide, and safety/limitations documentation. Adds docs inventory tool to validate documentation completeness.

## Step 52: Final Integration Test

Comprehensive integration test validating the full chain from synthetic BIDS through ALFF, ReHo, FC, confound matrix, and group summary without MATLAB/SPM.

## Step 53: Project Final Summary

Project summary at `reports/project_final_summary.md` documenting all 53 steps, 20 pipeline stages, 30+ tools, 50+ endpoints, and safety architecture.
