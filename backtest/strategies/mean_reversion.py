import pandas as pd

from backtest.engine.order import Order
from backtest.strategies.base import Strategy


class MeanReversion(Strategy):
    def __init__(
        self,
        ticker: str,
        lookback: int = 20,
        entry_z: float = -2.0,
        exit_z: float = 0.0,
        quantity: int = 100,
    ) -> None:
        self.ticker = ticker
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.quantity = quantity
        self._in_position: bool = False

    def on_data(self, history: pd.DataFrame) -> list[Order]:
        if len(history) < self.lookback:
            return []

        closes = history["Close"]
        rolling_mean = closes.rolling(self.lookback).mean().iloc[-1]
        rolling_std = closes.rolling(self.lookback).std().iloc[-1]

        if rolling_std == 0:
            return []

        z = (closes.iloc[-1] - rolling_mean) / rolling_std

        # Price is abnormally low — expect a reversion upward
        if z < self.entry_z and not self._in_position:
            self._in_position = True
            return [Order(self.ticker, "BUY", self.quantity)]

        # Price has recovered to (or above) the mean — exit
        if z > self.exit_z and self._in_position:
            self._in_position = False
            return [Order(self.ticker, "SELL", self.quantity)]

        return []
