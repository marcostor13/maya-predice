# MODEL_STUDY.md — Estudio del modelo predictivo y estrategia de precisión

> Estudio de cómo debe ser un buen modelo de predicción de fútbol, comparación con
> los modelos de referencia, análisis de lo que tenemos y una **estrategia
> matemática priorizada** para subir la precisión sin perder veracidad.

---

## 1. Qué hace bueno a un modelo predictivo de fútbol

No se trata de "acertar el ganador", sino de **estimar bien las probabilidades**.
Principios (consenso de la literatura):

1. **Calibración > accuracy.** Si dices 70% y ocurre ~70% de las veces, el modelo
   es útil aunque "falle" muchos partidos. La accuracy del resultado más probable
   engaña (el fútbol tiene mucho empate/azar).
2. **Reglas de puntuación propias (proper scoring rules).** Para evaluar usa
   medidas que premian la honestidad probabilística: **RPS** (la estándar en
   fútbol, ordinal: visitante < empate < local), **log-loss** y **Brier**.
3. **Conciencia temporal.** La forma reciente importa más → decaimiento temporal.
4. **Ajuste por rival y por contexto.** Goles a favor/en contra ponderados por la
   fuerza del oponente, la localía, la importancia del partido, las bajas.
5. **Incertidumbre y regularización.** Equipos con pocos datos deben "encogerse"
   hacia un prior (Elo, mercado) para no inflarse (caso Curaçao).
6. **Parsimonia + sin fuga de información (leakage).** Pocos parámetros bien
   estimados; nunca entrenar con datos del futuro.
7. **Validación walk-forward.** Reentrenar avanzando en el tiempo y medir fuera de
   muestra; comparar contra líneas base y contra el mercado.

---

## 2. Estudio de modelos de referencia (qué hacen y qué tomamos)

| Modelo | Idea central | Fortalezas | Límites | Qué tomamos |
|---|---|---|---|---|
| **Elo / pi-ratings** | Rating dinámico que sube/baja por resultado, margen y rival | Simple, robusto, **mejor que el ranking FIFA**; gran prior | No da goles esperados ni marcadores | ✅ Elo como **prior fuerte** |
| **Maher (1982) / Poisson** | Goles ~ Poisson(ataque×defensa) | Da marcadores y 1X2 | Subestima empates; goles independientes | Base del modelo |
| **Dixon-Coles (1997)** | Poisson bivariado + corrección de marcadores bajos + **decaimiento temporal** | Corrige empates; dinámico | Sin covariables; un solo deporte | ✅ **es nuestro núcleo** |
| **FiveThirtyEight SPI** | Ataque/defensa → goles esperados → 2 Poisson; ajustes (importancia, descanso, viaje) | Industrial, muchos ajustes, 500k+ partidos | Cerrado; necesita mucha data/feature-eng | ✅ ataque/defensa + ajustes |
| **Bayesiano jerárquico (Egidi, Pauli, Torelli 2018)** | Tasas de gol = combinación convexa de histórico **+ cuotas**; *partial pooling* | Iguala al mercado; cuantifica incertidumbre | Más complejo (MCMC) | 🎯 objetivo: **prior de mercado** + shrinkage |
| **ML (XGBoost / NN)** | Features (Elo, forma, xG, mercado) → clasificador | ~67% accuracy con buenas features | Caja negra; necesita muchas features; riesgo de leakage | Posible capa de *blending* |
| **Cuotas de casas (mercado)** | Probabilidad implícita del mercado | **La fuente más precisa que existe** | Llevan margen; no son "nuestras" | 🎯 **ensamblar** con el modelo |

**Conclusión del estudio:** los mejores sistemas (a) parten de un modelo
Poisson/Dixon-Coles con ataque-defensa, (b) lo **anclan** con un rating tipo Elo,
(c) añaden **covariables** (forma vía xG, valor de mercado, descanso, localía) y
(d) **se mezclan con las cuotas del mercado**, evaluando con **RPS** en
*walk-forward*. Eso es exactamente la hoja de ruta de §4–§5.

### 2.1 Caso de estudio — el supercomputador de Opta (Mundial 2026)

Opta publica predicciones del Mundial 2026 (favorita: España **16,1%**, Francia
13%, Inglaterra 11,2%, Argentina 10,4%, Portugal 7%, Brasil 6,6%, Alemania 5,1%,
Países Bajos 3,6%). Su metodología, reconstruida de sus artículos, es muy cercana
a la nuestra **y confirma la dirección de mejora**:

| Pieza de Opta | Qué hace | ¿Lo tenemos? |
|---|---|---|
| Estima cada partido (1X2) combinando **cuotas del mercado + Opta Power Rankings** | El mercado es la señal más precisa; la mezcla es el núcleo | ❌ **falta el mercado** (nuestra brecha #1) |
| **Power Rankings**: Elo jerárquico 0–100 ajustado por dif. de goles y **calidad de la competición**, actualizado a diario, sobre **~13.500 clubes** | La fuerza de una selección hereda el **nivel de club** de sus jugadores | ⚠️ parcial: tenemos Elo de selecciones, **no nivel de club** |
| Fuerzas de **ataque/defensa** calibradas con miles de partidos históricos | Igual que nuestro Dixon-Coles | ✅ sí (~49.000 partidos) |
| **10.000 simulaciones** Monte Carlo del torneo | Probabilidades de avance/campeón con poca varianza | ✅ (ahora a 10.000; antes 5.000) |

**Lecciones accionables del caso Opta:**
1. **El gran diferencial es la mezcla con las cuotas del mercado** (su input principal).
   Es exactamente nuestra acción #2 y el mayor salto de precisión disponible.
2. **El nivel de club importa**: Opta deriva la fuerza también del rendimiento en
   clubes (Power Rankings sobre 13.500 equipos), no solo de partidos de selección.
   Lo aproximamos con **valor de mercado del plantel** (acción #4) o ingiriendo un
   rating tipo Power Rankings como prior extra.
3. **10.000 simulaciones** como estándar de estabilidad (ya aplicado).
4. **Benchmark de realidad**: sus % publicados sirven de *sanity check* — si nuestra
   simulación se aleja mucho (p. ej. un 33% de campeón para un no-favorito), es señal
   de bug, no de modelo (fue el caso del bracket sembrado, ya corregido).

---

## 3. Análisis de lo que ya tenemos

### Datos disponibles
- ✅ **~49.000 partidos internacionales** reales (martj42), con marcador, fecha,
  sede neutral y tipo de torneo (importancia). Accesible y versionado.
- ✅ **Elo** calculado de ese histórico (ajustado por rival y diferencia de goles).
- ✅ Calendario, grupos, **sedes** (16 estadios) y resultados oficiales 2026.
- ✅ **Plantillas/estado de jugadores** (multi-fuente con consenso; Sportmonks).
- ✅ Caché de respuestas de APIs (no se consulta dos veces).
- ❌ **No tenemos (aún):** cuotas de mercado, xG por partido, valor de mercado por
  selección, descanso/viaje, altitud por sede.

### Modelo actual (resumen)
Dixon-Coles vectorizado con: ataque/defensa por equipo, ventaja de localía,
corrección ρ de marcadores bajos, **decaimiento temporal ξ**, **ponderación por
importancia**, **prior Elo** (regularización) y **ajuste por disponibilidad** de
plantilla. Simulación Monte Carlo con sorteo aleatorio.

### Brechas de precisión (diagnóstico)
1. **Falta la señal del mercado** (la más predictiva) → techo de precisión.
2. **Falta xG** → usamos goles (más ruido que la calidad de ocasiones).
3. **Falta valor de mercado** → poca info de la calidad *actual* del plantel.
4. **Sin calibración explícita** ni **RPS** como métrica guía.
5. **Hiperparámetros (ξ, peso del prior) fijados a mano**, no optimizados por RPS.
6. **Bracket aleatorio** (no respeta el cruce real del formato 2026).

---

## 4. Estrategia de precisión (priorizada por impacto/esfuerzo)

| # | Acción | Impacto | Esfuerzo | Depende de |
|---|---|---|---|---|
| 1 | **Métrica RPS + backtest walk-forward** (base de medición) | Alto (habilita todo) | Bajo | — (ya accesible) |
| 2 | **Ensamblar con cuotas de mercado** (combinación convexa) | **Muy alto** | Medio | API de cuotas |
| 3 | **Calibración** (temperature scaling / isotónica) | Medio-alto | Bajo | RPS/validación |
| 4 | **Covariable de valor de mercado** como prior por equipo | Medio-alto | Medio | Sportmonks/Transfermarkt |
| 5 | **Forma reciente vía xG** (sustituir/combinar goles por xG) | Alto | Medio-alto | API xG |
| 6 | **Optimizar ξ y peso del prior** minimizando RPS (grid/optuna) | Medio | Bajo | RPS walk-forward |
| 7 | **Contexto**: localía real de anfitriones, altitud (CDMX), descanso | Bajo-medio | Bajo | sedes/calendario |
| 8 | **Bracket oficial 2026** (cruces reales, mejores terceros) | Bajo (realismo) | Medio | — |

**Orden recomendado:** 1 → 3 → 6 (mejoras "gratis" con lo que ya tenemos) y, en
cuanto haya APIs de pago, 2 → 4 → 5 (el gran salto de precisión).

### 4.1 Resultado empírico — optimización de ξ por RPS (acción #6, hecho)

Tras añadir el RPS (acción #1) se hizo un **barrido walk-forward** (entreno con el
histórico anterior a 2024-01-01, evaluación sobre los 304 partidos posteriores).
Esto convierte la elección de hiperparámetros en una decisión **medida**, no a mano:

| ξ (decaimiento) | peso prior | RPS | ¿bate la base? |
|---|---|---|---|
| **0.0015** | 1.5 / 2.5 / 4.0 | **0.2128–0.2131** | ✅ sí |
| 0.0025 | 1.5 / 2.5 / 4.0 | 0.2187–0.2188 | ✅ sí (menos) |
| 0.004 | 1.5 / 2.5 / 4.0 | 0.2266–0.2272 | ❌ **no** |
| — base (tasas 1X2) | — | 0.2253 | — |

**Hallazgo:** el `ξ = 0.004` que teníamos en producción (vida media ~6 meses)
**empeoraba** la precisión fuera de muestra: descartaba demasiado histórico y el
modelo no llegaba a batir a la línea base. Con `ξ = 0.0015` (vida media ~15 meses)
el modelo **bate la base de forma consistente** para cualquier peso del prior. El
peso del prior apenas mueve el RPS (la regularización Elo ya está bien calibrada),
así que mantenemos `2.5` por su mejor *accuracy* y mayor protección de equipos con
pocos datos. **Decisión aplicada:** `model_decay_xi` 0.004 → **0.0015** por defecto.

Esto valida el principio §1.7 (validación walk-forward) y la acción #6: los
hiperparámetros se fijan **minimizando el RPS**, no por intuición.

---

## 5. Formulación matemática

### 5.1 Modelo base (lo que ya hacemos)
Para un partido (local h, visitante a), goles esperados:

```
λ_h = exp( αₕ − β_a + γ·(1−neutral) + Δatkₕ )      (goles del local)
μ_a = exp( α_a − βₕ + Δatk_a )                      (goles del visitante)
```

donde α = fuerza de ataque, β = fuerza de defensa, γ = ventaja de localía, Δ = ajuste
por disponibilidad de plantilla. Los goles siguen Poisson con la **corrección de
Dixon-Coles** τ(x,y;λ,μ,ρ) para marcadores bajos. La matriz de marcadores P(x,y)
da P(local), P(empate), P(visitante).

**Estimación (MAP penalizado):** maximizar la log-verosimilitud ponderada

```
ℓ(θ) = Σ_m  w_m · log P(x_m, y_m ; θ)   −  λ_prior · Σ_i ( (α_i − β_i) − z_i )²
        con   w_m = exp(−ξ · Δdías_m) · importancia_m
```

`z_i` = Elo estandarizado (prior). El término de penalización es un **shrinkage
bayesiano** (partial pooling) hacia el Elo: regulariza a los equipos con pocos
datos. `ξ` controla el decaimiento temporal; `importancia_m ∈ {0.5, 1, 1.5}`.

### 5.2 Extensión 1 — Covariables en las tasas de gol
Generalizamos el log de las tasas con un término lineal de covariables `x`:

```
log λ_h = αₕ − β_a + γ + θᵀ·x_{h,a}
```

con covariables candidatas: **diferencia de valor de mercado**, **forma xG**
(media móvil de xG a favor/en contra), **descanso** (días desde el último
partido), **altitud/anfitrión**. Los `θ` se estiman junto al resto por MLE/MAP.
Esto es lo que hace 538 con sus "ajustes".

### 5.3 Extensión 2 — Prior/ensamble con el mercado (el gran salto)
Las cuotas de cierre son la mejor fuente. Dos formas (Egidi et al. 2018):

- **Combinación convexa de tasas** (prior de mercado en el modelo):
  `log λ = (1−κ)·(modelo) + κ·(implícito por cuotas)`.
- **Ensamble de probabilidades** (más simple y robusto):
  ```
  P_final = ω · P_modelo + (1 − ω) · P_mercado
  ```
  con `ω ∈ [0,1]` elegido para **minimizar el RPS** en validación (típicamente el
  mercado pesa más). Alternativa: *log opinion pool* (media geométrica normalizada).

### 5.4 Calibración
Tras estimar, ajustar las probabilidades a la frecuencia real con **temperature
scaling** (un parámetro T que aplana/agudiza) o **isotónica**, optimizando RPS/
log-loss en validación. Mejora la fiabilidad sin reentrenar el modelo.

### 5.5 Evaluación (la brújula)
- **RPS** (primaria, ordinal):
  ```
  RPS = 1/(r−1) · Σ_{i=1}^{r−1} ( Σ_{j=1}^{i} (p_j − e_j) )²        (r = 3 resultados)
  ```
  Penaliza más equivocarse "lejos" (predecir local cuando gana visitante) que
  "cerca" (empate). 0 = perfecto.
- **log-loss** y **Brier** (secundarias), **curvas de fiabilidad** (calibración).
- **Walk-forward:** entrenar hasta la fecha *t*, predecir la jornada *t+1*, avanzar;
  comparar contra (a) tasas base, (b) Elo puro, (c) el mercado.
- **Optimización de hiperparámetros:** elegir `ξ`, `λ_prior`, `κ/ω`, `T` por
  **grid search/optuna minimizando el RPS walk-forward** (no a mano).

---

## 6. Cómo se traduce en "más preciso sin perder veracidad"
- **Veracidad:** todo sale de datos reales (resultados, Elo, mercado, xG) y se
  **valida fuera de muestra** con RPS; nada inventado.
- **Más preciso con el tiempo:** el decaimiento temporal + reentreno incorporan
  cada resultado nuevo; los hiperparámetros se re-optimizan periódicamente por RPS;
  y el ensamble con el mercado fija un "suelo" de calidad difícil de batir.

---

## 7. Pasos ya implementados
- **Acción #1 — RPS + backtest.** El backtest reporta **RPS, log-loss, Brier y
  accuracy** del modelo vs la línea base (`prediction/metrics.py`, `backtest.py`).
  Es la brújula de todo lo demás.
- **Acción #6 — ξ optimizado por RPS.** Barrido walk-forward → `ξ=0.0015` (bate la
  base), hardcodeado en `config.py` (ver §4.1).
- **Acción #2 — mecánica de ensamble lista.** `prediction/ensemble.py`:
  `blend()` (combinación convexa `ω·modelo + (1−ω)·externa`) y `best_blend_weight()`
  (elige `ω` minimizando RPS). Es la pieza central del enfoque Opta; **falta
  conectar la fuente externa** (API de cuotas / Power Rankings).
- **Estabilidad.** Simulación a **10.000** iteraciones (como Opta) y bracket
  aleatorio (favoritos realistas).

**Próximo gran salto:** conectar las **cuotas de cierre del mercado** (acción #2)
y un proxy de **nivel de club / valor de mercado** (acción #4); con ambos
enchufados al ensamble ya construido, la precisión debería acercarse a la de Opta.

## Fuentes
- FiveThirtyEight — *How Our Club / World Cup Soccer Predictions Work*.
- Dixon & Coles (1997); Maher (1982).
- Constantinou & Fenton — *Solving the Problem of Inadequate Scoring Rules* (RPS).
- Egidi, Pauli & Torelli (2018) — *Combining historical data and bookmakers' odds*.
- opisthokonta.net; dashee87.github.io (Dixon-Coles + time-weighting).
