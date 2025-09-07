@echo off
REM Multi-Platform Claude Code Launcher - Windows Batch Wrapper
REM Calls the unified Python launcher

setlocal

REM 用户可以在这里修改项目路径，默认为脚本的父目录（项目根目录）
set "PROJECT_DIR=%~dp0.."
set "LAUNCHER=%PROJECT_DIR%\bin\launcher.py"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.7+ first.
    exit /b 1
)

REM Check if launcher exists
if not exist "%LAUNCHER%" (
    echo ❌ Launcher script not found: %LAUNCHER%
    exit /b 1
)

REM Pass all arguments to the Python launcher
python "%LAUNCHER%" %*
exit /b %errorlevel%