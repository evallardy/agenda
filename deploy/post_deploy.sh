#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${SCRIPT_DIR}/project.conf" ]]; then
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/project.conf"
fi

APP_SOURCE_DIR="${APP_SOURCE_DIR:-${PROJECT_ROOT}}"
APP_VENV_DIR="${APP_VENV_DIR:-${PROJECT_ROOT}/.venv}"
DJANGO_ENV="${DJANGO_ENV:-production}"
DJANGO_ENV_FILE="${DJANGO_ENV_FILE:-.env.production}"

cd "${APP_SOURCE_DIR}"

if [[ ! -d "${APP_VENV_DIR}" ]]; then
  python3 -m venv "${APP_VENV_DIR}"
fi

source "${APP_VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements-prod.txt

export DJANGO_ENV
export DJANGO_ENV_FILE

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy