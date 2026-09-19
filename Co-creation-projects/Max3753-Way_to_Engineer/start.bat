@echo off
title Way to Engineer - 启动器
chcp 65001 >nul

echo ========================================
echo   Way to Engineer - 启动中...
echo ========================================
echo.

REM 检查后端虚拟环境
if not exist "backend\venv\Scripts\python.exe" (
    echo [!] 后端虚拟环境未找到，请先执行:
    echo     cd backend
    echo     python -m venv venv
    echo     venv\Scripts\activate ^&^& pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 检查前端依赖
if not exist "frontend\node_modules" (
    echo [!] 前端依赖未安装，请先执行:
    echo     cd frontend
    echo     npm install
    echo.
    pause
    exit /b 1
)

REM 启动后端 (新窗口)
echo [1/2] 启动后端服务...
start "Way-to-Engineer-Backend" cmd /c "cd /d %~dp0backend && venv\Scripts\activate && python run.py"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端 (新窗口)
echo [2/2] 启动前端服务...
start "Way-to-Engineer-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   后端: http://localhost:8000
echo   前端: http://localhost:5173
echo   按任意键关闭此窗口（服务将继续运行）
echo ========================================
echo.
pause >nul