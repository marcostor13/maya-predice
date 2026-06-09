---
name: add-player-source
description: Añade una nueva fuente de datos de plantillas (jugadores, suplentes, entrenadores) al backend de maya-predice implementando PlayerDataProvider, para que entre en el consenso multi-fuente. Usa esta skill al integrar una API de jugadores (API-Football, TheSportsDB, Wikidata u otra).
---

# Añadir una fuente de plantillas (multi-fuente / consenso)

Las plantillas se construyen por **consenso de varias fuentes**. Una fuente nueva
solo debe entregar observaciones normalizadas; el consenso y la persistencia no
cambian.

## 1. Implementa el proveedor
Crea `backend/app/data/players/<fuente>.py`:

```python
from app.data.players.base import (
    PlayerDataProvider, SquadObservation, PlayerObservation,
    CoachObservation, normalize_position, normalize_status,
)

class MiProvider(PlayerDataProvider):
    name = "mi-fuente"
    async def fetch_all(self) -> list[SquadObservation]:
        ...  # una SquadObservation por equipo (con players y coach)
```

- **Normaliza siempre** posición/estado/rol con los helpers de `base.py` (para que
  el consenso pueda comparar valores entre fuentes).
- El **nombre del jugador** va tal cual en `full_name`; la identidad entre fuentes
  se calcula con `normalize_name` (no inventes IDs).
- Degrada con gracia: si una llamada falla, captura y devuelve lo que tengas (una
  fuente caída no debe abortar el resto).

## 2. Regístrala
- Añádela al factory `build_player_providers()` en `services/squad_service.py`.
- Config en `core/config.py` + `.env.example` (key/host). Actívala en
  `PLAYER_SOURCES`. **API keys nunca en el repo.**
- Si la fuente es fiable, súbele la prioridad en `consensus.DEFAULT_PRIORITY`
  (la primera gana los empates); Wikidata va al final por ser ruidosa.

## 3. Red (producción)
El host externo debe estar en la **allowlist** del entorno (Coolify). En el
sandbox de desarrollo solo GitHub raw está permitido → usa el proveedor `fixture`.

## 4. Tests
Añade `backend/tests/test_<fuente>_parser.py` con un payload de muestra inline:
verifica el mapeo de posición/estado y la construcción de `PlayerObservation`.
No dependas de la red en los tests (parsea un dict/fixture).

## Checklist
- [ ] `fetch_all` devuelve SquadObservation normalizadas (posición/estado/rol).
- [ ] Identidad por nombre (sin IDs inventados); degrada con gracia.
- [ ] Registrada en el factory + config + `.env.example`; key fuera del repo.
- [ ] Prioridad de consenso ajustada si procede.
- [ ] Test de parseo sin red; `pytest` en verde.
