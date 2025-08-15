#!/usr/bin/env bash
set -euo pipefail

# Defaults (override by exporting before running)
APP_NAME="${APP_NAME:-bvsim-web}"
RESOURCE_GROUP="${RESOURCE_GROUP:-bvsim-rg}"
ENVIRONMENT="${ENVIRONMENT:-bvsim-env}"
LOCATION="${LOCATION:-westeurope}"
SOURCE_DIR="${SOURCE_DIR:-.}"

echo "Deploying $APP_NAME to $RESOURCE_GROUP in $LOCATION (env: $ENVIRONMENT) from $SOURCE_DIR"

# Ensure containerapp extension is present
az extension add --name containerapp --upgrade >/dev/null

# Deploy from local filesystem
az containerapp up \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$ENVIRONMENT" \
  --source "$SOURCE_DIR"

# Print URL
APP_FQDN=$(az containerapp show -g "$RESOURCE_GROUP" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv || true)
if [[ -n "${APP_FQDN:-}" ]]; then
  echo "App URL: https://$APP_FQDN"
else
  echo "Deployment completed. Retrieve URL later with: az containerapp show -g $RESOURCE_GROUP -n $APP_NAME --query properties.configuration.ingress.fqdn -o tsv"
fi
