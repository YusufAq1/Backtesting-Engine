from dataclasses import dataclass, field

from backtest.engine.order import Order


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, int] = field(default_factory=dict)
    equity_curve: list[dict] = field(default_factory=list)

    def execute_order(self, order: Order, price: float, commission_pct: float) -> bool:
        """Execute a market order at the given price. Returns False if rejected."""
        if order.side == "BUY":
            cost = price * order.quantity * (1 + commission_pct)
            if cost > self.cash:
                return False
            self.cash -= cost
            self.positions[order.ticker] = self.positions.get(order.ticker, 0) + order.quantity
            return True

        if order.side == "SELL":
            held = self.positions.get(order.ticker, 0)
            if held < order.quantity:
                return False
            self.cash += price * order.quantity * (1 - commission_pct)
            self.positions[order.ticker] -= order.quantity
            if self.positions[order.ticker] == 0:
                del self.positions[order.ticker]
            return True

        return False

    def get_equity(self, prices: dict[str, float]) -> float:
        """Return total portfolio value: cash + market value of all positions."""
        return self.cash + sum(
            shares * prices[ticker] for ticker, shares in self.positions.items()
        )

    def log_equity(self, date, prices: dict[str, float]) -> None:
        """Append today's total equity to the equity curve."""
        self.equity_curve.append({"date": date, "equity": self.get_equity(prices)})
