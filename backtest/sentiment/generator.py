from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from backtest.sentiment.config import (
    FINBERT_MODEL,
    LABEL_MAP,
    MAX_TEXT_LENGTH,
    NEWSAPI_SORT_BY,
    SENTIMENT_DATA_DIR,
)

# Stay safely below the free-tier limit of 100 requests/day
_NEWSAPI_REQUEST_LIMIT = 95


def generate_sentiment_csv(
    ticker: str,
    keyword: str,
    start_date: str,
    end_date: str,
    api_key: str,
    output_dir: str = SENTIMENT_DATA_DIR,
) -> Path:
    """
    Fetch news articles for `keyword`, score each with FinBERT, and write a
    CSV of daily aggregated sentiment scores to `output_dir/{ticker}_sentiment.csv`.

    Args:
        ticker:     Stock ticker symbol — used for the output filename.
        keyword:    Search term for NewsAPI (e.g. "Apple" for AAPL).
        start_date: Start date in YYYY-MM-DD format.
        end_date:   End date in YYYY-MM-DD format.
        api_key:    NewsAPI API key.
        output_dir: Directory to write the CSV. Created if it doesn't exist.

    Returns:
        Path to the written CSV file.
    """
    # --- Load FinBERT once ---
    print("Loading FinBERT model...")
    from transformers import pipeline  # imported here so the base package stays lightweight
    pipe = pipeline("text-classification", model=FINBERT_MODEL)
    print("FinBERT ready.")

    # --- Initialize NewsAPI client ---
    from newsapi import NewsApiClient
    newsapi = NewsApiClient(api_key=api_key)

    # --- Iterate day by day ---
    current = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    print(f"Generating sentiment for {ticker} ({keyword}) from {start_date} to {end_date}...")

    rows: list[dict] = []
    requests_used = 0
    kw_lower = keyword.lower()

    while current <= end:
        if requests_used >= _NEWSAPI_REQUEST_LIMIT:
            print(
                f"\nReached NewsAPI request limit ({_NEWSAPI_REQUEST_LIMIT} requests). "
                f"Stopping early — {len(rows)} days collected so far."
            )
            break

        next_day = current + timedelta(days=1)
        daily_score = 0.0
        article_count = 0

        try:
            response = newsapi.get_everything(
                q=keyword,
                from_param=current.isoformat(),
                to=next_day.isoformat(),
                language="en",
                sort_by=NEWSAPI_SORT_BY,
            )
            requests_used += 1

            articles = response.get("articles", [])

            # Filter: keyword must appear in title OR description
            articles = [
                a for a in articles
                if kw_lower in (a.get("title") or "").lower()
                or kw_lower in (a.get("description") or "").lower()
            ]

            scored: list[tuple[float, float]] = []  # (numeric_score, confidence)
            for article in articles:
                # Pick best available text, truncate to FinBERT's safe limit
                text = (
                    article.get("content")
                    or article.get("description")
                    or article.get("title")
                )
                if not text:
                    continue
                text = text[:MAX_TEXT_LENGTH]

                result = pipe(text)[0]
                label = result["label"].lower()
                confidence: float = result["score"]
                numeric_score = LABEL_MAP.get(label, 0) * confidence
                scored.append((numeric_score, confidence))

            if scored:
                weighted_sum = sum(score * conf for score, conf in scored)
                total_weight = sum(conf for _, conf in scored)
                daily_score = weighted_sum / total_weight if total_weight > 0 else 0.0
                article_count = len(scored)

        except Exception as exc:
            print(f"  {current}: ERROR — {exc}. Writing score=0.0 and continuing.")

        sign = "+" if daily_score >= 0 else ""
        print(f"{current}: score={sign}{daily_score:.2f} ({article_count} articles)")

        rows.append({
            "date": current.isoformat(),
            "sentiment_score": round(daily_score, 6),
            "article_count": article_count,
        })

        current += timedelta(days=1)

    # --- Write CSV ---
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{ticker}_sentiment.csv"

    pd.DataFrame(rows).to_csv(out_file, index=False)

    # --- Summary ---
    days_with = sum(1 for r in rows if r["article_count"] > 0)
    avg = sum(r["sentiment_score"] for r in rows) / len(rows) if rows else 0.0
    avg_sign = "+" if avg >= 0 else ""

    print(f"\nDone. {len(rows)} days processed, {days_with} with articles, "
          f"{len(rows) - days_with} with no coverage.")
    print(f"Average sentiment: {avg_sign}{avg:.2f}")
    print(f"Saved to: {out_file}")

    return out_file
