# Backtesting Engine — Project Spec

## What This Is

A Python backtesting engine that simulates trading strategies against historical stock data and reports performance metrics. Feed it a strategy, a ticker, a date range, and starting capital — it runs the simulation and outputs metrics + charts.

## Architecture

```
backtest/
├── data/
│   └── fetcher.py
├── engine/
│   ├── backtester.py
│   ├── portfolio.py
│   └── order.py
├── strategies/
│   ├── base.py
│   ├── sma_crossover.py
│   └── mean_reversion.py
├── metrics/
│   └── performance.py
├── visualize/
│   └── plots.py
├── tests/
│   ├── test_portfolio.py
│   └── test_backtester.py
├── main.py
└── config.py
```

## Core Loop (backtester.py)

```
for each trading day in date range:
    slice history up to and including today (NEVER include future data)
    call strategy.on_data(history_slice) -> list of Orders
    portfolio executes each order at today's close price
    portfolio logs total equity for today

compute metrics from equity curve
generate plots
```

**CRITICAL: The strategy must only ever receive data up to the current simulated day. No lookahead bias. This is the #1 correctness requirement of the entire project.**

## Component Specs

### data/fetcher.py
- Use `yfinance` to download OHLCV daily data for a given ticker and date range.
- Cache downloaded data to a local CSV in a `.cache/` directory so repeated runs don't re-download.
- Return a pandas DataFrame with columns: Date, Open, High, Low, Close, Volume. Date as index.

### engine/order.py
- A dataclass with fields: `ticker: str`, `side: Literal["BUY", "SELL"]`, `quantity: int`.
- That's it. No limit orders, no stop losses, no order types. Just market orders.

### engine/portfolio.py
- Tracks: `cash: float`, `positions: dict[str, int]` (ticker -> shares), `equity_curve: list[dict]` (date + total equity).
- `execute_order(order, price, commission_pct)` — adjusts cash and positions. For BUY: cash -= price * quantity * (1 + commission_pct). For SELL: cash += price * quantity * (1 - commission_pct). Reject orders that would overdraw cash or sell shares not held.
- `get_equity(prices: dict[str, float]) -> float` — returns cash + sum of (shares * current price) for all positions.
- `log_equity(date, prices)` — appends to equity_curve.

### strategies/base.py
```python
from abc import ABC, abstractmethod
import pandas as pd
from engine.order import Order

class Strategy(ABC):
    @abstractmethod
    def on_data(self, history: pd.DataFrame) -> list[Order]:
        """
        history: OHLCV DataFrame up to and including today. Index is Date.
        Return a list of Orders to execute. Return empty list for no action.
        """
        pass
```

### strategies/sma_crossover.py
- Parameters: `short_window` (default 20), `long_window` (default 50), `ticker`, `quantity` (shares per trade, default 100).
- Logic: compute short and long SMA from Close prices. If short SMA crosses above long SMA today (was below yesterday, is above today), return BUY. If short crosses below long, return SELL (only if holding shares). If not enough data for long SMA yet, return nothing.

### strategies/mean_reversion.py
- Parameters: `lookback` (default 20), `entry_z` (default -2.0), `exit_z` (default 0.0), `ticker`, `quantity` (default 100).
- Logic: compute rolling mean and std of Close over lookback period. Compute z-score of today's close. If z < entry_z and not in position, BUY. If z > exit_z and in position, SELL.

### metrics/performance.py
- Input: equity curve (list of dicts with date and equity).
- Compute and return a dict with:
  - `total_return_pct`: (final - initial) / initial * 100
  - `annualized_return_pct`: annualized from total return using actual day count
  - `sharpe_ratio`: (mean daily return / std daily return) * sqrt(252). If std is 0, return 0.
  - `max_drawdown_pct`: largest peak-to-trough decline as a percentage
  - `total_trades`: count of all executed orders
  - `win_rate_pct`: percentage of round-trip trades (buy then sell) that were profitable. If no completed trades, return 0.
- Also compute a buy-and-hold benchmark: what if you just bought at the start and held? Report its total return for comparison.

### visualize/plots.py
- Two charts saved as PNGs (and optionally shown with plt.show()):
  1. **Equity curve**: strategy equity over time + buy-and-hold benchmark line. Title, axis labels, legend.
  2. **Drawdown chart**: percentage drawdown over time as a filled area chart.
- Use matplotlib. Keep it clean and readable, no fancy styling.

### config.py
```python
STARTING_CAPITAL = 100_000.0
COMMISSION_PCT = 0.001  # 0.1%
DEFAULT_TICKER = "SPY"
DEFAULT_START = "2018-01-01"
DEFAULT_END = "2023-12-31"
```

### main.py
- CLI using argparse with flags: `--strategy` (sma_crossover | mean_reversion), `--ticker`, `--start`, `--end`, `--capital`.
- Flow: fetch data -> instantiate strategy -> run backtester -> print metrics table to stdout -> save plots.
- Example usage: `python main.py --strategy sma_crossover --ticker AAPL --start 2020-01-01 --end 2023-12-31`

## Tests

### test_portfolio.py
- Test BUY order correctly deducts cash and adds position.
- Test SELL order correctly adds cash and removes position.
- Test commission is applied correctly.
- Test BUY rejected when insufficient cash.
- Test SELL rejected when no position held.
- Test equity calculation with mixed positions and cash.

### test_backtester.py
- Test with a trivial strategy (always buy on day 1, sell on last day) against known data to verify final equity matches manual calculation.
- Test that strategy never receives future data (pass a strategy that asserts len(history) <= expected for each day).

## Constraints & Rules
- Python 3.11+. Use type hints everywhere.
- Dependencies: pandas, yfinance, matplotlib. Nothing else.
- No classes where a function will do. Keep it simple.
- No async, no threading, no over-engineering.
- All monetary values as floats. No Decimal.
- Strategies are long-only. No short selling.
- All trades execute at the day's Close price. No intraday.
- Print metrics as a clean formatted table to stdout, not just raw dict dump.
- Include a README.md with: what the project is (2 sentences), how to install deps, how to run it with examples, sample output, and a brief note on how lookahead bias is prevented.

## Implementation Order
1. `config.py` + `order.py` (trivial, get them out of the way)
2. `fetcher.py` (get data flowing)
3. `portfolio.py` + `test_portfolio.py` (get accounting right, test it)
4. `base.py` + `sma_crossover.py` (first strategy)
5. `backtester.py` + `test_backtester.py` (wire it together, test it)
6. `performance.py` (metrics)
7. `plots.py` (visualization)
8. `main.py` (CLI entry point)
9. `mean_reversion.py` (second strategy to prove the framework generalizes)
10. `README.md`

Build each step, verify it works before moving to the next. Run tests after steps 3 and 5.