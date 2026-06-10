"""Sincronización de plantillas multi-fuente con consenso y trazabilidad.

Flujo:
1. Cada proveedor activo (API-Football, TheSportsDB, Wikidata, fixture…) entrega
   sus `SquadObservation`.
2. Por equipo, se agrupan las observaciones de cada jugador (clave: nombre
   normalizado) y del entrenador.
3. `build_player_consensus` / `build_coach_consensus` deciden el valor final por
   voto mayoritario y calculan la confianza.
4. Se hace upsert de `Player`/`Coach` con `confidence`, `sources_count` y
   `source_data` (qué dijo cada fuente). Cada conflicto se guarda en
   `squad_discrepancies`.
5. Se registra un `SyncRun` (source="squads") para auditoría.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.players.base import (
    CoachObservation,
    PlayerDataProvider,
    PlayerObservation,
    SquadObservation,
)
from app.models.squad import Coach, Player, SquadDiscrepancy
from app.models.sync import SyncRun, SyncStatus
from app.models.team import Team
from app.services.squad.consensus import build_coach_consensus, build_player_consensus

logger = logging.getLogger("maya.squads")


def build_player_providers() -> list[PlayerDataProvider]:
    """Instancia los proveedores activos según la configuración."""
    providers: list[PlayerDataProvider] = []
    for name in settings.player_sources_list:
        if name == "apifootball" and settings.apifootball_key:
            from app.data.players.apifootball import APIFootballProvider

            providers.append(APIFootballProvider(settings.apifootball_key, settings.apifootball_host))
        elif name == "sportmonks" and settings.spapi_token:
            from app.data.players.sportmonks import SportmonksProvider

            providers.append(
                SportmonksProvider(
                    settings.spapi_token,
                    settings.sportmonks_base,
                    settings.sportmonks_cache_ttl_hours,
                )
            )
        elif name == "thesportsdb":
            from app.data.players.thesportsdb import TheSportsDBProvider

            providers.append(TheSportsDBProvider(settings.thesportsdb_key))
        elif name == "wikidata":
            from app.data.players.wikidata import WikidataProvider

            providers.append(WikidataProvider())
        elif name == "fixture":
            from app.data.players.localfixture import LocalFixtureProvider

            providers.append(LocalFixtureProvider(settings.squads_fixture_path))
        elif name == "remote" and settings.squads_remote_url:
            from app.data.players.localfixture import RemoteSquadProvider

            providers.append(RemoteSquadProvider(settings.squads_remote_url))
    return providers


def _group_by_team(observations: list[SquadObservation]) -> dict[str, list[SquadObservation]]:
    grouped: dict[str, list[SquadObservation]] = defaultdict(list)
    for obs in observations:
        grouped[obs.team_code].append(obs)
    return grouped


def _group_players(squads: list[SquadObservation]) -> dict[str, list[PlayerObservation]]:
    """Agrupa observaciones de jugadores de varias fuentes por nombre normalizado."""
    grouped: dict[str, list[PlayerObservation]] = defaultdict(list)
    for sq in squads:
        for p in sq.players:
            grouped[p.name_key].append(p)
    return grouped


async def sync_squads(
    db: AsyncSession, providers: list[PlayerDataProvider], trigger: str = "scheduled"
) -> SyncRun:
    """Ejecuta la sincronización de plantillas con consenso multi-fuente."""
    source_label = "+".join(p.name for p in providers) or "squads"
    run = SyncRun(source=f"squads:{source_label}", trigger=trigger, status=SyncStatus.RUNNING)
    db.add(run)
    await db.flush()

    try:
        # 1. Recolectar observaciones de todas las fuentes.
        all_obs: list[SquadObservation] = []
        for provider in providers:
            try:
                all_obs.extend(await provider.fetch_all())
            except Exception as exc:  # noqa: BLE001 — una fuente caída no aborta el resto
                logger.warning("Fuente %s falló: %s", provider.name, exc)

        by_team = _group_by_team(all_obs)
        teams = {t.code: t for t in (await db.execute(select(Team))).scalars().all()}

        players_upserted = coaches_upserted = discrepancies = 0

        for code, squads in by_team.items():
            team = teams.get(code)
            if team is None:
                continue

            # Reemplaza la plantilla previa de este equipo (idempotente por corrida).
            await db.execute(delete(Player).where(Player.team_id == team.id))

            # --- Jugadores ---
            for obs in _group_players(squads).values():
                consensus = build_player_consensus(obs)
                source_data = {
                    f: cv.by_source for f, cv in consensus.fields.items() if cv.by_source
                }
                db.add(
                    Player(
                        team_id=team.id,
                        full_name=consensus.full_name,
                        normalized_name=consensus.name_key,
                        position=consensus.value("position"),
                        shirt_number=consensus.value("shirt_number"),
                        club=consensus.value("club"),
                        birth_date=consensus.value("birth_date"),
                        role=consensus.value("role"),
                        status=consensus.value("status"),
                        confidence=consensus.confidence,
                        sources_count=consensus.sources_count,
                        source_data=source_data,
                    )
                )
                players_upserted += 1
                for cv in consensus.conflicts:
                    db.add(
                        SquadDiscrepancy(
                            sync_run_id=run.id,
                            team_code=code,
                            entity_type="player",
                            entity_name=consensus.full_name,
                            field=cv.field,
                            chosen_value=None if cv.value is None else str(cv.value),
                            agreement=cv.agreement,
                            by_source=cv.by_source,
                        )
                    )
                    discrepancies += 1

            # --- Entrenador ---
            coach_obs: list[CoachObservation] = [sq.coach for sq in squads if sq.coach]
            if coach_obs:
                cc = build_coach_consensus(coach_obs)
                existing = (
                    await db.execute(select(Coach).where(Coach.team_id == team.id))
                ).scalar_one_or_none()
                if existing is None:
                    existing = Coach(team_id=team.id, name=cc.value("name"))
                    db.add(existing)
                existing.name = cc.value("name")
                existing.nationality = cc.value("nationality")
                existing.status = cc.value("status")
                existing.confidence = cc.confidence
                existing.sources_count = cc.sources_count
                existing.source_data = {
                    f: v.by_source for f, v in cc.fields.items() if v.by_source
                }
                coaches_upserted += 1
                for cv in cc.conflicts:
                    db.add(
                        SquadDiscrepancy(
                            sync_run_id=run.id,
                            team_code=code,
                            entity_type="coach",
                            entity_name=cc.name,
                            field=cv.field,
                            chosen_value=None if cv.value is None else str(cv.value),
                            agreement=cv.agreement,
                            by_source=cv.by_source,
                        )
                    )
                    discrepancies += 1

        run.matches_seen = players_upserted
        run.created = players_upserted
        run.updated = coaches_upserted
        run.changes_count = discrepancies
        run.status = SyncStatus.SUCCESS
        run.message = (
            f"{players_upserted} jugadores, {coaches_upserted} entrenadores, "
            f"{discrepancies} discrepancias entre {len(providers)} fuentes."
        )
    except Exception as exc:  # noqa: BLE001
        run.status = SyncStatus.FAILED
        run.message = f"Error: {exc}"
        raise
    finally:
        run.finished_at = datetime.now(UTC)

    return run
