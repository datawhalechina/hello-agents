$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& .\.venv313\Scripts\python.exe -X utf8 -m pytest
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
& .\.venv313\Scripts\python.exe -X utf8 -m unittest discover -s backend\app\connectors\tests -v
if ($LASTEXITCODE -ne 0) { throw 'Connector tests failed' }
npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
