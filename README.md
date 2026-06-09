# maya-predice ⚽

Plataforma web de **predicción de los partidos del Mundial de Fútbol 2026**
mediante un modelo estadístico (Dixon-Coles / Poisson bivariado).

## Stack

- **Frontend:** Angular 18 (standalone) → Netlify
- **Backend:** FastAPI (Python 3.12) → Coolify
- **Base de datos:** PostgreSQL 16 (SQLAlchemy + Alembic) → Coolify
- **Modelado:** numpy · scipy · pandas · statsmodels

## Documentación (leer en este orden)

| Archivo            | Para qué sirve                                            |
|--------------------|-----------------------------------------------------------|
| `CLAUDE.md`        | Memoria persistente de Claude Code: estado y convenciones.|
| `PLATFORM.md`      | Qué incluye la plataforma (alcance funcional / features). |
| `ARCHITECTURE.md`  | Cómo está construida (arquitectura técnica, ADRs).        |

## Inicio rápido (local)

```bash
# Opción A — todo con Docker (db + backend)
docker compose up --build
# API:   http://localhost:8000/docs
# DB:    postgres://maya:maya@localhost:5432/maya_predice

# Opción B — backend a mano
cd backend
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start            # http://localhost:4200
```

## Estructura

```
backend/    FastAPI + motor de predicción + migraciones
frontend/   Angular SPA
.claude/    agents y skills de Claude Code
```

Ver `ARCHITECTURE.md` para el detalle.
