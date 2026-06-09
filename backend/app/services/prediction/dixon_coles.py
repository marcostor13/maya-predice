"""Modelo Dixon-Coles para predicción de partidos de fútbol.

Estima, por máxima verosimilitud, los parámetros de ataque y defensa de cada
equipo, la ventaja de localía y el parámetro de dependencia rho, a partir de un
histórico de partidos. Aplica decaimiento temporal: los partidos recientes pesan
más en la verosimilitud.

Mejoras respecto al modelo base:
- **Verosimilitud vectorizada** (numpy) → entrena con miles de partidos en
  segundos.
- **Campo neutral**: en sedes neutrales (caso típico de un Mundial) no se aplica
  la ventaja de localía.
- **Ajuste por disponibilidad**: la predicción acepta deltas de ataque/defensa
  por equipo (p.ej. derivados de bajas/lesiones) que modifican la fuerza efectiva.

Referencia: Dixon & Coles (1997).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from scipy.optimize import minimize

from app.services.prediction.poisson import MatchProbabilities, _tau, match_probabilities


@dataclass
class MatchResult:
    """Partido histórico usado para entrenar el modelo."""

    home: str
    away: str
    home_goals: int
    away_goals: int
    played_on: date | None = None
    neutral: bool = False


@dataclass
class TeamAdjustment:
    """Modificadores de fuerza efectiva (en log-espacio) de un equipo."""

    attack_delta: float = 0.0
    defense_delta: float = 0.0


class DixonColesModel:
    """Modelo Dixon-Coles ajustable y serializable."""

    def __init__(self, xi: float = 0.0):
        # xi: tasa de decaimiento temporal (por día). 0 => sin decaimiento.
        self.xi = xi
        self.teams: list[str] = []
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.home_advantage: float = 0.0
        self.rho: float = 0.0
        self._fitted = False

    # ---------- entrenamiento ----------

    def _time_weights(self, dates: list[date | None]) -> np.ndarray:
        if self.xi <= 0.0:
            return np.ones(len(dates))
        valid = [d for d in dates if d]
        if not valid:
            return np.ones(len(dates))
        today = max(valid)
        return np.array([np.exp(-self.xi * (today - d).days) if d else 1.0 for d in dates])

    def fit(
        self,
        matches: list[MatchResult],
        priors: dict[str, float] | None = None,
        prior_weight: float = 0.0,
    ) -> DixonColesModel:
        """Ajusta el modelo. Opcionalmente regulariza la fuerza neta de cada equipo
        (attack-defense) hacia un `prior` (p.ej. derivado de Elo) con peso
        `prior_weight` (MAP). Útil para equipos con pocos partidos."""
        if not matches:
            raise ValueError("Se requieren partidos para entrenar el modelo.")

        self.teams = sorted({t for m in matches for t in (m.home, m.away)})
        n = len(self.teams)
        idx = {t: i for i, t in enumerate(self.teams)}
        prior_vec = (
            np.array([(priors or {}).get(t, 0.0) for t in self.teams])
            if priors and prior_weight > 0
            else None
        )

        hi = np.array([idx[m.home] for m in matches])
        ai = np.array([idx[m.away] for m in matches])
        hg = np.array([m.home_goals for m in matches], dtype=float)
        ag = np.array([m.away_goals for m in matches], dtype=float)
        not_neutral = np.array([0.0 if m.neutral else 1.0 for m in matches])
        weights = self._time_weights([m.played_on for m in matches])

        # máscaras para la corrección de Dixon-Coles (marcadores bajos)
        m00 = (hg == 0) & (ag == 0)
        m01 = (hg == 0) & (ag == 1)
        m10 = (hg == 1) & (ag == 0)
        m11 = (hg == 1) & (ag == 1)

        def neg_log_likelihood(params: np.ndarray) -> float:
            attack = params[:n]
            defense = params[n : 2 * n]
            home_adv = params[2 * n]
            rho = params[2 * n + 1]

            lam = np.exp(attack[hi] - defense[ai] + home_adv * not_neutral)
            mu = np.exp(attack[ai] - defense[hi])

            ll = -lam + hg * np.log(lam) - mu + ag * np.log(mu)

            tau = np.ones_like(lam)
            tau = np.where(m00, 1.0 - lam * mu * rho, tau)
            tau = np.where(m01, 1.0 + lam * rho, tau)
            tau = np.where(m10, 1.0 + mu * rho, tau)
            tau = np.where(m11, 1.0 - rho, tau)
            tau = np.clip(tau, 1e-10, None)
            ll += np.log(tau)

            total = np.sum(weights * ll) - 100.0 * attack.mean() ** 2  # fija la escala
            if prior_vec is not None:
                total -= prior_weight * np.sum((attack - defense - prior_vec) ** 2)
            return -total

        x0 = np.concatenate([np.zeros(n), np.zeros(n), np.array([0.25]), np.array([-0.1])])
        bounds = [(-3, 3)] * (2 * n) + [(-1, 2), (-0.2, 0.2)]
        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B", bounds=bounds)

        attack, defense = result.x[:n], result.x[n : 2 * n]
        self.attack = {t: float(attack[idx[t]]) for t in self.teams}
        self.defense = {t: float(defense[idx[t]]) for t in self.teams}
        self.home_advantage = float(result.x[2 * n])
        self.rho = float(result.x[2 * n + 1])
        self._fitted = True
        return self

    # ---------- predicción ----------

    def expected_goals(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        home_adj: TeamAdjustment | None = None,
        away_adj: TeamAdjustment | None = None,
    ) -> tuple[float, float]:
        if not self._fitted:
            raise RuntimeError("El modelo no está entrenado. Llama a fit() primero.")
        for t in (home, away):
            if t not in self.attack:
                raise KeyError(f"Equipo desconocido para el modelo: {t}")

        ha = home_adj or TeamAdjustment()
        aa = away_adj or TeamAdjustment()
        atk_h = self.attack[home] + ha.attack_delta
        def_h = self.defense[home] + ha.defense_delta
        atk_a = self.attack[away] + aa.attack_delta
        def_a = self.defense[away] + aa.defense_delta

        home_term = 0.0 if neutral else self.home_advantage
        lam = float(np.exp(atk_h - def_a + home_term))
        mu = float(np.exp(atk_a - def_h))
        return lam, mu

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        home_adj: TeamAdjustment | None = None,
        away_adj: TeamAdjustment | None = None,
    ) -> MatchProbabilities:
        lam, mu = self.expected_goals(
            home, away, neutral=neutral, home_adj=home_adj, away_adj=away_adj
        )
        return match_probabilities(lam, mu, self.rho)

    # ---------- serialización ----------

    def to_dict(self) -> dict:
        return {
            "xi": self.xi,
            "attack": self.attack,
            "defense": self.defense,
            "home_advantage": self.home_advantage,
            "rho": self.rho,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DixonColesModel:
        model = cls(xi=data.get("xi", 0.0))
        model.attack = data["attack"]
        model.defense = data["defense"]
        model.home_advantage = data["home_advantage"]
        model.rho = data["rho"]
        model.teams = sorted(model.attack)
        model._fitted = True
        return model
