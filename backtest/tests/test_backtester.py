import pandas as pd
import pytest

from backtest.engine.backtester import run_backtest
from backtest.engine.order import Order
from backtest.strategies.base import Strategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_data(prices: list[float]) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with identical O/H/L/C values."""
    dates = pd.date_range("2023-01-01", periods=len(prices), freq="B")
    return pd.DataFrame(
        {"Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": 1000},
        index=dates,
    )


class BuyOnDayOneSellOnLastDay(Strategy):
    """Buys `quantity` shares on the first bar, sells them on the last bar."""

    def __init__(self, ticker: str, quantity: int, total_days: int) -> None:
        self.ticker = ticker
        self.quantity = quantity
        self.total_days = total_days
        self._bought = False
        self._sold = False

    def on_data(self, history: pd.DataFrame) -> list[Order]:
        if len(history) == 1 and not self._bought:
            self._bought = True
            return [Order(self.ticker, "BUY", self.quantity)]
        if len(history) == self.total_days and not self._sold:
            self._sold = True
            return [Order(self.ticker, "SELL", self.quantity)]
        return []


class NoLookaheadStrategy(Strategy):
    """Asserts that each call receives exactly one more row than the previous."""

    def __init__(self) -> None:
        self._call_count = 0

    def on_data(self, history: pd.DataFrame) -> list[Order]:
        self._call_count += 1
        assert len(history) == self._call_count, (
            f"Call {self._call_count}: expected {self._call_count} rows, got {len(history)}"
        )
        return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_final_equity_matches_manual_calculation():
    """Buy on day 1 @ 100, sell on day 5 @ 120. Verify equity via manual math."""
    prices = [100.0, 105.0, 110.0, 115.0, 120.0]
    data = make_data(prices)
    starting_capital = 10_000.0
    commission = 0.001
    quantity = 10

    strategy = BuyOnDayOneSellOnLastDay("TEST", quantity, total_days=5)
    portfolio, total_trades, _ = run_backtest(strategy, data, starting_capital, commission)

    # BUY: cost = 100 * 10 * 1.001 = 1001.0  →  cash = 8999.0
    # SELL: proceeds = 120 * 10 * 0.999 = 1198.8  →  cash = 10197.8
    expected_cash = pytest.approx(10_197.8)
    assert portfolio.cash == expected_cash
    assert "TEST" not in portfolio.positions
    assert total_trades == 2


def test_equity_curve_has_one_entry_per_day():
    prices = [100.0, 105.0, 110.0]
    data = make_data(prices)
    strategy = NoLookaheadStrategy()
    portfolio, _, _tl = run_backtest(strategy, data, starting_capital=10_000.0, commission_pct=0.0)
    assert len(portfolio.equity_curve) == len(prices)


def test_no_lookahead_bias():
    """Strategy asserts it only ever sees history up to the current day."""
    prices = [float(i) for i in range(1, 21)]
    data = make_data(prices)
    strategy = NoLookaheadStrategy()
    # If lookahead bias exists, the assertion inside on_data will raise
    run_backtest(strategy, data, starting_capital=100_000.0, commission_pct=0.0)
    assert strategy._call_count == len(prices)


def test_rejected_order_not_counted_as_trade():
    """An order that the portfolio rejects should not increment trade count."""

    class AlwaysBuy(Strategy):
        def on_data(self, history: pd.DataFrame) -> list[Order]:
            return [Order("TEST", "BUY", 999_999)]  # will overdraw cash

    data = make_data([100.0, 105.0])
    _, total_trades, _tl = run_backtest(
        AlwaysBuy(), data, starting_capital=1_000.0, commission_pct=0.0
    )
    assert total_trades == 0
