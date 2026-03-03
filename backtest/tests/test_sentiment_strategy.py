"""Tests for SentimentStrategy (6 tests)."""

import datetime

import pandas as pd
import pytest

from backtest.strategies.sentiment_strategy import SentimentStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_csv(tmp_path, scores: list[float], start: str = "2024-01-01") -> str:
    """Write a sentiment CSV to a temp file and return its path as a str."""
    base = datetime.date.fromisoformat(start)
    rows = [
        {
            "date": (base + datetime.timedelta(days=i)).isoformat(),
            "sentiment_score": s,
            "article_count": 1,
        }
        for i, s in enumerate(scores)
    ]
    path = tmp_path / "test_sentiment.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return str(path)


def _make_ohlcv(dates: list[datetime.date]) -> pd.DataFrame:
    """Minimal OHLCV DataFrame with Close=100 for each date."""
    return pd.DataFrame(
        {"Close": 100.0},
        index=pd.to_datetime(dates),
    )


def _run_strategy(strategy: SentimentStrategy, df: pd.DataFrame) -> list[list]:
    """Simulate the backtester's day-by-day history slicing."""
    return [strategy.on_data(df.iloc[: i + 1]) for i in range(len(df))]


# ---------------------------------------------------------------------------
# Test 1: Buy signal when sentiment exceeds threshold
# ---------------------------------------------------------------------------

def test_buy_signal_above_threshold(tmp_path):
    scores = [0.0, 0.0, 0.0, 0.0, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30]
    csv = _make_csv(tmp_path, scores)
    strategy = SentimentStrategy(
        ticker="TEST",
        sentiment_csv=csv,
        buy_threshold=0.20,
        sell_threshold=-0.10,
        smoothing_window=1,  # no smoothing
    )
    base = datetime.date(2024, 1, 1)
    dates = [base + datetime.timedelta(days=i) for i in range(len(scores))]
    df = _make_ohlcv(dates)
    orders = _run_strategy(strategy, df)

    # Days 0-3: no signal
    for i in range(4):
        assert orders[i] == [], f"Expected no order on day {i}"
    # Day 4: first day above threshold → BUY
    assert len(orders[4]) == 1
    assert orders[4][0].side == "BUY"
    # Days 5-9: already in position → no new buy
    for i in range(5, 10):
        assert orders[i] == [], f"Expected no order on day {i} (already in position)"


# ---------------------------------------------------------------------------
# Test 2: Sell signal when sentiment drops below threshold
# ---------------------------------------------------------------------------

def test_sell_signal_below_threshold(tmp_path):
    # Days 0-4: high sentiment → buy on day 0; days 5-9: negative → sell on day 5
    scores = [0.30, 0.30, 0.30, 0.30, 0.30, -0.20, -0.20, -0.20, -0.20, -0.20]
    csv = _make_csv(tmp_path, scores)
    strategy = SentimentStrategy(
        ticker="TEST",
        sentiment_csv=csv,
        buy_threshold=0.20,
        sell_threshold=-0.10,
        smoothing_window=1,
    )
    base = datetime.date(2024, 1, 1)
    dates = [base + datetime.timedelta(days=i) for i in range(len(scores))]
    df = _make_ohlcv(dates)
    orders = _run_strategy(strategy, df)

    assert orders[0][0].side == "BUY"
    assert orders[5][0].side == "SELL"
    # Days 6-9: no position → no orders
    for i in range(6, 10):
        assert orders[i] == []


# ---------------------------------------------------------------------------
# Test 3: Forward-fill on missing dates
# ---------------------------------------------------------------------------

def test_forward_fill_missing_date(tmp_path):
    # Mon–Thu scores all +0.30; Friday is absent from the CSV
    mon = datetime.date(2024, 1, 1)  # Monday
    tue = datetime.date(2024, 1, 2)
    wed = datetime.date(2024, 1, 3)
    thu = datetime.date(2024, 1, 4)
    fri = datetime.date(2024, 1, 5)  # NOT in CSV

    rows = [
        {"date": mon.isoformat(), "sentiment_score": 0.30, "article_count": 1},
        {"date": tue.isoformat(), "sentiment_score": 0.30, "article_count": 1},
        {"date": wed.isoformat(), "sentiment_score": 0.30, "article_count": 1},
        {"date": thu.isoformat(), "sentiment_score": 0.30, "article_count": 1},
    ]
    path = tmp_path / "fwd_fill.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    strategy = SentimentStrategy(
        ticker="TEST",
        sentiment_csv=str(path),
        buy_threshold=0.20,
        sell_threshold=-0.10,
        smoothing_window=1,
    )
    df = _make_ohlcv([mon, tue, wed, thu, fri])
    orders = _run_strategy(strategy, df)

    # Monday: buy
    assert orders[0][0].side == "BUY"
    # Friday: forward-fills Thursday's +0.30 → still in position, no order
    assert orders[4] == [], "Should not sell on Friday (forward-filled positive score)"


# ---------------------------------------------------------------------------
# Test 4: Smoothing window dampens a one-day dip
# ---------------------------------------------------------------------------

def test_smoothing_window_prevents_whipsaw(tmp_path):
    # Raw scores: day-1 dip is negative, but 3-day rolling avg stays positive
    scores = [0.5, -0.3, 0.4, 0.3, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    csv = _make_csv(tmp_path, scores)
    strategy = SentimentStrategy(
        ticker="TEST",
        sentiment_csv=csv,
        buy_threshold=0.20,
        sell_threshold=-0.10,
        smoothing_window=3,
    )
    base = datetime.date(2024, 1, 1)
    dates = [base + datetime.timedelta(days=i) for i in range(len(scores))]
    df = _make_ohlcv(dates)
    orders = _run_strategy(strategy, df)

    # Verify no SELL appears anywhere (the dip is smoothed away)
    sell_days = [i for i, o in enumerate(orders) if o and o[0].side == "SELL"]
    assert sell_days == [], f"Unexpected SELL on days: {sell_days}"


# ---------------------------------------------------------------------------
# Test 5: No trades when sentiment stays in neutral zone
# ---------------------------------------------------------------------------

def test_no_trades_in_neutral_zone(tmp_path):
    # All scores between sell_threshold (-0.10) and buy_threshold (0.20)
    scores = [0.05, -0.05, 0.10, 0.00, 0.08, -0.02, 0.12, 0.01, 0.09, -0.04]
    csv = _make_csv(tmp_path, scores)
    strategy = SentimentStrategy(
        ticker="TEST",
        sentiment_csv=csv,
        buy_threshold=0.20,
        sell_threshold=-0.10,
        smoothing_window=1,
    )
    base = datetime.date(2024, 1, 1)
    dates = [base + datetime.timedelta(days=i) for i in range(len(scores))]
    df = _make_ohlcv(dates)
    orders = _run_strategy(strategy, df)

    assert all(o == [] for o in orders), "Expected no orders in neutral zone"


# ---------------------------------------------------------------------------
# Test 6: Strategy doesn't buy twice (no double-entry)
# ---------------------------------------------------------------------------

def test_no_double_buy(tmp_path):
    # All scores well above buy threshold for every day
    scores = [0.50] * 10
    csv = _make_csv(tmp_path, scores)
    strategy = SentimentStrategy(
        ticker="TEST",
        sentiment_csv=csv,
        buy_threshold=0.20,
        sell_threshold=-0.10,
        smoothing_window=1,
    )
    base = datetime.date(2024, 1, 1)
    dates = [base + datetime.timedelta(days=i) for i in range(len(scores))]
    df = _make_ohlcv(dates)
    orders = _run_strategy(strategy, df)

    buy_days = [i for i, o in enumerate(orders) if o and o[0].side == "BUY"]
    assert buy_days == [0], f"Expected exactly one BUY on day 0, got: {buy_days}"
