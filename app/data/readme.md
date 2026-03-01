

---

# 📂 `app/data` Module

## Overview

The `data` module is the **market data infrastructure layer** of the trading engine.

It is responsible for:

* Receiving live market ticks (WebSocket ingestion)
* Building deterministic OHLC candles
* Validating candles
* Persisting candles to PostgreSQL
* Logging structured system events
* Supporting historical data loading

This module contains **no trading logic**.
It only handles market data lifecycle.

---

# 🧱 Architecture Philosophy

This layer follows strict separation of concerns:

| Layer       | Responsibility            |
| ----------- | ------------------------- |
| Ingestion   | Receive raw ticks         |
| Builder     | Convert ticks → candles   |
| Validation  | Ensure candle correctness |
| Persistence | Store candles in DB       |
| Logger      | Record system events      |
| Historical  | Fetch past candles        |
| Symbols     | Maintain symbol metadata  |

Each file does one job only.

---

# 📄 Files & Responsibilities

---

## 1️⃣ `builder.py`

### Purpose

Converts live ticks into deterministic time-based candles.

### Main Class

```python
class CandleBuilder
```

### Key Methods

#### `add_tick(price, tick_time, quantity=1) -> Optional[Candle]`

* Accepts tick data
* Aggregates OHLC
* Closes candle when timeframe boundary reached
* Returns closed candle if completed

#### `_start_new_candle(...)`

* Initializes a new candle

#### `_update_candle(...)`

* Updates high, low, close, volume, trade count

#### `_close_current_candle()`

* Validates candle
* Emits closed candle
* Logs state transitions

### Guarantees

* Tick-driven closure only
* No synthetic candles
* No timer-based closing
* Strict timezone enforcement
* Out-of-order tick rejection

---

## 2️⃣ `ingestion.py`

### Purpose

Connects to Angel SmartAPI WebSocket V2 and forwards ticks to builders.

### Main Class

```python
class AngelWebSocketIngestion
```

### Key Features

* WebSocket lifecycle handling
* Tick parsing
* Symbol-token mapping
* Clean callback hook for closed candles

### Constructor Supports

```python
on_candle_closed: Optional[Callable[[Candle], None]]
```

This enables event-driven architecture:

```
Tick → Builder → Closed Candle → Callback → Persistence
```

### Important Methods

* `start()`
* `_on_open()`
* `_on_data()`
* `_on_error()`
* `_on_close()`

### NOT Responsible For

* Persistence logic
* Strategy logic
* Retry logic
* Data correction

---

## 3️⃣ `persistence.py`

### Purpose

Handles PostgreSQL storage of closed candles.

### Main Class

```python
class PostgresCandleRepository
```

### Key Methods

#### `insert_candle(candle)`

* Inserts candle into DB
* Uses `ON CONFLICT DO NOTHING`
* Rolls back on failure
* Logs success/failure

#### `close()`

* Closes DB connection safely

### Design Principles

* Never crashes trading engine
* Explicit commit control
* No trading logic
* No gap detection

---

## 4️⃣ `models.py`

### Purpose

Defines core data structures.

### Main Class

```python
class Candle
```

### Fields

* symbol
* timeframe
* open_time
* close_time
* open_price
* high_price
* low_price
* close_price
* volume
* number_of_trades
* is_closed
* mode (live / historical)

This is the canonical candle representation across the system.

---

## 5️⃣ `validation.py`

### Purpose

Ensures candle integrity before emission.

### Key Function

```python
validate_candle(candle) -> (bool, reason)
```

Validates:

* OHLC consistency
* Time boundaries
* Logical correctness

Prevents corrupt data from propagating.

---

## 6️⃣ `logger.py`

### Purpose

Structured JSON event logger.

### Main Function

```python
log(event, layer, symbol, **payload)
```

### Features

* ISO-8601 IST timestamps
* JSON output
* Never throws exception
* Non-blocking
* Layer-aware logging

### Design Principle

> Logger is a fact recorder, not a decision-maker.

---

## 7️⃣ `historical.py`

### Purpose

Handles REST-based historical candle retrieval.

### Responsibilities

* Fetch historical OHLC
* Normalize timestamps
* Prepare for backtesting or recovery

This module supports offline analysis and gap recovery.

---

## 8️⃣ `symbols.py`

### Purpose

Maintains symbol metadata and mappings.

### Responsibilities

* Exchange symbol ↔ token mapping
* Centralized symbol management

---

## 9️⃣ `output.py`

### Purpose

Reserved for future use.

Planned for:

* Export utilities
* Data streaming outputs
* Reporting utilities

---

# 🔄 Data Flow Summary

### Live Mode

```
WebSocket
   ↓
Ingestion
   ↓
CandleBuilder
   ↓
Validation
   ↓
Callback
   ↓
Persistence
```

---

### Historical Mode

```
REST Fetch
   ↓
Historical Module
   ↓
Strategy / Backtest Engine
```

---

# 📌 Design Guarantees

* Deterministic candle building
* Strict timezone handling
* No silent data correction
* Event-driven persistence
* Clean modular architecture
* Production-ready layering

---

# 🚀 Future Extensions (Planned)

* Indicator engine
* Gap detection
* Aggregation layer (5m → 15m → 1h)
* Backtesting engine
* Real-time strategy evaluation
* Risk engine
* Telegram alert system

---

# 🏁 Current System Status

The `data` module now supports:

* Live streaming
* Multi-symbol aggregation
* Database persistence
* Structured logging
* Event-driven design

This is a stable foundation for building:

* Intraday systems
* Swing systems
* Backtesting engines
* Portfolio tracking tools

---


