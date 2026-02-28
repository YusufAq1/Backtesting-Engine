import pandas as pd

from backtest.engine.order import Order
from backtest.strategies.base import Strategy


class SMACrossover(Strategy):
    def __init__(
        self,
        ticker: str,
        short_window: int = 20,
        long_window: int = 50,
        quantity: int = 100,
    ) -> None:
        self.ticker = ticker
        self.short_window = short_window
        self.long_window = long_window
        self.quantity = quantity
        self._in_position: bool = False

    def on_data(self, history: pd.DataFrame) -> list[Order]:
        # Need long_window rows for today's SMA + 1 more for yesterday's — so long_window + 1 total
        if len(history) < self.long_window + 1:
            return []

        closes = history["Close"]
        short_sma = closes.rolling(self.short_window).mean()
        long_sma = closes.rolling(self.long_window).mean()

        short_today, short_yesterday = short_sma.iloc[-1], short_sma.iloc[-2]
        long_today, long_yesterday = long_sma.iloc[-1], long_sma.iloc[-2]

        # Golden cross: short crosses above long → BUY
        if short_yesterday < long_yesterday and short_today > long_today:
            if not self._in_position:
                self._in_position = True
                return [Order(self.ticker, "BUY", self.quantity)]

        # Death cross: short crosses below long → SELL (only if holding)
        elif short_yesterday > long_yesterday and short_today < long_today:
            if self._in_position:
                self._in_position = False
                return [Order(self.ticker, "SELL", self.quantity)]

        return []
