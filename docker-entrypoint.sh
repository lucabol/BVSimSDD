#!/bin/sh
set -eu

# Defaults (can be overridden via env)
: "${BVSIM_WEB_HOST:=0.0.0.0}"
: "${BVSIM_WEB_PORT:=8000}"
: "${BVSIM_WEB_WORKERS:=2}"
: "${BVSIM_WEB_TIMEOUT:=60}"
: "${BVSIM_WEB_LOGLEVEL:=info}"

# Seed templates into /data/templates if empty or missing
TEMPLATE_SRC="/opt/bvsim-templates"
TEMPLATE_DST="/data/templates"
if [ -d "$TEMPLATE_SRC" ]; then
  if [ ! -d "$TEMPLATE_DST" ] || [ -z "$(ls -A "$TEMPLATE_DST" 2>/dev/null || true)" ]; then
    mkdir -p "$TEMPLATE_DST"
    cp -r "$TEMPLATE_SRC"/* "$TEMPLATE_DST"/ 2>/dev/null || true
  fi
fi

# Ensure data directories exist
mkdir -p /data

# Start Gunicorn
exec gunicorn "bvsim_web:create_app()" \
  --bind "${BVSIM_WEB_HOST}:${BVSIM_WEB_PORT}" \
  --workers "${BVSIM_WEB_WORKERS}" \
  --timeout "${BVSIM_WEB_TIMEOUT}" \
  --log-level "${BVSIM_WEB_LOGLEVEL}" \
  --access-logfile - \
  --error-logfile -
