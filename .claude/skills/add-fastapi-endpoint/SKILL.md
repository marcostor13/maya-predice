---
name: add-fastapi-endpoint
description: Añade un endpoint REST al backend FastAPI de maya-predice siguiendo la arquitectura en capas (router → service → model) con su schema Pydantic y test. Usa esta skill cuando se pida crear o exponer un nuevo endpoint en el backend.
---

# Añadir un endpoint FastAPI

Sigue estos pasos para mantener la arquitectura en capas de maya-predice.

## 1. Schema (contrato)
En `backend/app/schemas/`, define o reutiliza los modelos Pydantic de
request/response. Usa `ConfigDict(from_attributes=True)` para los de respuesta
que mapean ORM.

## 2. Lógica de negocio
Si el endpoint hace algo más que un CRUD trivial, escribe la lógica en
`backend/app/services/` (función async que recibe `AsyncSession`). El router
NO debe contener lógica.

## 3. Router
Crea el endpoint en el módulo adecuado de `backend/app/api/endpoints/`
(o uno nuevo). Patrón:

```python
@router.get("/ruta", response_model=MiSchema)
async def handler(param: int, db: AsyncSession = Depends(get_db)):
    return await mi_servicio(db, param)
```

Registra routers nuevos en `backend/app/api/router.py`.

## 4. Errores
Usa `HTTPException` con códigos correctos (404 no encontrado, 400 input inválido,
409 conflicto de estado). Mensajes en español.

## 5. Test
Añade un test en `backend/tests/`. Si necesita DB, usa una sesión de prueba.
Ejecuta `pytest` y `ruff check`.

## Checklist
- [ ] Schema definido (sin exponer ORM directo).
- [ ] Lógica en services/, router delgado.
- [ ] Router registrado en api/router.py.
- [ ] Errores con HTTPException y códigos correctos.
- [ ] Test añadido y `pytest` en verde.
- [ ] Documenta el endpoint en ARCHITECTURE.md §"API" si es público.
