# Current Project Status

## Project Overview
A disciplined, risk-first intraday trading decision system built on industry-standard frameworks. Designed to generate structured trade signals for manual execution on NSE (Indian equities). Focus on 15-minute candle analysis with multi-timeframe trend confirmation.

---

## Core System Features (Complete)

### 1. Data Ingestion & Candle Management
- **Raw Data Sources**: Angel One, Upstox, Groww broker APIs (scaffolding in place)
- **Candle Construction**: Tick-to-15m aggregation with market-hour gating
- **Timeframe Generation**: Derives 1H and 1D candles from 15m base data
- **Data Validation**: OHLC integrity checks, volume sanity, timeframe alignment
- **Historical Support**: Fetch and cache historical candles
- **Persistence Layer**: PostgreSQL integration for trade ledger and signal history
- **Symbol Management**: Token mapping for Indian stocks

### 2. Technical Indicators (Production-Grade)

**All indicators use Wilder's exponential smoothing (RMA = EMA with α = 1/period)**

- **RSI (14-period)**: Relative Strength Index with edge-case handling
  - Properly handles: no gains, no losses, both zero scenarios
  - Output: 0–100 range, NaN for undefined states
  
- **ATR (14-period)**: Average True Range for volatility measurement
  - True Range calculation: max(H-L, |H-PC|, |L-PC|)
  - Used for: Stop-loss placement, position sizing, regime definition
  - Output: Absolute value + percentage of close
  
- **EMA (multiple periods)**: Exponential Moving Averages
  - Periods: 10, 20, 50, 100, 200 (all configurable)
  - Calculated on: 15m, 1H, 1D timeframes
  - Used for: Trend confirmation, support/resistance zones
  
- **ADX (14-period)**: Average Directional Index
  - Measures trend strength (not direction)
  - Calculation: +DI, -DI, DX smoothing via Wilder's method
  - Output: 0–100 scale (>25 = strong trend, <20 = ranging)
  - Used for: Regime filtering, trend validation
  
- **Volume Analysis**: 
  - RVOL (Relative Volume): Current volume vs 20-period SMA
  - Used for: Institutional activity confirmation
  
- **Price Action**:
  - Candle body percentage (body size vs range)
  - High/low positioning within candle range
  - Used for: Price action confirmation patterns

### 3. Multi-Timeframe Aggregator
- **Purpose**: Build 1H and 1D candles from 15m ticks, calculate indicators natively on each
- **Lookahead Bias Prevention**: All HTF data shifted by 1 period before merging to 15m
- **Master Dataset**: Single aligned DataFrame with:
  - 15m: RSI, volume, candle body %, RVOL
  - 1H: EMAs, ATR
  - 1D: EMAs, ATR, ADX
  - Market regime: Nifty 50 bullish flag (single-day lagged)
- **Performance**: Vectorized pandas operations, no loops, <1s for entire dataset

### 4. Risk Management (Professional-Grade)

**Position Sizer**
- Calculation: shares = (account_capital × risk_per_trade_%) / (entry_price - stop_loss_price)
- Safety: No fractional shares (NSE requirement), prevents over-leverage
- Input drivers: Account size, risk %, entry price, stop loss

**Exit Engine** (Hybrid Logic)
- **Stop-Loss**: Hard stop at calculated SL, no exceptions
- **Partial Take-Profit**: Exit 50% at 1.5× risk-reward ratio
- **Trailing Stop**: Move SL to breakeven (+buffer) after target 1 hit
- **Path-dependent simulation**: Steps through each candle sequentially
- **PnL Tracking**: Separates partial exit gains from runner gains
- **Exit Reasons**: STOP_LOSS, TARGET_1_PARTIAL, TARGET_2_RUNNER, TIMEOUT

**Risk Manager**
- **Signal Processing**: Reads strategy `signal` (0/1) and `regime_label`
- **SL Calculation**: entry_price - (ATR_pct × regime_multiplier)
- **Trade Ledger**: Records entry time, exit time, PnL, bars held, exit reason
- **Portfolio Rules**: Daily capital limits, risk per trade enforcement
- **Error Isolation**: Per-symbol fault handling, continues on failures

### 5. Portfolio Backtester
- **Input**: Multi-symbol dataframes with pre-calculated indicators
- **Processing**: Loops symbols → calls RiskManager → collects trades
- **Equity Curve**: Tracks capital growth/drawdown over time
- **Output Metrics**:
  - Total return %, win rate, risk-reward ratio
  - Max drawdown %, average bars held to win/loss
  - Per-symbol performance breakdown
  - Per-regime performance analysis
  - Complete trade ledger with fees
- **Fee Modeling**: 0.2% round-trip (broker + STT), deducted per trade
- **Safe Aggregation**: Handles empty trades, division by zero, infinity prevention

### 6. Configuration System
- **Portfolio Setup**: Reference capital (1 lakh+), risk per trade (1% default)
- **Exit Rules**: Partial exit % (50%), breakeven buffer (0.1%), partial RR (1.5×)
- **Broker Fees**: Flat 0.2% round-trip (configurable)
- **Regime Definition**: ATR-based thresholds (SET_1, SET_2, SET_3, SET_4)
- **Strategy Parameters**: Per-regime RSI floors, SL multipliers, EMA gaps, ADX minimums

### 7. Data Pipeline & Validation
- **Ingestion**: Tick-to-candle aggregation, timestamp alignment
- **Validation**: OHLC > 0, High ≥ Low, Close in range, Volume ≥ 0
- **Persistence**: Trade ledger, signal history, performance analytics
- **Logging**: Structured JSON events with timestamps, symbols, results

### 8. Broker Integration (Scaffolding)
- **Angel One**: API client for LTP, historical data
- **Upstox**: Fallback broker support
- **Groww**: Additional broker option
- **Factory Pattern**: Broker selection via config

### 9. Testing Infrastructure
- **test_broker.py**: Connection validation, credential handling
- **test_historical.py**: Historical candle fetching accuracy
- **test_live.py**: Live LTP streaming, real-time signals
- **Export Utils**: Trade ledger exporters for analysis and tax reporting

---

## Current Development Stage

### Strategy Exploration
- Target performance: **20% annual return** on 1 lakh capital
- Risk constraint: **<10% maximum drawdown**
- Pending decision: Multi-timeframe vs single-timeframe approach
- Researching: Optimal indicator combinations, entry/exit logic, trade frequency trade-offs

### Framework Status
- ✓ All components operational and generic (strategy-agnostic)
- ✓ Industry-standard math and practices
- ✓ Production-ready for backtesting
- ⏳ Awaiting new strategy implementation

---

## Technical Architecture

| Component | Type | Status | Generic? |
|-----------|------|--------|----------|
| IndicatorEngine | Library | ✓ Complete | ✓ Yes |
| MTFAggregator | Processor | ✓ Complete | ✓ Yes |
| RiskManager | Orchestrator | ✓ Complete | ✓ Yes |
| ExitEngine | Simulator | ✓ Complete | ✓ Yes |
| PositionSizer | Calculator | ✓ Complete | ✓ Yes |
| Backtester | Engine | ✓ Complete | ✓ Yes |
| BrokerAdapters | Connectors | ⏳ Scaffolding | ✓ Yes |
| Strategy | Logic | ⏳ TBD | ✗ Custom |
| Config | Rules | ✓ Template | ✓ Reusable |

---

## Next Immediate Steps

1. **Finalize strategy approach** (multi-TF vs single-TF)
2. **Design new strategy class** with signal generation logic
3. **Update config** with strategy-specific parameters
4. **Backtest** on 6+ months historical data
5. **Validate** against target metrics (20% return, <10% drawdown)
6. **Paper trade** before live execution
