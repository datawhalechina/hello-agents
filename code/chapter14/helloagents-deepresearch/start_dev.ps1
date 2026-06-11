$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendScript = Join-Path $ProjectRoot "start_backend.ps1"
$FrontendScript = Join-Path $ProjectRoot "start_frontend.ps1"

Write-Host "Opening backend and frontend dev servers in separate PowerShell windows..."

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $BackendScript
)

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $FrontendScript
)

Write-Host "Done. Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:5174"
