import pandas as pd
import numpy as np
from app.indicators.base_indicator import BaseIndicator


class ADX(BaseIndicator):
    """
    Average Directional Index (ADX) — Measures trend strength (not direction).
    
    ADX is calculated from the Average Directional Indicator (+DI, -DI).
    - DX = 100 * |+DI - -DI| / (+DI + -DI)
    - ADX = smoothed DX (using Wilder's smoothing)
    
    ADX > 25: Strong trend (up or down)
    ADX < 20: Weak trend / Ranging market
    ADX < 15: Very weak / No clear direction
    
    Parameters
    ----------
    period : int — DI period for calculation (typically 14)
    """
    
    def __init__(self, period: int = 14):
        super().__init__(period, source_col="close")
    
    @property
    def name(self) -> str:
        return f"ADX_{self.period}"
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute ADX using Wilder's smoothing method.
        
        Parameters
        ----------
        data : pd.DataFrame
            Must contain 'high', 'low', 'close' columns.
        
        Returns
        -------
        pd.Series
            ADX values (0-100) aligned to data's index.
        """
        self._validate(data)
        
        # Ensure required columns exist
        if 'high' not in data.columns or 'low' not in data.columns:
            raise ValueError("ADX requires 'high' and 'low' columns")
        
        high = data['high'].astype(float)
        low = data['low'].astype(float)
        close = data['close'].astype(float)
        
        # Calculate True Range
        tr = self._calculate_true_range(high, low, close)
        
        # Calculate +DM and -DM
        plus_dm, minus_dm = self._calculate_directional_movements(high, low)
        
        # Calculate +DI and -DI
        plus_di = self._calculate_di(plus_dm, tr, self.period)
        minus_di = self._calculate_di(minus_dm, tr, self.period)
        
        # Calculate DX
        di_sum = plus_di + minus_di
        dx = 100 * np.abs(plus_di - minus_di) / di_sum.replace(0, 1)  # Avoid division by zero
        
        # Smooth DX using Wilder's EMA (alpha = 1/period)
        adx = dx.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        
        # Fill NaN with 0 for initial periods
        adx = adx.fillna(0)
        adx.name = self.name
        
        return adx
    
    @staticmethod
    def _calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate True Range"""
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr
    
    @staticmethod
    def _calculate_directional_movements(high: pd.Series, low: pd.Series) -> tuple:
        """Calculate +DM and -DM"""
        up_move = high.diff()
        down_move = -low.diff()
        
        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)
        
        # +DM is positive only if up_move > 0 and up_move > down_move
        plus_dm = np.where((up_move > 0) & (up_move > down_move), up_move, 0)
        
        # -DM is positive only if down_move > 0 and down_move > up_move
        minus_dm = np.where((down_move > 0) & (down_move > up_move), down_move, 0)
        
        return pd.Series(plus_dm, index=high.index), pd.Series(minus_dm, index=high.index)
    
    @staticmethod
    def _calculate_di(dm: pd.Series, tr: pd.Series, period: int) -> pd.Series:
        """Calculate Directional Indicator (DI)"""
        # Smooth using Wilder's smoothing (alpha = 1/period)
        smoothed_dm = dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        smoothed_tr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        
        # Avoid division by zero
        di = 100 * smoothed_dm / smoothed_tr.replace(0, 1)
        
        return di
