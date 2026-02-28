import pandas as pd

from backtest.engine.portfolio import Portfolio
from backtest.strategies.base import Strategy


def run_backtest(
    strategy: Strategy,
    data: pd.DataFrame,
    starting_capital: float,
    commission_pct: float,
) -> tuple[Portfolio, int]:
    """
    Run a backtest over the full date range of `data`.

    On each day, the strategy receives only history up to and including that day
    (no lookahead bias). Orders are executed at that day's Close price.

    Returns the final Portfolio (with equity_curve populated) and total executed trade count.
    """
    portfolio = Portfolio(cash=starting_capital)
    total_trades = 0

    for i in range(len(data)):
        today = data.index[i]
        history = data.iloc[: i + 1]  # CRITICAL: never expose future rows

        orders = strategy.on_data(history)

        close_price = float(data.at[today, "Close"])

        for order in orders:
            if portfolio.execute_order(order, close_price, commission_pct):
                total_trades += 1

        # Price all current positions at today's close
        prices = {ticker: close_price for ticker in portfolio.positions}
        portfolio.log_equity(today, prices)

    return portfolio, total_trades
