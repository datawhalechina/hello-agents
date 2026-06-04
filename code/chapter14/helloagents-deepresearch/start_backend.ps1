$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Backend virtual environment not found: $PythonExe"
}

Set-Location $BackendDir
Write-Host "Starting backend at http://127.0.0.1:8000 ..."
& $PythonExe "src/main.py"
