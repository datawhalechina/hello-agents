param([switch]$Dev, [switch]$Notebook)
$ErrorActionPreference = 'Stop'
$previousPythonHome = $env:PYTHONHOME
$previousPythonPath = $env:PYTHONPATH
$previousLocation = Get-Location
try {
    Set-Location -LiteralPath $PSScriptRoot
    [Environment]::SetEnvironmentVariable('PYTHONHOME', $null, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONPATH', $null, 'Process')
    $nodeVersion = [Version]((& node --version).TrimStart('v'))
    if ($LASTEXITCODE -ne 0 -or $nodeVersion -lt [Version]'22.12.0') { throw 'Node.js 22.12+ is required.' }
    $pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -E -m venv .venv }
        else { & python -E -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create .venv. Install Python 3.11+ first.' }
    }
    & $pythonPath -E -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
    $requirements = if ($Dev) { 'requirements-dev.txt' } else { 'requirements.txt' }
    if (Get-Command uv -ErrorAction SilentlyContinue) { & uv pip install --python $pythonPath -r $requirements }
    else {
        & $pythonPath -E -m ensurepip --upgrade
        if ($LASTEXITCODE -ne 0) { throw 'Failed to initialize pip.' }
        & $pythonPath -E -m pip install -r $requirements
    }
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    if ($Notebook) {
        if (Get-Command uv -ErrorAction SilentlyContinue) { & uv pip install --python $pythonPath -r requirements-notebook.txt }
        else { & $pythonPath -E -m pip install -r requirements-notebook.txt }
        if ($LASTEXITCODE -ne 0) { throw 'Notebook dependency installation failed.' }
    }
    Set-Location -LiteralPath (Join-Path $PSScriptRoot 'desktop')
    & npm.cmd ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Client dependency installation failed.' }
    & node node_modules/electron/install.js
    if ($LASTEXITCODE -ne 0) { throw 'Electron download failed. See the README network troubleshooting steps.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Client build failed.' }
    Write-Host 'Setup complete. Run: .\start.ps1'
} finally {
    [Environment]::SetEnvironmentVariable('PYTHONHOME', $previousPythonHome, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONPATH', $previousPythonPath, 'Process')
    Set-Location -LiteralPath $previousLocation
}
