#!/usr/bin/env bash
# Launch BVSim web application.
# Optional positional args: [port] [host]
# Environment variables (override):
#   BVSIM_WEB_PORT - port to listen on (default 8000)
#   BVSIM_WEB_HOST - host interface (default 0.0.0.0)
#   BVSIM_WEB_DEBUG - true/false enable Flask debug (default true)
#   BVSIM_WEB_WORKERS - if set and gunicorn installed, use gunicorn with this many workers
# Examples:
#   ./run_web.sh            # run on 8000
#   ./run_web.sh 5000       # run on port 5000
#   ./run_web.sh 5000 127.0.0.1  # run bound to localhost
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Allow simple positional overrides
if [[ ${1:-} =~ ^[0-9]+$ ]]; then
  export BVSIM_WEB_PORT="$1"; shift || true
fi
if [[ ${1:-} != "" ]]; then
  export BVSIM_WEB_HOST="$1"; shift || true
fi

: "${BVSIM_WEB_PORT:=8000}"
: "${BVSIM_WEB_HOST:=0.0.0.0}"
: "${BVSIM_WEB_DEBUG:=true}"

# Decide runner: prefer gunicorn if multiple workers requested and available
if [[ -n "${BVSIM_WEB_WORKERS:-}" ]]; then
  if python -c "import gunicorn" 2>/dev/null; then
    exec python -m gunicorn -w "${BVSIM_WEB_WORKERS}" -b "${BVSIM_WEB_HOST}:${BVSIM_WEB_PORT}" 'bvsim_web.__main__:app'
  else
    echo "[INFO] gunicorn not installed; falling back to Flask dev server." >&2
  fi
fi

exec python -m bvsim_web
