from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

OUTPUT_DIR = Path("output")


def plot_results(
    equity_curve: list[dict],
    data: pd.DataFrame,
    starting_capital: float,
    output_dir: Path = OUTPUT_DIR,
    show: bool = False,
) -> None:
    """
    Save two charts to output_dir:
      1. equity_curve.png — strategy equity vs buy-and-hold benchmark
      2. drawdown.png     — percentage drawdown over time (filled area)
    """
    output_dir.mkdir(exist_ok=True)

    dates = [e["date"] for e in equity_curve]
    equities = [e["equity"] for e in equity_curve]

    # Buy-and-hold: scale starting capital by price return each day
    initial_price = float(data["Close"].iloc[0])
    bah_equities = [
        starting_capital * (float(data.at[d, "Close"]) / initial_price)
        for d in dates
    ]

    # --- Chart 1: Equity curve ---
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(dates, equities, label="Strategy", linewidth=1.5)
    ax.plot(dates, bah_equities, label="Buy & Hold", linewidth=1.5, linestyle="--")
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "equity_curve.png", dpi=150)
    if show:
        plt.show()
    plt.close(fig)

    # --- Chart 2: Drawdown ---
    equity_series = pd.Series(equities)
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max * 100

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(dates, drawdown, 0, alpha=0.4, color="red", label="Drawdown")
    ax.plot(dates, drawdown, color="red", linewidth=0.8)
    ax.set_title("Drawdown")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "drawdown.png", dpi=150)
    if show:
        plt.show()
    plt.close(fig)


def plot_monte_carlo(
    mc_result: dict,
    actual_total_return_pct: float,
    output_dir: Path = OUTPUT_DIR,
    show: bool = False,
) -> None:
    """
    Save output/monte_carlo.png — histogram of simulated total returns.

    Args:
        mc_result:               return value of run_monte_carlo()
        actual_total_return_pct: the real backtest's total return (for the blue line)
        output_dir:              directory to save the chart
        show:                    if True, call plt.show() after saving
    """
    output_dir.mkdir(exist_ok=True)

    all_returns = mc_result["all_total_returns"]
    n = mc_result["n_simulations"]
    prob_loss = mc_result["probability_of_loss"] * 100

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.hist(all_returns, bins=50, color="steelblue", edgecolor="white", linewidth=0.4)

    # Breakeven line
    ax.axvline(x=0, color="red", linestyle="--", linewidth=1.5, label="Breakeven (0%)")

    # Actual backtest return line
    sign = "+" if actual_total_return_pct >= 0 else ""
    ax.axvline(
        x=actual_total_return_pct,
        color="navy",
        linestyle="-",
        linewidth=1.5,
        label=f"Actual: {sign}{actual_total_return_pct:.2f}%",
    )

    # Annotations
    ax.text(
        0.02, 0.95,
        f"P(loss) = {prob_loss:.1f}%",
        transform=ax.transAxes,
        verticalalignment="top",
        fontsize=10,
    )

    ax.set_title(f"Monte Carlo Simulation — Distribution of Returns (N={n:,})")
    ax.set_xlabel("Total Return (%)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "monte_carlo.png", dpi=150)
    if show:
        plt.show()
    plt.close(fig)
