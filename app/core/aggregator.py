import pandas as pd

from app.indicators.ema import EMA
from app.indicators.rsi import RSI
from app.indicators.atr import ATR
from app.indicators.adx import ADX
from app.indicators.price_action import candle_body_pct

class MTFAggregator:
    """
    Multi-Timeframe Aggregator.
    Synthesizes higher timeframes (1H, 1D) from raw 15m data, calculates
    all required technical indicators natively, and cleanly merges them 
    back down to the 15m timeframe without lookahead bias.
    """

    def __init__(self, raw_15m_df: pd.DataFrame, nifty_1d_df: pd.DataFrame = None):
        """
        Initializes the aggregator with the raw 15m asset data and optional Nifty 50 Daily data.
        """
        self.df_15m = raw_15m_df.copy()
        self.nifty_1d_df = nifty_1d_df.copy() if nifty_1d_df is not None else None
        
        self.df_1H = pd.DataFrame()
        self.df_1D = pd.DataFrame()

    def _scrub_data(self) -> None:
        """Prepares the 15m data by handling missing ticks."""
        self.df_15m.index = pd.to_datetime(self.df_15m.index)
        self.df_15m.sort_index(inplace=True)

        price_cols = ["open", "high", "low", "close"]
        self.df_15m[price_cols] = self.df_15m[price_cols].ffill()
        if "volume" in self.df_15m.columns:
            self.df_15m["volume"] = self.df_15m["volume"].fillna(0)

    def _build_higher_timeframes(self) -> None:
        """Resamples 15m data into 1H and 1D candles."""
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }
        
        self.df_1H = self.df_15m.resample("1h").agg(agg_dict).dropna()
        self.df_1D = self.df_15m.resample("1D").agg(agg_dict).dropna()

    def _calculate_indicators(self) -> None:
        """Applies indicators to their respective native timeframes."""
        
        # --- 1. Daily Indicators ---
        self.df_1D["ATR_1D_14"] = ATR(period=14).calculate(self.df_1D)
        self.df_1D["ATR_Pct_1D_14"] = (self.df_1D["ATR_1D_14"] / self.df_1D["close"]) * 100
        
        for period in [10, 20, 50, 100, 200]:
            self.df_1D[f"EMA_1D_{period}"] = EMA(period=period).calculate(self.df_1D)

        self.df_1D["ADX_1D_14"] = ADX(period=14).calculate(self.df_1D)

        # --- 2. Hourly Indicators ---
        self.df_1H["ATR_1H_14"] = ATR(period=14).calculate(self.df_1H)
        
        for period in [20, 50, 100, 200]:
            self.df_1H[f"EMA_1H_{period}"] = EMA(period=period).calculate(self.df_1H)

        # --- 3. 15m Indicators ---
        self.df_15m["RSI_14"] = RSI(period=14).calculate(self.df_15m)
        self.df_15m["candle_body_pct"] = candle_body_pct(self.df_15m)
        
        self.df_15m["volume_sma_20"] = self.df_15m["volume"].rolling(window=20).mean()
        self.df_15m["RVOL"] = self.df_15m["volume"] / self.df_15m["volume_sma_20"].replace(0, 1) 

    def _process_nifty(self) -> pd.DataFrame:
        """
        Calculates the Nifty 50 market regime and shifts it by 1 day 
        to mathematically prevent lookahead bias in the backtest.
        """
        if self.nifty_1d_df is None or self.nifty_1d_df.empty:
            return pd.DataFrame()

        df_nifty = self.nifty_1d_df.copy()
        df_nifty.index = pd.to_datetime(df_nifty.index)
        df_nifty.sort_index(inplace=True)

        # Calculate the 50-Day EMA for the broader market
        df_nifty["NIFTY_EMA_50"] = EMA(period=50).calculate(df_nifty)
        
        # Create the bullish flag
        df_nifty["nifty_is_bullish"] = df_nifty["close"] > df_nifty["NIFTY_EMA_50"]

        # SHIFT BY 1: Ensure today's 15m candles only see YESTERDAY'S Nifty close
        safe_nifty = df_nifty[["nifty_is_bullish"]].shift(1).dropna()
        return safe_nifty

    def generate_master_dataset(self) -> pd.DataFrame:
        """
        Executes the data pipeline and safely merges higher timeframe 
        indicators down to the 15m base timeframe without lookahead bias.
        """
        self._scrub_data()
        self._build_higher_timeframes()
        self._calculate_indicators()

        safe_df_1H = self.df_1H.shift(1).dropna(how='all')
        safe_df_1D = self.df_1D.shift(1).dropna(how='all')

        df_merged = pd.merge_asof(
            self.df_15m,
            safe_df_1H[[col for col in safe_df_1H.columns if "EMA" in col or "ATR" in col]],
            left_index=True,
            right_index=True,
            direction="backward"
        )

        df_merged = pd.merge_asof(
            df_merged,
            safe_df_1D[[col for col in safe_df_1D.columns if "EMA" in col or "ATR" in col or "ADX" in col]],
            left_index=True,
            right_index=True,
            direction="backward"
        )

        # ============================================================================
        # NEW: INJECT NIFTY 50 REGIME FILTER
        # ============================================================================
        safe_nifty = self._process_nifty()
        if not safe_nifty.empty:
            df_merged = pd.merge_asof(
                df_merged,
                safe_nifty,
                left_index=True,
                right_index=True,
                direction="backward"
            )
        else:
            # Safe fallback if Nifty data isn't provided during a test run
            df_merged["nifty_is_bullish"] = True

        # The Warmup Flag
        df_merged["warmup_complete"] = df_merged.notna().all(axis=1)

        return df_merged