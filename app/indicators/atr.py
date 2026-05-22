import numpy as np
import pandas as pd
from app.indicators.base_indicator import BaseIndicator


class ATR(BaseIndicator):
    """
    Average True Range (ATR).

    True Range (TR) = max of:
        1. High - Low
        2. |High - Previous Close|
        3. |Low  - Previous Close|

    ATR = Wilder's Moving Average (RMA) of TR over `period` bars.

    Useful for:
        - Volatility measurement
        - Stop-loss placement
        - Position sizing

    Parameters
    ----------
    period : int — smoothing window (default: 14)
    """

    def __init__(self, period: int = 14):
        # ATR uses high/low/close — source_col is overridden via required_columns
        super().__init__(period, source_col="close")

    @property
    def name(self) -> str:
        return f"ATR_{self.period}"

    @property
    def required_columns(self) -> list[str]:
        return ["high", "low", "close"]

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute ATR.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain 'high', 'low', 'close' columns.

        Returns
        -------
        pd.Series
            ATR values aligned to data's index. Named 'ATR_{period}'.
        """
        self._validate(data)

        high       = data["high"].to_numpy()
        low        = data["low"].to_numpy()
        close      = data["close"].to_numpy()
        prev_close = np.empty_like(close)
        prev_close[0]  = np.nan
        prev_close[1:] = close[:-1]

        # True Range — three components, no extra DataFrame allocation
        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - prev_close),
                np.abs(low  - prev_close),
            ),
        )

        tr_series = pd.Series(tr, index=data.index)

        # Wilder's RMA
        atr = tr_series.ewm(
            alpha=1 / self.period,
            min_periods=self.period,
            adjust=False,
        ).mean()
        atr.name = self.name
        return atr
