"""Generate historical sentiment data for a ticker.

Usage:
    python scripts/generate_sentiment.py --ticker AAPL --keyword Apple --start 2025-01-01 --end 2025-01-31

Requires NEWS_API_KEY in .env or environment.
"""

import argparse
import os
import sys
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate daily FinBERT sentiment scores for a ticker using NewsAPI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ticker", required=True,
                        help="Stock ticker symbol (e.g. AAPL). Used for the output filename.")
    parser.add_argument("--keyword", required=True,
                        help="Search keyword for NewsAPI (e.g. 'Apple'). "
                             "Company names often work better than ticker symbols.")
    parser.add_argument("--start", required=True,
                        help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--end", required=True,
                        help="End date in YYYY-MM-DD format.")
    parser.add_argument("--output-dir", default="sentiment_data",
                        help="Directory to write the CSV (default: sentiment_data/).")
    args = parser.parse_args()

    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed; rely on environment variables

    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        print(
            "Error: NEWS_API_KEY is not set.\n"
            "Add it to a .env file in the project root:\n"
            "    NEWS_API_KEY=your_key_here\n"
            "Or export it as an environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create output directory if needed
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    from backtest.sentiment.generator import generate_sentiment_csv

    out_file = generate_sentiment_csv(
        ticker=args.ticker,
        keyword=args.keyword,
        start_date=args.start,
        end_date=args.end,
        api_key=api_key,
        output_dir=args.output_dir,
    )

    print(f"\nOutput: {out_file}")


if __name__ == "__main__":
    main()
