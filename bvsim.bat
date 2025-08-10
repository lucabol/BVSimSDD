@echo off
REM BVSim CLI wrapper script for Windows
REM This allows users to run 'bvsim' instead of 'python -m bvsim'

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set PYTHONPATH to include the src directory
set "PYTHONPATH=%SCRIPT_DIR%\src;%PYTHONPATH%"

REM Execute the bvsim module with all arguments
REM Try python3 first (preferred), then python, then py
python3 -m bvsim %*
if %errorlevel% neq 0 (
    python -m bvsim %*
    if %errorlevel% neq 0 (
        py -m bvsim %*
    )
)