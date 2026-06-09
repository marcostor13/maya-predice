#!/usr/bin/env sh
# Arranque de produccion resiliente: intenta esperar la DB y migrar, pero SIEMPRE
# arranca Gunicorn para que el contenedor quede vivo, /health responda y los logs
# sean visibles. Si la DB falla, lo deja claro en el log (revisa DATABASE_URL).

echo "[start] esperando a la base de datos..."
python -m app.core.wait_for_db || echo "[start] AVISO: la DB no respondio. Arranco igual para exponer /health. Revisa DATABASE_URL."

echo "[start] aplicando migraciones (alembic upgrade head)..."
alembic upgrade head || echo "[start] AVISO: las migraciones fallaron. El servidor arranca pero la DB no esta lista."

# Carga inicial automatica en segundo plano (idempotente: solo si la base esta
# vacia). No bloquea el arranque de Gunicorn ni el healthcheck.
if [ "${ENABLE_BOOTSTRAP:-true}" = "true" ]; then
  echo "[start] lanzando carga inicial en segundo plano (si la base esta vacia)..."
  python -m app.data.bootstrap &
fi

echo "[start] arrancando Gunicorn en 0.0.0.0:${PORT:-8000}..."
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b "0.0.0.0:${PORT:-8000}" -w 2
