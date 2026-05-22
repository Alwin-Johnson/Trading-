import pandas as pd
from app.risk.position_sizer import PositionSizer
from app.risk.exit_engine import ExitEngine

class RiskManager:
    """
    The Orchestrator. 
    Connects Strategy signals to Risk math and simulates the timeline for backtesting.
    Prevents overlapping trades to simulate realistic margin constraints.
    """

    def __init__(self, config: dict, strategy_name: str = "pullback"):
        """
        Parameters
        ----------
        config : dict
            The master configuration dictionary.
        strategy_name : str
            The key used in STRATEGY_CONFIG to fetch specific rules (Fixes Flaw 7).
        """
        self.config = config
        self.strategy_name = strategy_name
        self.exit_engine = ExitEngine(config)
        
        self.portfolio_rules = config.get("PORTFOLIO", {
            "reference_capital": 100000.0,
            "risk_per_trade_pct": 1.0
        })

    def run_backtest(self, master_df: pd.DataFrame) -> pd.DataFrame:
        """Executes the trade lifecycle simulation chronologically."""
        
        # --- PRE-FLIGHT VALIDATION (Fixes Flaw 6) ---
        required_cols = ['signal', 'regime_label', 'ATR_Pct_1D_14', 'close']
        missing_cols = [col for col in required_cols if col not in master_df.columns]
        if missing_cols:
            raise ValueError(f"Data missing required columns for RiskManager: {missing_cols}")

        ledger = []
        in_trade = False
        trade_exit_time = None

        for i in range(len(master_df)):
            idx = master_df.index[i] # Safe index access (Fixes Flaw 5)
            row = master_df.iloc[i]
            
            # --- STATE CHECK (Fixes Flaw 2) ---
            if in_trade:
                if trade_exit_time is not None and idx >= trade_exit_time:
                    in_trade = False
                else:
                    continue
                    
            # --- SIGNAL DETECTION ---
            if getattr(row, 'signal', 0) == 1:
                entry_price = float(row.close)
                regime_label = str(getattr(row, 'regime_label', 'NONE'))
                
                if regime_label == "NONE":
                    continue
                
                # Safely extract regime key (Fixes Flaw 1)
                regime_parts = regime_label.split("_")
                regime_key = "_".join(regime_parts[:2]) if len(regime_parts) >= 2 else regime_label
                
                # Fetch Strategy-Specific SL multiplier dynamically (Fixes Flaw 3 & 7)
                strategy_rules = self.config.get("STRATEGY_CONFIG", {}).get(self.strategy_name, {})
                sl_mult = strategy_rules.get(regime_key, {}).get("sl_mult", 2.0)
                
                # Calculate Absolute Initial Stop Loss
                raw_atr = float(row.ATR_Pct_1D_14)
                atr_pct = raw_atr if raw_atr < 1.0 else raw_atr / 100.0
                atr_val = atr_pct * entry_price
                initial_sl = entry_price - (atr_val * sl_mult)
                
                # Sanity Check: Long-only SL must be below Entry (Fixes Flaw 4)
                if initial_sl >= entry_price:
                    continue 
                
                # Size the Position
                shares = PositionSizer.calculate_shares(
                    account_capital=self.portfolio_rules["reference_capital"],
                    risk_per_trade_pct=self.portfolio_rules["risk_per_trade_pct"],
                    entry_price=entry_price,
                    stop_loss_price=initial_sl
                )
                
                if shares <= 0:
                    continue 
                    
                future_df = master_df.iloc[i + 1:]
                if future_df.empty:
                    continue 
                
                # Execute Trade
                trade_record = self.exit_engine.simulate_trade(
                    entry_price=entry_price,
                    initial_sl=initial_sl,
                    shares=shares,
                    future_df=future_df
                )
                
                # Append Metadata
                trade_record["entry_time"] = idx
                trade_record["regime"] = regime_label
                trade_record["initial_capital_deployed"] = round(shares * entry_price, 2)
                
                ledger.append(trade_record)
                
                # Lock Engine and ensure fallback if exit_time is missing (Fixes Flaw 8)
                in_trade = True
                trade_exit_time = trade_record.get("exit_time")
                if trade_exit_time is None:
                    trade_exit_time = master_df.index[-1]
                
        # Format output
        ledger_df = pd.DataFrame(ledger)
        if not ledger_df.empty:
            cols = [
                "entry_time", "exit_time", "regime", "entry_price", "initial_sl", 
                "target_1_price", "final_exit_price", "total_shares", 
                "initial_capital_deployed", "target_1_pnl", "runner_pnl", 
                "total_realized_pnl", "bars_held", "exit_reason", "hit_target_1"
            ]
            ordered_cols = [c for c in cols if c in ledger_df.columns]
            ledger_df = ledger_df[ordered_cols]
            
        return ledger_df