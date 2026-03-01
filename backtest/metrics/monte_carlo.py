import math

import numpy as np


def run_monte_carlo(
    equity_curve: list[dict],
    n_simulations: int = 10_000,
    seed: int | None = None,
) -> dict:
    """
    Bootstrap Monte Carlo simulation by resampling the strategy's daily returns.

    For each simulation, daily returns are resampled with replacement and a new
    equity curve is reconstructed. This reveals the distribution of outcomes
    had market conditions been slightly different.

    Args:
        equity_curve:  list of {"date": ..., "equity": float} from Portfolio.equity_curve
        n_simulations: number of bootstrap resamples (default 10,000)
        seed:          optional int for reproducible results

    Returns a dict with percentile distributions for total_return_pct, sharpe_ratio,
    max_drawdown_pct, plus probability_of_loss and all_total_returns.
    """
    rng = np.random.default_rng(seed)

    equities = np.array([e["equity"] for e in equity_curve], dtype=float)
    initial = equities[0]

    # Daily returns: the "deck of cards" to resample from
    daily_returns = np.diff(equities) / equities[:-1]
    n = len(daily_returns)

    total_returns: list[float] = []
    sharpe_ratios: list[float] = []
    max_drawdowns: list[float] = []

    for _ in range(n_simulations):
        # Bootstrap resample with replacement
        resampled = rng.choice(daily_returns, size=n, replace=True)

        # Reconstruct equity curve: initial * cumprod(1 + r)
        sim_equity = initial * np.concatenate([[1.0], np.cumprod(1.0 + resampled)])

        # Total return
        total_returns.append((sim_equity[-1] - initial) / initial * 100)

        # Sharpe ratio (annualised)
        std = resampled.std()
        sharpe_ratios.append(
            (resampled.mean() / std) * math.sqrt(252) if std != 0 else 0.0
        )

        # Max drawdown
        rolling_max = np.maximum.accumulate(sim_equity)
        drawdown = (sim_equity - rolling_max) / rolling_max * 100
        max_drawdowns.append(float(drawdown.min()))

    arr_returns = np.array(total_returns)
    arr_sharpe = np.array(sharpe_ratios)
    arr_drawdown = np.array(max_drawdowns)

    def _percentiles(arr: np.ndarray) -> dict:
        return {
            "p5":  float(np.percentile(arr, 5)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
            "mean": float(arr.mean()),
        }

    return {
        "n_simulations": n_simulations,
        "total_return_pct": _percentiles(arr_returns),
        "sharpe_ratio": _percentiles(arr_sharpe),
        "max_drawdown_pct": _percentiles(arr_drawdown),
        "probability_of_loss": float((arr_returns < 0).sum() / n_simulations),
        "all_total_returns": arr_returns.tolist(),
    }
