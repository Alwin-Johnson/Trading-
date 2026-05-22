# Project Overview

This project is a disciplined, risk-first trading decision system designed for
swing trading with minimal capital risk. The core philosophy prioritizes capital
preservation and consistent, steady returns over aggressive profit-taking.

The system assists a human trader by producing structured, explainable, and
risk-managed trade plans — not by executing trades automatically.

---

## What This Project Is

- A backend-only trading decision engine
- Focus: Swing trading with strict risk discipline
- Produces structured trade outcomes:
  - BUY / SELL / NO_TRADE
  - Entry price
  - Risk-managed trade plan
- Designed for manual execution by a human trader
- Built with minimal-risk constraints:
  - Maximum 10% portfolio drawdown tolerance
  - Position sizing: Fixed 1% risk per trade
  - Stop-loss: Always defined and enforced
  - Capital protection over profit maximization

---

## What This Project Is NOT

- Not a price prediction system
- Not a high-frequency trading system
- Not leverage-based trading (vanilla cash positions only)
- Not a system for aggressive profit-seeking
- Not a fully autonomous trading bot
- Not dependent on TradingView or external charting tools

---

## Core Philosophy

- **Capital preservation is non-negotiable**
- **Minimal risk per trade (1% of capital max)**
- **No trade is a valid and often optimal outcome**
- **Steady returns beat volatile spikes**
- **Deterministic logic is preferred over black-box prediction**
- **Every trade must have a defined, enforced stop-loss**
- **Failures must be safe, explainable, and auditable**

---

## Current Focus (Phase Context)

At present, the system focuses exclusively on:

- Swing trading (minimal risk approach)
- Indian markets (NSE)
- Manual execution
- Single-strategy discipline
- Portfolio drawdown cap: 10% maximum
- Risk per trade: 1% of capital

This focus is intentional and exists to establish correctness, safety, and
operational discipline with capital preservation as the top priority.

---

## System Approach (High Level)

At a high level, the system works as follows:

1. Market data is ingested and validated
2. Indicators are computed on closed candles
3. Strategy logic evaluates potential trade setups
4. Risk rules approve, adjust, or reject trades
5. Session state is updated
6. Decisions and reasoning are communicated to the user

At any point, if conditions are unsafe or unclear, the system produces
**NO TRADE**.

---

## Intended Users

- Conservative traders prioritizing capital preservation
- Disciplined discretionary or semi-systematic traders
- Investors seeking steady, low-volatility returns
- Small teams building risk-controlled trading infrastructure
- Developers experimenting with systematic trading under strict capital constraints

This system is NOT intended for:
- Aggressive profit-seekers or leverage traders
- Unsupervised retail auto-trading
- Speculative or high-frequency trading

---

## Evolution Model

The system evolves through clearly defined phases:

- Early phases prioritize discipline, correctness, and safety
- Later phases introduce ML-based filtering and contextual awareness
- Support for additional timeframes and trading styles is added only after
  intraday behavior is stable and well understood
- Automation is optional and considered only after sustained profitability
  and drawdown control

The roadmap explicitly defines what belongs in each phase.

---

## Source of Truth

System behavior and constraints are governed by:

- `product_constraints.md`
- `architecture.md`
- `file_structure.md`
- `roadmap.md`

If ambiguity exists, these documents take precedence over code.

---

## Project Status

The current phase, progress, and next steps are tracked in:

- `current_status.md`
