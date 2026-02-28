import math

import pandas as pd


def compute_metrics(
    equity_curve: list[dict],
    total_trades: int,
    trade_log: list[dict],
    data: pd.DataFrame,
) -> dict:
    """
    Compute performance metrics from a completed backtest.

    Args:
        equity_curve: list of {"date": ..., "equity": float} from Portfolio.equity_curve
        total_trades:  count of all accepted orders
        trade_log:     list of {"side", "price", "quantity", "ticker", "date"} from backtester
        data:          original OHLCV DataFrame (used for buy-and-hold benchmark)

    Returns a dict with keys:
        total_return_pct, annualized_return_pct, sharpe_ratio, max_drawdown_pct,
        total_trades, win_rate_pct, buy_and_hold_return_pct
    """
    equities = [e["equity"] for e in equity_curve]
    dates = [e["date"] for e in equity_curve]

    initial = equities[0]
    final = equities[-1]

    # --- Total return ---
    total_return_pct = (final - initial) / initial * 100

    # --- Annualized return ---
    n_days = (dates[-1] - dates[0]).days
    if n_days > 0:
        annualized_return_pct = ((final / initial) ** (365.0 / n_days) - 1) * 100
    else:
        annualized_return_pct = 0.0

    # --- Sharpe ratio (annualized) ---
    daily_returns = pd.Series(equities).pct_change().dropna()
    std = daily_returns.std()
    sharpe_ratio = (daily_returns.mean() / std) * math.sqrt(252) if std != 0 else 0.0

    # --- Max drawdown ---
    equity_series = pd.Series(equities)
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max * 100
    max_drawdown_pct = float(drawdown.min())

    # --- Win rate (round-trip trades) ---
    wins = 0
    completed = 0
    pending_buys: list[float] = []
    for trade in trade_log:
        if trade["side"] == "BUY":
            pending_buys.append(trade["price"])
        elif trade["side"] == "SELL" and pending_buys:
            buy_price = pending_buys.pop(0)
            completed += 1
            if trade["price"] > buy_price:
                wins += 1
    win_rate_pct = (wins / completed * 100) if completed > 0 else 0.0

    # --- Buy-and-hold benchmark ---
    bah_initial = float(data["Close"].iloc[0])
    bah_final = float(data["Close"].iloc[-1])
    buy_and_hold_return_pct = (bah_final - bah_initial) / bah_initial * 100

    return {
        "total_return_pct": total_return_pct,
        "annualized_return_pct": annualized_return_pct,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown_pct": max_drawdown_pct,
        "total_trades": total_trades,
        "win_rate_pct": win_rate_pct,
        "buy_and_hold_return_pct": buy_and_hold_return_pct,
    }
