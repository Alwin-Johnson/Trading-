import math

class PositionSizer:
    """
    Pure mathematical engine for calculating position sizes.
    Ensures uniform account risk across all trades for backtesting and live execution.
    """

    @staticmethod
    def calculate_shares(
        account_capital: float,
        risk_per_trade_pct: float,
        entry_price: float,
        stop_loss_price: float
    ) -> int:
        """
        Calculates the exact integer number of shares to buy.
        
        Parameters
        ----------
        account_capital : float
            Total available margin/capital in the account.
        risk_per_trade_pct : float
            Percentage of total capital to risk on this single trade (e.g., 1.0 for 1%).
        entry_price : float
            The exact price the asset will be purchased at.
        stop_loss_price : float
            The exact price where the trade will be invalidated and cut.
            
        Returns
        -------
        int
            The number of shares to purchase. Returns 0 if invalid or too risky.
        """
        
        # 1. Calculate absolute risk budget 
        risk_budget = account_capital * (risk_per_trade_pct / 100.0)

        # 2. Calculate the risk distance per single share
        risk_per_share = abs(entry_price - stop_loss_price)

        # Safety Guard: Prevent division by zero if SL accidentally equals Entry
        if risk_per_share <= 0:
            return 0

        # 3. Calculate raw share count
        raw_shares = risk_budget / risk_per_share

        # 4. NSE Equities do not allow fractional shares. We MUST round down (floor)
        # to ensure we never accidentally exceed our exact risk budget.
        shares = math.floor(raw_shares)

        # 5. Margin Check (The Buying Power Guard)
        # Prevents the math from suggesting a position size that exceeds total capital
        # just because the stop loss is extremely tight.
        total_position_cost = shares * entry_price
        
        if total_position_cost > account_capital:
            # Downgrade the share count to the absolute maximum the account can afford
            shares = math.floor(account_capital / entry_price)

        # Return the final approved share count (ensuring no negative numbers)
        return max(0, shares)