from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(".cache")


def fetch_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download OHLCV daily data for a ticker, caching results to .cache/."""
    cache_path = CACHE_DIR / f"{ticker}_{start}_{end}.csv"

    if cache_path.exists():
        df = pd.read_csv(cache_path, index_col="Date", parse_dates=True)
        return df

    CACHE_DIR.mkdir(exist_ok=True)

    raw = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index.name = "Date"
    df.index = df.index.tz_localize(None)  # strip timezone for clean CSV round-tripping

    df.to_csv(cache_path)
    return df
