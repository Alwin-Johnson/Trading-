import pandas as pd
from app.indicators.base_indicator import BaseIndicator


class RSI(BaseIndicator):
    """
    Relative Strength Index (RSI) — Wilder's smoothing method.

    Formula
    -------
        delta   = price.diff()
        gain    = delta.clip(lower=0)
        loss    = (-delta).clip(lower=0)

        avg_gain  (first)  = gain[:period].mean()
        avg_gain  (rest)   = (prev_avg_gain * (period-1) + current_gain) / period
        (same for avg_loss)

        RS  = avg_gain / avg_loss
        RSI = 100 - (100 / (1 + RS))

    Parameters
    ----------
    period     : int — smoothing period (default: 14)
    source_col : str — column to compute RSI on (default: 'close')
    """

    def __init__(self, period: int = 14, source_col: str = "close"):
        super().__init__(period, source_col)

    @property
    def name(self) -> str:
        return f"RSI_{self.period}"

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute RSI using Wilder's smoothed moving average.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain the column specified by source_col.

        Returns
        -------
        pd.Series
            RSI values (0–100) aligned to data's index. Named '{name}'.
        """
        self._validate(data)

        delta = data[self.source_col].diff()

        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        # Wilder's smoothing = RMA = EMA with alpha = 1/period
        avg_gain = gain.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()

        # Mathematically correct edge-case handling:
        #   avg_loss == 0 → no losses in window  → RSI = 100 (pure uptrend)
        #   avg_gain == 0 → no gains in window   → RSI = 0   (pure downtrend)
        #   Both == 0     → flat price            → RSI = NaN (undefined)
        rs = avg_gain / avg_loss

        rsi = pd.Series(index=data.index, dtype=float)
        both_zero  = (avg_gain == 0) & (avg_loss == 0)
        loss_zero  = (avg_loss == 0) & (avg_gain != 0)
        normal     = ~both_zero & ~loss_zero

        rsi[both_zero] = float("nan")
        rsi[loss_zero] = 100.0
        rsi[normal]    = 100 - (100 / (1 + rs[normal]))

        rsi.name = self.name
        return rsi
