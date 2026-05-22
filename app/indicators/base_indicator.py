from abc import ABC, abstractmethod

import pandas as pd

from app.indicators.utils import validate_input_dataframe, check_required_columns


class BaseIndicator(ABC):
    """
    Abstract base class for all technical indicators.

    All indicators must:
    - Accept a DataFrame as input
    - Return a pandas Series
    - Never modify the original DataFrame
    - Never print, log, or emit signals
    - Never access external resources

    Attributes are read-only after initialization to prevent runtime mutation bugs.
    """

    def __init__(self, period: int, source_col: str = "close"):
        if not isinstance(period, int):
            raise TypeError(f"period must be an int, got {type(period).__name__}")
        if period <= 0:
            raise ValueError(f"period must be a positive integer, got {period}")
        if not isinstance(source_col, str):
            raise TypeError(f"source_col must be a str, got {type(source_col).__name__}")

        # Stored as private — exposed via read-only properties
        self._period = period
        self._source_col = source_col

    # ------------------------------------------------------------------
    # Read-only attributes (frozen after __init__)
    # ------------------------------------------------------------------

    @property
    def period(self) -> int:
        return self._period

    @property
    def source_col(self) -> str:
        return self._source_col

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the indicator (e.g. 'EMA_20')."""
        ...

    @property
    def required_columns(self) -> list[str]:
        """Columns that must be present in the input DataFrame."""
        return [self._source_col]

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the indicator.

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV data. Must contain all columns listed in required_columns.

        Returns
        -------
        pd.Series
            Computed indicator values, aligned to the input index.
        """
        ...

    # ------------------------------------------------------------------
    # Shared validation (top-level import — no lazy import overhead)
    # ------------------------------------------------------------------

    def _validate(self, data: pd.DataFrame) -> None:
        validate_input_dataframe(data)
        check_required_columns(data, self.required_columns)
