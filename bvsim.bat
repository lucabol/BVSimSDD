@echo off
REM BVSim CLI wrapper script for Windows
REM This allows users to run 'bvsim' instead of 'python -m bvsim'

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set PYTHONPATH to include the src directory
set "PYTHONPATH=%SCRIPT_DIR%\src;%PYTHONPATH%"

REM Find the first available Python command by testing quietly
set "PYTHON_CMD="

REM Test python3 (quietly check if it exists)
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python3"
    goto :run_bvsim
)

REM Test python (quietly check if it exists)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :run_bvsim
)

REM Test py (quietly check if it exists)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :run_bvsim
)

REM If no Python found, show helpful error message
echo ERROR: Python is not installed or not in PATH
echo Please install Python 3.7+ from https://python.org
echo Make sure to check "Add Python to PATH" during installation
exit /b 1

:run_bvsim
REM Execute the bvsim module with the detected Python command
%PYTHON_CMD% -m bvsim %*