"""Configuración **pública** del sitio (no requiere autenticación).

Expone solo lo que el frontend necesita para pintar elementos de monetización
(el CTA de afiliado). Nunca devuelve secretos ni ajustes internos. Los valores
salen del `settings` en memoria (con los overrides del panel ya aplicados).
"""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def public_config() -> dict:
    """Datos públicos para el frontend (afiliado)."""
    return {
        "affiliate": {
            "enabled": settings.affiliate_enabled,
            "url": settings.affiliate_url if settings.affiliate_enabled else "",
            "label": settings.affiliate_label,
        }
    }
