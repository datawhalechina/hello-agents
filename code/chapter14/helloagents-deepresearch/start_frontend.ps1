$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $ProjectRoot "frontend"

Set-Location $FrontendDir
Write-Host "Starting frontend at http://127.0.0.1:5174 ..."
npm run dev -- --host 127.0.0.1 --port 5174
