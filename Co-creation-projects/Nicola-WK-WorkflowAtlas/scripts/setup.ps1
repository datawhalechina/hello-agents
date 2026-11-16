$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
python -m pip install uv
if ($LASTEXITCODE -ne 0) { throw 'Could not install uv' }
python -m uv python install 3.13
if ($LASTEXITCODE -ne 0) { throw 'Could not install Python 3.13' }
if (-not (Test-Path -LiteralPath '.venv313\Scripts\python.exe')) {
    python -m uv venv --python 3.13 .venv313
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment' }
}
python -m uv pip sync --python .venv313\Scripts\python.exe requirements.lock
if ($LASTEXITCODE -ne 0) { throw 'Could not install locked dependencies' }
python -m uv pip install --python .venv313\Scripts\python.exe --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw 'Could not install application' }
npm.cmd ci --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Could not install frontend dependencies' }
npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
Write-Host 'Setup complete. Run .\scripts\start.ps1 and open http://127.0.0.1:8000'
