import argparse

from backtest.config import (
    COMMISSION_PCT,
    DEFAULT_END,
    DEFAULT_START,
    DEFAULT_TICKER,
    STARTING_CAPITAL,
)
from backtest.data.fetcher import fetch_data
from backtest.engine.backtester import run_backtest
from backtest.metrics.performance import compute_metrics
from backtest.visualize.plots import plot_results


def _build_strategy(name: str, ticker: str):
    if name == "sma_crossover":
        from backtest.strategies.sma_crossover import SMACrossover
        return SMACrossover(ticker=ticker)
    if name == "mean_reversion":
        from backtest.strategies.mean_reversion import MeanReversion
        return MeanReversion(ticker=ticker)
    raise ValueError(f"Unknown strategy: {name}")


def _print_metrics(metrics: dict, args: argparse.Namespace) -> None:
    sep = "=" * 52
    div = "-" * 52

    print(f"\n{sep}")
    print(f"  Strategy : {args.strategy}")
    print(f"  Ticker   : {args.ticker}")
    print(f"  Period   : {args.start}  ->  {args.end}")
    print(f"  Capital  : ${args.capital:,.2f}")
    print(sep)

    rows = [
        ("Total Return",       f"{metrics['total_return_pct']:+.2f}%"),
        ("Annualized Return",  f"{metrics['annualized_return_pct']:+.2f}%"),
        ("Sharpe Ratio",       f"{metrics['sharpe_ratio']:.3f}"),
        ("Max Drawdown",       f"{metrics['max_drawdown_pct']:.2f}%"),
        ("Total Trades",       str(metrics['total_trades'])),
        ("Win Rate",           f"{metrics['win_rate_pct']:.1f}%"),
    ]
    for label, value in rows:
        print(f"  {label:<22}  {value:>10}")

    print(div)
    print(f"  {'Buy & Hold Return':<22}  {metrics['buy_and_hold_return_pct']:>+10.2f}%")
    print(f"{sep}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backtest against historical data.")
    parser.add_argument("--strategy", choices=["sma_crossover", "mean_reversion"],
                        default="sma_crossover")
    parser.add_argument("--ticker",   default=DEFAULT_TICKER)
    parser.add_argument("--start",    default=DEFAULT_START)
    parser.add_argument("--end",      default=DEFAULT_END)
    parser.add_argument("--capital",  type=float, default=STARTING_CAPITAL)
    args = parser.parse_args()

    print(f"Fetching data for {args.ticker}  ({args.start} -> {args.end}) ...")
    data = fetch_data(args.ticker, args.start, args.end)

    strategy = _build_strategy(args.strategy, args.ticker)
    print(f"Running {args.strategy} ...")

    portfolio, total_trades, trade_log = run_backtest(
        strategy, data, args.capital, COMMISSION_PCT
    )

    metrics = compute_metrics(portfolio.equity_curve, total_trades, trade_log, data)
    _print_metrics(metrics, args)

    plot_results(portfolio.equity_curve, data, args.capital)
    print("Charts saved to  output/equity_curve.png  and  output/drawdown.png")


if __name__ == "__main__":
    main()
