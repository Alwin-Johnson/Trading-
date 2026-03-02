"""
upstox.py

Upstox broker — fully self-contained implementation.
NSE Equity only: Delivery + Intraday.
No F&O. No BSE.

All rates sourced from: upstox.com/brokerage-charges/
Effective from: 1st October 2024

Charge structure:
─────────────────────────────────────────────────────────────
BROKERAGE
  Delivery  : ₹20 per executed order (buy + sell = ₹40 total)
  Intraday  : min(₹20, 0.1% of order value) per executed order

STT (Securities Transaction Tax)
  Delivery  : 0.1% on buy value + 0.1% on sell value
  Intraday  : 0% on buy, 0.025% on sell value

EXCHANGE TRANSACTION CHARGES (NSE)
  Delivery  : 0.00297% on turnover (buy + sell)
  Intraday  : 0.00297% on turnover (buy + sell)

IPFT (Investor Protection Fund Trust) — NSE
  Delivery  : ₹0.10 per lakh of turnover = 0.0001% on turnover
  Intraday  : ₹0.10 per lakh of turnover = 0.0001% on turnover

SEBI CHARGES
  All       : ₹10 per crore of turnover = 0.00001% on turnover

STAMP DUTY
  Delivery  : 0.015% on buy value only
  Intraday  : 0.003% on buy value only

DP CHARGES (Depository Participant)
  Delivery  : ₹20 per scrip per day on sell side only
  Intraday  : ₹0

GST
  Delivery  : 18% on (brokerage + exchange + dp + ipft)
  Intraday  : 18% on (brokerage + exchange + ipft)
─────────────────────────────────────────────────────────────

Design rules:
  - Stateless: no instance state, pure calculation
  - No intermediate rounding — round only at final return
  - No prints, no logs, no DB calls
  - All rates defined as constants in this file
"""

from .base_broker import BaseBroker, TradeType, Side


# ─────────────────────────────────────────────
# CONSTANTS — All rates centralized here
# Update this section when government/exchange revises rates
# ─────────────────────────────────────────────

# Brokerage
BROKERAGE_DELIVERY_PER_ORDER = 20.0          # ₹20 flat per order
BROKERAGE_INTRADAY_CAP = 20.0                # ₹20 cap per order
BROKERAGE_INTRADAY_RATE = 0.001              # 0.1% of order value

# STT rates
STT_DELIVERY_BUY_RATE = 0.001               # 0.1% on buy value
STT_DELIVERY_SELL_RATE = 0.001              # 0.1% on sell value
STT_INTRADAY_BUY_RATE = 0.0                 # 0% on buy
STT_INTRADAY_SELL_RATE = 0.00025            # 0.025% on sell value

# Exchange transaction charges (NSE)
EXCHANGE_RATE = 0.0000297                   # 0.00297% on turnover

# IPFT charges (NSE)
IPFT_RATE = 0.000001                        # 0.0001% on turnover (₹0.10 per lakh)

# SEBI charges
SEBI_RATE = 0.0000001                       # 0.00001% on turnover (₹10 per crore)

# Stamp duty
STAMP_DELIVERY_RATE = 0.00015               # 0.015% on buy value
STAMP_INTRADAY_RATE = 0.00003              # 0.003% on buy value

# DP charges
DP_DELIVERY_CHARGE = 20.0                   # ₹20 per scrip per sell transaction
DP_INTRADAY_CHARGE = 0.0                    # No DP for intraday

# GST
GST_RATE = 0.18                             # 18%


class UpstoxBroker(BaseBroker):
    """
    Upstox broker implementation for NSE Equity.
    Supports: Delivery, Intraday.
    """

    BROKER_NAME = "Upstox"
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
        Calculate brokerage for a single order.

        Delivery : ₹20 flat per order
        Intraday : min(₹20, 0.1% of order value)
        """
        if trade_type == "delivery":
            return BROKERAGE_DELIVERY_PER_ORDER
        else:
            return min(BROKERAGE_INTRADAY_CAP, BROKERAGE_INTRADAY_RATE * order_value)

    # ─────────────────────────────────────────────
    # SECTION B — Statutory Charge Helpers
    # ─────────────────────────────────────────────

    def _calculate_stt(
        self,
        buy_value: float,
        sell_value: float,
        trade_type: TradeType,
    ) -> float:
        """
        STT on buy and/or sell depending on trade type.
        """
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
        """SEBI regulatory charges on total turnover."""
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
        """DP charges: flat per sell transaction for delivery only."""
        if trade_type == "delivery":
            return DP_DELIVERY_CHARGE
        else:
            return DP_INTRADAY_CHARGE

    def _calculate_gst(
        self,
        brokerage: float,
        exchange: float,
        dp: float,
        ipft: float,
        trade_type: TradeType,
    ) -> float:
        """
        GST = 18% on (brokerage + exchange + ipft) for intraday
        GST = 18% on (brokerage + exchange + dp + ipft) for delivery
        """
        if trade_type == "delivery":
            gst_base = brokerage + exchange + dp + ipft
        else:
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
        Statutory charges (STT, stamp, etc.) require both sides — handled at trade level.

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

        # Step 2 — Brokerage (buy order + sell order)
        buy_order = self.calculate_order_cost(buy_price, quantity, "buy", trade_type)
        sell_order = self.calculate_order_cost(sell_price, quantity, "sell", trade_type)
        brokerage = buy_order["brokerage"] + sell_order["brokerage"]
        dp = sell_order["dp"]

        # Step 3 — Statutory charges (full precision, no rounding yet)
        stt = self._calculate_stt(buy_value, sell_value, trade_type)
        exchange = self._calculate_exchange_charges(turnover)
        ipft = self._calculate_ipft(turnover)
        sebi = self._calculate_sebi(turnover)
        stamp = self._calculate_stamp_duty(buy_value, trade_type)

        # Step 4 — GST
        gst = self._calculate_gst(brokerage, exchange, dp, ipft, trade_type)

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
