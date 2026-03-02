"""
base_broker.py

Defines the contract every broker must implement.
No logic. No constants. No calculations.
Only interface definition.
"""

from abc import ABC, abstractmethod
from typing import Literal


TradeType = Literal["delivery", "intraday"]
Side = Literal["buy", "sell"]


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.

    Every broker must implement:
        - calculate_order_cost()
        - calculate_trade_cost()

    Expected return structure for calculate_trade_cost():
    {
        "buy_value":      float,   # buy_price × quantity
        "sell_value":     float,   # sell_price × quantity
        "turnover":       float,   # buy_value + sell_value
        "gross_profit":   float,   # sell_value - buy_value
        "brokerage":      float,   # total brokerage (buy + sell orders)
        "stt":            float,   # securities transaction tax
        "exchange":       float,   # NSE transaction charges
        "ipft":           float,   # investor protection fund trust
        "sebi":           float,   # SEBI regulatory charges
        "stamp":          float,   # stamp duty
        "dp":             float,   # depository participant charges
        "gst":            float,   # GST on applicable components
        "total_charges":  float,   # sum of all charges
        "net_profit":     float,   # gross_profit - total_charges
    }
    """

    @abstractmethod
    def calculate_order_cost(
        self,
        price: float,
        quantity: int,
        side: Side,
        trade_type: TradeType,
    ) -> dict:
        """
        Calculate costs for a single order (buy or sell).

        Args:
            price:      Execution price per share
            quantity:   Number of shares
            side:       "buy" or "sell"
            trade_type: "delivery" or "intraday"

        Returns:
            dict with brokerage and dp for this order side.
        """
        pass

    @abstractmethod
    def calculate_trade_cost(
        self,
        buy_price: float,
        sell_price: float,
        quantity: int,
        trade_type: TradeType,
    ) -> dict:
        """
        Calculate full cost breakdown for a complete trade (buy + sell).

        Args:
            buy_price:  Price at which shares were bought
            sell_price: Price at which shares were sold
            quantity:   Number of shares traded
            trade_type: "delivery" or "intraday"

        Returns:
            Full structured breakdown dict (see class docstring).
        """
        pass
