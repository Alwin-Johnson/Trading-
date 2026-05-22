import numpy as np
import pandas as pd
from app.indicators.utils import validate_input_dataframe, check_required_columns

# ---------------------------------------------------------------------------
# Price Action utilities — functional design.
# These functions calculate structural characteristics of the candles.
# They never modify the input DataFrame.
# ---------------------------------------------------------------------------

def candle_body_pct(data: pd.DataFrame) -> pd.Series:
    """
    Calculates the absolute percentage size of the candle body (Open to Close).
    Used to filter out low-conviction Doji candles and bid-ask noise.

    Formula: (|Close - Open| / Open) * 100

    Parameters
    ----------
    data : pd.DataFrame
        Must contain 'open', 'close' columns.

    Returns
    -------
    pd.Series
        Body size as a percentage, named 'candle_body_pct'.
    """
    validate_input_dataframe(data)
    check_required_columns(data, ["open", "close"])

    # Extract to pure numpy arrays for maximum performance
    # Extract to pure numpy arrays for maximum performance
    open_price  = data["open"].to_numpy(dtype=float)
    close_price = data["close"].to_numpy(dtype=float)

    # Calculate absolute body size
    body_size = np.abs(close_price - open_price)

    # Temporarily silence Numpy's zero-division warning, because we 
    # explicitly handle it safely using np.where right below it.
    with np.errstate(divide='ignore', invalid='ignore'):
        body_pct = np.where(
            open_price > 0,
            (body_size / open_price) * 100,
            0.0
        )

    result = pd.Series(body_pct, index=data.index, name="candle_body_pct")
    return result


def consolidation_range(data: pd.DataFrame, period: int = 6) -> pd.Series:
    """
    Calculates the percentage width of the price range over a rolling window.
    Formula: (Rolling Max High - Rolling Min Low) / Rolling Min Low

    Useful for identifying tight volatility compression (boxes) before breakouts.

    Parameters
    ----------
    data   : pd.DataFrame
        Must contain 'high', 'low' columns.
    period : int
        Rolling window size for the consolidation box (default: 6).

    Returns
    -------
    pd.Series
        Decimal representation of the box width (e.g., 0.02 = 2% wide box).
        Named 'consolidation_range_{period}'.
    """
    validate_input_dataframe(data)
    check_required_columns(data, ["high", "low"])

    # Find the absolute highest and lowest points of the rolling window
    rolling_high = data["high"].rolling(window=period, min_periods=period).max()
    rolling_low  = data["low"].rolling(window=period, min_periods=period).min()

    # Calculate the percentage distance between the ceiling and the floor
    # Edge case: use np.where to avoid division by zero when rolling_low ≈ 0
    box_range = np.where(
        rolling_low > 0,
        (rolling_high - rolling_low) / rolling_low,
        np.nan
    )
    box_range = pd.Series(box_range, index=data.index)

    box_range.name = f"consolidation_range_{period}"
    return box_range