"""Simulador Monte Carlo del torneo basado en un modelo de predicción.

Dado un modelo entrenado y la estructura de grupos, simula N veces el torneo
completo (fase de grupos + eliminatorias con el formato del Mundial 2026) y
estima la probabilidad de que cada selección alcance cada fase y sea campeona.

Nota: el bracket exacto del Mundial 2026 (cruces entre grupos, mejores terceros)
se modela de forma simplificada aquí; afinarlo es parte de la Fase 1/2 (ver
PLATFORM.md). El objetivo es dejar la estructura lista para iterar.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from app.services.prediction.dixon_coles import DixonColesModel


class TournamentSimulator:
    def __init__(self, model: DixonColesModel, rng: np.random.Generator | None = None):
        self.model = model
        self.rng = rng or np.random.default_rng()

    def _simulate_goals(self, home: str, away: str) -> tuple[int, int]:
        lam, mu = self.model.expected_goals(home, away)
        return int(self.rng.poisson(lam)), int(self.rng.poisson(mu))

    def _knockout_winner(self, home: str, away: str) -> str:
        h, a = self._simulate_goals(home, away)
        if h == a:  # desempate (penales) ~ moneda ponderada por fuerza esperada
            lam, mu = self.model.expected_goals(home, away)
            return home if self.rng.random() < lam / (lam + mu) else away
        return home if h > a else away

    def simulate_group(self, teams: list[str]) -> list[str]:
        """Round-robin de un grupo; devuelve los equipos ordenados por puntos."""
        points: dict[str, int] = defaultdict(int)
        gd: dict[str, int] = defaultdict(int)
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                h, a = self._simulate_goals(teams[i], teams[j])
                gd[teams[i]] += h - a
                gd[teams[j]] += a - h
                if h > a:
                    points[teams[i]] += 3
                elif a > h:
                    points[teams[j]] += 3
                else:
                    points[teams[i]] += 1
                    points[teams[j]] += 1
        return sorted(teams, key=lambda t: (points[t], gd[t]), reverse=True)

    def run(self, groups: dict[str, list[str]], iterations: int = 10_000) -> dict[str, dict]:
        """Ejecuta la simulación Monte Carlo.

        `groups`: {"A": ["MEX", "...", ...], "B": [...], ...}
        Devuelve por equipo: prob de avanzar de grupo y de ser campeón.
        """
        advanced = defaultdict(int)
        champions = defaultdict(int)

        for _ in range(iterations):
            qualified: list[str] = []
            for teams in groups.values():
                ranked = self.simulate_group(teams)
                top2 = ranked[:2]
                qualified.extend(top2)
                for t in top2:
                    advanced[t] += 1

            # Bracket simple: emparejar secuencialmente hasta que quede 1.
            bracket = qualified[:]
            self.rng.shuffle(bracket)
            while len(bracket) > 1:
                next_round = []
                for k in range(0, len(bracket) - 1, 2):
                    next_round.append(self._knockout_winner(bracket[k], bracket[k + 1]))
                if len(bracket) % 2 == 1:
                    next_round.append(bracket[-1])
                bracket = next_round
            if bracket:
                champions[bracket[0]] += 1

        return {
            t: {
                "advance_prob": advanced[t] / iterations,
                "champion_prob": champions[t] / iterations,
            }
            for t in {team for teams in groups.values() for team in teams}
        }
