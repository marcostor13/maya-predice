"""Modelo Dixon-Coles para predicción de partidos de fútbol.

Estima, por máxima verosimilitud, los parámetros de ataque y defensa de cada
equipo, la ventaja de localía y el parámetro de dependencia rho, a partir de un
histórico de partidos. Aplica decaimiento temporal: los partidos recientes pesan
más en la verosimilitud.

Referencia: Dixon & Coles (1997), "Modelling Association Football Scores and
Inefficiencies in the Football Betting Market".

Uso típico:
    model = DixonColesModel()
    model.fit(matches)                       # matches: lista de MatchResult
    pred = model.predict("ARG", "BRA")       # MatchProbabilities
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


class DixonColesModel:
    """Modelo Dixon-Coles ajustable y serializable.

    Parámetros estimados:
      - attack[team], defense[team]
      - home_advantage (gamma)
      - rho (dependencia para marcadores bajos)
    """

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

    def _time_weights(self, matches: list[MatchResult]) -> np.ndarray:
        if self.xi <= 0.0:
            return np.ones(len(matches))
        today = max((m.played_on for m in matches if m.played_on), default=None)
        if today is None:
            return np.ones(len(matches))
        weights = []
        for m in matches:
            days = (today - m.played_on).days if m.played_on else 0
            weights.append(np.exp(-self.xi * days))
        return np.array(weights)

    def fit(self, matches: list[MatchResult]) -> DixonColesModel:
        if not matches:
            raise ValueError("Se requieren partidos para entrenar el modelo.")

        self.teams = sorted({t for m in matches for t in (m.home, m.away)})
        n = len(self.teams)
        idx = {t: i for i, t in enumerate(self.teams)}
        weights = self._time_weights(matches)

        # Vector de parámetros: [attack(n), defense(n), home_adv, rho]
        # Restricción de identificabilidad: media de ataques = 0 (se aplica suave).
        def unpack(params: np.ndarray):
            attack = params[:n]
            defense = params[n : 2 * n]
            home_adv = params[2 * n]
            rho = params[2 * n + 1]
            return attack, defense, home_adv, rho

        def neg_log_likelihood(params: np.ndarray) -> float:
            attack, defense, home_adv, rho = unpack(params)
            ll = 0.0
            for w, m in zip(weights, matches, strict=True):
                hi, ai = idx[m.home], idx[m.away]
                lam = np.exp(attack[hi] - defense[ai] + home_adv)
                mu = np.exp(attack[ai] - defense[hi])
                tau = _tau(m.home_goals, m.away_goals, lam, mu, rho)
                tau = max(tau, 1e-10)
                ll += w * (
                    np.log(tau)
                    - lam
                    + m.home_goals * np.log(lam)
                    - mu
                    + m.away_goals * np.log(mu)
                )
            # penalización suave para fijar la escala (sum attack ~ 0)
            ll -= 100.0 * (attack.mean()) ** 2
            return -ll

        x0 = np.concatenate([
            np.zeros(n),        # attack
            np.zeros(n),        # defense
            np.array([0.25]),   # home advantage inicial
            np.array([-0.1]),   # rho inicial
        ])
        bounds = [(-3, 3)] * (2 * n) + [(-1, 2), (-0.3, 0.3)]

        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B", bounds=bounds)

        attack, defense, home_adv, rho = unpack(result.x)
        self.attack = {t: float(attack[idx[t]]) for t in self.teams}
        self.defense = {t: float(defense[idx[t]]) for t in self.teams}
        self.home_advantage = float(home_adv)
        self.rho = float(rho)
        self._fitted = True
        return self

    # ---------- predicción ----------

    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        if not self._fitted:
            raise RuntimeError("El modelo no está entrenado. Llama a fit() primero.")
        for t in (home, away):
            if t not in self.attack:
                raise KeyError(f"Equipo desconocido para el modelo: {t}")
        lam = float(np.exp(self.attack[home] - self.defense[away] + self.home_advantage))
        mu = float(np.exp(self.attack[away] - self.defense[home]))
        return lam, mu

    def predict(self, home: str, away: str) -> MatchProbabilities:
        lam, mu = self.expected_goals(home, away)
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
