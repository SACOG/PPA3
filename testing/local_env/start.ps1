param(
    [string]$Root,
    [string]$Python,
    [int]$Port = 5000,
    [switch]$SkipDoctor
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if ($Python) { $env:PPA3_PRO_PYTHON = $Python }
$localRoot = Get-PpaLocalRoot $Root
$python = Get-PpaArcGisPython $localRoot
$env:PPA3_LOCAL_ROOT = $localRoot
$env:PPA3_PORT = [string]$Port
if (-not $SkipDoctor) {
    & $python (Join-Path $PSScriptRoot 'doctor.py') --root $localRoot --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Environment check failed; see the diagnostics above.' }
}
Write-Host "Starting PPA3 Test Harness at http://127.0.0.1:$Port"
& $python (Join-Path $PSScriptRoot 'webapp\app.py')
exit $LASTEXITCODE
