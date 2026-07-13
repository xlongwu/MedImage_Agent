param(
    [switch]$SkipDependencyInstall,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$SpecPath = Join-Path $RepoRoot "desktop\packaging\pyinstaller_backend.spec"
$GpuManifestScript = Join-Path $RepoRoot "desktop\packaging\write_gpu_runtime_manifest.py"
$DistPath = Join-Path $RepoRoot "desktop\packaging\dist\backend"
$WorkPath = Join-Path $RepoRoot "desktop\packaging\build\backend"
$AnalysisTocPath = Join-Path $WorkPath "pyinstaller_backend\Analysis-00.toc"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not $PythonExe) {
    if (Test-Path $VenvPython) {
        $PythonExe = $VenvPython
    } elseif (-not $SkipDependencyInstall) {
        python -m venv (Join-Path $RepoRoot ".venv")
        $PythonExe = $VenvPython
    } else {
        $PythonExe = "python"
    }
}

Push-Location $RepoRoot
try {
    if (-not $SkipDependencyInstall) {
        & $PythonExe -m pip install -r requirements.txt
        & $PythonExe -m pip install pyinstaller
    }

    # Native preprocessing imports these modules lazily, so PyInstaller can
    # otherwise produce a sidecar that starts successfully but fails only
    # after a real scientific run begins.
    & $PythonExe -c "import numpy, scipy, scipy.ndimage, scipy.signal, nibabel; print('Scientific packaging dependencies available')"
    if ($LASTEXITCODE -ne 0) {
        throw "Scientific packaging dependency check failed. Install requirements.txt before building the backend sidecar."
    }

    & $PythonExe -m PyInstaller $SpecPath `
        --distpath $DistPath `
        --workpath $WorkPath `
        --noconfirm `
        --clean
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller backend build failed with exit code $LASTEXITCODE."
    }

    $ExePath = Join-Path $DistPath "medimage-backend.exe"
    if (-not (Test-Path $ExePath)) {
        throw "PyInstaller did not produce $ExePath"
    }

    & $PythonExe $GpuManifestScript $DistPath --analysis-toc $AnalysisTocPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to write the GPU runtime manifest."
    }

    Write-Host "Backend sidecar built: $ExePath"
}
finally {
    Pop-Location
}
