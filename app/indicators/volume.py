import pandas as pd

from app.indicators.utils import validate_input_dataframe, check_required_columns


# ---------------------------------------------------------------------------
# Volume utilities — intentionally functional (no class wrapper needed).
# All functions accept a DataFrame, return a Series or scalar.
# They never modify the input DataFrame.
# ---------------------------------------------------------------------------


def volume_sma(data: pd.DataFrame, period: int = 20, col: str = "volume") -> pd.Series:
    """
    Simple Moving Average of volume.

    Parameters
    ----------
    data   : pd.DataFrame — must contain `col`
    period : int          — rolling window (default: 20)
    col    : str          — volume column name (default: 'volume')

    Returns
    -------
    pd.Series — rolling SMA of volume, named 'volume_sma_{period}'
    """
    _validate(data, col)
    sma = data[col].rolling(window=period, min_periods=period).mean()
    sma.name = f"volume_sma_{period}"
    return sma


def relative_volume(
    data: pd.DataFrame,
    period: int = 20,
    col: str = "volume",
) -> pd.Series:
    """
    Relative Volume (RVOL) — current volume divided by its rolling average.

    RVOL > 1  →  above-average activity
    RVOL < 1  →  below-average activity

    Parameters
    ----------
    data   : pd.DataFrame
    period : int — look-back for average (default: 20)
    col    : str — volume column name (default: 'volume')

    Returns
    -------
    pd.Series — RVOL values, named 'rvol_{period}'
    """
    _validate(data, col)
    avg = volume_sma(data, period=period, col=col)
    rvol = data[col] / avg
    rvol.name = f"rvol_{period}"
    return rvol


def is_volume_spike(
    data: pd.DataFrame,
    period: int = 20,
    threshold: float = 2.0,
    col: str = "volume",
) -> pd.Series:
    """
    Boolean mask — True where volume exceeds `threshold` × its rolling average.

    Parameters
    ----------
    data      : pd.DataFrame
    period    : int   — look-back for average (default: 20)
    threshold : float — multiplier to define a spike (default: 2.0)
    col       : str   — volume column name (default: 'volume')

    Returns
    -------
    pd.Series[bool] — named 'volume_spike_{period}'
    """
    _validate(data, col)
    rvol = relative_volume(data, period=period, col=col)
    spike = rvol >= threshold
    spike.name = f"volume_spike_{period}"
    return spike


# ---------------------------------------------------------------------------
# Internal helper — reuses shared utils for consistency
# ---------------------------------------------------------------------------

def _validate(data: pd.DataFrame, col: str) -> None:
    validate_input_dataframe(data)
    check_required_columns(data, [col])
