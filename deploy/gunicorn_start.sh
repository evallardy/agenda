#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${SCRIPT_DIR}/project.conf" ]]; then
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/project.conf"
fi

PROJECT_NAME="${PROJECT_NAME:-agenda}"
APP_SOURCE_DIR="${APP_SOURCE_DIR:-${PROJECT_ROOT}}"
APP_VENV_DIR="${APP_VENV_DIR:-${PROJECT_ROOT}/.venv}"
APP_RUN_DIR="${APP_RUN_DIR:-/run/gunicorn}"
APP_LOG_DIR="${APP_LOG_DIR:-/var/log/gunicorn}"
DJANGO_ENV="${DJANGO_ENV:-production}"
DJANGO_ENV_FILE="${DJANGO_ENV_FILE:-.env.production}"
DJANGO_WSGI_MODULE="${DJANGO_WSGI_MODULE:-agenda.wsgi}"
GUNICORN_BIND="${GUNICORN_BIND:-unix:${APP_RUN_DIR}/${PROJECT_NAME}.sock}"

mkdir -p "${APP_RUN_DIR}" "${APP_LOG_DIR}"

cd "${APP_SOURCE_DIR}"
source "${APP_VENV_DIR}/bin/activate"

export DJANGO_ENV
export DJANGO_ENV_FILE

exec gunicorn "${DJANGO_WSGI_MODULE}:application" \
  --name "${PROJECT_NAME}" \
  --bind "${GUNICORN_BIND}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -