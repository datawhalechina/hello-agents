param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Start', 'Stop')]
    [string]$Action,
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$mainPath = Join-Path $projectRoot 'main.py'

try {
    if ($Action -eq 'Stop') {
        & $pythonPath $mainPath --stop
        exit $LASTEXITCODE
    }

    Set-Location -LiteralPath $projectRoot
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Missing .venv. Follow README to create the virtual environment and install requirements.txt.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) {
        throw 'Build the frontend first: cd frontend, npm.cmd ci, npm.cmd run build.'
    }
    Write-Host "OfferNote: http://127.0.0.1:$Port"
    Write-Host 'Press Ctrl+C to stop. Keep this window open while using OfferNote.'
    & $pythonPath $mainPath --port $Port
    exit $LASTEXITCODE
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
