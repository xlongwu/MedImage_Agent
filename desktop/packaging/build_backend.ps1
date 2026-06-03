param(
    [switch]$SkipDependencyInstall,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$SpecPath = Join-Path $RepoRoot "desktop\packaging\pyinstaller_backend.spec"
$DistPath = Join-Path $RepoRoot "desktop\packaging\dist\backend"
$WorkPath = Join-Path $RepoRoot "desktop\packaging\build\backend"
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

    & $PythonExe -m PyInstaller $SpecPath `
        --distpath $DistPath `
        --workpath $WorkPath `
        --noconfirm `
        --clean

    $ExePath = Join-Path $DistPath "medimage-backend.exe"
    if (-not (Test-Path $ExePath)) {
        throw "PyInstaller did not produce $ExePath"
    }

    Write-Host "Backend sidecar built: $ExePath"
}
finally {
    Pop-Location
}
