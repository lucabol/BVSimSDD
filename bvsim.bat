@echo off
REM BVSim CLI wrapper script for Windows
REM This allows users to run 'bvsim' instead of 'python -m bvsim'

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set PYTHONPATH to include the src directory
set "PYTHONPATH=%SCRIPT_DIR%\src;%PYTHONPATH%"

REM Try python commands in order, use the first one that works
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    python3 -m bvsim %*
    exit /b %errorlevel%
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    python -m bvsim %*
    exit /b %errorlevel%
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -m bvsim %*
    exit /b %errorlevel%
)

REM If no Python found, show helpful error message
echo ERROR: Python is not installed or not in PATH
echo Please install Python 3.7+ from https://python.org
echo Make sure to check "Add Python to PATH" during installation
exit /b 1