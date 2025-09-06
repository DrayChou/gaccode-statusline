@echo off
REM Multi-Platform Claude Code Launcher - Windows Batch Wrapper
REM Calls the unified Python launcher

setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%launcher.py"

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