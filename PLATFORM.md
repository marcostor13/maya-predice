# PLATFORM.md — Qué incluye la plataforma maya-predice

> Especificación de producto. Define **qué** se desarrolla (alcance funcional,
> features, datos y reglas). Para el **cómo** técnico ver `ARCHITECTURE.md`.
> Mantener sincronizado con la checklist de estado en `CLAUDE.md`.

---

## 1. Objetivo

Plataforma web pública que muestra **predicciones estadísticas de los partidos
del Mundial de Fútbol 2026**: probabilidad de victoria/empate/derrota, marcador
más probable, goles esperados, y simulación del avance del torneo.

Público: aficionados al fútbol. Tono: visual, claro, confiable (mostrar que las
predicciones vienen de un modelo, no de opiniones).

## 2. El Mundial 2026 (reglas del dominio)

- **48 selecciones**, 3 países anfitriones (México, EE. UU., Canadá).
- **Fase de grupos:** 12 grupos de 4 equipos. Avanzan los 2 primeros de cada
  grupo + los 8 mejores terceros → **32 equipos** a eliminatorias.
- **Eliminatorias:** dieciseisavos → octavos → cuartos → semifinales → final
  (y tercer puesto).
- El esquema de datos y el simulador **deben soportar este formato**.

## 3. Funcionalidades (features)

### F1 — Catálogo de equipos
- Listado de las 48 selecciones con: nombre, bandera/código, confederación,
  grupo asignado, ranking FIFA, fuerza estimada (ataque/defensa del modelo).
- Detalle de equipo: parámetros del modelo y próximos partidos.

### F2 — Calendario de partidos
- Listado de partidos por fase y por grupo, con fecha/hora, sede y estado
  (programado / en juego / finalizado).
- Filtros por grupo, fase y selección.

### F3 — Predicción de partido (núcleo)
Para cada partido:
- Probabilidad de **victoria local / empate / victoria visitante**.
- **Goles esperados** de cada equipo (λ, μ).
- **Marcador más probable** y top-5 marcadores con su probabilidad.
- Si es eliminatoria: probabilidad de que cada equipo **avance**.

### F4 — Tabla de grupos / standings simulados
- Para cada grupo, probabilidad de que cada equipo termine 1.º, 2.º, etc.
- Puntos esperados.

### F5 — Simulación del torneo
- Simulación **Monte Carlo** (N iteraciones) del bracket completo.
- Salida: probabilidad de cada selección de llegar a octavos, cuartos, semis,
  final y de **ser campeón**.

### F6 — Comparador / detalle del modelo
- Página que explica el modelo (Dixon-Coles) de forma accesible.
- Versión del modelo y fecha de última actualización de predicciones.

### F7 (futuro) — Backtesting / precisión
- Métricas de calibración (Brier score, log-loss) sobre partidos ya jugados.

### F8 — Datos oficiales y verificación diaria (implementada)
- Ingesta de toda la información oficial del torneo desde la fuente oficial.
- **Verificación automática al final de cada día**: detecta y registra cambios
  (resultados de los partidos jugados, cambios de horario/sede, resolución de
  cruces eliminatorios) para mantener la plataforma siempre al día.
- Auditoría consultable: historial de verificaciones y log de "qué cambió".

### F13 — Frontend web animado (implementada)
- **Dashboard** con hero animado, favoritos al título, próximos partidos con
  barras de probabilidad y llamada a la suscripción.
- **Fixture completo**: 104 partidos por fase/grupo, horarios en zona local,
  resultados y pronósticos, con filtros.
- **Equipos**: las 48 selecciones y, por equipo, su **plantilla** (jugadores por
  posición, suplentes, entrenador) con el **estado** de cada uno.
- **Simulación interactiva**: el usuario ejecuta el Monte Carlo y ve el podio y el
  ranking de probabilidades de campeón animados.
- Diseño cuidado y muy animado (tema oscuro, glassmorphism, transiciones,
  banderas). **Footer con autoría: Marcos Torres** (web, Instagram, Facebook,
  TikTok) y **suscripción por correo** para recibir predicciones y novedades.

### F12 — Actualización en vivo durante el torneo (implementada)
- A medida que **terminan los partidos**, la plataforma reingiere los resultados y
  **recalcula automáticamente** las estadísticas del modelo, las predicciones de
  los partidos venideros y la simulación del torneo.
- Eficiente: solo recalcula cuando hay cambios. Frecuencia configurable
  (`LIVE_POLL_MINUTES`); también disparable manualmente (`POST /sync/recompute`).

### F11 — Simulación del torneo + prior Elo (implementada)
- **Probabilidades de avance y de título** por selección vía simulación Monte
  Carlo del formato 2026 (grupos + mejores terceros + eliminatorias), usando el
  modelo entrenado y los ajustes por disponibilidad.
- El modelo incorpora un **prior Elo** (calculado del histórico) que regulariza a
  las selecciones con pocos partidos recientes.

### F10 — Modelo entrenado con histórico + ajuste por bajas (implementada)
- El modelo se **entrena con resultados históricos reales** (miles de partidos
  internacionales) y con los resultados del propio torneo; respeta la sede neutral
  y da más peso a lo reciente.
- Las predicciones se **ajustan por la disponibilidad de la plantilla**: las bajas,
  lesiones y sanciones reducen la fuerza efectiva del equipo (más en ataque o en
  defensa según las posiciones afectadas). El ajuste aplicado queda registrado.
- Catálogo de datos/fuentes para seguir nutriendo el modelo: ver `DATA_SOURCES.md`.

### F9 — Plantillas multi-fuente con veracidad (implementada)
- **Plantilla completa** por selección: jugadores, suplentes y entrenador, con
  posición, dorsal, club y **estado** (disponible/lesionado/sancionado/duda/baja).
- **Cruce de 3 fuentes** (API-Football, TheSportsDB, Wikidata) con **consenso por
  voto mayoritario**: cada dato lleva un nivel de **confianza** según cuántas
  fuentes coinciden, y los **conflictos** quedan registrados (qué dijo cada una).
- Se actualiza en la verificación diaria. Endpoint de plantilla y de discrepancias.
- Datos sensibles a la veracidad: a mayor acuerdo entre fuentes, mayor confianza.

## 4. Datos

### Entidades
- **Tournament:** edición del torneo (Mundial 2026), formato, fechas.
- **Team:** selección (nombre, código ISO, confederación, grupo, ranking FIFA).
- **Match:** partido (local, visitante, fase, grupo, fecha, sede, resultado).
- **Prediction:** salida del modelo para un partido (probabilidades, goles
  esperados, matriz de marcadores) versionada.
- **TeamStrength:** parámetros ataque/defensa por versión de modelo.

### Fuentes de datos
- **Fuente oficial primaria (implementada):** `openfootball/worldcup.json` —
  JSON de dominio público derivado del calendario oficial de la FIFA (104
  partidos, 12 grupos, sedes, horarios y resultados). La FIFA no ofrece API
  pública y `api.fifa.com` bloquea servidores (403), por eso se usa openfootball
  tras una abstracción de proveedor swappable (ver ADR-004). Ingesta en
  `backend/app/data/`.
- **Verificación diaria (implementada):** un job programado (06:00 UTC por
  defecto) re-consulta la fuente, hace upsert idempotente y **registra cada
  cambio** (resultado, horario, sede, resolución de cruces) en `data_changes`,
  con un `SyncRun` de auditoría. Disparable también manualmente vía API o CLI.
- **Pendiente:** resultados históricos de selecciones para entrenar el modelo
  (se puede añadir como segundo proveedor) y ranking FIFA.

## 5. Reglas de negocio
- Las predicciones se **recalculan** y se guarda cada corrida con
  `model_version` + timestamp (auditoría e historial).
- Los goles esperados nunca son negativos; las probabilidades de un partido
  suman 1.
- La simulación respeta el formato 2026 (grupos, mejores terceros, bracket).
- Datos de partidos finalizados son inmutables salvo corrección manual.

## 6. Roadmap por fases

**Fase 0 — Scaffolding (hecho):** estructura, docs, agents/skills, configs.

**Fase 1 — Backend core:**
- Modelos ORM + migraciones.
- Motor Dixon-Coles + simulador Monte Carlo.
- Endpoints: teams, matches, predictions, simulate.
- Seed con equipos y grupos del Mundial 2026.

**Fase 2 — Datos reales:**
- Ingesta de históricos y fixture oficial.
- Entrenamiento/calibración del modelo, backtesting.

**Fase 3 — Frontend:**
- Dashboard (F2/F3), detalle de partido (F3), standings (F4), simulación (F5).
- Página explicativa del modelo (F6).

**Fase 4 — Producción:**
- Deploy frontend (Netlify) + backend/DB (Coolify), dominios, CI/CD.

**Fase 5 — Mejoras:**
- Backtesting/precisión (F7), actualizaciones en vivo durante el torneo.

## 7. Fuera de alcance (por ahora)
- Apuestas reales / dinero.
- Cuentas de usuario y predicciones personalizadas (posible fase futura).
- App móvil nativa (la web es responsive).
