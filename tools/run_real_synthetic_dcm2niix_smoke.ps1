<#
.SYNOPSIS
  Local synthetic dcm2niix smoke evidence runner — Phase 4H-3d.
  Sets PATH + env flags, runs smoke tests, reports evidence.

.DESCRIPTION
  Runs the Phase 4H real dcm2niix synthetic smoke integration test with
  all required environment flags and PATH configured for the local
  mamba Python environment.  Does NOT convert user rawdata.

.PARAMETER PythonExe
  Path to Python executable (default: D:\Anaconda3\envs\mamba\python.exe).

.PARAMETER EnvRoot
  Root of the mamba conda environment (default: D:\Anaconda3\envs\mamba).

.PARAMETER SkipSafetyRegression
  If set, skip the Phase 2/3/SPM safety regression tests.
#>

param(
    [string]$PythonExe = "D:\Anaconda3\envs\mamba\python.exe",
    [string]$EnvRoot = "D:\Anaconda3\envs\mamba",
    [switch]$SkipSafetyRegression
)

$ErrorActionPreference = "Stop"

# ═══════════════════════════════════════════════════════════════════════
# 1. Set PATH
# ═══════════════════════════════════════════════════════════════════════
$env:PATH = "$EnvRoot;$EnvRoot\Scripts;$EnvRoot\Library\bin;$env:PATH"
Write-Host "=== PATH configured ===" -ForegroundColor Cyan
Write-Host "Python: $PythonExe"
Write-Host "EnvRoot: $EnvRoot"

# ═══════════════════════════════════════════════════════════════════════
# 2. Set all 9 required MEDIMAGE flags
# ═══════════════════════════════════════════════════════════════════════
$env:MEDIMAGE_ENABLE_DICOM_CONVERSION         = "1"
$env:MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE    = "1"
$env:MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE       = "1"
$env:MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION = "1"
$env:MEDIMAGE_ALLOW_REAL_DCM2NIIX_SMOKE       = "1"
$env:MEDIMAGE_MATLAB_ENABLED                  = "1"
$env:MEDIMAGE_SPM_SMOKE_ENABLED               = "1"
$env:MEDIMAGE_ENABLE_REVIEWED_EXECUTION       = "1"
$env:MEDIMAGE_ENABLE_REAL_PREPROCESSING       = "1"

Write-Host "=== MEDIMAGE flags set ===" -ForegroundColor Cyan
& $PythonExe -c "import os; [print(f'  {k}={v}') for k,v in sorted(os.environ.items()) if k.startswith('MEDIMAGE_')]"

# ═══════════════════════════════════════════════════════════════════════
# 3. Tool availability checks
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=== Tool availability ===" -ForegroundColor Cyan

$dcm2niixPath = & $PythonExe -c "import shutil; p=shutil.which('dcm2niix'); print(p if p else 'NOT FOUND')"
Write-Host "dcm2niix: $dcm2niixPath"

$pydicomCheck = & $PythonExe -c "import pydicom; print('pydicom OK')" 2>&1
if ($LASTEXITCODE -eq 0) { Write-Host "pydicom: OK" } else { Write-Host "pydicom: MISSING" }

# ═══════════════════════════════════════════════════════════════════════
# 4. Run unit smoke evidence tests
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=== Unit: smoke evidence tests ===" -ForegroundColor Cyan
& $PythonExe -m pytest tests/unit/test_dicom_conversion_smoke_evidence.py `
    --tb=short --basetemp=.pytest_tmp
$unitExit = $LASTEXITCODE

# ═══════════════════════════════════════════════════════════════════════
# 5. Run integration synthetic smoke (real dcm2niix)
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=== Integration: real synthetic dcm2niix smoke ===" -ForegroundColor Cyan
& $PythonExe -m pytest tests/integration/test_dicom_conversion_real_synthetic_smoke.py `
    --tb=long --basetemp=.pytest_tmp -s
$integExit = $LASTEXITCODE

if ($integExit -eq 0) {
    Write-Host ""
    Write-Host "REAL SYNTHETIC DCM2NIIX SMOKE PASSED" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "REAL SYNTHETIC SMOKE SKIPPED OR FAILED (exit=$integExit)" -ForegroundColor Yellow
    Write-Host "Inspect output above for skip reason." -ForegroundColor Yellow
}

# ═══════════════════════════════════════════════════════════════════════
# 6. Safety regression (optional)
# ═══════════════════════════════════════════════════════════════════════
if (-not $SkipSafetyRegression) {
    Write-Host ""
    Write-Host "=== Safety regression ===" -ForegroundColor Cyan
    & $PythonExe -m pytest `
        tests/unit/test_phase3_feature_regression_matrix.py `
        tests/unit/test_spm_safe_allowlist_policy.py `
        tests/unit/test_phase2_feature_regression_matrix.py `
        --tb=short --basetemp=.pytest_tmp
}

# ═══════════════════════════════════════════════════════════════════════
# 7. Summary
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "USER RAWDATA CONVERSION REMAINS DISABLED" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

exit $integExit
