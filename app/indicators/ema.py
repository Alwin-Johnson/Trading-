import pandas as pd
from app.indicators.base_indicator import BaseIndicator


class EMA(BaseIndicator):
    """
    Exponential Moving Average (EMA).

    Formula
    -------
        alpha   = 2 / (period + 1)
        EMA_t   = (Price_t * alpha) + (EMA_{t-1} * (1 - alpha))

    Parameters
    ----------
    period     : int   — look-back window (e.g. 20, 50, 200)
    source_col : str   — column to compute EMA on (default: 'close')
    """

    def __init__(self, period: int, source_col: str = "close"):
        super().__init__(period, source_col)

    @property
    def name(self) -> str:
        return f"EMA_{self.period}"

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute EMA for the given DataFrame.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain the column specified by source_col.

        Returns
        -------
        pd.Series
            EMA values aligned to data's index. Named '{name}'.
        """
        self._validate(data)

        ema = data[self.source_col].ewm(
            span=self.period,
            adjust=False,
            min_periods=self.period,
        ).mean()
        ema.name = self.name
        return ema
