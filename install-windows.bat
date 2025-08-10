@echo off
echo BVSim Windows Installation Script
echo ==================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        py --version >nul 2>&1
        if %errorlevel% neq 0 (
            echo ERROR: Python is not installed or not in PATH
            echo Please install Python 3.7+ from https://python.org
            echo Make sure to check "Add Python to PATH" during installation
            pause
            exit /b 1
        ) else (
            echo Found Python via 'py' command
        )
    ) else (
        echo Found Python 3
    )
) else (
    echo Found Python
)

echo.
echo Verifying BVSim installation...

REM Test the wrapper script
call bvsim.bat --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: BVSim installation test failed
    echo Please ensure you're running this from the BVSim directory
    pause
    exit /b 1
)

echo.
echo ✓ BVSim installation verified!
echo.
echo Usage:
echo   bvsim.bat --help              # Show help
echo   bvsim.bat skills               # Analyze skills impact
echo   bvsim.bat compare              # Compare teams
echo   bvsim.bat simulate             # Simulate matches
echo.
echo To use 'bvsim' globally (without .bat extension):
echo 1. Add this directory to your PATH, or
echo 2. Copy bvsim.bat to a directory already in your PATH
echo.
echo Quick test:
call bvsim.bat --version
echo.
echo Installation complete! Press any key to exit.
pause >nul