FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# No hace falta build-essential: numpy/scipy/pandas/asyncpg se instalan como
# wheels precompilados (manylinux). Evitarlo reduce mucho el tamaño de la imagen
# y el tiempo de build.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 8000

# Espera la DB, aplica migraciones y arranca el servidor.
CMD ["sh", "start.sh"]
