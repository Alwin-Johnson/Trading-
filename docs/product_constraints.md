# Product Constraints

This document defines the non-negotiable constraints for the swing trading system.
These constraints act as a contract and must not change casually.

---

## 1. Trading Scope

- Market: NSE (India)
- Trading Type: Swing trading
- Execution: Manual (no auto-trading)
- Instruments: Equities (NSE cash segment)
- No leverage: Vanilla positions only
- System is allowed to produce NO TRADE for an entire session
- Target return: 20% annually
- Maximum portfolio drawdown: 10%

---

## 2. Strategy Constraints

- Only ONE strategy is allowed in Phase 1
- Strategy logic may only:
  - Generate BUY / SELL / NO_TRADE signals
  - Provide entry price suggestions
- Strategy must NOT:
  - Decide quantity
  - Decide stop-loss or targets
  - Override risk rules

---

## 3. Risk & Capital Protection (Non-Negotiable)

- **Risk per trade: Maximum 1% of capital** (fixed)
- Risk engine has absolute veto power over all strategies
- Position sizing is always derived from risk budget, never fixed
- Stop-loss is mandatory on every trade (no exceptions)
- Portfolio drawdown limit: Maximum 10%
- Daily loss limit enforcement: Required
- Capital protection has absolute priority over profit
- Slippage and fees must be modeled in backtests

---

## 4. Data Integrity Rules

- Only CLOSED candles may be used for decisions
- Partial candles must be ignored
- If market data is missing or invalid → NO TRADE
- Candle validation rules apply (OHLC integrity, volume sanity)
- ATR-based stop-loss calculation mandatory

---

## 5. System Behavior

- Deterministic risk rules are non-negotiable
- Strategy logic may decide WHEN to trade, risk engine ALWAYS decides HOW MUCH
- ML models (when added) may only FILTER trades, not override risk limits
- Backtests must include:
  - Broker fees (0.2% round-trip)
  - Slippage modeling
  - Win rate, risk-reward ratio, max drawdown

---

## 6. Change Policy

- Parameter tuning (RSI levels, EMA periods) is allowed with backtest validation
- Risk constraint changes require explicit review
- Changes to the following are LOCKED (cannot change):
  - 1% risk-per-trade limit
  - 10% maximum drawdown tolerance
  - Stop-loss enforcement
  - Risk engine veto power
  - Manual execution assumption
  - No leverage rule
