# Backtesting Engine — Project Spec

## What This Is

A Python backtesting engine that simulates trading strategies against historical stock data and reports performance metrics. Feed it a strategy, a ticker, a date range, and starting capital, it runs the simulation and outputs metrics + charts.

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


## Monte Carlo Simulation (New Feature)

### What It Is

A statistical robustness test for backtested strategies. A single backtest on a single date range can be misleading — the strategy may have gotten lucky with the particular sequence of market conditions. Monte Carlo simulation answers: **"If market conditions were slightly different but still realistic, would this strategy still hold up?"**

It does this by resampling the strategy's actual daily returns in random order thousands of times, recomputing performance metrics each time, and reporting the **distribution** of outcomes instead of a single number.

### Why It Matters

- A strategy with a +5% return and a Sharpe of 0.5 could be robust (it holds up in most resampled scenarios) or fragile (it only worked because of one lucky streak). Monte Carlo tells you which.
- This is the single most impressive addition for a hiring manager reviewing the project — it shows statistical literacy and healthy skepticism of backtesting results.

### Architecture Changes

```
backtest/
├── metrics/
│   ├── performance.py          # existing — no changes
│   └── monte_carlo.py          # NEW — Monte Carlo simulation engine
├── visualize/
│   └── plots.py                # MODIFIED — add Monte Carlo distribution chart
├── tests/
│   ├── test_portfolio.py       # existing — no changes
│   ├── test_backtester.py      # existing — no changes
│   └── test_monte_carlo.py     # NEW — tests for Monte Carlo module
├── main.py                     # MODIFIED — add --monte-carlo flag
└── ...
```

### metrics/monte_carlo.py

**Function**: `run_monte_carlo(equity_curve, n_simulations, seed) -> dict`

**Inputs**:
- `equity_curve`: list of dicts with `{"date": ..., "equity": float}` — same format as `Portfolio.equity_curve`.
- `n_simulations`: int, default `10_000`. Number of resampled simulations to run.
- `seed`: optional int for reproducibility. If provided, use `np.random.default_rng(seed)`.

**Logic — step by step**:
1. Extract the equity values from `equity_curve` into a list/array.
2. Compute daily returns: `daily_returns[i] = (equity[i] - equity[i-1]) / equity[i-1]` for `i = 1..n`. This gives you a list of percentage changes — the "deck of cards."
3. For each simulation `s` in `range(n_simulations)`:
   a. **Resample with replacement**: use `rng.choice(daily_returns, size=len(daily_returns), replace=True)` to create a new shuffled sequence of returns. "With replacement" means the same daily return can appear more than once — this is standard bootstrap resampling.
   b. **Reconstruct an equity curve** from the resampled returns: start at `equity[0]`, then for each resampled return `r`, compute `equity_next = equity_prev * (1 + r)`.
   c. **Compute metrics** for this simulated equity curve:
      - `total_return_pct`: `(final - initial) / initial * 100`
      - `sharpe_ratio`: `(mean(resampled_returns) / std(resampled_returns)) * sqrt(252)`. If std is 0, Sharpe is 0.
      - `max_drawdown_pct`: largest peak-to-trough decline in the simulated curve.
   d. Store all three metrics for this simulation.
4. After all simulations complete, compute percentiles across all runs.

**Return value** — a dict with this exact structure:
```python
{
    "n_simulations": 10000,
    "total_return_pct": {
        "p5":  <float>,   # 5th percentile
        "p25": <float>,   # 25th percentile
        "p50": <float>,   # median
        "p75": <float>,   # 75th percentile
        "p95": <float>,   # 95th percentile
        "mean": <float>,
    },
    "sharpe_ratio": {
        "p5":  <float>,
        "p25": <float>,
        "p50": <float>,
        "p75": <float>,
        "p95": <float>,
        "mean": <float>,
    },
    "max_drawdown_pct": {
        "p5":  <float>,   # note: these are negative numbers; p5 is the WORST drawdown
        "p25": <float>,
        "p50": <float>,
        "p75": <float>,
        "p95": <float>,
        "mean": <float>,
    },
    "probability_of_loss": <float>,  # fraction of simulations where total_return_pct < 0
    "all_total_returns": <list[float]>,  # raw list of all 10k total returns (for histogram plotting)
}
```

**Important implementation notes**:
- Use `numpy` for all resampling and array math — do NOT use a Python for-loop over 10,000 simulations with pure Python lists. Vectorize where possible. The resampling itself must use a loop (each sim is independent), but the per-simulation equity reconstruction can use `np.cumprod`.
- Resampling is done on **daily returns**, NOT on raw equity values or prices. This preserves the statistical properties of the actual strategy performance.
- `replace=True` is critical — this is bootstrap resampling. Without replacement would just be a permutation, which doesn't let you explore the tails of the distribution properly.

### visualize/plots.py — Modifications

Add a **third chart**: `output/monte_carlo.png`

This is a **histogram** of the `all_total_returns` from the Monte Carlo result.

- X-axis: Total Return (%)
- Y-axis: Frequency (count of simulations)
- Draw a vertical dashed red line at x=0 (breakeven)
- Draw a vertical solid blue line at the actual backtest's total return
- Add a text annotation showing: "P(loss) = X%" in the top-left
- Add a text annotation showing: "Actual: +X.XX%" next to the blue line
- Title: "Monte Carlo Simulation — Distribution of Returns (N=10,000)"
- Use ~50 bins. Use a blue-ish color for the histogram bars.
- Clean and readable, consistent with the existing chart style.

### main.py — Modifications

Add a new CLI flag:
```python
parser.add_argument("--monte-carlo", action="store_true", default=False,
                    help="Run Monte Carlo simulation (10,000 resamples) to assess strategy robustness")
parser.add_argument("--mc-sims", type=int, default=10_000,
                    help="Number of Monte Carlo simulations (default: 10000)")
```

**Flow when `--monte-carlo` is passed**:
1. Run the normal backtest as before (fetch data → run strategy → compute metrics → print metrics).
2. After printing the standard metrics table, call `run_monte_carlo(portfolio.equity_curve, args.mc_sims)`.
3. Print the Monte Carlo results as a separate table below the standard metrics.
4. Save the histogram chart.

**Monte Carlo output format** (printed to stdout):
```
Monte Carlo Simulation (10,000 runs)
====================================================
                       5th %    Median    95th %
  Total Return        -3.21%    +5.12%   +14.87%
  Sharpe Ratio         -0.12      0.46      1.03
  Max Drawdown        -18.4%     -7.2%     -2.1%
----------------------------------------------------
  Probability of Loss   12.3%
====================================================

Chart saved to  output/monte_carlo.png
```

### tests/test_monte_carlo.py

**Test 1: Deterministic output with seed**
- Create a known equity curve (e.g., 5 days: [100, 102, 101, 105, 103]).
- Run `run_monte_carlo(equity_curve, n_simulations=100, seed=42)`.
- Run it again with the same seed.
- Assert all output values are identical between the two runs.

**Test 2: Return structure is correct**
- Run Monte Carlo on any equity curve.
- Assert the returned dict has all expected keys: `n_simulations`, `total_return_pct`, `sharpe_ratio`, `max_drawdown_pct`, `probability_of_loss`, `all_total_returns`.
- Assert each metric sub-dict has keys: `p5`, `p25`, `p50`, `p75`, `p95`, `mean`.
- Assert `len(result["all_total_returns"]) == n_simulations`.

**Test 3: Percentile ordering**
- For each metric, assert `p5 <= p25 <= p50 <= p75 <= p95`.
- For max drawdown (which is negative), assert `p5 <= p25 <= p50 <= p75 <= p95` still holds (p5 is most negative = worst drawdown).

**Test 4: Probability of loss is bounded**
- Assert `0.0 <= probability_of_loss <= 1.0`.

**Test 5: Flat equity curve**
- Input an equity curve that never changes: [100, 100, 100, 100, 100].
- Daily returns are all 0. Resampled returns are all 0. Total return should be 0% for every simulation.
- Assert `probability_of_loss == 0.0`, all percentiles for total return are 0.0, Sharpe is 0.0.

### Dependencies

Add `numpy` to `requirements.txt` if not already present. No other new dependencies.

### Implementation Order

1. `metrics/monte_carlo.py` — implement `run_monte_carlo()`.
2. `tests/test_monte_carlo.py` — write and run all 5 tests, make sure they pass.
3. `visualize/plots.py` — add the histogram chart function.
4. `main.py` — add `--monte-carlo` and `--mc-sims` flags, wire up the flow.
5. Run a full end-to-end test: `python main.py --strategy sma_crossover --ticker AAPL --start 2020-01-01 --end 2023-12-31 --monte-carlo`
6. Update `README.md` — add a Monte Carlo section with sample output and a screenshot of the histogram chart.