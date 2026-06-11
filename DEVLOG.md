# DEVLOG.md — Bitácora de desarrollo de maya-predice

> Registro **cronológico y permanente** de lo que vamos implementando, por qué, y
> cómo se verificó. Sirve para guiarnos y tener siempre claro qué se ha construido.
> **Regla:** cada vez que se complete un bloque de trabajo, añade una entrada al
> final con: objetivo, decisiones, qué se implementó, verificación y pendientes.
> Para el estado operativo vivo ver `CLAUDE.md`; para el producto `PLATFORM.md`;
> para la arquitectura `ARCHITECTURE.md`.

---

## Entrada 001 — Scaffolding inicial del proyecto
**Fecha:** 2026-06-09 · **Commit:** `04b25c3`

**Objetivo.** Crear toda la base para desarrollar una web que predice los
partidos del Mundial 2026 (frontend Angular, backend Python, base de datos,
despliegue Netlify/Coolify) y la documentación guía.

**Decisiones clave.**
- **Backend → FastAPI** (mejor para APIs de modelos estadísticos: async,
  Pydantic, integración con numpy/scipy/pandas).
- **Base de datos → PostgreSQL** en vez de MongoDB: los datos de fútbol son
  relacionales y se explotan con agregaciones SQL (ADR-001).
- **Modelo → Dixon-Coles** (Poisson bivariado con corrección para marcadores
  bajos), estándar en predicción de fútbol (ADR-003).

**Qué se implementó.**
- Documentación guía: `CLAUDE.md` (memoria), `ARCHITECTURE.md` (arquitectura +
  ADRs), `PLATFORM.md` (producto/alcance).
- Backend FastAPI en capas (api → services → models, schemas Pydantic), motor
  de predicción Dixon-Coles + simulador Monte Carlo, modelos ORM base.
- Frontend Angular 18 standalone (servicios, modelos, dashboard, detalle).
- Infra: `docker-compose`, `Dockerfile`, `netlify.toml`, Alembic.
- `.claude/`: 4 agents (backend, frontend, data-scientist, devops) y skills.

**Verificación.** 10 tests del motor de predicción en verde (normalización de la
matriz de marcadores, suma de probabilidades = 1, monotonicidad fuerza→victoria).

**Pendientes que dejó.** Datos reales, calibración, frontend completo, CI/CD.

---

## Entrada 002 — Datos oficiales del torneo + verificación diaria
**Fecha:** 2026-06-09 · **Commit:** `34ecf60`

**Objetivo.** Guardar toda la información oficial del Mundial conectada a datos
FIFA y verificarla a diario tras los partidos, registrando los cambios.

**Investigación / decisiones.**
- La **FIFA no tiene API pública**; `api.fifa.com` **devuelve 403 a servidores**
  (verificado). → Se usa **openfootball/worldcup.json**: JSON de dominio público
  derivado del calendario oficial FIFA, sin API key, accesible desde servidores
  (ADR-004). Tras una **abstracción `DataProvider`** para poder sustituir/añadir
  fuentes (p.ej. API-Football) sin tocar el resto.
- Upsert **idempotente** por `Match.external_ref` (clave estable: grupos por
  equipos; eliminatorias por "ranura" fase+fecha+hora+sede).

**Qué se implementó.**
- Proveedor openfootball + mapeo canónico de las 48 selecciones (código FIFA +
  confederación).
- `sync_service` con `compute_changes` (diff puro) → registra cada cambio en
  `data_changes` y cada corrida en `sync_runs` (auditoría).
- Verificación diaria con **APScheduler** (06:00 UTC, configurable) + CLI
  `python -m app.data.sync` para cron en Coolify.
- Modelos `SyncRun`/`DataChange`; `Match` con `external_ref`, `matchday` y
  placeholders de eliminatorias (FK de equipo nullable).
- Endpoints `/api/v1/sync` (runs, changes, run manual). Migración inicial Alembic.

**Verificación (end-to-end contra PostgreSQL real).**
- Parseo de los **104 partidos** reales (72 grupo + 32 eliminatorias), 48
  equipos, horarios convertidos a UTC, `external_ref` únicos.
- Corrida 1: 104 altas. Corrida 2 (re-sync): **0 cambios** (idempotencia).
  Corrida 3 (resultado simulado): detecta **3 cambios** (goles local/visitante +
  estado scheduled→finished).
- **Bug corregido por la verificación:** el grupo llegaba como `"Group A"` y la
  columna era `String(2)` → se normaliza a `"A"`.
- 21 tests en verde.

**Pendientes que dejó.** Histórico para entrenar el modelo; calibración; frontend.

---

## Entrada 003 — Plantillas (jugadores, suplentes, entrenadores) multi-fuente con consenso
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Guardar la información completa de jugadores, suplentes y
entrenadores con su **estado** (disponible, lesionado, sancionado, duda, baja),
consultando **3 fuentes** y cruzándolas para dar veracidad.

**Investigación / decisiones.**
- Las APIs de jugadores (API-Football, TheSportsDB, Wikidata, Wikipedia) **no son
  accesibles desde este entorno**: la red del entorno tiene una **allowlist** y
  esos hosts devuelven `403 "Host not in allowlist"` (solo `raw.githubusercontent`
  está permitido aquí). En **producción (Coolify)** la allowlist y las API keys
  las configura el usuario.
- Por eso el diseño separa **arquitectura** (verificable ahora) de **acceso a
  red** (depende de producción): se construyó el **motor de consenso** y la
  ingesta multi-fuente, más **3 adaptadores reales** listos para producción y un
  **proveedor de fixture** verificable offline (ADR-005).
- **Veracidad por consenso:** cada campo de cada jugador se decide por **voto
  mayoritario** entre fuentes (desempate por prioridad de fuente); se calcula la
  **confianza** (grado de acuerdo) y se registran las **discrepancias** (qué dijo
  cada fuente). Identidad de jugador entre fuentes = **nombre normalizado** (sin
  acentos/puntuación).

**Qué se implementó.**
- Abstracción `PlayerDataProvider` + observaciones normalizadas
  (`PlayerObservation`, `CoachObservation`, `SquadObservation`) y helpers de
  normalización (posición, estado, rol, nombre).
- **3 adaptadores de fuentes reales:** `apifootball` (squad + lesiones + coach),
  `thesportsdb` (gratuita), `wikidata` (SPARQL, sin key). Configurables por
  `PLAYER_SOURCES` + keys en `.env`.
- Proveedor `fixture`/`remote` (JSON propio) para desarrollo/offline + archivo de
  muestra `app/data/samples/squads_sample.json`.
- **Motor de consenso** puro `services/squad/consensus.py` (`merge_field`,
  `build_player_consensus`, `build_coach_consensus`).
- `squad_service` que reúne fuentes, agrupa por jugador, aplica consenso, hace
  upsert de `Player`/`Coach` con `confidence`, `sources_count` y `source_data`
  (trazabilidad), y guarda conflictos en `squad_discrepancies`.
- Modelos `Coach`, `Player` (con estado/rol/posición), `SquadDiscrepancy`.
- Endpoints `/api/v1/squads/{code}`, `/squads/discrepancies`, `/squads/sync`.
- Job diario extendido para sincronizar también plantillas; CLI
  `python -m app.data.sync_squads`. Migración Alembic de plantillas.

**Verificación (end-to-end contra PostgreSQL real).**
- Consenso de **3 fuentes** con conflicto deliberado: Messi (3/3) → confianza
  **1.0**, 0 discrepancias; Enzo Fernández (conflicto) → dorsal 24 y estado
  *available* por mayoría (2/3), confianza **0.867**, **2 discrepancias**
  registradas con la traza de cada fuente.
- Proveedor fixture real: carga 7 jugadores + 2 entrenadores desde el archivo.
- 31 tests en verde (consenso, parser fixture, + los anteriores).
- **2 bugs corregidos por la verificación:** (1) `position` es palabra reservada
  en PostgreSQL → la columna se mapea a `player_position` y el tipo enum a
  `position_enum`; SQLAlchemy no las entrecomillaba.

**Pendientes que dejó.**
- En producción: poner los hosts de las 3 fuentes en la allowlist de Coolify,
  cargar `APIFOOTBALL_KEY` y activar `PLAYER_SOURCES=apifootball,thesportsdb,wikidata`.
- Afinar el adaptador Wikidata (la fuente más ruidosa) y el mapeo de IDs de
  equipo en API-Football/TheSportsDB con datos reales.
- Relacionar el estado de los jugadores con el modelo de predicción (ajustar la
  fuerza del equipo según bajas/lesiones).

---

## Entrada 004 — Entrenamiento con histórico real + ajuste por disponibilidad
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Nutrir el modelo con datos reales y conectar el estado de las
plantillas con la predicción (ajustar la fuerza por bajas/lesiones). Además,
sugerir más datos/fuentes para enriquecer el modelo.

**Investigación / decisiones.**
- Fuente para entrenar: **martj42/international_results** (dominio público, ~49k
  partidos internacionales 1872–2026, con sede neutral). **Accesible vía GitHub
  raw** → usable ya (verificado HTTP 200, 3.7 MB).
- Mapeo de nombres del dataset → códigos FIFA de las 48 (alias añadidos, p.ej.
  "Bosnia and Herzegovina"). Filtro configurable `both|any|all` (por defecto
  `both`: ~998 partidos entre las 48 desde 2018 → entrena en ~2 s).
- **Sede neutral**: en un Mundial casi todo es neutral; el modelo ahora no aplica
  ventaja de localía en partidos neutrales. Fit **vectorizado** (numpy) para
  escalar a miles de partidos.
- **Ajuste por disponibilidad**: factor de ataque/defensa por equipo = fracción
  del peso (posición × rol) que sigue disponible; se aplica como delta en
  log-espacio. Con plantilla completa, delta 0 (solo penaliza por bajas).

**Qué se implementó.**
- `data/history.py` (provider + `parse_results` puro), `team_mapping.resolve_history_team`.
- `prediction/dixon_coles.py` reescrito: fit vectorizado, `neutral`, `TeamAdjustment`.
- `prediction/availability.py` (puro): `compute_team_availability/adjustment`.
- `prediction/training.py`: entrena (histórico + torneo), cachea modelo, persiste
  `team_strengths`. CLI `python -m app.data.train`.
- `prediction_service` usa modelo entrenado + ajuste; guarda `Prediction.adjustments`.
- Endpoint `POST /predictions/train`; job diario reentrena el modelo.
- Config: `HISTORY_*`, `MODEL_DECAY_XI`, `ENABLE_AVAILABILITY_ADJUSTMENT`,
  `AVAILABILITY_ADJ_STRENGTH`. Migración de la columna `adjustments`.
- **`DATA_SOURCES.md`**: catálogo de datos/fuentes sugeridas (Elo, ranking FIFA,
  xG, valor de mercado, cuotas, contexto de partido) con estado de acceso.

**Verificación (end-to-end contra PostgreSQL real).**
- Entrenamiento con datos reales en ~2 s: 48 equipos, ventaja local 0.17,
  rho −0.137; **top ataque BEL/BRA/ESP/FRA/GER** (coherente con la realidad).
- Predicción BRA-MAR: sin bajas **47%/27%/26%** (1.72-1.24 goles); al lesionar 3
  titulares ofensivos del local la disponibilidad de ataque cae a 0.44 y pasa a
  **34%/30%/36%** (Marruecos se vuelve ligero favorito). Ajuste registrado.
- 46 tests en verde (disponibilidad, parser histórico, modelo+ajuste, +previos).

**Pendientes que dejó.**
- Integrar Elo/ranking FIFA como prior, y xG para ponderar por calidad (DATA_SOURCES).
- Localía real de anfitriones (MEX/USA/CAN) y contexto (altitud Ciudad de México).
- Calibración/backtesting (Brier, log-loss) y simulación del torneo con el modelo
  entrenado + disponibilidad.

---

## Entrada 005 — Prior Elo + simulación del torneo + actualización en vivo
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** (1) Añadir Elo como prior del modelo, (2) conectar el simulador
Monte Carlo con el modelo entrenado + disponibilidad, y (3) recalcular en vivo:
al terminar partidos, actualizar estadísticas y predicciones de lo venidero.

**Decisiones.**
- **Elo desde el histórico** (no fuente externa): reproducible, suma cero, con
  multiplicador por diferencia de goles y localía en no-neutrales. Se convierte en
  prior de fuerza neta (z-score) y se usa como término MAP en el fit
  (`prior_weight`). Regulariza a equipos con pocos partidos.
- **Simulación**: formato 2026 (12 grupos, 2 primeros + 8 mejores terceros,
  eliminatoria sembrada por fuerza), sede neutral y ajustes por disponibilidad.
  Bracket por rondas anidadas → siempre un campeón y probabilidades monótonas.
- **Actualización en vivo**: pipeline `recompute` (sync resultados → si cambian:
  reentrena + regenera predicciones + re-simula). Disparado por un job de
  intervalo (`LIVE_POLL_MINUTES`) además del refresco diario. Eficiente: no
  recalcula si no hubo cambios.

**Qué se implementó.**
- `prediction/elo.py` (compute_elo, elo_to_priors); `dixon_coles.fit` con priors.
- `prediction/simulator.py` reescrito (modelo+ajustes+neutral, formato 48,
  rondas anidadas); `simulation_service.py`; modelos `SimulationRun/Result`.
- `services/recompute.py` (pipeline); `prediction_service.regenerate_upcoming_predictions`
  y `compute_all_adjustments`.
- Scheduler con 2 jobs (diario + en vivo); CLI `python -m app.data.recompute`.
- Endpoints `GET/POST /simulate/*`, `POST /sync/recompute`; columna `team_strengths.elo`.
- Config: `ELO_PRIOR_WEIGHT`, `SIMULATION_ITERATIONS`, `ENABLE_LIVE_UPDATES`,
  `LIVE_POLL_MINUTES`. Migración de tablas de simulación + columna elo.
- `DATA_SOURCES.md` actualizado (Elo integrado).

**Verificación (end-to-end contra PostgreSQL real).**
- Entrenamiento con prior Elo: top ataque BEL/BRA/ESP/FRA/ARG (coherente).
- Simulación (3000 iter): top campeón BEL 22%, ARG 12%, FRA 10%, BRA 9%, POR/ESP
  8% — favoritos creíbles; probabilidades de campeón suman 1.
- Pipeline en vivo: force → regenera 72 predicciones + simula 48; sin cambios →
  no recalcula (eficiente); al "terminar" un BRA 5-0 su prob. de campeón sube
  (8.8%→10.1%).
- 54 tests en verde.

**Pendientes que dejó.**
- Bracket oficial 2026 exacto (hoy siembra por fuerza).
- Localía real de anfitriones; xG / valor de mercado / cuotas (DATA_SOURCES).
- Calibración/backtesting (Brier, log-loss) y frontend (dashboard + simulación).

---

## Entrada 006 — Frontend Angular animado + suscripción por email
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Construir la web: dashboard animado, simulación interactiva, info de
cada equipo, fixture completo con horarios y resultados; muy animado y con buen
diseño; footer con autoría (Marcos Torres + redes) y opción de suscripción por
correo para recibir predicciones.

**Qué se implementó.**
- **Backend:** modelo `Subscriber` + endpoints `POST /subscribers` (idempotente,
  email normalizado y validado) y `GET /subscribers/count`; endpoint
  `GET /predictions` (última predicción por partido, para el fixture/dashboard sin
  N llamadas). Migración de la tabla. `pydantic[email]` en requirements.
- **Frontend Angular 18 (standalone + signals):**
  - Tema global (Poppins/Inter, glassmorphism, gradientes) y librería de
    animaciones (keyframes CSS + `@angular/animations` con `stagger`).
  - Navbar sticky; footer con **autoría Marcos Torres** (web, IG, FB, TikTok).
  - `shared/subscribe`: formulario de suscripción por email.
  - Páginas (rutas lazy): `dashboard` (hero, favoritos, próximos partidos),
    `fixture` (104 partidos, filtros, horarios locales, resultados, pronósticos),
    `teams` (48 selecciones por grupo), `team-detail` (plantilla por posición +
    estado de cada jugador + DT), `simulation` (ejecutar Monte Carlo, podio y
    ranking de probabilidades de campeón).
  - `ApiService` ampliado; modelos TS; util de banderas emoji (48) y animaciones.

**Verificación.**
- Backend: `POST /subscribers` 201 + idempotencia (email case-insensitive) +
  rechazo de email inválido + `count`, contra PostgreSQL. `GET /predictions` OK.
  54 tests del backend en verde.
- Frontend: **`npm run build` compila** (bundle 360 kB inicial / 98 kB transfer;
  chunks lazy por ruta). Se corrigieron usos de `as` en `@else if` (Angular solo
  lo permite en el `@if` primario) anidando los bloques.

**Pendientes que dejó.**
- Envío real de emails a suscriptores (SMTP/proveedor) — hoy solo se almacenan.
- CI/CD Netlify (front) + Coolify (back); calibración/backtesting; bracket oficial.

---

## Entrada 007 — Envío de emails a suscriptores + CI/CD + guía de despliegue
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Enviar predicciones/novedades por email a los suscriptores tras cada
jornada, montar CI/CD y documentar el despliegue en Coolify + Netlify.

**Qué se implementó.**
- **Emails (`services/notifications.py`):** *digest* HTML (resultados recientes,
  favoritos al título, próximos partidos con pronóstico) enviado por SMTP en BCC
  a los suscriptores activos. Se dispara en el refresco diario si hubo resultados.
  Config `SMTP_*` + `NOTIFICATIONS_ENABLED`; CLI `python -m app.data.notify`.
  `aiosmtplib` en requirements.
- **CI:** `.github/workflows/ci.yml` — ruff + pytest (backend) y npm build (frontend).
  Se limpió el lint del backend (ruff 0 errores; `line-length=120`, ignore UP042).
- **CD / despliegue:** `DEPLOYMENT.md` paso a paso (PostgreSQL y app en Coolify con
  Dockerfile + migraciones automáticas, variables de entorno, dominios, carga
  inicial; Netlify con `netlify.toml`; CORS; SMTP; checklist y troubleshooting).

**Verificación.**
- Email end-to-end contra un servidor SMTP local (aiosmtpd): `notify_subscribers`
  envió a 2 suscriptores; el servidor recibió 1 mensaje con ambos en BCC y el HTML
  con cabecera, resultados, favoritos y enlace. Gate "solo con resultados" OK.
- `ruff check app/ tests/` limpio; 54 tests backend en verde; build del frontend OK.

**Pendientes que dejó.**
- Completar en producción las variables/keys reales en Coolify y Netlify.
- Calibración/backtesting (Brier, log-loss); bracket oficial 2026 exacto.
- Doble opt-in / baja de suscripción (enlace unsubscribe) para cumplimiento.

---

## Entrada 008 — Backtesting/calibración + baja de suscripción (unsubscribe)
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Medir la precisión del modelo (calibración) y completar el email con
un enlace de baja por cumplimiento.

**Qué se implementó.**
- **Métricas (`prediction/metrics.py`, puras):** log-loss, Brier multiclase y
  accuracy para predicciones 1X2.
- **Backtest (`prediction/backtest.py`):** evaluación fuera de muestra (entrena
  pre-corte, evalúa post-corte) con Elo+prior; compara contra la línea base
  (tasas empíricas). CLI `python -m app.data.backtest`; endpoint
  `GET /predictions/backtest`.
- **Unsubscribe:** `Subscriber.token` (único); endpoint
  `GET /subscribers/unsubscribe/{token}` con página HTML de confirmación;
  `notifications` ahora envía **un email por destinatario** con su enlace de baja
  y cabecera `List-Unsubscribe` (antes era BCC). Config `API_PUBLIC_URL`.
  Migración del token.

**Verificación.**
- Backtest real (corte 2024-01-01): entreno 694, test 304 → modelo log-loss
  **1.071** (base 1.099), Brier **0.641** (0.667), accuracy **46.1%** (40.5%):
  **supera a la base en las tres métricas**.
- Email/baja end-to-end (SMTP local): 2 mensajes (1 destinatario c/u) con enlaces
  de baja distintos; el endpoint da de baja con el token; el reenvío va solo a los
  activos. 60 tests en verde; ruff limpio.

**Pendientes que dejó.**
- Doble opt-in (confirmación de alta) si se requiere; bracket oficial 2026 exacto;
  walk-forward con reentrenos periódicos para un backtest aún más realista.

---

## Entrada 009 — Calibración de favoritos + variable de importancia del partido
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Los favoritos salían poco realistas (Bélgica/Curaçao arriba).
Hacer el modelo más realista y analizar qué variables lo fortalecen.

**Diagnóstico (con datos).** Con `HISTORY_TEAM_FILTER=both` (solo partidos entre
las 48) había **muestra pequeña**: Curaçao salía #1 con solo 14 partidos. Bélgica
arriba por su fuerte registro 2018-2022. El Elo (ajustado por rival y diferencia
de goles) es más predictivo que el ranking FIFA → conviene anclarse a él.

**Qué se implementó.**
- Nuevos valores por defecto: `HISTORY_TEAM_FILTER=any` (cada selección ~100
  partidos, ratings estables), `MODEL_DECAY_XI=0.004` (más forma reciente),
  `ELO_PRIOR_WEIGHT=2.5` (ancla fuerte al Elo).
- **Ponderación por importancia del partido**: `MatchResult.importance`
  (amistoso 0.5 / clasificatorio 1.0 / fase final 1.5), derivada del `tournament`
  del histórico; entra en el `fit` multiplicada por el decaimiento temporal.
- `DATA_SOURCES.md`: análisis de variables que fortalecen el modelo (Elo, xG,
  valor de mercado, importancia, forma, descanso) con impacto y estado.

**Verificación.** Con la nueva config + importancia, top favoritos:
**ESP, BRA, FRA, BEL, ARG, GER, COL, NOR, POR…** — realista y alineado con el
consenso (Bélgica baja a ~4º). 61 tests en verde; ruff limpio.

**Pendientes que dejó.**
- Siguiente salto de precisión: **xG** y/o **valor de mercado**; blending con
  cuotas para calibrar; localía real de anfitriones; bracket oficial 2026.

---

## Entrada 010 — Sedes completas + hooks de plantillas/valor de mercado
**Fecha:** 2026-06-09 · **Commit:** `pendiente`

**Objetivo.** Cargar info de sedes, plantillas/jugadores y reforzar el modelo con
xG/valor de mercado.

**Investigación (red = allowlist, solo GitHub).**
- **xG y valor de mercado de selecciones**: NO disponibles gratis/GitHub; los
  datasets de ranking FIFA hallados están desactualizados (2020). Requieren APIs
  de pago (StatsBomb/Sportmonks, Transfermarkt) → producción con keys.
- **Plantillas**: los 3 proveedores (apifootball/thesportsdb/wikidata) ya existen
  pero necesitan keys + allowlist en Coolify (la key de API-Football del usuario
  daba 403). Verificado: no accesibles desde el sandbox.

**Qué se implementó (verificable ahora).**
- **Catálogo de sedes** `data/venues.py`: las 16 sedes 2026 (estadio, ciudad,
  país, aforo). Endpoint `GET /api/v1/venues` y `venue_detail` en cada partido.
  Frontend (fixture) muestra «🏟️ Estadio · Ciudad». Cobertura 16/16 verificada.
- TheSportsDB: throttling (1.5 s/equipo) + captura de 429 para que la key gratuita
  no aborte la sincronización de plantillas.
- `DATA_SOURCES.md`: estado actualizado (sedes ✅) y nota honesta sobre xG/valor.

**Verificación.** Catálogo cubre las 16 sedes del calendario oficial; ruff limpio;
61 tests en verde; build del frontend OK.

**Pendientes que dejó.**
- En producción: keys válidas + allowlist para plantillas reales.
- xG / valor de mercado vía API de pago (hook listo: proveedor + prior).

---

## Entrada 011 — Sportmonks (plantillas/jugadores) + caché de respuestas en DB
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Integrar Sportmonks (token `SPAPI_TOKEN`) para plantillas/jugadores,
guardando cada consulta en la base de datos para no pedir dos veces lo mismo.

**Qué se implementó.**
- **Caché de respuestas** (`models/cache.py` + `data/players/_cache.py`): tabla
  `api_cache` keyed por hash del endpoint+params (sin token). `cached_get_json`
  consulta la DB antes de llamar a la API; si existe (y no caducó por
  `SPORTMONKS_CACHE_TTL_HOURS`, default 24h, <=0 = indefinida) la devuelve sin
  gastar crédito. Reutilizable por cualquier proveedor.
- **Proveedor Sportmonks** (`data/players/sportmonks.py`): resuelve cada selección
  a su team_id (search), pide el squad con `include=player.position`, mapea a
  `PlayerObservation` (nombre, posición, dorsal, fecha de nacimiento). Auth por
  header `Authorization`; throttle entre equipos. Toda llamada pasa por la caché.
- Config `spapi_token` (env **SPAPI_TOKEN**), `sportmonks_base`,
  `sportmonks_cache_ttl_hours`. Registrado en `build_player_providers` (activar con
  `PLAYER_SOURCES=sportmonks`). Migración de `api_cache`.

**Verificación (contra PostgreSQL).** 3 llamadas (2 idénticas + 1 distinta) →
**solo 2 llamadas reales a la API** (la repetida vino de la caché); 2 filas en
`api_cache`. ruff limpio; 61 tests en verde.

**Pendientes.** Ajustar nombres de campos del JSON real de Sportmonks si difieren
(implementado de forma defensiva); valor de mercado/xG de Sportmonks si el plan los
incluye (capturar en `source_data`/columna nueva).

---

## Entrada 012 — Panel de administración (frontend) con token
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Una vista de administrador para ejecutar todas las operaciones con
botones y una descripción de cada una.

**Qué se implementó.**
- **Backend** `api/endpoints/admin.py` protegido por `ADMIN_TOKEN` (cabecera
  `X-Admin-Token`; 503 si no se configura, 401 si el token es inválido):
  `/admin/check`, `/admin/status` (conteos), y operaciones `/admin/{bootstrap,
  recompute, sync, train, simulate, squads, notify}` (POST) y `/admin/backtest`
  (GET). Reusan los servicios existentes.
- **Frontend** `/admin`: login con el token (guardado en localStorage), panel de
  estado (equipos, partidos, predicciones, suscriptores, filas de caché, última
  simulación) y tarjetas con **botón + descripción** por comando; muestra el
  resultado/errores. Enlace discreto «Admin» en el footer.
- Config `admin_token`; `.env.example`.

**Verificación.** Guard 503/401/ok correcto; ruff limpio; 61 tests en verde; build
del frontend OK.

**Pendientes.** Operaciones largas (train/recompute/simulate) corren síncronas con
`--timeout 180`; si crecieran, pasarlas a tareas en segundo plano con polling.

---

## Entrada 013 — Login JWT para el panel admin (usuario/contraseña en DB)
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Sustituir el token estático del panel por un **login JWT** con
usuario y contraseña guardados (hasheados) en la base de datos.

**Qué se implementó.**
- `core/security.py` (sin dependencias): hash de contraseñas PBKDF2 y **JWT HS256
  con la librería estándar** (HMAC). Se evitó PyJWT (el sistema traía uno roto por
  `cryptography`); el HS256 propio es ligero y portable.
- Modelo `AdminUser` (username único + password_hash); migración.
- Script `python -m app.data.create_admin <usuario> <contraseña>` (o interactivo).
- `admin.py`: `POST /admin/login` (verifica contra la DB, emite JWT); el resto de
  endpoints exigen `Authorization: Bearer <token>`. Config `JWT_SECRET`
  (respaldo `ADMIN_TOKEN`), `JWT_EXPIRE_HOURS`.
- Frontend `/admin`: login con **usuario + contraseña** → guarda el JWT en
  localStorage → lo envía como Bearer.

**Verificación (contra PostgreSQL).** Script crea el usuario; login correcto emite
token; JWT válido da acceso; JWT inválido / sin token / contraseña incorrecta →
401. 67 tests en verde (incl. hash/JWT), ruff limpio, build del frontend OK.

**Pendientes.** Opcional: refresh tokens, varios roles, cambio de contraseña desde
el panel.

---

## Entrada 014 — Bracket aleatorio (favoritos realistas) + admin simplificado
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Problema.** Tras una carga inicial, Bélgica salía 33% campeón. Causa: el bracket
de eliminatorias estaba **sembrado por fuerza** (el mejor evita rivales fuertes),
lo que regala el camino al equipo top e infla su % (amplificado si la config de
Coolify tenía variables viejas como `HISTORY_TEAM_FILTER=both`).

**Qué se implementó.**
- **Simulador:** el cuadro ahora es un **sorteo aleatorio** (`_make_bracket`), como
  el sorteo real, sin camino regalado. Verificado: el máximo de campeón baja a
  ~12% (realista) en vez de inflarse.
- **Panel admin más simple:** una acción principal **«Actualizar predicciones»**
  (= recompute: reingiere resultados y recalcula modelo+predicciones+simulación,
  sin borrar nada). El resto pasa a «Operaciones avanzadas» (colapsable).
- **Info de factores:** endpoint `GET /admin/factors` y panel «Qué se tiene en
  cuenta para la predicción» (fuerza histórica, prior Elo, forma reciente,
  importancia, sede neutral, Dixon-Coles, disponibilidad, Monte Carlo) + la config
  actual (filtro, ξ, prior, iteraciones, fuentes).

**Verificación.** Champion realista con bracket aleatorio; ruff limpio; 67 tests en
verde; build del frontend OK.

**Pendiente / acción del usuario.** Quitar de Coolify las variables que sobrescriben
los nuevos defaults (`HISTORY_TEAM_FILTER`, `MODEL_DECAY_XI`, `ELO_PRIOR_WEIGHT`)
para que apliquen los valores calibrados (any / 0.0015 / 2.5).

---

## Entrada 015 — Estudio del modelo, métrica RPS y ξ optimizado por RPS
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Responder «cómo debe ser un modelo predictivo, qué hacen otros
modelos similares y qué estrategia matemática seguir para más precisión», y dejar
el primer paso medible implementado.

**Qué se implementó.**
- **`MODEL_STUDY.md`** — estudio completo: (1) principios de un buen modelo
  (calibración > accuracy, *proper scoring rules*/RPS, conciencia temporal, ajuste
  por rival, regularización/shrinkage, parsimonia, walk-forward); (2) comparación
  de modelos de referencia (Elo, Maher/Poisson, Dixon-Coles, 538 SPI, bayesiano
  jerárquico, ML, cuotas de mercado) y qué tomamos de cada uno; (3) análisis de lo
  que ya tenemos y brechas; (4) **estrategia priorizada** (RPS → calibración →
  optimizar hiperparámetros → ensamble con mercado → valor de mercado → xG →
  contexto → bracket real); (5) **formulación matemática** (MAP penalizado con
  verosimilitud ponderada, covariables, ensamble convexo con el mercado,
  *temperature scaling*, fórmula del RPS).
- **Métrica RPS** (`prediction/metrics.py`) — *Ranked Probability Score*, la
  estándar en fútbol (ordinal: penaliza más equivocarse «lejos»). El backtest
  (`prediction/backtest.py`, CLI `app.data.backtest`) ahora reporta RPS del modelo
  vs línea base y declara si la **supera**. 4 tests nuevos del RPS.
- **ξ optimizado por RPS** — barrido walk-forward (corte 2024, 304 partidos de
  test): `ξ=0.0015` bate la base (RPS 0.213 vs 0.225); `ξ=0.004` (lo que había)
  **no** la batía (0.227). Se baja el default `model_decay_xi` 0.004 → **0.0015**.
  El peso del prior apenas mueve el RPS → se mantiene en 2.5. Ver `MODEL_STUDY.md`
  §4.1.

**Verificación.** Barrido RPS reproducible (tabla en §4.1); ruff limpio; pytest en
verde (incluidos los 4 tests del RPS).

**Pendientes que dejó.** Acciones #2–#5 de la estrategia (ensamble con cuotas,
calibración, valor de mercado, xG) cuando haya APIs; bracket oficial 2026.

---

## Entrada 016 — Hiperparámetros hardcodeados + recompute en segundo plano
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** (1) Que los hiperparámetros calibrados no los degrade ningún valor
viejo del entorno; (2) que el botón «Actualizar predicciones» no bloquee la página
ni se rompa al recargar.

**Qué se implementó.**
- **Hiperparámetros calibrados hardcodeados.** `history_team_filter` (any),
  `model_decay_xi` (0.0015) y `elo_prior_weight` (2.5) dejan de ser campos de
  entorno y pasan a **constantes + propiedades de solo lectura** en `config.py`:
  aunque Coolify/.env traiga `MODEL_DECAY_XI=0.004`, se ignora. Para recalibrar se
  cambia en `config.py` y se revalida con `python -m app.data.backtest`.
- **Recompute en segundo plano (a prueba de recargas).** `POST /admin/recompute`
  ya no corre síncrono (reentreno + 5000 simulaciones colgaban la petición y un
  refresco la cortaba, con riesgo de timeout del proxy). Ahora crea un **`JobRun`**
  y lanza la tarea con su **propia sesión de DB**, respondiendo al instante. El
  panel consulta `GET /admin/job` por polling (cada 3 s). Como producción corre
  **2 workers Gunicorn**, el estado vive en la **DB** (tabla `job_runs`), no en
  memoria, para que cualquier worker lo lea. Migración `c1a2b3d4e5f6`.
  - `app/services/jobs.py`: un job a la vez (bloqueo por `JobInProgress`), detección
    de jobs obsoletos (>30 min = worker caído, no bloquea), registro de done/error.
  - Frontend: el botón lanza el job y hace polling; **si recargas o cierras**, al
    volver el panel se reengancha al job en curso (`resumeJob`) y muestra un aviso
    «puedes recargar o cerrar, seguirá corriendo en el servidor».

**Verificación.** ruff limpio; **74 tests** en verde (incl. 3 nuevos del job runner
contra SQLite en memoria, con `importorskip` para no romper CI); migración válida
en modo offline (`alembic upgrade --sql`); `npm run build` OK.

**Pendientes que dejó.** Igual que la 015 (acciones #2–#5 de la estrategia).

---

## Entrada 017 — Análisis del supercomputador de Opta + ensamble y 10k sims
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Analizar la metodología del supercomputador de Opta (Mundial 2026) y
aplicar lo accionable para maximizar la precisión.

**Hallazgos (Opta).** Estima cada partido combinando **cuotas del mercado + Opta
Power Rankings** (Elo jerárquico 0–100 sobre ~13.500 clubes, ajustado por dif. de
goles y calidad de competición), ataque/defensa calibrados con histórico y **10.000
simulaciones**. Favorita: España 16,1%, Francia 13%, Inglaterra 11,2%, Argentina
10,4%. Confirma nuestras dos mayores brechas: **falta el mercado** y **falta el
nivel de club** (lo aproxima el valor de mercado del plantel). Detalle en
`MODEL_STUDY.md §2.1`.

**Qué se implementó.**
- **Mecánica de ensamble** (`prediction/ensemble.py`): `blend()` (combinación
  convexa `ω·modelo + (1−ω)·externa`, renormalizada) y `best_blend_weight()` (elige
  `ω` minimizando RPS). Es la pieza central del enfoque Opta; queda **lista para
  enchufar** la fuente externa (cuotas / Power Rankings). 7 tests.
- **Simulación a 10.000 iteraciones** (antes 5.000), como Opta: menos varianza en
  las probabilidades de avance/campeón.
- Estudio actualizado: §2.1 (caso Opta + benchmark de realidad) y §7 (pasos hechos).

**Verificación.** ruff limpio; **81 tests** en verde (7 nuevos del ensamble).

**Pendientes que dejó.** Conectar la fuente externa al ensamble: **API de cuotas**
(acción #2, el mayor salto) y **valor de mercado / Power Rankings** (acción #4).
Ambas requieren API + allowlist en Coolify → decisión del usuario.

---

## Entrada 018 — Web scraping de Wikipedia: plantillas, DT, fotos e info
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Enriquecer las plantillas con **fotos** de jugadores, **información**,
las bajas/lesionados (faltantes) y el **entrenador**, vía web scraping además de las
APIs.

**Qué se implementó.**
- **Foto + info en el modelo:** `Player.photo_url`/`Player.info` y `Coach.photo_url`
  (migración `d2b3c4e5f6a7`); expuestos en `PlayerRead`/`CoachRead`. La cadena
  observación → consenso → servicio propaga los campos.
- **Consenso para foto/info:** como cada fuente trae una URL distinta, NO se votan
  por mayoría: `merge_first_available()` toma la de **mayor prioridad** sin marcar
  conflicto (no ensucia `squad_discrepancies`). La confianza se sigue midiendo solo
  con los campos votados.
- **Scraper de Wikipedia** (`app/data/players/wikipedia.py`, fuente `wikipedia`):
  API de MediaWiki (sin clave). Parsea las plantillas wiki `{{nat fs player}}`
  (dorsal, posición, nombre, club), el seleccionador (`|manager=`) y trae la **foto**
  de cada jugador/DT con `prop=pageimages` en lotes de 50. El parser de wikitexto
  (`parse_squad_wikitext`) es puro y testeado (maneja wikilinks `[[A|B]]`).
- **Fotos desde las fuentes que ya las daban:** TheSportsDB (`strCutout`/`strThumb`
  + biografía) y Wikidata (imagen P18). Antes se ignoraban.
- **Faltantes (bajas/lesionados):** ya modelados en `PlayerStatus`
  (injured/suspended/doubtful/out) y consensuados; el frontend los pinta con color.
- **Frontend:** la vista de equipo muestra el **avatar** de cada jugador (con
  iniciales de fallback) y la **foto del DT** en la cabecera.
- **Prioridad de consenso** ampliada: apifootball > sportmonks > thesportsdb >
  wikipedia > wikidata > fixture.

**Verificación.** ruff limpio; **87 tests** en verde (4 del parser de Wikipedia + 2
del consenso de fotos); migración válida en modo offline; `npm run build` OK.

**Pendiente / acción del usuario.** En Coolify: añadir `en.wikipedia.org`,
`commons.wikimedia.org` y `query.wikidata.org` a la allowlist y poner
`PLAYER_SOURCES=thesportsdb,wikipedia,wikidata` (+ apifootball/sportmonks si hay
keys). En el sandbox de desarrollo esos hosts no responden (por eso `fixture` sigue
siendo el default en dev).

---

## Entrada 019 — Ensamble con cuotas de mercado (The Odds API)
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Implementar la mayor palanca de precisión del estudio (acción #2, el
núcleo del método de Opta): **mezclar la predicción del modelo con las cuotas del
mercado**, la señal más predictiva que existe.

**Decisiones.**
- **Fuente: The Odds API** (the-odds-api.com), capa **gratuita** (500 créditos/mes):
  una sola llamada trae las cuotas 1X2 de todo el Mundial; con el caché en DB
  (`api_cache`) el gasto es mínimo. Elegida por coste €0 frente al add-on de odds de
  Sportmonks (€14–69/mes) y API-Football ($19/mes).
- **Fase 1 (hecha): predicciones por partido.** Se mezclan las predicciones 1X2
  guardadas. **Fase 2 (futuro): el simulador** — inyectar cuotas en los partidos de
  grupo es invasivo (la tabla necesita diferencia de goles, no solo 1X2), se hará
  tras verificar el flujo de cuotas en producción.

**Qué se implementó.**
- **Proveedor** `app/data/odds/the_odds_api.py`: `decimal_to_probabilities` (cuotas
  → prob. implícita **sin margen**), `parse_odds_events` (promedia casas, indexa por
  nombres normalizados) y `TheOddsApiProvider.fetch_match_probabilities` (1 llamada
  cacheada). Funciones puras y testeadas.
- **Mezcla** en `predict_and_store(market=…)` con `blend_one` (P = ω·modelo +
  (1−ω)·mercado); guarda en `Prediction.ensemble` la terna del modelo, la del mercado
  y ω (migración `e3c4d5f6a7b8`). `regenerate_upcoming_predictions` obtiene las cuotas
  (1 llamada) y empareja por nombre de equipo normalizado.
- **Defensivo:** si el ensamble está apagado, no hay key o falla la API → predicción
  **solo-modelo** (nunca rompe). Flag `ENABLE_MARKET_ENSEMBLE` (def. off),
  `ODDS_API_KEY`, `ENSEMBLE_MODEL_WEIGHT` (ω, def. 0.4 → el mercado pesa más).
- **Transparencia:** `/admin/factors` añade el factor "Cuotas de mercado" + la config;
  el fixture muestra "💰 incluye mercado" en los partidos mezclados.

**Verificación.** ruff limpio; **92 tests** en verde (5 nuevos del proveedor de
cuotas); migración válida en modo offline; `npm run build` OK.

**Pendiente / acción del usuario.** En Coolify: allowlistar `api.the-odds-api.com`,
poner `ODDS_API_KEY` y `ENABLE_MARKET_ENSEMBLE=true`. Afinar ω por RPS cuando haya
cuotas históricas (mecánica `best_blend_weight` ya lista). Fase 2: ensamble en el
simulador (probabilidades de campeón).

---

## Entrada 020 — Aprendizaje continuo: cron horario multi-fuente
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Que el modelo mejore **cada hora** recopilando datos de diversas
fuentes de forma constante y reentrenándose con ellos.

**Qué se implementó.**
- **Job horario `run_hourly_refresh`** (scheduler, cada `HOURLY_REFRESH_MINUTES`=60,
  flag `HOURLY_REFRESH_ENABLED` on): (1) sincroniza plantillas multi-fuente
  (jugadores/lesiones/fotos + DT desde thesportsdb/wikipedia/wikidata/apifootball/
  sportmonks), (2) lanza el recálculo forzado → reingesta de resultados + **cuotas**
  → reentreno → predicciones → simulación. El modelo se afina con datos frescos.
- **Recálculos serializados.** Diario, horario, en vivo y manual ahora pasan **todos**
  por `jobs.start_job` (un job a la vez, visible en `job_runs`/panel). `_trigger_recompute`
  centraliza el lanzamiento y omite si ya hay uno en curso.
- **Anti-duplicado entre workers.** `start_job` toma un **lock consultivo de Postgres**
  (`pg_advisory_xact_lock`) en el "comprobar + crear job": con 2 workers Gunicorn —cada
  uno con su scheduler— no se crean dos recálculos a la vez. No-op en SQLite (tests).
- **CLI `python -m app.data.learn`** para cron externo (Coolify con `ENABLE_SCHEDULER=
  false`): mismo ciclo (plantillas + recálculo) en un proceso que termina.
- El **digest por email** queda solo en el job diario (no spamea cada hora).

**Verificación.** ruff limpio; **92 tests** en verde (start_job sigue OK en SQLite, el
lock es no-op fuera de Postgres); imports del scheduler/CLI correctos.

**Pendiente / acción del usuario.** En Coolify ya viene activo por defecto
(`HOURLY_REFRESH_ENABLED=true`). Asegurar la allowlist de fuentes (wikipedia/
wikidata/thesportsdb/odds) y, si se prefiere cron externo, `ENABLE_SCHEDULER=false`
+ programar `python -m app.data.learn` cada hora. Durante el torneo se puede bajar
`LIVE_POLL_MINUTES` para captar resultados más rápido.

---

## Entrada 021 — Configuración editable desde el panel admin
**Fecha:** 2026-06-10 · **Commit:** `pendiente`

**Objetivo.** Poder cambiar las configuraciones operativas desde el **panel admin**
(no solo por variables de entorno en Coolify).

**Qué se implementó.**
- **Overrides en DB** (`app_settings`, migración `f5a6b7c8d9e0`): cada fila pisa el
  valor de entorno de un ajuste **operativo**. Servicio `app/services/app_settings.py`
  con un registro `EDITABLE` (clave, tipo, grupo, etiqueta, descripción, min/max,
  secreto) + `apply_overrides`/`save_overrides`/`effective_config`.
- **Ajustes editables:** cron horario (on + minutos), actualización en vivo (on +
  minutos), ensamble de mercado (on + ω + API key de The Odds API), fuentes de
  plantillas, ajuste por disponibilidad (on + fuerza), iteraciones de simulación,
  emails a suscriptores, hora del refresco diario. **NO** los hiperparámetros del
  modelo (ξ/filtro/prior), que siguen blindados.
- **Aplicación en caliente, multi-worker:** los overrides se aplican sobre el
  `settings` en memoria al **arrancar** (lifespan) y al **inicio de cada job** del
  scheduler (`_refresh_overrides`), de modo que los 2 workers Gunicorn convergen.
  Los jobs horario/vivo además **comprueban su flag** en runtime (on/off inmediato).
- **Endpoints** `GET/POST /admin/settings` (los secretos no se exponen; un valor
  vacío = "no cambiar"). Al guardar se reprograma el scheduler del worker.
- **Frontend:** panel **⚙️ Configuración** en `/admin`, agrupado, con toggles,
  números y textos; botón Guardar. Secretos como password con placeholder "guardada".

**Verificación.** ruff limpio; **96 tests** en verde (4 nuevos: coerción/clamp,
ocultado de secretos y roundtrip guardar→aplicar contra SQLite); migración válida
en modo offline; `npm run build` OK.

**Nota.** Los cambios de **comportamiento** (ensamble, fuentes, ω, on/off de crones)
aplican en el próximo ciclo; los **intervalos** de los crones aplican del todo tras
reiniciar el backend (o en el worker que atendió el guardado).

---

## Entrada 022 — Monetización: AdSense + afiliados de apuestas
**Fecha:** 2026-06-11 · **Commit:** `pendiente`

**Objetivo.** Monetizar la plataforma aprovechando el pico de tráfico del Mundial
(empieza hoy): anuncios display + afiliación de casas de apuestas.

**Qué se implementó.**
- **`MONETIZATION.md`**: análisis completo (vías, ingresos estimados, esfuerzo,
  plazos, hoja de ruta y consideraciones legales).
- **Anuncios (AdSense):** `shared/ad-slot` (solo carga si hay `adsenseClient` +
  consentimiento), banner de cookies (`shared/consent-banner` + `consent.service`),
  página `/privacidad`, `ads.txt` servido en la raíz (`src/static` + `angular.json`).
  Slots en dashboard y fixture. Sin configurar → el sitio queda idéntico.
- **Afiliados (editable en caliente):** ajustes `affiliate_enabled/url/label` (grupo
  Monetización del panel ⚙️), endpoint público `GET /api/v1/config` (sin secretos),
  componente `shared/affiliate-cta` con `rel="sponsored"` + aviso +18, en dashboard
  y fixture. `ConfigService` carga la config pública una vez al arrancar.
- **Cumplimiento:** disclaimer permanente en el footer (+18, juego responsable,
  "estimaciones estadísticas, no consejo de apuestas") + enlace a Privacidad.

**Verificación.** ruff limpio; **98 tests** en verde (2 nuevos del endpoint público);
`npm run build` OK; `ads.txt` copiado a la raíz del publish de Netlify.

**Acción del usuario.** (1) Crear cuenta AdSense y pegar el `pub-id` en
`environment*.ts` + `ads.txt`. (2) Alta en un programa de afiliados; pegar la URL en
el panel y activar. (3) Revisar la regulación de juego del país objetivo.

---

## Entrada 023 — SEO + Google Analytics + agente de crecimiento (DeepSeek)
**Fecha:** 2026-06-11 · **Commit:** `pendiente`

**Objetivo.** (1) Optimizar SEO e indexar en Google; (2) Google Analytics; (3) un
cron cada 2 h que investigue y proponga cómo promocionar y monetizar mejor el sitio,
de forma automática y organizada, avisando por email cuando haga falta configurar algo.
Dominio público de producción: **mayapredice.site**.

**Qué se implementó (Fase A — frontend, en producción).**
- **`index.html`**: meta description, `canonical`, Open Graph, Twitter Card,
  `theme-color`, `robots`, JSON-LD (`WebSite` + `SportsEvent` Mundial 2026) y hueco
  para el meta de verificación de Search Console.
- **Google Analytics 4** (`G-8KRF0P5NZJ`) con **Consent Mode v2**: denegado por
  defecto; concedido al aceptar cookies (`ConsentService` propaga el consent a gtag).
- **`SeoService`** + `data.seo` por ruta (título/description/canonical/OG por página)
  vía listener de router en `AppComponent`.
- **`robots.txt`** (allow + `Sitemap:`, `Disallow: /admin`) y **`sitemap.xml`**
  generado en build (`scripts/gen-sitemap.mjs`: rutas estáticas + 48 equipos desde la
  API con fallback). `angular.json` copia `robots.txt`.

**Qué se implementó (Fase C — backend, apagado por defecto).**
- **Agente de crecimiento** (`services/growth/`): cliente DeepSeek (httpx, API
  OpenAI-compatible), IndexNow, y `run_growth_cycle` → reúne contexto del sitio +
  **historial de ideas previas** (se "entrena"/itera y evita repetir) → pide a DeepSeek
  ideas de SEO/promoción/contenido/monetización en JSON → las persiste
  (`GrowthRun`/`GrowthInsight`, migración `a1b2c3d4e5f6`) → ejecuta acciones
  automáticas seguras (ping IndexNow) → envía **email-digest** al dueño.
- **Regla dura:** las ideas de **monetización** SIEMPRE requieren aprobación (no se
  ejecutan solas; van al email para tu OK). Si falta `DEEPSEEK_API_KEY`, el ciclo
  termina y **te avisa por email**.
- **Scheduler:** job `growth_agent` cada `GROWTH_AGENT_MINUTES` (=120) si
  `GROWTH_AGENT_ENABLED` (off). Reprogramable desde el panel. CLI `python -m app.data.grow`.
- Ajustes editables (grupo "Crecimiento"; keys como secreto), endpoints
  `/admin/growth*`, `notifications.send_growth_report`.

**Fase B — Prerender/SSG: pendiente.** Se intentó el prerender estático de Angular 18,
pero el extractor de rutas del builder montaba la plataforma de navegador (DOCUMENT
global) en este setup manual → `document is not defined` incluso con config mínima.
Se revirtió para no romper el build de Netlify. Googlebot renderiza el JS, así que el
SEO por ruta ya funciona; el SSG queda como follow-up (idealmente vía `ng add @angular/ssr`).

**Verificación.** `npm run build` OK (sitemap + robots en la raíz; GA en el `<head>`);
backend **101 tests** en verde + ruff limpio; migración encadena en un solo head.

**Acción del usuario (config).** Ver `SEO.md` §checklist: en Coolify
`DEEPSEEK_API_KEY` + `GROWTH_AGENT_ENABLED=true` + `PUBLIC_SITE_URL` + `INDEXNOW_KEY` +
`SMTP_*`, y `CORS_ORIGINS`/`SITE_URL` con `mayapredice.site`; **allowlist** de
`api.deepseek.com` e `api.indexnow.org`; Netlify → dominio `mayapredice.site`; Search
Console → verificar + enviar sitemap; subir `assets/og-cover.png` (1200×630);
**rotar** la API key de DeepSeek.
