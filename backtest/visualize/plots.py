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
