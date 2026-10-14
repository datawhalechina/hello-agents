@echo off
cd /d "%~dp0"
set "PYEXE=%USERPROFILE%\Documents\Codex\runtime\Python312\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
"%PYEXE%" -m pip install -r requirements.txt
echo.
echo Done. Now copy .env.example to .env and fill in your LLM_API_KEY.
pause
