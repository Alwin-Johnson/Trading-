# app/core/backtester.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

from app.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class PortfolioBacktester:
    def __init__(self, config: dict):
        self.config = config
        
        portfolio_rules = self.config.get("PORTFOLIO", {})
        self.initial_capital = portfolio_rules.get("reference_capital", 100000.0)
        self.risk_per_trade = portfolio_rules.get("risk_per_trade_pct", 1.0)
        
        self.all_trades = []

    def run_portfolio(self, data_dict: Dict[str, pd.DataFrame], strategy_name: str = "pullback") -> Dict[str, Any]:
        """Runs the backtest across multiple symbols using the new Risk Architecture."""
        
        # --- INPUT VALIDATION (Fixes Flaw 6) ---
        if not data_dict:
            return {"error": "Empty data dictionary provided. Backtest aborted."}
            
        logger.info(f"Starting Portfolio Backtest for {len(data_dict)} symbols using '{strategy_name}'...")
        risk_manager = RiskManager(config=self.config, strategy_name=strategy_name)

        for symbol, df in data_dict.items():
            # --- PER-SYMBOL ERROR HANDLING (Fixes Flaw 4) ---
            try:
                logger.info(f"Processing {symbol}...")
                ledger_df = risk_manager.run_backtest(df)
                
                if not ledger_df.empty:
                    ledger_df.insert(0, 'symbol', symbol)
                    
                    # --- SAFE DIVISION (Fixes Flaw 5) ---
                    # Replace 0 capital deployed with 1 to prevent infinity/NaN, though it should mathematically never be 0.
                    safe_capital = ledger_df['initial_capital_deployed'].replace(0, 1)
                    ledger_df['return_pct'] = (ledger_df['total_realized_pnl'] / safe_capital) * 100
                    
                    # Calculate broker fees and net P&L with is_true_win BEFORE converting to dict
                    broker_fee_pct = 0.002  # 0.2% round-trip fees and STT
                    ledger_df["broker_fees"] = ledger_df["initial_capital_deployed"] * broker_fee_pct
                    ledger_df["total_realized_pnl"] = ledger_df["total_realized_pnl"] - ledger_df["broker_fees"]
                    ledger_df["is_true_win"] = ledger_df["total_realized_pnl"] > 0
                    
                    # Recalculate return_pct with the updated total_realized_pnl
                    safe_capital = ledger_df['initial_capital_deployed'].replace(0, 1)
                    ledger_df['return_pct'] = (ledger_df['total_realized_pnl'] / safe_capital) * 100
                    
                    trades_list = ledger_df.to_dict(orient="records")
                    self.all_trades.extend(trades_list)
                    
            except Exception as e:
                logger.error(f"Critical failure while processing {symbol}: {e}")
                continue # Skip this symbol and keep the rest of the backtest alive

        return self._generate_tearsheet()

    def _generate_tearsheet(self) -> Dict[str, Any]:
        """Calculates institutional-grade performance metrics."""
        if not self.all_trades:
            return {"error": "No trades executed during backtest period."}

        # --- SAFE SORTING (Fixes Flaw 1) ---
        # If exit_time is None, treat it as the absolute maximum future timestamp so it sorts to the end
        self.all_trades.sort(key=lambda x: x.get("exit_time") or pd.Timestamp.max)
        trades_df = pd.DataFrame(self.all_trades)
        
        # Note: is_true_win and broker_fees are already calculated in run_portfolio() before dict conversion
        # This ensures they're available in the ALL_TRADES output

        # Reconstruct True Portfolio Equity Curve
        current_capital = self.initial_capital
        peak_capital = self.initial_capital
        max_drawdown = 0.0
        
        for index, trade in trades_df.iterrows():
            current_capital += trade.get("total_realized_pnl", 0)
            
            if current_capital > peak_capital:
                peak_capital = current_capital
                
            drawdown = (peak_capital - current_capital) / peak_capital
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                
        final_portfolio_value = current_capital
        total_return_pct = ((final_portfolio_value - self.initial_capital) / self.initial_capital) * 100

        # Recalculate return_pct on the trades_df so avg_win_pct reflects the new NET P&L
        safe_capital_df = trades_df['initial_capital_deployed'].replace(0, 1)
        trades_df['return_pct'] = (trades_df['total_realized_pnl'] / safe_capital_df) * 100

        # Core Trade Metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df["is_true_win"] == True]
        losing_trades = trades_df[trades_df["is_true_win"] == False]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win_pct = winning_trades["return_pct"].mean() if not winning_trades.empty else 0.0
        avg_loss_pct = losing_trades["return_pct"].mean() if not losing_trades.empty else 0.0
        
        # --- JSON-SAFE INFINITY (Fixes Flaw 2) ---
        if avg_loss_pct == 0:
            rr_ratio = 999.99 
        else:
            rr_ratio = abs(avg_win_pct / avg_loss_pct)

        # Time-to-Profit Analytics
        avg_bars_to_win = winning_trades["bars_held"].mean() if not winning_trades.empty else 0
        avg_bars_to_loss = losing_trades["bars_held"].mean() if not losing_trades.empty else 0

        # Grouped Analytics
        symbol_performance = trades_df.groupby("symbol").agg(
            total_trades=("symbol", "count"),
            win_rate=("is_true_win", lambda x: x.mean() * 100),
            net_profit=("total_realized_pnl", "sum")
        ).to_dict(orient="index")

        # --- CORRECT COUNT AGGREGATION (Fixes Flaws 3 & 7) ---
        # We count based on 'entry_time' since it is guaranteed to exist for every trade record
        regime_performance = trades_df.groupby("regime").agg(
            total_trades=("entry_time", "count"),
            win_rate=("is_true_win", lambda x: x.mean() * 100)
        ).to_dict(orient="index")
        
        exit_reasons = trades_df["exit_reason"].value_counts().to_dict()

        return {
            "OVERALL_SUMMARY": {
                "total_trades": total_trades,
                "win_rate_pct": round(win_rate, 2),
                "total_return_pct": round(total_return_pct, 2),
                "max_drawdown_pct": round(max_drawdown * 100, 2),
                "final_capital": round(final_portfolio_value, 2),
                "risk_reward_ratio": round(rr_ratio, 2),
                "avg_win_pct": round(avg_win_pct, 2),
                "avg_loss_pct": round(avg_loss_pct, 2),
            },
            "TIME_ANALYTICS": {
                "avg_bars_to_win": round(avg_bars_to_win, 1),
                "avg_bars_to_loss": round(avg_bars_to_loss, 1),
            },
            "EXIT_ANALYTICS": exit_reasons,
            "PER_SYMBOL": symbol_performance,
            "PER_REGIME": regime_performance,
            "ALL_TRADES": self.all_trades 
        }