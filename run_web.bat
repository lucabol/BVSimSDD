@echo off
REM BVSim Web launcher (Windows)
REM Usage: run_web.bat [port] [host]
REM Examples:
REM   run_web.bat             (defaults 8000 0.0.0.0)
REM   run_web.bat 5000        (port 5000)
REM   run_web.bat 5000 127.0.0.1
REM Environment overrides (set before calling or via args):
REM   BVSIM_WEB_PORT (default 8000)
REM   BVSIM_WEB_HOST (default 0.0.0.0)
REM   BVSIM_WEB_DEBUG (default true)
REM   BVSIM_WEB_WORKERS (if set and gunicorn present, use gunicorn)

SETLOCAL ENABLEDELAYEDEXPANSION

REM Resolve script directory
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
pushd "%SCRIPT_DIR%" >nul

REM Ensure src on PYTHONPATH so module imports work when run from Explorer
set "PYTHONPATH=%SCRIPT_DIR%\src;%PYTHONPATH%"

REM Positional override for port (numeric)
if not "%~1"=="" (
  set "_ARG1=%~1"
  for /f "delims=0123456789" %%A in ("%_ARG1%") do set _NONNUM=1
  if not defined _NONNUM (
    set "BVSIM_WEB_PORT=%_ARG1%"
    shift
  )
  set "_NONNUM="
)
REM Positional override for host
if not "%~1"=="" (
  set "BVSIM_WEB_HOST=%~1"
  shift
)

if not defined BVSIM_WEB_PORT set "BVSIM_WEB_PORT=8000"
if not defined BVSIM_WEB_HOST set "BVSIM_WEB_HOST=0.0.0.0"
if not defined BVSIM_WEB_DEBUG set "BVSIM_WEB_DEBUG=true"

echo Launching BVSim web on %BVSIM_WEB_HOST%:%BVSIM_WEB_PORT% (debug=%BVSIM_WEB_DEBUG%)

REM If BVSIM_WEB_WORKERS set and gunicorn available, attempt gunicorn (Python on Windows may not have it)
if defined BVSIM_WEB_WORKERS (
  py -c "import gunicorn" 2>nul 1>nul && (
    echo Using gunicorn with %BVSIM_WEB_WORKERS% workers
    py -m gunicorn -w %BVSIM_WEB_WORKERS% -b %BVSIM_WEB_HOST%:%BVSIM_WEB_PORT% bvsim_web.__main__:app
    goto :EOF
  )
)

REM Try runners similar to bvsim.bat for robustness
py -m bvsim_web 2>nul
if %errorlevel% equ 0 goto :EOF

python3 -m bvsim_web 2>nul
if %errorlevel% neq 9009 if %errorlevel% equ 0 goto :EOF
if %errorlevel% neq 9009 goto :EOF

python -m bvsim_web 2>nul
if %errorlevel% equ 0 goto :EOF

echo ERROR: Could not start BVSim web (Python not found?).
echo Tried: py, python3, python.
echo Ensure Python 3 is installed and on PATH.
popd >nul
exit /b 1

ENDLOCAL
