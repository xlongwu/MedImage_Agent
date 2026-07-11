$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Push-Location $RepoRoot
try {
    $PreviousDicomExecuteUi = $env:VITE_ENABLE_DICOM_EXECUTE_UI
    $HadDicomExecuteUi = Test-Path Env:VITE_ENABLE_DICOM_EXECUTE_UI
    $env:VITE_ENABLE_DICOM_EXECUTE_UI = "1"
    npm --prefix src/frontend run build
    $IndexPath = Join-Path $RepoRoot "src\frontend\dist\index.html"
    if (-not (Test-Path $IndexPath)) {
        throw "Frontend build did not produce $IndexPath"
    }
    Write-Host "Frontend static build ready: $IndexPath"
}
finally {
    if ($HadDicomExecuteUi) {
        $env:VITE_ENABLE_DICOM_EXECUTE_UI = $PreviousDicomExecuteUi
    }
    else {
        Remove-Item Env:VITE_ENABLE_DICOM_EXECUTE_UI -ErrorAction SilentlyContinue
    }
    Pop-Location
}
