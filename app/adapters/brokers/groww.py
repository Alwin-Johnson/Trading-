"""
groww.py

Groww broker — fully self-contained implementation.
NSE Equity only: Delivery + Intraday.
No F&O. No BSE.

All rates sourced from: groww.in/pricing
Verified against: groww.in/calculators/brokerage-calculator

Charge structure:
─────────────────────────────────────────────────────────────
BROKERAGE
  Delivery  : min(₹20, 0.1% of order value) per executed order
  Intraday  : min(₹20, 0.1% of order value) per executed order
  (Same rule for both segments)

STT (Securities Transaction Tax)
  Delivery  : 0.1% on buy value + 0.1% on sell value
  Intraday  : 0% on buy, 0.025% on sell value only

EXCHANGE TRANSACTION CHARGES (NSE)
  Delivery  : 0.00297% on turnover (buy + sell)
  Intraday  : 0.00297% on turnover (buy + sell)

IPFT (Investor Protection Fund Trust) — NSE
  Delivery  : 0.0001% on turnover
  Intraday  : 0.0001% on turnover

SEBI CHARGES (Official rate)
  All       : ₹10 per crore = 0.00001% on turnover

STAMP DUTY
  Delivery  : 0.015% on buy value only
  Intraday  : 0.003% on buy value only

DP CHARGES
  Delivery  : ₹18.25 base + 18% GST on DP = ₹21.535 per sell transaction
              GST on DP is calculated separately internally,
              then folded into the dp line item at return.
  Intraday  : ₹0

GST
  Base      : 18% on (brokerage + exchange + IPFT)
  DP GST    : 18% on ₹18.25 (calculated internally, included in dp line)
  Note      : SEBI and DP base are NOT part of main GST base.
              Verified against official Groww brokerage calculator.
─────────────────────────────────────────────────────────────

Design rules:
  - Stateless: no instance state, pure calculation
  - No intermediate rounding — round only at final return
  - No prints, no logs, no DB calls
  - All rates defined as constants in this file
  - dp_gst calculated internally, folded into dp line item
  - Base class return structure unchanged
"""

from .base_broker import BaseBroker, TradeType, Side


# ─────────────────────────────────────────────
# CONSTANTS — All rates centralized here
# Update this section when government/exchange revises rates
# ─────────────────────────────────────────────

# Brokerage
BROKERAGE_CAP = 20.0                        # ₹20 cap per order
BROKERAGE_RATE = 0.001                      # 0.1% of order value

# STT rates
STT_DELIVERY_BUY_RATE = 0.001              # 0.1% on buy value
STT_DELIVERY_SELL_RATE = 0.001             # 0.1% on sell value
STT_INTRADAY_BUY_RATE = 0.0               # 0% on buy
STT_INTRADAY_SELL_RATE = 0.00025          # 0.025% on sell value

# Exchange transaction charges (NSE)
EXCHANGE_RATE = 0.0000297                  # 0.00297% on turnover

# IPFT charges (NSE)
IPFT_RATE = 0.000001                       # 0.0001% on turnover

# SEBI charges (official: ₹10 per crore)
SEBI_RATE = 0.0000001                      # 0.00001% on turnover

# Stamp duty
STAMP_DELIVERY_RATE = 0.00015             # 0.015% on buy value
STAMP_INTRADAY_RATE = 0.00003            # 0.003% on buy value

# DP charges
DP_DELIVERY_BASE = 18.25                   # ₹18.25 base (before GST)
DP_INTRADAY = 0.0                          # No DP for intraday

# GST
GST_RATE = 0.18                            # 18%


class GrowwBroker(BaseBroker):
    """
    Groww broker implementation for NSE Equity.
    Supports: Delivery, Intraday.
    """

    BROKER_NAME = "Groww"
    SUPPORTED_INSTRUMENTS = ["equity"]
    SUPPORTED_TRADE_TYPES = ["delivery", "intraday"]

    # ─────────────────────────────────────────────
    # SECTION A — Brokerage Logic
    # ─────────────────────────────────────────────

    def _calculate_brokerage(
        self,
        order_value: float,
        trade_type: TradeType,
    ) -> float:
        """
        Brokerage = min(₹20, 0.1% of order value) per order.
        Same rule for both delivery and intraday.
        """
        return min(BROKERAGE_CAP, BROKERAGE_RATE * order_value)

    # ─────────────────────────────────────────────
    # SECTION B — Statutory Charge Helpers
    # ─────────────────────────────────────────────

    def _calculate_stt(
        self,
        buy_value: float,
        sell_value: float,
        trade_type: TradeType,
    ) -> float:
        """STT on buy and/or sell depending on trade type."""
        if trade_type == "delivery":
            return (STT_DELIVERY_BUY_RATE * buy_value) + (STT_DELIVERY_SELL_RATE * sell_value)
        else:
            return STT_INTRADAY_SELL_RATE * sell_value

    def _calculate_exchange_charges(self, turnover: float) -> float:
        """NSE transaction charges on total turnover."""
        return EXCHANGE_RATE * turnover

    def _calculate_ipft(self, turnover: float) -> float:
        """IPFT charges on total turnover."""
        return IPFT_RATE * turnover

    def _calculate_sebi(self, turnover: float) -> float:
        """SEBI regulatory charges on turnover. Official rate: ₹10/crore."""
        return SEBI_RATE * turnover

    def _calculate_stamp_duty(
        self,
        buy_value: float,
        trade_type: TradeType,
    ) -> float:
        """Stamp duty on buy value only."""
        if trade_type == "delivery":
            return STAMP_DELIVERY_RATE * buy_value
        else:
            return STAMP_INTRADAY_RATE * buy_value

    def _calculate_dp(self, trade_type: TradeType) -> float:
        """
        DP charge for delivery sell transactions.
        Base = ₹18.25, GST on DP = 18% × 18.25 = ₹3.285
        Total dp returned = ₹18.25 + ₹3.285 = ₹21.535

        dp_gst is calculated internally and folded into dp.
        Base class return structure is unchanged.
        """
        if trade_type == "delivery":
            dp_gst = DP_DELIVERY_BASE * GST_RATE
            return DP_DELIVERY_BASE + dp_gst
        else:
            return DP_INTRADAY

    def _calculate_gst(
        self,
        brokerage: float,
        exchange: float,
        ipft: float,
    ) -> float:
        """
        GST = 18% on (brokerage + exchange + IPFT).
        SEBI and DP are excluded from this GST base.
        DP has its own GST handled internally in _calculate_dp().
        Verified against Groww's official brokerage calculator.
        """
        gst_base = brokerage + exchange + ipft
        return GST_RATE * gst_base

    # ─────────────────────────────────────────────
    # SECTION C — Order-Level Cost
    # ─────────────────────────────────────────────

    def calculate_order_cost(
        self,
        price: float,
        quantity: int,
        side: Side,
        trade_type: TradeType,
    ) -> dict:
        """
        Cost breakdown for a single order (buy or sell).
        Computes brokerage and DP only.
        Statutory charges require both sides — handled at trade level.

        Returns:
            {
                "order_value": float,
                "brokerage":   float,
                "dp":          float,
            }
        """
        order_value = price * quantity
        brokerage = self._calculate_brokerage(order_value, trade_type)
        dp = self._calculate_dp(trade_type) if side == "sell" else 0.0

        return {
            "order_value": order_value,
            "brokerage": brokerage,
            "dp": dp,
        }

    # ─────────────────────────────────────────────
    # SECTION D — Trade-Level Cost (Full Breakdown)
    # ─────────────────────────────────────────────

    def calculate_trade_cost(
        self,
        buy_price: float,
        sell_price: float,
        quantity: int,
        trade_type: TradeType,
    ) -> dict:
        """
        Full cost breakdown for a complete round-trip trade.

        Args:
            buy_price:  Price at which stock was bought
            sell_price: Price at which stock was sold
            quantity:   Number of shares
            trade_type: "delivery" or "intraday"

        Returns:
            Complete structured breakdown dict.
        """
        # Step 1 — Order values and turnover
        buy_value = buy_price * quantity
        sell_value = sell_price * quantity
        turnover = buy_value + sell_value
        gross_profit = sell_value - buy_value

        # Step 2 — Brokerage (buy order + sell order) and DP
        buy_order = self.calculate_order_cost(buy_price, quantity, "buy", trade_type)
        sell_order = self.calculate_order_cost(sell_price, quantity, "sell", trade_type)
        brokerage = buy_order["brokerage"] + sell_order["brokerage"]
        dp = sell_order["dp"]  # includes dp_gst internally for delivery

        # Step 3 — Statutory charges (full precision, no rounding yet)
        stt = self._calculate_stt(buy_value, sell_value, trade_type)
        exchange = self._calculate_exchange_charges(turnover)
        ipft = self._calculate_ipft(turnover)
        sebi = self._calculate_sebi(turnover)
        stamp = self._calculate_stamp_duty(buy_value, trade_type)

        # Step 4 — GST (on brokerage + exchange + ipft only)
        gst = self._calculate_gst(brokerage, exchange, ipft)

        # Step 5 — Totals
        total_charges = brokerage + stt + exchange + ipft + sebi + stamp + dp + gst
        net_profit = gross_profit - total_charges

        # Step 6 — Round only at return
        return {
            "buy_value":     round(buy_value, 2),
            "sell_value":    round(sell_value, 2),
            "turnover":      round(turnover, 2),
            "gross_profit":  round(gross_profit, 2),
            "brokerage":     round(brokerage, 2),
            "stt":           round(stt, 2),
            "exchange":      round(exchange, 2),
            "ipft":          round(ipft, 2),
            "sebi":          round(sebi, 2),
            "stamp":         round(stamp, 2),
            "dp":            round(dp, 2),
            "gst":           round(gst, 2),
            "total_charges": round(total_charges, 2),
            "net_profit":    round(net_profit, 2),
        }