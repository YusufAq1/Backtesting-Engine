import pytest

from backtest.metrics.monte_carlo import run_monte_carlo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_equity_curve(values: list[float]) -> list[dict]:
    import datetime
    return [
        {"date": datetime.date(2023, 1, i + 1), "equity": v}
        for i, v in enumerate(values)
    ]


SAMPLE_CURVE = make_equity_curve([100.0, 102.0, 101.0, 105.0, 103.0])
FLAT_CURVE   = make_equity_curve([100.0, 100.0, 100.0, 100.0, 100.0])

METRIC_KEYS     = {"p5", "p25", "p50", "p75", "p95", "mean"}
TOP_LEVEL_KEYS  = {
    "n_simulations", "total_return_pct", "sharpe_ratio",
    "max_drawdown_pct", "probability_of_loss", "all_total_returns",
}


# ---------------------------------------------------------------------------
# Test 1: Deterministic output with seed
# ---------------------------------------------------------------------------

def test_deterministic_with_seed():
    result_a = run_monte_carlo(SAMPLE_CURVE, n_simulations=100, seed=42)
    result_b = run_monte_carlo(SAMPLE_CURVE, n_simulations=100, seed=42)

    assert result_a["total_return_pct"]  == result_b["total_return_pct"]
    assert result_a["sharpe_ratio"]      == result_b["sharpe_ratio"]
    assert result_a["max_drawdown_pct"]  == result_b["max_drawdown_pct"]
    assert result_a["probability_of_loss"] == result_b["probability_of_loss"]
    assert result_a["all_total_returns"] == result_b["all_total_returns"]


# ---------------------------------------------------------------------------
# Test 2: Return structure is correct
# ---------------------------------------------------------------------------

def test_return_structure():
    result = run_monte_carlo(SAMPLE_CURVE, n_simulations=50, seed=0)

    assert set(result.keys()) == TOP_LEVEL_KEYS

    for metric in ("total_return_pct", "sharpe_ratio", "max_drawdown_pct"):
        assert set(result[metric].keys()) == METRIC_KEYS, (
            f"{metric} is missing percentile keys"
        )

    assert result["n_simulations"] == 50
    assert len(result["all_total_returns"]) == 50


# ---------------------------------------------------------------------------
# Test 3: Percentile ordering
# ---------------------------------------------------------------------------

def test_percentile_ordering():
    result = run_monte_carlo(SAMPLE_CURVE, n_simulations=500, seed=7)

    for metric in ("total_return_pct", "sharpe_ratio", "max_drawdown_pct"):
        d = result[metric]
        assert d["p5"] <= d["p25"] <= d["p50"] <= d["p75"] <= d["p95"], (
            f"Percentiles out of order for {metric}: {d}"
        )


# ---------------------------------------------------------------------------
# Test 4: Probability of loss is bounded [0, 1]
# ---------------------------------------------------------------------------

def test_probability_of_loss_bounded():
    result = run_monte_carlo(SAMPLE_CURVE, n_simulations=200, seed=1)
    assert 0.0 <= result["probability_of_loss"] <= 1.0


# ---------------------------------------------------------------------------
# Test 5: Flat equity curve → all returns 0, no loss
# ---------------------------------------------------------------------------

def test_flat_equity_curve():
    result = run_monte_carlo(FLAT_CURVE, n_simulations=100, seed=0)

    assert result["probability_of_loss"] == 0.0

    for pct_key in ("p5", "p25", "p50", "p75", "p95", "mean"):
        assert result["total_return_pct"][pct_key] == pytest.approx(0.0), (
            f"total_return_pct[{pct_key}] should be 0 for flat curve"
        )
        assert result["sharpe_ratio"][pct_key] == pytest.approx(0.0), (
            f"sharpe_ratio[{pct_key}] should be 0 for flat curve"
        )
