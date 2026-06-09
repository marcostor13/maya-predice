# CLAUDE.md — Memoria Persistente del Proyecto

> Este es el archivo de **memoria persistente** de Claude Code para el proyecto
> **maya-predice**. Léelo SIEMPRE al iniciar una sesión. Mantenlo actualizado:
> cuando tomes una decisión importante, cambies una convención o termines un
> hito, añádelo aquí. Es la fuente de verdad operativa del día a día.

---

## 1. Qué es el proyecto

**maya-predice** es una plataforma web que **predice los resultados de los
partidos del Mundial de Fútbol 2026** usando un modelo estadístico
(Dixon-Coles / Poisson bivariado).

- **Producto y alcance funcional:** ver `PLATFORM.md`
- **Arquitectura técnica detallada:** ver `ARCHITECTURE.md`
- **Este archivo (CLAUDE.md):** memoria operativa, convenciones, estado actual.

## 2. Stack (resumen — detalle en ARCHITECTURE.md)

| Capa        | Tecnología                          | Deploy   |
|-------------|-------------------------------------|----------|
| Frontend    | Angular 18 (standalone components)  | Netlify  |
| Backend     | FastAPI (Python 3.12)               | Coolify  |
| Base datos  | PostgreSQL 16 + SQLAlchemy/Alembic  | Coolify  |
| Modelado    | numpy, scipy, pandas, statsmodels   | —        |

> Decisión: usamos **PostgreSQL** (no MongoDB) porque los datos son relacionales
> y el modelado requiere agregaciones SQL. Ver ADR en ARCHITECTURE.md §"Decisiones".

## 3. Estructura del repositorio

```
maya-predice/
├── CLAUDE.md            ← este archivo (memoria persistente)
├── ARCHITECTURE.md      ← guía de arquitectura (consultar siempre)
├── PLATFORM.md          ← qué incluye la plataforma (qué desarrollar)
├── docker-compose.yml   ← entorno local (postgres + backend)
├── backend/             ← FastAPI + modelo de predicción
│   ├── app/
│   │   ├── main.py
│   │   ├── core/        ← config, database
│   │   ├── models/      ← SQLAlchemy ORM
│   │   ├── schemas/     ← Pydantic
│   │   ├── api/         ← routers (endpoints REST)
│   │   ├── services/    ← lógica de negocio + motor de predicción
│   │   └── data/        ← ingesta / seeds
│   ├── alembic/         ← migraciones
│   └── tests/
├── frontend/            ← Angular
│   └── src/app/
└── .claude/
    ├── agents/          ← subagentes especializados
    ├── skills/          ← skills reutilizables
    └── settings.json
```

## 4. Convenciones de código

### Backend (Python)
- Python 3.12, formateo con **ruff** (lint + format). Type hints obligatorios.
- Async/await en endpoints y acceso a DB (SQLAlchemy async).
- Capas: `api/` (HTTP) → `services/` (lógica) → `models/` (ORM). Los routers
  **no** contienen lógica de negocio; delegan en services.
- Schemas Pydantic separados de modelos ORM. Nunca exponer modelos ORM directo.
- Nombres: `snake_case` para módulos/funciones, `PascalCase` para clases.

### Frontend (Angular)
- Angular 18 **standalone components** (sin NgModules).
- Signals para estado de componente; servicios con `providedIn: 'root'`.
- HTTP a través de servicios en `core/services/`. Tipos en `core/models/`.
- Estilos: SCSS por componente. Nombres de archivo `kebab-case`.

### Git
- Rama de desarrollo: `claude/world-cup-prediction-setup-4qo2w6`.
- Commits descriptivos en imperativo. No crear PRs salvo que se pida.

## 5. Comandos frecuentes

```bash
# Levantar todo en local (db + backend)
docker compose up --build

# Backend (sin docker)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000/docs

# Migraciones
cd backend && alembic revision --autogenerate -m "msg" && alembic upgrade head

# Tests backend
cd backend && pytest

# Frontend
cd frontend && npm install && npm start  # http://localhost:4200
```

## 6. Estado actual del proyecto

- [x] Scaffolding inicial (estructura, docs, agents/skills, configs).
- [x] Motor de predicción Dixon-Coles base implementado (`services/prediction/`).
- [x] Modelos ORM: Team, Match, Prediction, Tournament.
- [x] Endpoints base: health, teams, matches, predictions.
- [ ] Ingesta real de datos históricos (fuente por definir).
- [ ] Calibración y backtesting del modelo.
- [ ] Frontend: dashboard de predicciones + detalle de partido.
- [ ] CI/CD (Netlify + Coolify) configurado en producción.

> **Actualiza esta checklist** conforme avances. Es lo primero que mira Claude.

## 7. Notas / gotchas

- El Mundial 2026 tiene **48 equipos** y formato nuevo (12 grupos de 4). El
  modelo y el esquema de torneo deben soportarlo (ver PLATFORM.md §formato).
- Las predicciones se recalculan: guardamos cada corrida con `model_version`
  y `created_at` para poder auditar y comparar.
- Secrets nunca en el repo: usar `.env` (local) y variables en Coolify/Netlify.
