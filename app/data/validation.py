from typing import Tuple, Optional
from datetime import time, timedelta, datetime
from zoneinfo import ZoneInfo
import math

from app.data.models import Candle


# ============================================================
# Phase-1 CONSTANTS (LOCKED)
# ============================================================

MARKET_START = time(9, 15)
MARKET_END = time(15, 30)

ALLOWED_TIMEFRAMES = {
    "ONE_MINUTE": timedelta(minutes=1),
    "THREE_MINUTE": timedelta(minutes=3),
    "FIVE_MINUTE": timedelta(minutes=5),
    "TEN_MINUTE": timedelta(minutes=10),
    "FIFTEEN_MINUTE": timedelta(minutes=15),
    "THIRTY_MINUTE": timedelta(minutes=30),
    "ONE_HOUR": timedelta(hours=1),
    "ONE_DAY": timedelta(days=1),
}

MIN_VOLUME = 1
MIN_N0_OF_TRADES = 1

FUTURE_TIME_TOLERANCE_SECONDS = 60
EPOCH_CUTOFF = datetime(1980, 1, 1, tzinfo=ZoneInfo("Asia/Kolkata"))

IST = ZoneInfo("Asia/Kolkata")


# ============================================================
# Phase-1 Candle Validation
# ============================================================

def validate_candle(candle: Candle) -> Tuple[bool, Optional[str]]:
    """
    Phase-1 validation for closed market candles.
    Answers ONLY:
    'Is this candle REAL and structurally correct?'
    """

    # --------------------------------------------------------
    # 1️⃣ Candle Finality
    # --------------------------------------------------------
    if not candle.is_closed:
        return False, "CANDLE_NOT_CLOSED"

    # --------------------------------------------------------
    # 2️⃣ Timeframe Validity
    # --------------------------------------------------------
    if candle.timeframe not in ALLOWED_TIMEFRAMES:
        return False, "UNSUPPORTED_TIMEFRAME"

    expected_duration = ALLOWED_TIMEFRAMES[candle.timeframe]

    # --------------------------------------------------------
    # 3️⃣ Timestamp Sanity (Angel-safe)
    # --------------------------------------------------------
    if not isinstance(candle.open_time, datetime) or not isinstance(candle.close_time, datetime):
        return False, "TIMESTAMP_CORRUPT"

    if candle.open_time.tzinfo is None or candle.close_time.tzinfo is None:
        return False, "TIMESTAMP_NO_TIMEZONE"

    if candle.open_time < EPOCH_CUTOFF or candle.close_time < EPOCH_CUTOFF:
        return False, "TIMESTAMP_CORRUPT"

    ist_now = datetime.now(IST)
    if candle.open_time > ist_now + timedelta(seconds=FUTURE_TIME_TOLERANCE_SECONDS):
        return False, "TIMESTAMP_IN_FUTURE"

    # --------------------------------------------------------
    # 4️⃣ Time Integrity
    # --------------------------------------------------------
    if candle.open_time >= candle.close_time:
        return False, "INVALID_TIME_RANGE"

    if (candle.close_time - candle.open_time) != expected_duration:
        return False, "TIMEFRAME_MISMATCH"

    # Market hours rule (skip for historical data, only enforce for live)
    # Historical data from Angel API may include candles slightly outside hours
    if candle.mode != "historical":
        if candle.close_time.time() > MARKET_END:
            return False, "MARKET_HOURS_VIOLATION"
        
        if candle.open_time.time() < MARKET_START and candle.close_time.time() <= MARKET_START:
            return False, "MARKET_HOURS_VIOLATION"
    # --------------------------------------------------------
    # 5️⃣ Price Type + Positivity
    # --------------------------------------------------------
    prices = [
        candle.open_price,
        candle.high_price,
        candle.low_price,
        candle.close_price,
    ]

    for price in prices:
        if not isinstance(price, (int, float)):
            return False, "PRICE_NOT_NUMERIC"
        if price <= 0:
            return False, "NON_POSITIVE_PRICE"

    # --------------------------------------------------------
    # 6️⃣ OHLC Structural Consistency
    # --------------------------------------------------------
    if candle.high_price < candle.low_price:
        return False, "INVALID_OHLC"

    if candle.high_price < candle.open_price:
        return False, "INVALID_OHLC"

    if candle.high_price < candle.close_price:
        return False, "INVALID_OHLC"

    if candle.low_price > candle.open_price:
        return False, "INVALID_OHLC"

    if candle.low_price > candle.close_price:
        return False, "INVALID_OHLC"

    # --------------------------------------------------------
    # 7️⃣ Activity Existence & Completeness
    # --------------------------------------------------------
    if not isinstance(candle.volume, (int, float)):
        return False, "VOLUME_NOT_NUMERIC"

    if candle.volume != int(candle.volume):
        return False, "VOLUME_NOT_INTEGER"

    # if int(candle.volume) < MIN_VOLUME:
    #     return False, "VOLUME_ZERO"

    if not isinstance(candle.number_of_trades, int):
        return False, "NO_OF_TRADES_NOT_INTEGER"

    # if candle.mode=="live":
    #     if candle.number_of_trades <= 0 or candle.number_of_trades < MIN_N0_OF_TRADES:
    #         return False, "NO_OF_TRADES_ZERO or BELOW MINIMUM"


    # --------------------------------------------------------
    # ✅ PASSED ALL PHASE-1 CHECKS
    # --------------------------------------------------------
    return True, None


# ============================================================
# 🚫 NOT PART OF PHASE-1 (DOCUMENTATION ONLY)
# ============================================================
#
# Phase-2 (Stability / Control):
# - Relative volume checks
# - Volume spike detection
# - Candle range % limits
# - Flash spike detection
# - Circuit breaker inference
# - Gap severity analysis
#
# Phase-3 (Intelligence / ML):
# - ATR-based volatility regimes
# - Index correlation (NIFTY shock)
# - Time-of-day performance modeling
#
# Phase-4 (Context / News):
# - RBI / CPI / earnings awareness
#
# RULE:
# Phase-1 = REAL
# Phase-2 = STABLE
# Phase-3 = MEANING
#
# ============================================================
