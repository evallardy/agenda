#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/deploy/.env.deploy"

if [ -f "${ENV_FILE}" ]; then
    set -a
    . "${ENV_FILE}"
    set +a
fi

. "${PROJECT_DIR}/.venv/bin/activate"
cd "${PROJECT_DIR}"

exec gunicorn "${BAR_GUNICORN_APP:-agenda.wsgi:application}" \
  --name "${BAR_SERVICE_NAME:-agenda}" \
  --bind "${BAR_GUNICORN_BIND:-unix:/tmp/gunicorn-agenda.sock}" \
  --workers "${BAR_GUNICORN_WORKERS:-3}" \
  --worker-class "${BAR_GUNICORN_WORKER_CLASS:-sync}" \
  --timeout "${BAR_GUNICORN_TIMEOUT:-120}" \
  --graceful-timeout "${BAR_GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --keep-alive "${BAR_GUNICORN_KEEPALIVE:-5}" \
  --access-logfile "${BAR_GUNICORN_ACCESSLOG:--}" \
  --error-logfile "${BAR_GUNICORN_ERRORLOG:--}"