function Get-PpaArcGisPython([string]$Root) {
    if ($env:PPA3_PRO_PYTHON) {
        if (-not (Test-Path -LiteralPath $env:PPA3_PRO_PYTHON -PathType Leaf)) {
            throw "PPA3_PRO_PYTHON does not exist: $env:PPA3_PRO_PYTHON"
        }
        return (Resolve-Path -LiteralPath $env:PPA3_PRO_PYTHON).Path
    }
    if ($Root) {
        $runtimeConfig = Join-Path $Root 'harness-runtime.json'
        if (Test-Path -LiteralPath $runtimeConfig -PathType Leaf) {
            $savedPython = (Get-Content -LiteralPath $runtimeConfig -Raw | ConvertFrom-Json).python
            if ($savedPython -and (Test-Path -LiteralPath $savedPython -PathType Leaf)) {
                return (Resolve-Path -LiteralPath $savedPython).Path
            }
        }
    }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe'),
        (Join-Path $env:ProgramFiles 'ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe')
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw 'ArcGIS Pro Python was not found. Install ArcGIS Pro or set PPA3_PRO_PYTHON.'
}

function Get-PpaLocalRoot([string]$Root) {
    if ($Root) { return [System.IO.Path]::GetFullPath($Root) }
    if ($env:PPA3_LOCAL_ROOT) { return [System.IO.Path]::GetFullPath($env:PPA3_LOCAL_ROOT) }
    return 'C:\PPA3Testing'
}
