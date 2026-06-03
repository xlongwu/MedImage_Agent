$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Push-Location $RepoRoot
try {
    npm --prefix src/frontend run build
    $IndexPath = Join-Path $RepoRoot "src\frontend\dist\index.html"
    if (-not (Test-Path $IndexPath)) {
        throw "Frontend build did not produce $IndexPath"
    }
    Write-Host "Frontend static build ready: $IndexPath"
}
finally {
    Pop-Location
}
