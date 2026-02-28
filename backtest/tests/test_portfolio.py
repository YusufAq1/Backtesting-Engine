import pytest

from backtest.engine.order import Order
from backtest.engine.portfolio import Portfolio


def make_portfolio(cash: float = 100_000.0) -> Portfolio:
    return Portfolio(cash=cash)


# --- BUY ---

def test_buy_deducts_cash_and_adds_position():
    p = make_portfolio()
    order = Order("SPY", "BUY", 100)
    accepted = p.execute_order(order, price=400.0, commission_pct=0.0)

    assert accepted is True
    assert p.cash == 100_000.0 - 400.0 * 100
    assert p.positions["SPY"] == 100


def test_buy_applies_commission():
    p = make_portfolio()
    order = Order("SPY", "BUY", 10)
    p.execute_order(order, price=100.0, commission_pct=0.001)

    # cost = 100 * 10 * 1.001 = 1001.0
    assert p.cash == pytest.approx(100_000.0 - 1001.0)


def test_buy_rejected_when_insufficient_cash():
    p = make_portfolio(cash=500.0)
    order = Order("SPY", "BUY", 100)
    accepted = p.execute_order(order, price=400.0, commission_pct=0.0)

    assert accepted is False
    assert p.cash == 500.0          # cash unchanged
    assert "SPY" not in p.positions  # no position opened


# --- SELL ---

def test_sell_adds_cash_and_removes_position():
    p = make_portfolio()
    p.execute_order(Order("SPY", "BUY", 100), price=400.0, commission_pct=0.0)
    accepted = p.execute_order(Order("SPY", "SELL", 100), price=420.0, commission_pct=0.0)

    assert accepted is True
    assert p.cash == pytest.approx(100_000.0 - 40_000.0 + 42_000.0)
    assert "SPY" not in p.positions  # fully closed


def test_sell_applies_commission():
    p = make_portfolio()
    p.execute_order(Order("SPY", "BUY", 10), price=100.0, commission_pct=0.0)
    p.execute_order(Order("SPY", "SELL", 10), price=100.0, commission_pct=0.001)

    # buy cost = 1000, sell proceeds = 1000 * 0.999 = 999
    expected_cash = 100_000.0 - 1000.0 + 999.0
    assert p.cash == pytest.approx(expected_cash)


def test_sell_rejected_when_no_position():
    p = make_portfolio()
    accepted = p.execute_order(Order("SPY", "SELL", 100), price=400.0, commission_pct=0.0)

    assert accepted is False
    assert p.cash == 100_000.0


def test_sell_rejected_when_insufficient_shares():
    p = make_portfolio()
    p.execute_order(Order("SPY", "BUY", 50), price=100.0, commission_pct=0.0)
    accepted = p.execute_order(Order("SPY", "SELL", 100), price=100.0, commission_pct=0.0)

    assert accepted is False
    assert p.positions["SPY"] == 50  # unchanged


# --- EQUITY ---

def test_get_equity_cash_only():
    p = make_portfolio(cash=50_000.0)
    assert p.get_equity({}) == 50_000.0


def test_get_equity_mixed_positions_and_cash():
    p = make_portfolio(cash=10_000.0)
    p.positions["SPY"] = 100
    p.positions["AAPL"] = 50
    equity = p.get_equity({"SPY": 400.0, "AAPL": 180.0})

    # 10000 + 100*400 + 50*180 = 10000 + 40000 + 9000 = 59000
    assert equity == pytest.approx(59_000.0)


def test_log_equity_appends_to_curve():
    from datetime import date
    p = make_portfolio(cash=100_000.0)
    p.log_equity(date(2023, 1, 3), {})
    p.log_equity(date(2023, 1, 4), {})

    assert len(p.equity_curve) == 2
    assert p.equity_curve[0] == {"date": date(2023, 1, 3), "equity": 100_000.0}
    assert p.equity_curve[1] == {"date": date(2023, 1, 4), "equity": 100_000.0}
