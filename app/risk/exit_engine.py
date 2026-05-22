import pandas as pd
import math

class ExitEngine:
    """
    Simulates the lifecycle of a trade for backtesting.
    Fully validates inputs, tracks separated PnL metrics, and safely executes Hybrid Exits.
    """

    def __init__(self, config: dict):
        # Safely extract rules with fallbacks to prevent missing config crashes (Flaw 4)
        self.rules = config.get("STRATEGY_CONFIG", {}).get("global", {}).get("exit", {})
        
    def simulate_trade(self, entry_price: float, initial_sl: float, shares: int, future_df: pd.DataFrame) -> dict:
        """
        Steps through future market data to execute complex exit logic.
        """
        # --- DATA SAFETY CHECKS (Flaw 5) ---
        if future_df.empty or "ATR_Pct_1D_14" not in future_df.columns:
            return self._generate_error_record(entry_price, initial_sl, shares, "INVALID_DATA")

        # --- INITIALIZATION ---
        risk_per_share = entry_price - initial_sl
        target_1_rr = max(0.1, self.rules.get("partial_exit_1_rr", 1.5)) # Prevent negative RR
        target_1_price = entry_price + (risk_per_share * target_1_rr)
        
        shares_remaining = shares
        current_sl = initial_sl
        
        target_1_hit = False
        bars_held = 0
        
        # PnL Tracking (Flaw 2)
        target_1_pnl = 0.0
        runner_pnl = 0.0
        
        # Exit Data (Flaw 6)
        final_exit_price = None
        exit_time = None
        exit_reason = "OPEN"
        
        be_buffer = entry_price * self.rules.get("breakeven_buffer_pct", 0.001)

        # --- PATH-DEPENDENT SIMULATION ---
        for row in future_df.itertuples():
            bars_held += 1
            current_close = float(row.close)
            current_high = float(row.high)
            current_low = float(row.low)
            
            # ATR Safety (Flaw 1): Ensure it's treated correctly whether 2.0 or 0.02
            raw_atr = float(row.ATR_Pct_1D_14)
            atr_pct = raw_atr if raw_atr < 1.0 else raw_atr / 100.0
            current_atr_val = atr_pct * current_close 
            
            # RULE A: CHECK HARD/TRAILING STOP LOSS
            if current_low <= current_sl:
                final_exit_price = current_sl
                runner_loss = (final_exit_price - entry_price) * shares_remaining
                runner_pnl += runner_loss
                
                shares_remaining = 0
                exit_time = getattr(row, 'Index', None)
                exit_reason = "STOP_LOSS" if not target_1_hit else "TRAILING_STOP_HIT"
                break

            # RULE B: CHECK TARGET 1 (PARTIAL EXIT)
            if not target_1_hit and current_high >= target_1_price:
                partial_pct = min(1.0, max(0.1, self.rules.get("partial_exit_percent", 0.5)))
                
                # FIX 3: Only split if we have 2 or more shares. Otherwise, let the single share ride.
                shares_to_sell = math.floor(shares * partial_pct) if shares >= 2 else 0
                
                target_1_pnl = (target_1_price - entry_price) * shares_to_sell
                shares_remaining -= shares_to_sell
                target_1_hit = True
                
                if self.rules.get("move_to_breakeven", True):
                    current_sl = entry_price + be_buffer

            # RULE C: TRAILING ATR STOP
            if target_1_hit and self.rules.get("use_trailing_atr", True):
                trail_mult = max(0.5, self.rules.get("atr_trailing_mult", 2.0))
                dynamic_trail_price = current_close - (current_atr_val * trail_mult)
                current_sl = max(current_sl, dynamic_trail_price)

            # RULE D: SMART TIME STOP
            # Config: max_candles = hours. Data: bars_held = 15-minute candles
            # Convert: 1 hour = 4 candles of 15 minutes. So divide bars_held by 4.
            max_hours = self.rules.get("adaptive_time_stop", {}).get("max_candles", 40)
            hours_held = bars_held / 4.0  # Convert 15-min candles to hours
            
            # ONLY apply time stop if Target 1 hasn't been hit. 
            if not target_1_hit and hours_held >= max_hours:
                # FIX 4: Remove the price check. If the time limit is hit, kill the trade 
                # at current market price to free up capital from dead markets.
                final_exit_price = current_close
                runner_pnl += (final_exit_price - entry_price) * shares_remaining
                
                shares_remaining = 0
                exit_time = getattr(row, 'Index', None)
                exit_reason = "TIME_STOP_FLAT"
                break

        # EDGE CASE: Data ends before trade closes
        if shares_remaining > 0:
            final_exit_price = float(future_df.iloc[-1].close)
            runner_pnl += (final_exit_price - entry_price) * shares_remaining
            exit_time = future_df.index[-1]
            exit_reason = "DATA_END_FORCE_CLOSE"

        # --- PACKAGE RECORD (Flaws 2 & 6 Fix) ---
        return {
            "entry_price": round(entry_price, 2),
            "initial_sl": round(initial_sl, 2),
            "target_1_price": round(target_1_price, 2),
            "final_exit_price": round(final_exit_price, 2) if final_exit_price else None,
            "total_shares": shares,
            "exit_time": exit_time,
            "target_1_pnl": round(target_1_pnl, 2),
            "runner_pnl": round(runner_pnl, 2),
            "total_realized_pnl": round(target_1_pnl + runner_pnl, 2),
            "exit_reason": exit_reason,
            "bars_held": bars_held,
            "hit_target_1": target_1_hit
        }
        
    def _generate_error_record(self, entry_price: float, initial_sl: float, shares: int, reason: str) -> dict:
        """Fallback empty record for invalid data."""
        return {
            "entry_price": entry_price, "initial_sl": initial_sl, "target_1_price": 0.0,
            "final_exit_price": 0.0, "total_shares": shares, "exit_time": None,
            "target_1_pnl": 0.0, "runner_pnl": 0.0, "total_realized_pnl": 0.0,
            "exit_reason": reason, "bars_held": 0, "hit_target_1": False
        }