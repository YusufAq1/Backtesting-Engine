from dataclasses import dataclass
from typing import Literal


@dataclass
class Order:
    ticker: str
    side: Literal["BUY", "SELL"]
    quantity: int
