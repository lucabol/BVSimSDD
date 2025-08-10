@echo off
REM BVSim CLI wrapper script for Windows
REM This allows users to run 'bvsim' instead of 'python -m bvsim'

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set PYTHONPATH to include the src directory
set "PYTHONPATH=%SCRIPT_DIR%\src;%PYTHONPATH%"

REM Try py first (Python Launcher - most reliable on Windows)
py -m bvsim %* 2>nul
if %errorlevel% equ 0 exit /b 0

REM Try python3 
python3 -m bvsim %* 2>nul  
if %errorlevel% neq 9009 exit /b %errorlevel%

REM Try python (suppress Microsoft Store message)
python -m bvsim %* 2>nul
if %errorlevel% neq 9009 exit /b %errorlevel%

REM If we get here, no Python worked
echo ERROR: Python is not installed or not accessible
echo.
echo Please install Python 3.7+ from https://python.org
echo Make sure to check "Add Python to PATH" during installation
echo.
echo If Python is installed, try running one of these commands directly:
echo   py -m bvsim --help
echo   python -m bvsim --help
exit /b 1