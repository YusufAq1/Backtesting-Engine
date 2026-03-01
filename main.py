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
from backtest.visualize.plots import plot_monte_carlo, plot_results


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


def _print_monte_carlo(mc: dict) -> None:
    n = mc["n_simulations"]
    sep = "=" * 52
    div = "-" * 52

    print(f"\nMonte Carlo Simulation ({n:,} runs)")
    print(sep)
    print(f"  {'':22}  {'5th %':>8}  {'Median':>8}  {'95th %':>8}")

    def fmt_return(d: dict) -> str:
        return f"{d['p5']:>+8.2f}%  {d['p50']:>+8.2f}%  {d['p95']:>+8.2f}%"

    def fmt_sharpe(d: dict) -> str:
        return f"{d['p5']:>9.3f}  {d['p50']:>8.3f}  {d['p95']:>8.3f}"

    def fmt_drawdown(d: dict) -> str:
        return f"{d['p5']:>8.2f}%  {d['p50']:>8.2f}%  {d['p95']:>8.2f}%"

    print(f"  {'Total Return':<22}  {fmt_return(mc['total_return_pct'])}")
    print(f"  {'Sharpe Ratio':<22}  {fmt_sharpe(mc['sharpe_ratio'])}")
    print(f"  {'Max Drawdown':<22}  {fmt_drawdown(mc['max_drawdown_pct'])}")
    print(div)
    print(f"  {'Probability of Loss':<22}  {mc['probability_of_loss'] * 100:>8.1f}%")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backtest against historical data.")
    parser.add_argument("--strategy", choices=["sma_crossover", "mean_reversion"],
                        default="sma_crossover")
    parser.add_argument("--ticker",   default=DEFAULT_TICKER)
    parser.add_argument("--start",    default=DEFAULT_START)
    parser.add_argument("--end",      default=DEFAULT_END)
    parser.add_argument("--capital",  type=float, default=STARTING_CAPITAL)
    parser.add_argument("--monte-carlo", action="store_true", default=False,
                        help="Run Monte Carlo simulation (bootstrap resampling) to assess strategy robustness")
    parser.add_argument("--mc-sims", type=int, default=10_000,
                        help="Number of Monte Carlo simulations (default: 10000)")
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

    if args.monte_carlo:
        from backtest.metrics.monte_carlo import run_monte_carlo
        print(f"\nRunning Monte Carlo simulation ({args.mc_sims:,} runs) ...")
        mc = run_monte_carlo(portfolio.equity_curve, n_simulations=args.mc_sims)
        _print_monte_carlo(mc)
        plot_monte_carlo(mc, metrics["total_return_pct"])
        print("Chart saved to   output/monte_carlo.png")


if __name__ == "__main__":
    main()
