@echo off
REM ============================================================
REM  Build a standalone Windows .exe (no Python required on
REM  the target machine). Run:  scripts\build_exe.bat
REM  Output:  dist\coding-assistant.exe  (project root)
REM ============================================================
setlocal
rem Switch to the project root (one level up from this script)
cd /d "%~dp0.."

echo [1/3] Installing build tools...
python -m pip install --upgrade pip
python -m pip install pyinstaller

echo [2/3] Installing project dependencies...
python -m pip install -r requirements.txt

echo [3/3] Building executable...
python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name coding-assistant ^
    --collect-all coding_assistant ^
    coding_assistant/__main__.py

echo.
echo Done! Your executable is at:  dist\coding-assistant.exe
echo Share this single file - the other person does NOT need Python.
endlocal
