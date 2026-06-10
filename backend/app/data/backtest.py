"""Backtesting del modelo desde la CLI.

    python -m app.data.backtest [YYYY-MM-DD]

Entrena con el histórico anterior a la fecha de corte y evalúa sobre el posterior,
mostrando log-loss, Brier y accuracy frente a la línea base.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date

from app.services.prediction.backtest import run_backtest


async def main() -> None:
    cutoff = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    r = await run_backtest(cutoff)
    print(f"[backtest] corte={r.cutoff}  entreno={r.train_matches}  test={r.test_matches}")
    print(
        f"[backtest] modelo : RPS={r.rps:.4f}  log-loss={r.log_loss:.3f}  "
        f"Brier={r.brier:.3f}  acc={r.accuracy:.3f}"
    )
    print(
        f"[backtest] base   : RPS={r.baseline_rps:.4f}  log-loss={r.baseline_log_loss:.3f}  "
        f"Brier={r.baseline_brier:.3f}  acc={r.baseline_accuracy:.3f}"
    )
    better = r.rps < r.baseline_rps
    print(f"[backtest] el modelo {'SUPERA' if better else 'NO supera'} a la línea base (RPS).")


if __name__ == "__main__":
    asyncio.run(main())
