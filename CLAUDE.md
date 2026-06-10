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
- **Bitácora de lo implementado (cronológica):** ver `DEVLOG.md` — añade una
  entrada cada vez que completes un bloque de trabajo.
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

# Ingesta + verificación de datos oficiales (partidos)
cd backend && python -m app.data.sync

# Sincronización de plantillas multi-fuente (jugadores/suplentes/DT)
cd backend && python -m app.data.sync_squads

# Entrenar el modelo con histórico real + persistir fuerzas por equipo
cd backend && python -m app.data.train

# Crear usuario del panel de administración (login JWT)
cd backend && python -m app.data.create_admin <usuario> <contraseña>

# Recálculo en vivo (reingesta de resultados + reentreno + predicciones + simulación)
cd backend && python -m app.data.recompute

# Aprendizaje continuo (plantillas multi-fuente + recálculo forzado) — para cron horario
cd backend && python -m app.data.learn

# Tests backend
cd backend && pytest

# Frontend
cd frontend && npm install && npm start  # http://localhost:4200
```

## 6. Estado actual del proyecto

- [x] Scaffolding inicial (estructura, docs, agents/skills, configs).
- [x] Motor de predicción Dixon-Coles base implementado (`services/prediction/`).
- [x] Modelos ORM: Team, Match, Prediction, Tournament, SyncRun, DataChange.
- [x] Endpoints base: health, teams, matches, predictions, sync.
- [x] Migración inicial Alembic (verificada contra PostgreSQL real).
- [x] **Datos oficiales 2026**: proveedor openfootball + sync idempotente +
      verificación diaria con detección de cambios (104 partidos, 48 equipos).
      Verificado end-to-end contra PostgreSQL.
- [x] **Plantillas multi-fuente**: jugadores/suplentes/DT + estado, consenso de
      3 fuentes (apifootball/thesportsdb/wikidata) con confianza y discrepancias.
      Verificado end-to-end contra PostgreSQL (consenso + conflictos).
- [x] **Modelo entrenado con histórico real** (martj42, ~49k partidos) + sede
      neutral + fit vectorizado; **ajuste por disponibilidad** de plantilla.
      Verificado: top ataque coherente y la predicción cambia con bajas.
- [x] **Prior Elo + simulación Monte Carlo + actualización en vivo**: Elo desde
      el histórico como prior; probabilidades de avance/campeón; recálculo al
      terminar partidos. Verificado end-to-end (favoritos coherentes; reactividad).
- [ ] Producción: añadir hosts de plantillas a la allowlist de Coolify + keys,
      activar `PLAYER_SOURCES=apifootball,thesportsdb,wikidata`. Durante el torneo
      bajar `LIVE_POLL_MINUTES` (p.ej. 30).
- [ ] Más fuentes para nutrir el modelo (xG, valor de mercado, cuotas): `DATA_SOURCES.md`.
- [ ] Bracket oficial 2026 exacto en el simulador; calibración y backtesting.
- [x] **Frontend Angular animado**: dashboard, fixture con horarios/resultados,
      equipos + detalle de plantilla, simulación interactiva, footer con autoría
      (Marcos Torres) y **suscripción por email**. Verificado: `npm run build` OK.
- [x] **Envío de emails a suscriptores** (digest SMTP tras el refresco diario).
      Verificado end-to-end con servidor SMTP local (BCC, HTML correcto).
- [x] **CI/CD**: GitHub Actions (ruff + pytest + build) y guía de despliegue
      `DEPLOYMENT.md` (Coolify backend+DB, Netlify frontend, auto-deploy).
- [x] **Backtesting/calibración**: log-loss/Brier/accuracy fuera de muestra vs
      línea base. Verificado: el modelo supera a la base (CLI/endpoint `backtest`).
- [x] **Baja de suscripción (unsubscribe)**: token por suscriptor, envío
      individual con enlace propio + `List-Unsubscribe`. Verificado end-to-end.
- [ ] Producción real: completar variables/keys en Coolify y Netlify según `DEPLOYMENT.md`.

> **Actualiza esta checklist** conforme avances. Es lo primero que mira Claude.

## 7. Notas / gotchas

- El Mundial 2026 tiene **48 equipos** y formato nuevo (12 grupos de 4). El
  modelo y el esquema de torneo deben soportarlo (ver PLATFORM.md §formato).
- Las predicciones se recalculan: guardamos cada corrida con `model_version`
  y `created_at` para poder auditar y comparar.
- Secrets nunca en el repo: usar `.env` (local) y variables en Coolify/Netlify.
- **Datos oficiales**: fuente = openfootball (ADR-004); la API directa de FIFA da
  403 desde servidores. El sync es idempotente por `Match.external_ref`. El job
  diario corre vía APScheduler (`ENABLE_SCHEDULER`/`SYNC_HOUR_UTC`) o cron con
  `python -m app.data.sync`. Cada cambio queda en `data_changes`.
- El proveedor normaliza el grupo `"Group A"` → `"A"` (las columnas `group` son
  `String(2)`). Las eliminatorias guardan placeholders (`W101`, `1A`) hasta que
  se resuelve el cruce; los FK de equipo son nullable.
- **Plantillas**: consenso multi-fuente por nombre normalizado; cada dato lleva
  `confidence`/`sources_count`/`source_data` y los conflictos van a
  `squad_discrepancies`. Fuentes activas vía `PLAYER_SOURCES`.
- **Red del entorno = allowlist.** En el sandbox solo `raw.githubusercontent.com`
  responde; las APIs externas dan 403. En Coolify hay que allowlistar hosts +
  poner keys. Por eso `fixture` es la fuente por defecto en dev.
- **PostgreSQL: palabras reservadas.** `position` es reservada → se mapea a
  `player_position` y su enum a `position_enum` (SQLAlchemy no las entrecomilla).
  Cuidado al nombrar columnas/enums nuevos.
- **Hiperparámetros del modelo hardcodeados.** `history_team_filter` (any),
  `model_decay_xi` (0.0015) y `elo_prior_weight` (2.5) NO se leen del entorno: son
  constantes + propiedades de solo lectura en `config.py` (valores validados por
  RPS, ver `MODEL_STUDY.md`). Para recalibrar se cambian ahí y se revalida con
  `python -m app.data.backtest`. Ya no sirve ponerlos como variable en Coolify.
- **Recompute = job en segundo plano.** `POST /admin/recompute` lanza un `JobRun`
  (tabla `job_runs`) y responde al instante; el panel hace polling a `GET
  /admin/job`. El estado va en DB (no en memoria) porque producción corre 2 workers
  Gunicorn. El job corre con su **propia sesión** (`app/services/jobs.py`); un job a
  la vez; los obsoletos (>30 min) no bloquean.
- **Plantillas: fotos + scraping.** Las fuentes aportan foto/info: `wikipedia`
  (scraping vía API de MediaWiki: plantilla `{{nat fs player}}`, DT y fotos),
  `thesportsdb` (strCutout) y `wikidata` (P18). Foto/info se consensúan por
  **prioridad** (`merge_first_available`), no por voto. En Coolify allowlistar
  `en.wikipedia.org`/`commons.wikimedia.org` y poner `PLAYER_SOURCES`.
- **Ensamble con el mercado (acción #2).** `POST` recompute mezcla la predicción 1X2
  con las cuotas de **The Odds API** (`app/data/odds/`): `P = ω·modelo + (1−ω)·mercado`
  (`ensemble_model_weight`, ω=0.4). Flag `ENABLE_MARKET_ENSEMBLE` (off por defecto) +
  `ODDS_API_KEY`. Defensivo: sin cuotas → solo-modelo. Solo afecta las predicciones
  por partido; el **simulador** (campeón) sigue solo-modelo (Fase 2). Detalle en
  `MODEL_STUDY.md` y `DEVLOG` 019.
- **Aprendizaje continuo (cron horario).** `run_hourly_refresh` (scheduler, cada
  `HOURLY_REFRESH_MINUTES`=60, flag `HOURLY_REFRESH_ENABLED`): sincroniza plantillas
  multi-fuente y lanza el recálculo forzado. **Todos** los recálculos (horario, diario,
  en vivo, manual) pasan por `jobs.start_job` → **uno a la vez**, con un **lock
  consultivo de Postgres** (`pg_advisory_xact_lock`) para que los 2 workers Gunicorn
  no lo dupliquen. Cron externo (si `ENABLE_SCHEDULER=false`): `python -m app.data.learn`.
