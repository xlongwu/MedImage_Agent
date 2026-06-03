param(
    [switch]$SkipFullPytest,
    [switch]$SkipDependencyInstall,
    [switch]$SkipNpmInstall,
    [string]$ElectronRuntimeZip,
    [string]$NsisArchive,
    [string]$NsisResourcesArchive,
    [switch]$DirOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Push-Location $RepoRoot
try {
    python -m pytest tests/unit/test_desktop_backend_entry.py -v
    python -m pytest tests/unit/test_desktop_packaging_contract.py -v
    python -m pytest tests/unit/test_gui_reviewed_execution_blocklist.py -v
    python -m pytest tests/unit/test_gui_model_mock_real_boundary.py -v
    python -m pytest tests/unit/test_execute_reviewed_api.py -v

    if (-not $SkipFullPytest) {
        python -m pytest --tb=short
    }

    & (Join-Path $RepoRoot "desktop\packaging\build_frontend.ps1")
    & (Join-Path $RepoRoot "desktop\packaging\build_backend.ps1") -SkipDependencyInstall:$SkipDependencyInstall
    & (Join-Path $RepoRoot "desktop\packaging\build_launcher.ps1") -SkipDependencyInstall:$SkipDependencyInstall
    $DesktopBuildArgs = @{
        SkipNpmInstall = $SkipNpmInstall
    }
    if ($ElectronRuntimeZip) {
        $DesktopBuildArgs.ElectronRuntimeZip = $ElectronRuntimeZip
    }
    if ($NsisArchive) {
        $DesktopBuildArgs.NsisArchive = $NsisArchive
    }
    if ($NsisResourcesArchive) {
        $DesktopBuildArgs.NsisResourcesArchive = $NsisResourcesArchive
    }
    if ($DirOnly) {
        $DesktopBuildArgs.DirOnly = $true
    }
    & (Join-Path $RepoRoot "desktop\packaging\build_desktop.ps1") @DesktopBuildArgs

    Write-Host "Windows desktop packaging complete."
    Write-Host "Electron installer/portable artifacts are under desktop\electron\dist."
    Write-Host "PyInstaller launcher fallback is under desktop\packaging\dist\launcher."
}
finally {
    Pop-Location
}
