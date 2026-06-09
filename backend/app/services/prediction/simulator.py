"""Simulador Monte Carlo del Mundial 2026 (formato de 48 equipos).

Usa el modelo Dixon-Coles entrenado, aplica los ajustes por disponibilidad de
cada selección y trata todos los partidos como sede neutral. Simula N veces:
- fase de grupos (12 grupos de 4, todos contra todos),
- clasifican los 2 primeros de cada grupo + los 8 mejores terceros (32),
- eliminatorias a partido único hasta la final,
y estima la probabilidad de cada selección de superar la fase de grupos y de
alcanzar cada ronda (incl. campeón).

Nota: el emparejamiento exacto del bracket oficial 2026 es complejo; aquí se usa
un bracket equilibrado por siembra (los más fuertes evitan cruzarse pronto), lo
que da probabilidades de campeón coherentes. Refinarlo es trabajo futuro.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from app.services.prediction.dixon_coles import DixonColesModel, TeamAdjustment


class TournamentSimulator:
    def __init__(
        self,
        model: DixonColesModel,
        adjustments: dict[str, TeamAdjustment] | None = None,
        rng: np.random.Generator | None = None,
    ):
        self.model = model
        self.adjustments = adjustments or {}
        self.rng = rng or np.random.default_rng()

    def _expected(self, home: str, away: str) -> tuple[float, float]:
        return self.model.expected_goals(
            home,
            away,
            neutral=True,
            home_adj=self.adjustments.get(home),
            away_adj=self.adjustments.get(away),
        )

    def _goals(self, home: str, away: str) -> tuple[int, int]:
        lam, mu = self._expected(home, away)
        return int(self.rng.poisson(lam)), int(self.rng.poisson(mu))

    def _winner(self, home: str, away: str) -> str:
        h, a = self._goals(home, away)
        if h == a:  # desempate (prórroga/penales) ponderado por fuerza esperada
            lam, mu = self._expected(home, away)
            return home if self.rng.random() < lam / (lam + mu) else away
        return home if h > a else away

    def _simulate_group(self, teams: list[str]) -> list[tuple[str, int, int, int]]:
        """Round-robin; devuelve [(equipo, puntos, dif_goles, goles_favor)] ordenado."""
        pts = defaultdict(int)
        gd = defaultdict(int)
        gf = defaultdict(int)
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                h, a = self._goals(teams[i], teams[j])
                gf[teams[i]] += h
                gf[teams[j]] += a
                gd[teams[i]] += h - a
                gd[teams[j]] += a - h
                if h > a:
                    pts[teams[i]] += 3
                elif a > h:
                    pts[teams[j]] += 3
                else:
                    pts[teams[i]] += 1
                    pts[teams[j]] += 1
        ranked = sorted(teams, key=lambda t: (pts[t], gd[t], gf[t]), reverse=True)
        return [(t, pts[t], gd[t], gf[t]) for t in ranked]

    def _seeded_bracket(self, qualified: list[str]) -> list[str]:
        """Ordena los 32 clasificados por fuerza para sembrar el bracket
        (1 vs 32, 2 vs 31, …) y que los favoritos no se crucen pronto."""
        def strength(code: str) -> float:
            adj = self.adjustments.get(code, TeamAdjustment())
            return self.model.attack.get(code, 0.0) - self.model.defense.get(code, 0.0) + (
                adj.attack_delta - adj.defense_delta
            )

        ordered = sorted(qualified, key=strength, reverse=True)
        n = len(ordered)
        bracket: list[str] = []
        for i in range(n // 2):
            bracket.append(ordered[i])
            bracket.append(ordered[n - 1 - i])
        return bracket

    def run(self, groups: dict[str, list[str]], iterations: int = 5000) -> dict[str, dict]:
        all_teams = [t for ts in groups.values() for t in ts]
        stages = ("advance", "round16", "quarter", "semi", "final", "champion")
        counts: dict[str, dict[str, int]] = {t: dict.fromkeys(stages, 0) for t in all_teams}

        for _ in range(iterations):
            qualified: list[str] = []
            thirds: list[tuple[str, int, int, int]] = []
            for teams in groups.values():
                ranked = self._simulate_group(teams)
                for t, *_ in ranked[:2]:
                    qualified.append(t)
                    counts[t]["advance"] += 1
                if len(ranked) >= 3:
                    thirds.append(ranked[2])
            # 8 mejores terceros
            thirds.sort(key=lambda r: (r[1], r[2], r[3]), reverse=True)
            for t, *_ in thirds[:8]:
                qualified.append(t)
                counts[t]["advance"] += 1

            self._knockout(qualified, counts)

        return {t: {s: counts[t][s] / iterations for s in stages} for t in all_teams}

    def _knockout(self, qualified: list[str], counts: dict[str, dict[str, int]]) -> None:
        """Simula la eliminatoria y acumula la ronda alcanzada por cada equipo.

        Registra los equipos vivos al inicio de cada ronda (conjuntos anidados):
        garantiza exactamente un campeón y probabilidades monótonas con cualquier
        tamaño de cuadro. En el cuadro real de 32 las rondas son 32→16→8→4→2→1.
        """
        bracket = self._seeded_bracket(qualified)
        if not bracket:
            return
        rounds: list[list[str]] = [list(bracket)]
        while len(bracket) > 1:
            nxt = [
                self._winner(bracket[k], bracket[k + 1])
                for k in range(0, len(bracket) - 1, 2)
            ]
            if len(bracket) % 2 == 1:  # bye: el último pasa sin jugar
                nxt.append(bracket[-1])
            bracket = nxt
            rounds.append(list(bracket))

        # Etapa = estar vivo en la ronda correspondiente, contada desde el final.
        stage_by_offset = {1: "champion", 2: "final", 3: "semi", 4: "quarter", 5: "round16"}
        for offset, stage in stage_by_offset.items():
            if len(rounds) >= offset:
                for team in rounds[-offset]:
                    counts[team][stage] += 1
