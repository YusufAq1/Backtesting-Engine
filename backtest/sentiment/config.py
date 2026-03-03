# FinBERT model identifier on Hugging Face
FINBERT_MODEL: str = "ProsusAI/finbert"

# Label-to-numeric mapping
LABEL_MAP: dict[str, int] = {"positive": 1, "neutral": 0, "negative": -1}

# NewsAPI settings
# Free tier only returns articles from the last ~30 days.
NEWSAPI_MAX_ARTICLES_PER_DAY: int = 100
NEWSAPI_SORT_BY: str = "relevancy"

# FinBERT input limit — truncate article text to this many characters
# (FinBERT's tokenizer has a 512-token limit; ~1500 chars is safe)
MAX_TEXT_LENGTH: int = 1500

# Output directory for generated CSVs
SENTIMENT_DATA_DIR: str = "sentiment_data"
