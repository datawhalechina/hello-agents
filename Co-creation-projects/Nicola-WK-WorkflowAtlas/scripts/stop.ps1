$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath '.runtime\server.pid') {
    $recordedId = [int](Get-Content -LiteralPath '.runtime\server.pid')
    $serverProcess = Get-Process -Id $recordedId -ErrorAction SilentlyContinue
    if ($serverProcess) {
        $expectedPath = (Resolve-Path -LiteralPath '.venv313\Scripts\python.exe').Path
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $recordedId"
        if ($serverProcess.Path -ne $expectedPath -or $processInfo.CommandLine -notlike '*app.main:create_app*') {
            throw 'Recorded PID belongs to a different process; refusing to stop it'
        }
        # The Windows venv launcher has a child interpreter which owns the
        # listening socket. Stop the validated application tree together.
        & taskkill.exe /PID $recordedId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop the recorded application process tree' }
    }
    Remove-Item -LiteralPath '.runtime\server.pid'
    Write-Host 'Background preview stopped'
}
