FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl: necesario para el healthcheck de Coolify (GET /health dentro del contenedor).
# No hace falta build-essential: numpy/scipy/pandas/asyncpg se instalan como wheels
# precompilados (manylinux), así la imagen se mantiene ligera.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x start.sh

# Puerto interno (informativo). El bind real usa $PORT (por defecto 8000).
EXPOSE 8000

# Espera la DB, aplica migraciones y arranca el servidor.
CMD ["sh", "start.sh"]
