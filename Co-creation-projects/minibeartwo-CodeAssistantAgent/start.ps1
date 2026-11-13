param([switch]$Dev)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv/Scripts/python.exe'))) { throw 'Run .\setup.ps1 first.' }
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'desktop/node_modules'))) { throw 'Run .\setup.ps1 first.' }
$previousLocation = Get-Location
$previousRunAsNode = $env:ELECTRON_RUN_AS_NODE
try {
    [Environment]::SetEnvironmentVariable('ELECTRON_RUN_AS_NODE', $null, 'Process')
    Set-Location -LiteralPath (Join-Path $PSScriptRoot 'desktop')
    if ($Dev) { & npm.cmd run dev } else { & npm.cmd start }
    if ($LASTEXITCODE -ne 0) { throw "Client exited with code $LASTEXITCODE" }
} finally {
    [Environment]::SetEnvironmentVariable('ELECTRON_RUN_AS_NODE', $previousRunAsNode, 'Process')
    Set-Location -LiteralPath $previousLocation
}
