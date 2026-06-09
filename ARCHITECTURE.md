# ARCHITECTURE.md — Arquitectura de maya-predice

> Guía de arquitectura. **Consúltala siempre** antes de introducir un cambio
> estructural, una dependencia nueva o un patrón distinto. Si te desvías de lo
> aquí descrito, documenta el porqué en la sección "Decisiones (ADR)".

---

## 1. Visión general

```
                    ┌──────────────────────────┐
                    │  Navegador (usuario)      │
                    └────────────┬─────────────┘
                                 │ HTTPS
                    ┌────────────▼─────────────┐
                    │  Frontend Angular 18      │  ← Netlify (CDN estático)
                    │  SPA standalone components │
                    └────────────┬─────────────┘
                                 │ REST/JSON (HTTPS)
                    ┌────────────▼─────────────┐
                    │  Backend FastAPI          │  ← Coolify (Docker)
                    │  ┌─────────────────────┐  │
                    │  │ api/  (routers)     │  │
                    │  │ services/ (lógica)  │  │
                    │  │ prediction/ (modelo)│  │
                    │  │ models/ (ORM)       │  │
                    │  └─────────────────────┘  │
                    └────────────┬─────────────┘
                                 │ SQL (asyncpg)
                    ┌────────────▼─────────────┐
                    │  PostgreSQL 16            │  ← Coolify (Docker volume)
                    └──────────────────────────┘
```

## 2. Componentes

### 2.1 Frontend — Angular 18
- SPA con **standalone components** (sin NgModules), routing lazy.
- Estado local con **signals**; datos remotos vía servicios `HttpClient`.
- Estructura:
  ```
  src/app/
  ├── core/
  │   ├── services/      ← ApiService, PredictionService, MatchService
  │   ├── models/        ← interfaces TS (Team, Match, Prediction)
  │   └── interceptors/  ← base-url, error handling
  ├── features/
  │   ├── dashboard/     ← listado de partidos + predicciones
  │   ├── match-detail/  ← detalle y probabilidades de un partido
  │   └── standings/     ← tabla de grupos / simulación de torneo
  └── shared/            ← componentes UI reutilizables
  ```
- Build a estático → **Netlify**. `environment.ts` apunta a la URL del backend.

### 2.2 Backend — FastAPI
Arquitectura en capas, una responsabilidad por capa:

| Capa         | Carpeta            | Responsabilidad                                  |
|--------------|--------------------|--------------------------------------------------|
| Transporte   | `app/api/`         | Routers REST, validación I/O, códigos HTTP.      |
| Lógica       | `app/services/`    | Reglas de negocio, orquestación.                 |
| Predicción   | `app/services/prediction/` | Modelos estadísticos (Dixon-Coles, Poisson). |
| Persistencia | `app/models/`      | Modelos ORM SQLAlchemy.                          |
| Contratos    | `app/schemas/`     | DTOs Pydantic (request/response).                |
| Infra        | `app/core/`        | Config, conexión DB, dependencias.               |

Reglas:
- Los **routers no contienen lógica**: validan y delegan en `services/`.
- **Nunca** se exponen modelos ORM al exterior; siempre vía schemas Pydantic.
- Acceso a DB **async** (SQLAlchemy 2.0 async + asyncpg).
- Inyección de dependencias de FastAPI para `AsyncSession`.

### 2.3 Base de datos — PostgreSQL 16
- ORM: SQLAlchemy 2.0 (async). Migraciones: **Alembic**.
- Esquema relacional principal (ver `backend/app/models/`):

```
tournaments ──< matches >── teams          predictions >── matches
   (1)            (N)         (2)              (N)           (1)

teams(id, name, code, fifa_rank, confederation, group, ...)
matches(id, tournament_id, home_team_id, away_team_id, stage, kickoff,
        home_goals, away_goals, status)
predictions(id, match_id, model_version, p_home, p_draw, p_away,
            expected_home_goals, expected_away_goals, scoreline_probs,
            created_at)
team_strengths(id, team_id, attack, defense, model_version, computed_at)
```

## 3. El modelo de predicción (núcleo)

Usamos el modelo **Dixon-Coles (1997)**, una mejora del Poisson bivariado que es
el estándar para predicción de fútbol.

1. Cada equipo tiene parámetros de **ataque** (αᵢ) y **defensa** (βᵢ).
   Existe una **ventaja de localía** (γ) global.
2. Goles esperados:
   - λ_home = exp(αₕ + β_a + γ)   (goles del local)
   - μ_away = exp(α_a + βₕ)        (goles del visitante)
3. Goles del local/visitante ~ Poisson(λ), Poisson(μ), con la **corrección τ de
   Dixon-Coles** para resultados de pocos goles (0-0, 1-0, 0-1, 1-1), que
   corrige la dependencia que el Poisson puro no captura.
4. Los parámetros se estiman por **máxima verosimilitud** sobre partidos
   históricos, con **decaimiento temporal** (ξ): los partidos recientes pesan más.
5. A partir de (λ, μ, τ) se construye la **matriz de probabilidad de marcadores**
   (0..10 × 0..10) y de ahí: P(victoria local), P(empate), P(victoria visitante),
   marcador más probable, y para fases eliminatorias la probabilidad de avanzar.

Implementación: `backend/app/services/prediction/`
- `dixon_coles.py` — estimación de parámetros y predicción de un partido.
- `poisson.py` — utilidades de la distribución y matriz de marcadores.
- `simulator.py` — simulación Monte Carlo del torneo (avance por fases).

> El modelo es **versionado** (`model_version`). Cada corrida persiste sus
> predicciones para auditoría y backtesting.

## 4. API (contrato REST)

Base: `/api/v1`. OpenAPI/Swagger autogenerado en `/docs`.

| Método | Ruta                              | Descripción                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/health`                         | Healthcheck.                         |
| GET    | `/api/v1/teams`                   | Lista de equipos.                    |
| GET    | `/api/v1/teams/{id}`              | Detalle + fuerza estimada.           |
| GET    | `/api/v1/matches`                 | Partidos (filtros: stage, group).    |
| GET    | `/api/v1/matches/{id}`            | Detalle de partido.                  |
| GET    | `/api/v1/predictions/match/{id}`  | Predicción de un partido.            |
| POST   | `/api/v1/predictions/run`         | Ejecuta el modelo y persiste.        |
| GET    | `/api/v1/simulate/tournament`     | Simulación Monte Carlo del torneo.   |
| GET    | `/api/v1/sync/runs`               | Historial de verificaciones.         |
| GET    | `/api/v1/sync/changes`            | Cambios detectados (qué cambió hoy). |
| POST   | `/api/v1/sync/run`                | Verificación manual inmediata.       |

## 4.b Ingesta y verificación de datos oficiales

Toda la información del torneo proviene de una **fuente oficial** y se **verifica
a diario** detectando cambios. Diseño:

```
                 ┌─────────────────────────────┐
   Fuente        │ DataProvider (abstracción)  │
   oficial  ───▶ │   └ OpenFootballProvider    │  parse_matches() puro/testeable
                 └──────────────┬──────────────┘
                                │ list[ProviderMatch] normalizado
                 ┌──────────────▼──────────────┐
                 │ sync_service                │  upsert idempotente por external_ref
                 │  · _ensure_teams            │  + compute_changes (diff puro)
                 │  · compute_changes          │
                 └──────────────┬──────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        matches/teams      sync_runs         data_changes
        (estado actual)   (auditoría)     (qué cambió y cuándo)
```

- **Proveedor (`app/data/providers/`)**: interfaz `DataProvider.fetch_matches()`.
  Implementación primaria `OpenFootballProvider`. La fuente es swappable (ver
  ADR-004); se puede añadir API-Football u otra detrás de la misma interfaz.
- **`external_ref`**: clave estable por partido para upsert idempotente. Grupos:
  `G:<grupo>:<local>-<visitante>`. Eliminatorias: `K:<fase>:<fecha>:<hora>:<sede>`
  (la "ranura" no cambia aunque el cruce aún tenga placeholders como `W101`).
- **Detección de cambios**: `compute_changes(old, new)` compara campos vigilados
  (horario, sede, equipos/placeholders, resultado, estado) y registra cada
  diferencia en `data_changes`, asociada a un `SyncRun`.
- **Verificación diaria**: `core/scheduler.py` (APScheduler) ejecuta el sync a
  `SYNC_HOUR_UTC` (por defecto 06:00 UTC, tras finalizar los partidos del día).
  Alternativa: cron en Coolify con `python -m app.data.sync` (poner
  `ENABLE_SCHEDULER=false`).
- **Equipos**: las 48 selecciones provienen del mapeo canónico
  `app/data/team_mapping.py` (nombre → código FIFA + confederación).

## 5. Despliegue

### Frontend → Netlify
- Build: `npm run build` → `dist/maya-predice/browser`.
- `netlify.toml` define publish dir y redirects SPA. Variable de entorno con la
  URL pública del backend.

### Backend + DB → Coolify
- `backend/Dockerfile` construye la imagen FastAPI (uvicorn/gunicorn).
- PostgreSQL como servicio/recurso en Coolify (volumen persistente).
- Variables de entorno en Coolify: `DATABASE_URL`, `CORS_ORIGINS`, `ENV`.
- Migraciones Alembic se ejecutan en el arranque (entrypoint) o como job.

### Local
- `docker-compose.yml` levanta `db` (postgres) + `backend`. El frontend se corre
  con `npm start` apuntando a `http://localhost:8000`.

## 6. Seguridad y configuración
- Secrets solo por variables de entorno (`.env` local, Coolify/Netlify en prod).
  Nunca commitear `.env`.
- CORS restringido a los orígenes del frontend (`CORS_ORIGINS`).
- Validación estricta de entrada con Pydantic.

## 7. Decisiones (ADR)

### ADR-001 — PostgreSQL en lugar de MongoDB Atlas
**Contexto:** el brief sugería MongoDB Atlas "o una alternativa mejor para datos
estadísticos". Los datos (equipos, partidos, resultados, parámetros del modelo)
son **relacionales** y se explotan con **agregaciones, joins y window functions**
(forma reciente, head-to-head, fuerza por confederación).
**Decisión:** PostgreSQL 16. Mejor para analítica/estadística, transaccional,
SQL maduro, y Coolify lo despliega sin fricción.
**Consecuencia:** SQLAlchemy + Alembic. Si en el futuro hiciera falta documento
flexible (p.ej. cachés de simulaciones), se puede usar una columna `JSONB`.

### ADR-002 — FastAPI como backend
**Decisión:** FastAPI por rendimiento async, validación Pydantic, OpenAPI
automático e integración natural con el stack científico (numpy/scipy/pandas).

### ADR-003 — Modelo Dixon-Coles
**Decisión:** Dixon-Coles sobre Poisson simple por su corrección para marcadores
bajos y su uso consolidado en predicción de fútbol. Versionado para backtesting.

### ADR-004 — Fuente de datos oficiales: openfootball (no api.fifa.com directo)
**Contexto:** se requería conectar con datos oficiales de la FIFA y verificarlos
a diario. La FIFA **no ofrece una API pública** para desarrolladores; su API de
contenido (`api.fifa.com`) **devuelve 403 a clientes de servidor** (verificado),
por lo que no es fiable en producción.
**Decisión:** usar **openfootball/worldcup.json** como fuente primaria: JSON de
**dominio público** derivado del calendario oficial de la FIFA, sin API key y
accesible desde servidores. Incluye los 104 partidos, 12 grupos, sedes, horarios
y resultados (que añade tras cada partido). Se accede tras una abstracción
`DataProvider`, de modo que se puede sustituir/complementar por un proveedor de
pago (p.ej. API-Football) para datos en vivo más ricos sin tocar el resto.
**Verificado:** parseo de los 104 partidos reales, ingesta y detección de cambios
contra PostgreSQL (alta de 104 + idempotencia en re-sync + detección de resultado).
**Consecuencia:** dependencia de un repo comunitario; mitigada por la abstracción
de proveedor y por registrar cada cambio en `data_changes` para auditoría.
