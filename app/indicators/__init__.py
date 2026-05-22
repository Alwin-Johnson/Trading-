"""
indicators/
-----------
Pure computation layer — no strategy logic, no signals, no I/O.

Public API
----------
    from indicators import EMA, RSI, ATR
    from indicators.volume import volume_sma, relative_volume, is_volume_spike
    from indicators.utils  import validate_input_dataframe, handle_missing_values

Usage pattern
-------------
    ema_series = EMA(period=20).calculate(df)          # pd.Series
    rsi_series = RSI(period=14).calculate(df)          # pd.Series
    atr_series = ATR(period=14).calculate(df)          # pd.Series

    # Attach to a copy of your DataFrame in your strategy layer:
    result = df.copy()
    result["EMA_20"] = ema_series
"""

__version__ = "0.1.0"

from app.indicators.base_indicator import BaseIndicator
from app.indicators.ema            import EMA
from app.indicators.rsi            import RSI
from app.indicators.atr            import ATR
from app.indicators.volume         import volume_sma, relative_volume, is_volume_spike
from app.indicators.utils          import (
    validate_input_dataframe,
    check_required_columns,
    handle_missing_values,
    rolling_mean,
    normalize_column_names,
)

__all__ = [
    # Classes
    "BaseIndicator",
    "EMA",
    "RSI",
    "ATR",
    # Volume functions
    "volume_sma",
    "relative_volume",
    "is_volume_spike",
    # Utils
    "validate_input_dataframe",
    "check_required_columns",
    "handle_missing_values",
    "rolling_mean",
    "normalize_column_names",
]
