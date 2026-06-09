<#
.SYNOPSIS
  Internal FunRaw/T1Raw DICOM conversion smoke — Phase 4I-1.
  Runs the internal-only prototype on the real DemoData project.

.PARAMETER ProjectId
  Project ID from POST /api/projects/create (required).

.PARAMETER ConversionRunId
  Conversion run ID from persist-plan response (required).

.PARAMETER PythonExe
  Path to Python executable (default: D:\Anaconda3\envs\mamba\python.exe).

.PARAMETER EnvRoot
  Root of the mamba environment (default: D:\Anaconda3\envs\mamba).
#>

param(
    [Parameter(Mandatory)]
    [string]$ProjectId,
    [Parameter(Mandatory)]
    [string]$ConversionRunId,
    [string]$PythonExe = "D:\Anaconda3\envs\mamba\python.exe",
    [string]$EnvRoot = "D:\Anaconda3\envs\mamba"
)

$ErrorActionPreference = "Stop"

# ═══════════════════════════════════════════════════════════════════════
# 1. Set PATH and env flags
# ═══════════════════════════════════════════════════════════════════════
$env:PATH = "$EnvRoot;$EnvRoot\Scripts;$EnvRoot\Library\bin;$env:PATH"

$env:MEDIMAGE_ENABLE_DICOM_CONVERSION                       = "1"
$env:MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE                  = "1"
$env:MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE                     = "1"
$env:MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION          = "1"
$env:MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE                     = "1"
$env:MEDIMAGE_ALLOW_INTERNAL_USER_DICOM_CONVERSION_PROTOTYPE = "1"
$env:MEDIMAGE_MATLAB_ENABLED                                = "1"
$env:MEDIMAGE_SPM_SMOKE_ENABLED                             = "1"
$env:MEDIMAGE_ENABLE_REVIEWED_EXECUTION                     = "1"
$env:MEDIMAGE_ENABLE_REAL_PREPROCESSING                     = "1"

Write-Host "=== Internal FunRaw/T1Raw Conversion Smoke ===" -ForegroundColor Cyan
Write-Host "ProjectId: $ProjectId"
Write-Host "ConversionRunId: $ConversionRunId"

# ═══════════════════════════════════════════════════════════════════════
# 2. Verify tools
# ═══════════════════════════════════════════════════════════════════════
$dcm = & $PythonExe -c "import shutil; print(shutil.which('dcm2niix') or 'NOT FOUND')"
Write-Host "dcm2niix: $dcm"
& $PythonExe -c "import pydicom; print('pydicom ok')"

# ═══════════════════════════════════════════════════════════════════════
# 3. Run internal conversion
# ═══════════════════════════════════════════════════════════════════════
$pyScript = @"
import json, os
from pathlib import Path
from src.backend.app.services.dicom_conversion_execution import (
    run_internal_user_dicom_conversion_from_persisted_package,
)
from src.backend.app.services.mock_store import mock_store

project = mock_store.get_project('$ProjectId')
if not project:
    print(json.dumps({"error": "Project not found: $ProjectId"}))
    exit(1)

metadata = project.metadata or {}
project_dir = metadata.get('project_dir', '')
rawdata_dir = metadata.get('rawdata_dir', '')

result = run_internal_user_dicom_conversion_from_persisted_package(
    project_id='$ProjectId',
    conversion_run_id='$ConversionRunId',
    env=None,
    project_dir=project_dir,
    rawdata_dir=rawdata_dir,
)

output = result.model_dump()
print(json.dumps(output, indent=2, default=str))
"@

$tempPy = Join-Path $env:TEMP "internal_conversion_smoke_$PID.py"
$pyScript | Out-File -FilePath $tempPy -Encoding utf8

& $PythonExe $tempPy
$exitCode = $LASTEXITCODE
Remove-Item $tempPy -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "USER RAWDATA CONVERSION REMAINS INTERNAL-ONLY AND DISABLED FOR PUBLIC USE" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

exit $exitCode
