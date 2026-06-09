"""Backtesting del modelo: evaluación fuera de muestra (out-of-sample).

Entrena el modelo con los partidos **anteriores** a una fecha de corte y lo evalúa
sobre los partidos **posteriores** (que no vio), midiendo log-loss, Brier y
accuracy. Se compara contra una línea base (tasas empíricas 1X2 del histórico de
entrenamiento), de modo que se puede afirmar si el modelo aporta valor real.

`outcome` y las métricas son puras; la orquestación usa el histórico (martj42).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date

from app.core.config import settings
from app.data.history import ResultsHistoryProvider
from app.services.prediction.dixon_coles import DixonColesModel, MatchResult
from app.services.prediction.elo import compute_elo, elo_to_priors
from app.services.prediction.metrics import accuracy, brier_score, log_loss

logger = logging.getLogger("maya.backtest")


def outcome(m: MatchResult) -> str:
    if m.home_goals > m.away_goals:
        return "H"
    if m.home_goals < m.away_goals:
        return "A"
    return "D"


def _base_rates(matches: list[MatchResult]) -> tuple[float, float, float]:
    if not matches:
        return (1 / 3, 1 / 3, 1 / 3)
    h = d = a = 0
    for m in matches:
        o = outcome(m)
        h += o == "H"
        d += o == "D"
        a += o == "A"
    n = len(matches)
    return (h / n, d / n, a / n)


@dataclass
class BacktestResult:
    cutoff: str
    train_matches: int
    test_matches: int
    log_loss: float
    brier: float
    accuracy: float
    baseline_log_loss: float
    baseline_brier: float
    baseline_accuracy: float

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def evaluate(
    train: list[MatchResult], test: list[MatchResult], *, xi: float, prior_weight: float
) -> BacktestResult:
    """Entrena con `train` y evalúa sobre `test` (función determinista, sin red)."""
    model = DixonColesModel(xi=xi)
    priors = elo_to_priors(compute_elo(train)) if prior_weight > 0 else None
    model.fit(train, priors=priors, prior_weight=prior_weight)

    base = _base_rates(train)
    probs: list[tuple[float, float, float]] = []
    base_probs: list[tuple[float, float, float]] = []
    outcomes: list[str] = []
    for m in test:
        if m.home in model.attack and m.away in model.attack:
            p = model.predict(m.home, m.away, neutral=m.neutral)
            probs.append((p.p_home, p.p_draw, p.p_away))
            base_probs.append(base)
            outcomes.append(outcome(m))

    return BacktestResult(
        cutoff="",
        train_matches=len(train),
        test_matches=len(probs),
        log_loss=log_loss(probs, outcomes),
        brier=brier_score(probs, outcomes),
        accuracy=accuracy(probs, outcomes),
        baseline_log_loss=log_loss(base_probs, outcomes),
        baseline_brier=brier_score(base_probs, outcomes),
        baseline_accuracy=accuracy(base_probs, outcomes),
    )


async def run_backtest(cutoff: date | None = None) -> BacktestResult:
    """Descarga el histórico, parte por la fecha de corte y evalúa el modelo."""
    cutoff = cutoff or date(2024, 1, 1)
    history = await ResultsHistoryProvider(team_filter="both").fetch_results()
    train = [m for m in history if m.played_on and m.played_on < cutoff]
    test = [m for m in history if m.played_on and m.played_on >= cutoff]
    if not train or not test:
        raise ValueError("Datos insuficientes para el backtest en esa fecha de corte.")

    result = evaluate(
        train, test, xi=settings.model_decay_xi, prior_weight=settings.elo_prior_weight
    )
    result.cutoff = cutoff.isoformat()
    logger.info(
        "Backtest %s: log-loss %.3f (base %.3f), Brier %.3f, acc %.3f en %s partidos.",
        result.cutoff,
        result.log_loss,
        result.baseline_log_loss,
        result.brier,
        result.accuracy,
        result.test_matches,
    )
    return result
