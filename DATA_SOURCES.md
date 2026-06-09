# DATA_SOURCES.md — Catálogo de datos y fuentes para nutrir el modelo

> Qué datos enriquecen la predicción, con qué fuentes obtenerlos, qué aportan al
> modelo y su estado (accesible ya / requiere allowlist+key). Sirve para decidir
> qué integrar a continuación. Leyenda de acceso:
> 🟢 accesible vía GitHub raw (ya usable) · 🟡 requiere allowlist + API key en
> producción · 🔵 requiere scraping/licencia.

---

## Estado actual (ya integrado)

| Dato | Fuente | Estado | Qué aporta |
|------|--------|--------|------------|
| Calendario, grupos, sedes, resultados 2026 | openfootball | 🟢 | Estructura del torneo + resultados (verificación diaria). |
| Plantillas, suplentes, DT, estado | API-Football + TheSportsDB + Wikidata (consenso) | 🟡 | Disponibilidad de jugadores → ajuste de fuerza. |
| **Histórico internacional (49k partidos)** | martj42/international_results | 🟢 | **Entrena el modelo** (ataque/defensa, localía, rho). |
| **Elo internacional (prior)** | calculado del histórico (`prediction/elo.py`) | 🟢 | Prior de fuerza; regulariza equipos con pocos partidos. |

---

## Recomendado a continuación (orden de impacto/esfuerzo)

> El **Elo** ya está integrado (calculado del histórico) como prior. El ranking
> FIFA oficial como segunda señal queda de baja prioridad.

### 1. xG (expected goals) y estadísticas de tiro — calidad, no solo resultado 🟡
**Por qué.** El marcador tiene mucho ruido; el **xG mide la calidad de las
ocasiones** y predice mejor el rendimiento futuro que los goles. Permite ponderar
la forma reciente por mérito real.
- **FBref / StatsBomb** (Opta-like), **Understat**, **API-Football** (xG post-2017).
- Datasets: `eatpizzanot/soccer-dataset` (367k partidos, xG donde existe) 🟢.
**Integración.** Sustituir/combinar goles por xG en el ajuste de fuerza; usar
medias móviles de xG a favor/en contra como features.

### 2. Valor de mercado / fuerza de plantilla — fuerza estructural 🔵
**Por qué.** El **valor de mercado agregado** (Transfermarkt) correlaciona fuerte
con el nivel de la selección y cubre a equipos con poco histórico.
- **Transfermarkt** (scraping/licencia) 🔵; algunos datasets derivados en GitHub 🟢.
**Integración.** Feature de prior por equipo; útil para los debutantes 2026.

### 3. Cuotas de casas de apuestas — consenso de mercado para calibración 🟡
**Por qué.** Las **odds de cierre** (sobre todo Pinnacle) son un benchmark
difícil de batir; sirven para **calibrar y validar** (¿estamos por encima del
mercado?) y para blending.
- **The Odds API**, **OddsPortal**, feeds de Pinnacle. 🟡.
**Integración.** Convertir odds→probabilidades (quitando el margen) y comparar
con el modelo (Brier/log-loss); opcional: blending modelo+mercado.

### 4. Contexto del partido — ajustes finos 🟢/🟡
- **Sede/altitud/clima**: Ciudad de México (2240 m) y calor en sedes de EE. UU.
  afectan al ritmo y a los goles. Datos de altitud por sede (estáticos) 🟢; clima
  por API (Open-Meteo) 🟡.
- **Descanso/viaje entre partidos**: derivable del propio calendario 🟢.
- **Importancia/tipo de partido**: ya en el histórico (`tournament`) 🟢 — se puede
  ponderar (amistoso < clasificatorio < fase final).
- **Localía real de anfitriones (MEX/USA/CAN)**: aplicar ventaja de localía solo a
  los anfitriones en sus sedes (hoy las predicciones del torneo son neutrales).

### 5. Lesiones/sanciones en vivo y alineaciones confirmadas 🟡
**Por qué.** Ya ajustamos por disponibilidad; con **alineaciones confirmadas**
~1 h antes del partido el ajuste es mucho más preciso.
- **API-Football** (`/injuries`, `/fixtures/lineups`), **TheSportsDB**. 🟡.

---

## Notas de integración (arquitectura)
- Toda fuente nueva entra **detrás de una abstracción** (`DataProvider` /
  `PlayerDataProvider`) y, si aporta señal de fuerza, se combina en el
  entrenamiento o como prior — nunca cableada en el modelo.
- **Red del entorno = allowlist**: en producción (Coolify) hay que allowlistar el
  host y cargar la API key. En el sandbox de desarrollo solo GitHub raw responde.
- Preferir fuentes **reproducibles y versionables** (CSV/JSON en GitHub) para
  poder hacer **backtesting** estable.

## Fuentes citadas
- martj42/international_results · openfootball/worldcup.json
- eloratings.net · "International Football Elo Ratings" (Kaggle)
- FBref/StatsBomb · Understat · eatpizzanot/soccer-dataset
- Transfermarkt · The Odds API · Pinnacle · Open-Meteo · API-Football
