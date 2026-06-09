---
name: work-on-prediction-model
description: Guía para modificar o extender el modelo de predicción de fútbol (Dixon-Coles / Poisson / simulador Monte Carlo) de maya-predice de forma segura y verificable. Usa esta skill al tocar backend/app/services/prediction/.
---

# Trabajar en el modelo de predicción

El núcleo estadístico vive en `backend/app/services/prediction/`:
- `poisson.py` — matriz de marcadores y probabilidades 1X2 (+ corrección τ).
- `dixon_coles.py` — estimación MLE de ataque/defensa, localía y ρ.
- `simulator.py` — simulación Monte Carlo del torneo.

## Principios invariables (no romper)
1. La matriz de marcadores **suma 1** tras la corrección/truncamiento.
2. Las probabilidades de un partido (home+draw+away) **suman 1**.
3. Goles esperados (λ, μ) **≥ 0** (se obtienen de `exp(...)`).
4. Mayor fuerza de ataque ⇒ mayor probabilidad de victoria (monotonicidad).
5. El modelo es **versionado** (`model_version`); cada corrida se persiste.

## Cómo proceder
1. Lee `ARCHITECTURE.md` §"El modelo de predicción".
2. Si cambias la matemática (p.ej. añadir features, cambiar la verosimilitud),
   explica el fundamento estadístico y, si es un cambio de enfoque, añade un ADR.
3. Mantén la API pública de las clases (`DixonColesModel.fit/predict`,
   `match_probabilities`) o actualiza a la vez `prediction_service.py`.
4. Para calibración/backtesting usa log-loss y Brier score sobre partidos ya
   jugados; reporta los números.

## Verificación obligatoria
- Añade/actualiza tests en `backend/tests/test_poisson.py` y
  `test_dixon_coles.py` cubriendo los invariantes de arriba.
- Ejecuta `pytest` y deja todo en verde antes de terminar.

## Checklist
- [ ] Invariantes 1–5 respetados y testeados.
- [ ] API pública estable o callers actualizados.
- [ ] Cambio de enfoque ⇒ ADR en ARCHITECTURE.md.
- [ ] `pytest` en verde.
