#!/bin/sh
set -eu

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Running database migrations..."
python manage.py migrate --noinput

WORKERS="${WEB_CONCURRENCY:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
BIND="${GUNICORN_BIND:-0.0.0.0:8000}"
LOG_LEVEL="${GUNICORN_LOG_LEVEL:-info}"

echo "Starting Gunicorn+Uvicorn ASGI (${WORKERS} workers) on ${BIND}..."
exec gunicorn core.asgi:application \
    --bind "${BIND}" \
    --workers "${WORKERS}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout "${TIMEOUT}" \
    --log-level "${LOG_LEVEL}" \
    --access-logfile - \
    --error-logfile - \
    --preload
