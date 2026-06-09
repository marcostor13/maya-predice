#!/usr/bin/env sh
# Arranque de producción: espera la DB, aplica migraciones y lanza Gunicorn.
set -e

echo "[start] esperando a la base de datos…"
python -m app.core.wait_for_db

echo "[start] aplicando migraciones (alembic upgrade head)…"
alembic upgrade head

echo "[start] arrancando Gunicorn en 0.0.0.0:8000…"
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w 2
