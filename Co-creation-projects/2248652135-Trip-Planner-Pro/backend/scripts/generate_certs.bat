@echo off
REM 生成自签名SSL证书用于本地HTTPS开发
REM 使用前请确保OpenSSL已安装

set CERT_DIR=%~dp0..\certs

if not exist "%CERT_DIR%" mkdir "%CERT_DIR%"

echo Generating self-signed SSL certificates...
openssl req -x509 -newkey rsa:2048 -keyout "%CERT_DIR%\key.pem" -out "%CERT_DIR%\cert.pem" -days 365 -nodes -subj "//CN=localhost"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ SSL certificates generated successfully!
    echo   Cert: %CERT_DIR%\cert.pem
    echo   Key:  %CERT_DIR%\key.pem
    echo.
    echo To enable HTTPS, set in backend\.env:
    echo   SSL_ENABLED=true
) else (
    echo.
    echo ❌ Failed to generate certificates.
    echo Please make sure OpenSSL is installed and available in PATH.
)
