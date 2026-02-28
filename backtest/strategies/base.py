from abc import ABC, abstractmethod

import pandas as pd

from backtest.engine.order import Order


class Strategy(ABC):
    @abstractmethod
    def on_data(self, history: pd.DataFrame) -> list[Order]:
        """
        history: OHLCV DataFrame up to and including today. Index is Date.
        Return a list of Orders to execute. Return empty list for no action.
        """
        pass
