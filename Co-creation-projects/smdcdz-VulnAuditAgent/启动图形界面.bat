@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "PYEXE=%USERPROFILE%\Documents\Codex\runtime\Python312\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
"%PYEXE%" app.py
if errorlevel 1 pause
