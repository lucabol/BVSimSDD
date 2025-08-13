@echo off
REM Launch BVSim web application (Windows)
REM Optional arguments: [port] [host]
REM Environment variables you can set before calling:
REM   set BVSIM_WEB_PORT=8000
REM   set BVSIM_WEB_HOST=0.0.0.0
REM   set BVSIM_WEB_DEBUG=true
REM   set BVSIM_WEB_WORKERS=4   (requires gunicorn via WSL or not typically used on Windows)

SETLOCAL ENABLEDELAYEDEXPANSION

IF NOT "%1"=="" (
  for /f "delims=0123456789" %%A in ("%1") do set notnum=1
  if NOT defined notnum (
    set BVSIM_WEB_PORT=%1
    shift
  )
)
IF NOT "%1"=="" (
  set BVSIM_WEB_HOST=%1
  shift
)

IF NOT DEFINED BVSIM_WEB_PORT set BVSIM_WEB_PORT=8000
IF NOT DEFINED BVSIM_WEB_HOST set BVSIM_WEB_HOST=0.0.0.0
IF NOT DEFINED BVSIM_WEB_DEBUG set BVSIM_WEB_DEBUG=true

REM Simple run using Python module
python -m bvsim_web
ENDLOCAL
