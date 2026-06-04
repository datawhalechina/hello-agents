$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $ProjectRoot "frontend"

Set-Location $FrontendDir
Write-Host "Starting frontend at http://localhost:5173 ..."
npm run dev
