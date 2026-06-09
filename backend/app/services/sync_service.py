"""Sincronización con la fuente oficial y detección de cambios.

Flujo:
1. El proveedor (openfootball/FIFA) entrega los partidos normalizados.
2. Se hace upsert idempotente por `external_ref`.
3. Se comparan campo a campo con lo almacenado y cada diferencia se registra en
   `data_changes` (resultado, horario, sede, resolución de un cruce, etc.).
4. Se crea un `SyncRun` con el resumen para auditoría.

`compute_changes` es una función pura (sin DB) y por eso es directamente testeable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.providers.base import DataProvider, ProviderMatch
from app.models.match import Match, MatchStatus
from app.models.sync import DataChange, SyncRun, SyncStatus
from app.models.team import Team
from app.models.tournament import Tournament

# Campos que se vigilan en cada partido.
TRACKED_FIELDS = (
    "kickoff",
    "venue",
    "matchday",
    "group",
    "stage",
    "home_code",
    "away_code",
    "home_placeholder",
    "away_placeholder",
    "home_goals",
    "away_goals",
    "status",
)


def _provider_match_to_dict(pm: ProviderMatch) -> dict:
    return {
        "kickoff": pm.kickoff.astimezone(timezone.utc).isoformat() if pm.kickoff else None,
        "venue": pm.venue,
        "matchday": pm.matchday,
        "group": pm.group,
        "stage": pm.stage.value,
        "home_code": pm.home_code,
        "away_code": pm.away_code,
        "home_placeholder": pm.home_placeholder,
        "away_placeholder": pm.away_placeholder,
        "home_goals": pm.home_goals,
        "away_goals": pm.away_goals,
        "status": MatchStatus.FINISHED.value if pm.is_finished else MatchStatus.SCHEDULED.value,
    }


def compute_changes(old: dict | None, new: dict) -> list[tuple[str, str | None, str | None]]:
    """Devuelve [(campo, valor_anterior, valor_nuevo)] entre dos estados.

    Si `old` es None, es un alta y no se reportan campos individuales.
    """
    if old is None:
        return []
    changes: list[tuple[str, str | None, str | None]] = []
    for field in TRACKED_FIELDS:
        ov, nv = old.get(field), new.get(field)
        if ov != nv:
            changes.append((field, None if ov is None else str(ov), None if nv is None else str(nv)))
    return changes


async def _get_or_create_tournament(db: AsyncSession) -> Tournament:
    t = (await db.execute(select(Tournament).where(Tournament.year == 2026))).scalar_one_or_none()
    if t is None:
        t = Tournament(name="Copa Mundial de la FIFA 2026", year=2026, num_teams=48)
        db.add(t)
        await db.flush()
    return t


async def _ensure_teams(db: AsyncSession, matches: list[ProviderMatch]) -> dict[str, Team]:
    """Crea/actualiza las selecciones reales presentes en los partidos. Devuelve code->Team."""
    by_code = {t.code: t for t in (await db.execute(select(Team))).scalars().all()}
    for pm in matches:
        for name, code, conf, grp in (
            (pm.home_name, pm.home_code, pm.home_confederation, pm.group),
            (pm.away_name, pm.away_code, pm.away_confederation, pm.group),
        ):
            if not code:
                continue
            team = by_code.get(code)
            if team is None:
                team = Team(name=name, code=code, confederation=conf, group=grp)
                db.add(team)
                by_code[code] = team
            elif grp and team.group != grp:
                team.group = grp
    await db.flush()
    return by_code


def _existing_match_to_dict(m: Match, id_to_code: dict[int, str]) -> dict:
    return {
        "kickoff": m.kickoff.astimezone(timezone.utc).isoformat() if m.kickoff else None,
        "venue": m.venue,
        "matchday": m.matchday,
        "group": m.group,
        "stage": m.stage.value,
        "home_code": id_to_code.get(m.home_team_id) if m.home_team_id else None,
        "away_code": id_to_code.get(m.away_team_id) if m.away_team_id else None,
        "home_placeholder": m.home_placeholder,
        "away_placeholder": m.away_placeholder,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "status": m.status.value,
    }


def _apply(m: Match, pm: ProviderMatch, code_to_team: dict[str, Team]) -> None:
    m.stage = pm.stage
    m.matchday = pm.matchday
    m.group = pm.group
    m.venue = pm.venue
    m.kickoff = pm.kickoff
    m.home_placeholder = pm.home_placeholder
    m.away_placeholder = pm.away_placeholder
    m.home_team_id = code_to_team[pm.home_code].id if pm.home_code else None
    m.away_team_id = code_to_team[pm.away_code].id if pm.away_code else None
    m.home_goals = pm.home_goals
    m.away_goals = pm.away_goals
    m.status = MatchStatus.FINISHED if pm.is_finished else MatchStatus.SCHEDULED


async def sync_official_data(
    db: AsyncSession, provider: DataProvider, trigger: str = "scheduled"
) -> SyncRun:
    """Ejecuta una sincronización completa y registra el resultado."""
    run = SyncRun(source=provider.name, trigger=trigger, status=SyncStatus.RUNNING)
    db.add(run)
    await db.flush()

    try:
        provider_matches = await provider.fetch_matches()
        tournament = await _get_or_create_tournament(db)
        code_to_team = await _ensure_teams(db, provider_matches)
        id_to_code = {t.id: t.code for t in code_to_team.values()}

        existing = {
            m.external_ref: m
            for m in (
                await db.execute(select(Match).where(Match.tournament_id == tournament.id))
            ).scalars().all()
        }

        created = updated = changes_count = 0

        for pm in provider_matches:
            new_state = _provider_match_to_dict(pm)
            match = existing.get(pm.external_ref)

            if match is None:
                match = Match(tournament_id=tournament.id, external_ref=pm.external_ref)
                _apply(match, pm, code_to_team)
                db.add(match)
                await db.flush()
                created += 1
                db.add(
                    DataChange(
                        sync_run_id=run.id,
                        match_id=match.id,
                        external_ref=pm.external_ref,
                        change_type="created",
                        field="match",
                        old_value=None,
                        new_value=f"{pm.home_code or pm.home_placeholder} vs "
                        f"{pm.away_code or pm.away_placeholder}",
                    )
                )
                changes_count += 1
            else:
                old_state = _existing_match_to_dict(match, id_to_code)
                diffs = compute_changes(old_state, new_state)
                if diffs:
                    _apply(match, pm, code_to_team)
                    updated += 1
                    for field, ov, nv in diffs:
                        db.add(
                            DataChange(
                                sync_run_id=run.id,
                                match_id=match.id,
                                external_ref=pm.external_ref,
                                change_type="updated",
                                field=field,
                                old_value=ov,
                                new_value=nv,
                            )
                        )
                        changes_count += 1

        run.matches_seen = len(provider_matches)
        run.created = created
        run.updated = updated
        run.changes_count = changes_count
        run.status = SyncStatus.SUCCESS
        run.message = f"{created} altas, {updated} actualizados, {changes_count} cambios."
    except Exception as exc:  # noqa: BLE001
        run.status = SyncStatus.FAILED
        run.message = f"Error: {exc}"
        run.finished_at = datetime.now(timezone.utc)
        raise
    finally:
        run.finished_at = datetime.now(timezone.utc)

    return run


def default_provider() -> DataProvider:
    """Proveedor configurado por defecto (openfootball)."""
    from app.data.providers.openfootball import OpenFootballProvider

    return OpenFootballProvider(settings.data_source_url)
