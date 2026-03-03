import datetime

import pandas as pd

from backtest.engine.order import Order
from backtest.strategies.base import Strategy


class SentimentStrategy(Strategy):
    """
    Buys when the smoothed FinBERT sentiment score exceeds `buy_threshold`
    and sells when it drops below `sell_threshold`.

    Sentiment data is loaded from a pre-generated CSV produced by
    scripts/generate_sentiment.py. The strategy itself has no ML
    dependencies — it only reads the CSV with pandas.
    """

    def __init__(
        self,
        ticker: str,
        sentiment_csv: str,
        buy_threshold: float = 0.20,
        sell_threshold: float = -0.10,
        smoothing_window: int = 5,
        quantity: int = 100,
    ) -> None:
        self.ticker = ticker
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.quantity = quantity

        # Load and smooth the sentiment CSV
        df = pd.read_csv(sentiment_csv, parse_dates=["date"])
        df = df.set_index("date")
        df["smoothed"] = (
            df["sentiment_score"]
            .rolling(window=smoothing_window, min_periods=1)
            .mean()
        )

        # Normalise index to datetime.date for O(1) lookup
        self._scores: dict[datetime.date, float] = {
            idx.date() if hasattr(idx, "date") else idx: float(row["smoothed"])
            for idx, row in df.iterrows()
        }

        self._last_known_score: float = 0.0
        self._in_position: bool = False

    # ------------------------------------------------------------------
    def on_data(self, history: pd.DataFrame) -> list[Order]:
        raw_today = history.index[-1]
        today: datetime.date = (
            raw_today.date() if hasattr(raw_today, "date") else raw_today
        )

        # Forward-fill: use last known score if today has no data
        if today in self._scores:
            self._last_known_score = self._scores[today]
        score = self._last_known_score

        if score >= self.buy_threshold and not self._in_position:
            self._in_position = True
            return [Order(self.ticker, "BUY", self.quantity)]

        if score <= self.sell_threshold and self._in_position:
            self._in_position = False
            return [Order(self.ticker, "SELL", self.quantity)]

        return []
