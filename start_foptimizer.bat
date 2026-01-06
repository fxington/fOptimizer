@echo off
setlocal enabledelayedexpansion
title fOptimizer Launcher

cd /d "%~dp0"

if not exist ".venv\" (
    echo [INFO] Fresh install detected. Creating virtual environment...
    python -m venv .venv
    
    if %errorlevel% neq 0 (
        echo [ERROR] Python not found. Please install Python and add it to your PATH.
        pause
        exit /b
    )
    
    echo [INFO] Upgrading pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
)

if exist "pyproject.toml" (
    echo [INFO] Updating dependencies...
    .venv\Scripts\python.exe -m pip install -e . --quiet
) else (
    echo [ERROR] pyproject.toml not found in %cd%
    pause
    exit /b
)

set PYTHONPATH=%~dp0src
echo [INFO] Launching fOptimizer...
start "" ".venv\Scripts\pythonw.exe" -m foptimizer.gui.app
exit