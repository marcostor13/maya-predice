---
name: add-data-provider
description: Añade un nuevo proveedor de datos oficiales (p.ej. API-Football, FIFA, otra fuente) al backend de maya-predice implementando la interfaz DataProvider, sin tocar el servicio de sincronización. Usa esta skill al integrar una fuente de datos del torneo.
---

# Añadir un proveedor de datos

La ingesta usa una abstracción: cualquier fuente implementa `DataProvider` y
devuelve `ProviderMatch` normalizados. El servicio de sync y la detección de
cambios no cambian.

## 1. Implementa el proveedor
Crea `backend/app/data/providers/<fuente>.py`:

```python
from app.data.providers.base import DataProvider, ProviderMatch

class MiProvider(DataProvider):
    name = "mi-fuente"
    async def fetch_matches(self) -> list[ProviderMatch]:
        ...  # llamada HTTP + mapeo a ProviderMatch
```

Separa el **parseo puro** (función que recibe el payload y devuelve
`list[ProviderMatch]`) del fetch HTTP, igual que `openfootball.parse_matches`,
para poder testearlo sin red.

## 2. Reglas de mapeo (críticas)
- **`external_ref`** debe ser **estable entre sincronizaciones** (clave de
  upsert). Sigue el patrón existente: grupos por equipos, eliminatorias por
  ranura (fase+fecha+hora+sede). NO uses IDs que cambien.
- Resuelve selecciones reales con `app/data/team_mapping.resolve_team`; añade
  ALIASES si la fuente usa otra grafía. Si el equipo no está definido, deja
  `home_code`/`away_code` en None y guarda el placeholder.
- `kickoff` siempre en **UTC**. Normaliza el grupo a la letra (`"A"`).

## 3. Conéctalo
- Cámbialo en `sync_service.default_provider()` o hazlo configurable por env.
- Si requiere API key, añádela a `core/config.py` y `.env.example` (nunca al repo).

## 4. Tests
Añade `backend/tests/test_<fuente>_parser.py` con un payload de muestra inline:
verifica nº de partidos, resolución de equipos, placeholders, kickoff UTC,
parseo de resultados y unicidad/estabilidad de `external_ref`.

## Checklist
- [ ] `parse_*` puro y testeado (sin red).
- [ ] `external_ref` estable y único.
- [ ] Equipos vía team_mapping; kickoff en UTC; grupo normalizado.
- [ ] API keys en env, no en el repo.
- [ ] `pytest` en verde.
