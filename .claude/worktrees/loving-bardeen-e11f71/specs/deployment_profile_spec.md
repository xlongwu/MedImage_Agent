# Deployment Profile Specification

This document defines the MVP local and Docker demo deployment profiles for MedImage Agent.

## Goals

Deployment profiles should make the project easier to run, demo, and audit.

They should provide:

- local development profile
- Docker demo profile
- environment variable template
- backend service definition
- frontend service definition
- volume policy
- health check API
- deployment readiness report
- explicit MATLAB / SPM / DPABI external dependency notes

## Scope

Supported in this step:

- local profile YAML
- Docker demo compose YAML
- backend Dockerfile
- frontend Dockerfile
- nginx config
- .env.example
- deployment profile scanner
- API health endpoint
- frontend deployment panel
- lightweight unit test

Unsupported in this step:

- automatic Docker build
- automatic Docker deployment
- cloud deployment
- production authentication
- HTTPS certificate automation
- running pipelines
- launching MATLAB
- running DPABI
- running DPARSF_run
- running DPARSFA_run
- real medical image processing

## Deployment Modes

### local_dev

- backend runs with uvicorn
- frontend runs with npm run dev
- MATLAB/SPM/DPABI may be available locally
- full execution still requires approval gates

### docker_demo

- backend and frontend run in containers
- MATLAB is disabled by default
- DPABI execution is disabled by default
- only read/report/preview/dashboard functions are expected
- work/reports/logs/examples are mounted
- third_party is not copied into images

## Required Outputs

```text
deploy/local_profile.yaml
deploy/docker-compose.demo.yml
deploy/backend.Dockerfile
deploy/frontend.Dockerfile
deploy/nginx.conf
.env.example
work/deployment/deployment_profile.json
reports/deployment/deployment_profile_report.md
```

## Safety Rules

Do not run Docker automatically.
Do not execute pipelines.
Do not launch MATLAB.
Do not run DPABI.
Do not expose rawdata by default.
Do not copy third_party toolboxes into Docker images.
Do not delete files.
Do not deploy to cloud automatically.
