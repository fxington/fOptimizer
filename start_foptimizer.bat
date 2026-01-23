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
)

if exist "pyproject.toml" (
    echo [INFO] Upgrading installation packages...
    .venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel --quiet || goto :error_exit
    echo [INFO] Updating dependencies...
    .venv\Scripts\python.exe -m pip install -e . --quiet || goto :error_exit
    call ".venv\Scripts\python.exe" -c "import static_ffmpeg; static_ffmpeg.add_paths()"
) else (
    echo [ERROR] pyproject.toml not found in %cd%
    pause
    exit /b
)

set PYTHONPATH=%~dp0src
echo [INFO] Launching fOptimizer...
".venv\Scripts\python.exe" -c "import foptimizer.gui.app" 2>nul
if %errorlevel% neq 0 goto :error_exit
start "" ".venv\Scripts\pythonw.exe" -m foptimizer.gui.app
exit

:error_exit
".venv\Scripts\python.exe" -m foptimizer.gui.app
pause