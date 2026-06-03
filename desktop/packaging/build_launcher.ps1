param(
    [switch]$SkipDependencyInstall,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$SpecPath = Join-Path $RepoRoot "desktop\packaging\pyinstaller_desktop_launcher.spec"
$DistPath = Join-Path $RepoRoot "desktop\packaging\dist\launcher"
$WorkPath = Join-Path $RepoRoot "desktop\packaging\build\launcher"
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
    if (-not (Test-Path (Join-Path $RepoRoot "src\frontend\dist\index.html"))) {
        npm --prefix src/frontend run build
    }

    if (-not $SkipDependencyInstall) {
        & $PythonExe -m pip install -r requirements.txt
        & $PythonExe -m pip install pyinstaller
    }

    & $PythonExe -m PyInstaller $SpecPath `
        --distpath $DistPath `
        --workpath $WorkPath `
        --noconfirm `
        --clean

    $ExePath = Join-Path $DistPath "MedImage Agent.exe"
    if (-not (Test-Path $ExePath)) {
        throw "PyInstaller did not produce $ExePath"
    }

    Write-Host "Desktop launcher built: $ExePath"
}
finally {
    Pop-Location
}
