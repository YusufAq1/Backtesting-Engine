# Backtesting Engine

A Python backtesting engine that simulates trading strategies against historical stock data and reports performance metrics. Feed it a strategy, a ticker, a date range, and starting capital — it runs the simulation and outputs a metrics table plus charts.

## Install

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

## Usage

```bash
python main.py --strategy <sma_crossover|mean_reversion> --ticker <TICKER> --start <YYYY-MM-DD> --end <YYYY-MM-DD> --capital <AMOUNT>
```

All flags are optional and fall back to defaults (`SPY`, `2018-01-01`, `2023-12-31`, `$100,000`).

### Examples

```bash
# SMA crossover on AAPL, 2020–2023
python main.py --strategy sma_crossover --ticker AAPL --start 2020-01-01 --end 2023-12-31

# Mean reversion on SPY with custom capital
python main.py --strategy mean_reversion --ticker SPY --start 2018-01-01 --end 2023-12-31 --capital 50000
```

## Sample Output

```
====================================================
  Strategy : sma_crossover
  Ticker   : AAPL
  Period   : 2020-01-01  ->  2023-12-31
  Capital  : $100,000.00
====================================================
  Total Return                +5.36%
  Annualized Return           +1.32%
  Sharpe Ratio                 0.488
  Max Drawdown                -4.99%
  Total Trades                    21
  Win Rate                     60.0%
----------------------------------------------------
  Buy & Hold Return          +163.19%
====================================================

Charts saved to  output/equity_curve.png  and  output/drawdown.png
```

Two PNG charts are saved to `output/`:
- `equity_curve.png` — strategy equity vs buy-and-hold benchmark over time
- `drawdown.png` — percentage drawdown from peak as a filled area chart

## Strategies

| Strategy | Description |
|---|---|
| `sma_crossover` | Buys when the short SMA crosses above the long SMA (golden cross), sells on the death cross |
| `mean_reversion` | Buys when price falls more than 2 standard deviations below its rolling mean; sells when it recovers to the mean |

## Lookahead Bias Prevention

On each simulated trading day, the strategy receives only a slice of historical data **up to and including that day** — never any future rows. This is enforced in `backtest/engine/backtester.py` with `data.iloc[:i+1]`, where `i` is the current day index. A dedicated test in `backtest/tests/test_backtester.py` asserts that `len(history) == call_count` on every single call to verify this guarantee holds.
