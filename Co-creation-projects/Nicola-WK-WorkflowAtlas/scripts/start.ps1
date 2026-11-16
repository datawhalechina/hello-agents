param([int]$Port = 8000, [switch]$Background)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv313\Scripts\python.exe')) {
    throw 'Run scripts\setup.ps1 first'
}
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    throw 'Build the frontend with npm run build --prefix frontend first'
}
if ($Background) {
    if (Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port is already in use; stop the existing service before starting another instance"
    }
    New-Item -ItemType Directory -Force -Path '.runtime' | Out-Null
    if (Test-Path -LiteralPath '.runtime\server.pid') {
        $recordedId = Get-Content -LiteralPath '.runtime\server.pid'
        if (Get-Process -Id $recordedId -ErrorAction SilentlyContinue) {
            throw 'A recorded background process is running; stop it with scripts\stop.ps1 first'
        }
    }
    $executablePath = (Resolve-Path -LiteralPath '.venv313\Scripts\python.exe').Path
    $serverProcess = Start-Process -FilePath $executablePath -ArgumentList @('-X','utf8','-m','uvicorn','app.main:create_app','--factory','--host','127.0.0.1','--port',"$Port") -WorkingDirectory (Get-Location).Path -WindowStyle Hidden -RedirectStandardOutput '.runtime\server.log' -RedirectStandardError '.runtime\server-error.log' -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $serverProcess.Refresh()
        if ($serverProcess.HasExited) { break }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 1
            if ($health.status -eq 'ok') { $ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 200
    }
    if (-not $ready) {
        $serverProcess.Refresh()
        if (-not $serverProcess.HasExited) { & taskkill.exe /PID $serverProcess.Id /T /F | Out-Null }
        throw 'Server did not become healthy; inspect .runtime\server-error.log'
    }
    Set-Content -LiteralPath '.runtime\server.pid' -Value $serverProcess.Id
    Write-Host "Background server launched (PID $($serverProcess.Id)); open http://127.0.0.1:$Port"
} else {
    & .\.venv313\Scripts\python.exe -X utf8 -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port $Port
}
