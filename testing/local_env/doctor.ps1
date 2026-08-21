param(
    [string]$Root,
    [string]$Python,
    [int]$Port = 5000
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if ($Python) { $env:PPA3_PRO_PYTHON = $Python }
$localRoot = Get-PpaLocalRoot $Root
$python = Get-PpaArcGisPython $localRoot
& $python (Join-Path $PSScriptRoot 'doctor.py') --root $localRoot --port $Port
exit $LASTEXITCODE
