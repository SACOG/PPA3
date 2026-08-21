param(
    [string]$Root,
    [string]$Python,
    [string]$CandidateSource,
    [switch]$SkipDataRefresh,
    [switch]$SkipArchiveSchemas,
    [switch]$SkipDependencyInstall
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if ($Python) { $env:PPA3_PRO_PYTHON = $Python }
$localRoot = Get-PpaLocalRoot $Root
$python = Get-PpaArcGisPython $localRoot
$env:PPA3_LOCAL_ROOT = $localRoot
New-Item -ItemType Directory -Path $localRoot -Force | Out-Null
@{ python = $python } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $localRoot 'harness-runtime.json') -Encoding utf8

Write-Host "ArcGIS Python: $python"
Write-Host "Sandbox root:  $localRoot"

if (-not $SkipDependencyInstall) {
    & $python -c "import flask, jinja2, yaml, pytest" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Installing local-harness Python packages...'
        & $python -m pip install Flask Jinja2 PyYAML pytest
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    }
}

if (-not $SkipDataRefresh) {
    $buildArgs = @((Join-Path $PSScriptRoot 'build_test_gdb.py'), '--root', $localRoot)
    if ($CandidateSource) { $buildArgs += @('--candidate-source', $CandidateSource) }
    & $python @buildArgs
    if ($LASTEXITCODE -ne 0) { throw 'Sandbox data build failed.' }
}
if (-not $SkipArchiveSchemas) {
    & $python (Join-Path $PSScriptRoot 'build_run_tables.py') --root $localRoot
    if ($LASTEXITCODE -ne 0) { throw 'Archive-schema build failed.' }
}

& $python -m pytest (Join-Path $PSScriptRoot 'tests') -q -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw 'Local-harness tests failed.' }
& $python (Join-Path $PSScriptRoot 'doctor.py') --root $localRoot
if ($LASTEXITCODE -ne 0) { throw 'Environment setup finished with failed health checks.' }
Write-Host 'Setup complete. Launch with testing\local_env\start.ps1.'
