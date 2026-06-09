"""Ajuste de la fuerza de un equipo según la disponibilidad de sus jugadores.

Convierte el estado de la plantilla (titulares/suplentes, lesionados,
sancionados, dudas…) en deltas de ataque y defensa que modifican la fuerza
efectiva del equipo en el modelo Dixon-Coles.

Idea: cada jugador aporta un peso a ataque y a defensa según su posición y su rol
(titular pesa más que suplente). Si no está disponible, ese peso se pierde. La
**disponibilidad** de ataque/defensa es la fracción del peso total que sigue
disponible; con plantilla completa vale 1.0 y el delta es 0 (el modelo nunca se
vuelve más fuerte que su línea base, solo se penaliza por bajas).

Módulo puro y determinista: testeable sin DB ni red.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.squad import PlayerStatus, Position, SquadRole
from app.services.prediction.dixon_coles import TeamAdjustment


@dataclass(frozen=True)
class PlayerImpact:
    position: Position
    role: SquadRole
    status: PlayerStatus


@dataclass
class AvailabilityConfig:
    # Cuánto pesa un jugador según su rol en la plantilla.
    role_weight: dict[SquadRole, float] = field(
        default_factory=lambda: {
            SquadRole.STARTER: 1.0,
            SquadRole.SUBSTITUTE: 0.35,
            SquadRole.RESERVE: 0.1,
            SquadRole.UNKNOWN: 0.5,
        }
    )
    # Fracción de aporte disponible según el estado del jugador.
    status_availability: dict[PlayerStatus, float] = field(
        default_factory=lambda: {
            PlayerStatus.AVAILABLE: 1.0,
            PlayerStatus.DOUBTFUL: 0.5,
            PlayerStatus.INJURED: 0.0,
            PlayerStatus.SUSPENDED: 0.0,
            PlayerStatus.OUT: 0.0,
            PlayerStatus.UNKNOWN: 1.0,  # sin información => se asume disponible
        }
    )
    # Cuánto contribuye cada posición a ataque y a defensa.
    position_attack: dict[Position, float] = field(
        default_factory=lambda: {
            Position.GK: 0.0,
            Position.DEF: 0.2,
            Position.MID: 0.5,
            Position.FWD: 0.9,
            Position.UNKNOWN: 0.4,
        }
    )
    position_defense: dict[Position, float] = field(
        default_factory=lambda: {
            Position.GK: 1.0,
            Position.DEF: 0.9,
            Position.MID: 0.5,
            Position.FWD: 0.1,
            Position.UNKNOWN: 0.4,
        }
    )
    # Escala del ajuste en log-espacio: con disponibilidad 0 el delta = -adj_strength.
    adj_strength: float = 0.5


@dataclass
class TeamAvailability:
    attack_availability: float  # 0..1
    defense_availability: float  # 0..1
    missing: list[str]          # nombres/etiquetas de bajas relevantes (informativo)

    def to_adjustment(self, adj_strength: float) -> TeamAdjustment:
        return TeamAdjustment(
            attack_delta=adj_strength * (self.attack_availability - 1.0),
            defense_delta=adj_strength * (self.defense_availability - 1.0),
        )


def compute_team_availability(
    players: list[PlayerImpact], config: AvailabilityConfig | None = None
) -> TeamAvailability:
    """Calcula la disponibilidad de ataque/defensa de un equipo (1.0 = completa)."""
    cfg = config or AvailabilityConfig()

    total_atk = avail_atk = 0.0
    total_def = avail_def = 0.0
    for p in players:
        role_w = cfg.role_weight.get(p.role, 0.5)
        avail = cfg.status_availability.get(p.status, 1.0)
        w_atk = role_w * cfg.position_attack.get(p.position, 0.4)
        w_def = role_w * cfg.position_defense.get(p.position, 0.4)
        total_atk += w_atk
        total_def += w_def
        avail_atk += w_atk * avail
        avail_def += w_def * avail

    attack_availability = avail_atk / total_atk if total_atk > 0 else 1.0
    defense_availability = avail_def / total_def if total_def > 0 else 1.0
    return TeamAvailability(
        attack_availability=round(attack_availability, 4),
        defense_availability=round(defense_availability, 4),
        missing=[],
    )


def compute_team_adjustment(
    players: list[PlayerImpact], config: AvailabilityConfig | None = None
) -> tuple[TeamAdjustment, TeamAvailability]:
    cfg = config or AvailabilityConfig()
    availability = compute_team_availability(players, cfg)
    return availability.to_adjustment(cfg.adj_strength), availability
