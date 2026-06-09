#!/usr/bin/env sh
# Arranque de produccion resiliente: intenta esperar la DB y migrar, pero SIEMPRE
# arranca Gunicorn para que el contenedor quede vivo, /health responda y los logs
# sean visibles. Si la DB falla, lo deja claro en el log (revisa DATABASE_URL).

echo "[start] esperando a la base de datos..."
python -m app.core.wait_for_db || echo "[start] AVISO: la DB no respondio. Arranco igual para exponer /health. Revisa DATABASE_URL."

echo "[start] aplicando migraciones (alembic upgrade head)..."
alembic upgrade head || echo "[start] AVISO: las migraciones fallaron. El servidor arranca pero la DB no esta lista."

echo "[start] arrancando Gunicorn en 0.0.0.0:8000..."
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w 2
