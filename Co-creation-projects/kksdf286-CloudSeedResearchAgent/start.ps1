param(
    [string]$Python = "python",
    [string]$EnvFile = "",
    [int]$Port = 8765
)
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Push-Location -LiteralPath $PSScriptRoot
try {
    $launchArgs = @("-u", "main.py", "serve", "--port", "$Port")
    if ($EnvFile) { $launchArgs += @("--env-file", $EnvFile) }
    & $Python @launchArgs
    if ($LASTEXITCODE -ne 0) { throw "启动失败，请检查Python环境和配置。" }
} finally {
    Pop-Location
}
