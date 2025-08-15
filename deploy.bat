@echo off
setlocal enabledelayedexpansion

REM Defaults (override before running)
if not defined APP_NAME set APP_NAME=bvsim-web
if not defined RESOURCE_GROUP set RESOURCE_GROUP=bvsim-rg
if not defined ENVIRONMENT set ENVIRONMENT=bvsim-env
if not defined LOCATION set LOCATION=westeurope
if not defined SOURCE_DIR set SOURCE_DIR=.

echo Deploying %APP_NAME% to %RESOURCE_GROUP% in %LOCATION% (env: %ENVIRONMENT%) from %SOURCE_DIR%

REM Ensure containerapp extension
az extension add --name containerapp --upgrade >nul 2>nul

REM Deploy from local filesystem
az containerapp up ^
  --name "%APP_NAME%" ^
  --resource-group "%RESOURCE_GROUP%" ^
  --location "%LOCATION%" ^
  --environment "%ENVIRONMENT%" ^
  --source "%SOURCE_DIR%"

REM Print URL
for /f "tokens=* usebackq" %%i in (`az containerapp show -g "%RESOURCE_GROUP%" -n "%APP_NAME%" --query properties.configuration.ingress.fqdn -o tsv 2^>nul`) do set APP_FQDN=%%i
if defined APP_FQDN (
  echo App URL: https://%APP_FQDN%
) else (
  echo Deployment completed. Retrieve URL later with: az containerapp show -g %RESOURCE_GROUP% -n %APP_NAME% --query properties.configuration.ingress.fqdn -o tsv
)
