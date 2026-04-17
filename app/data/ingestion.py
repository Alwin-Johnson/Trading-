"""
ingestion.py

Phase-1 Market Data Ingestion (Angel SmartAPI V2)

Responsibilities:
- Connect to Angel SmartAPI WebSocket V2
- Receive raw tick messages
- Parse minimal required fields (no validation)
- Forward ticks to CandleBuilder
- Emit structured log events

NOT responsible for:
- Validation
- Candle logic
- Retry / reconnect
- REST fallback
- Data fixing or inference
"""

from typing import Callable, Dict, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from app.data.builder import CandleBuilder
from app.data.logger import log
from app.data.models import Candle


IST = ZoneInfo("Asia/Kolkata")


class AngelWebSocketIngestion:
    """
    Angel SmartAPI WebSocket V2 adapter.

    Phase-1 guarantees:
    - Observes market facts only
    - Never mutates tick data
    - Never retries or reconnects
    - Never assumes missing data
    """

    def __init__(
        self,
        auth_token: str,
        api_key: str,
        client_code: str,
        feed_token: str,
        symbol_token_map: Dict[str, str],
        builders: Dict[str, CandleBuilder],
        on_candle_closed: Optional[Callable[[Candle], None]] = None,

    ):
        """
        Parameters:
        - symbol_token_map: { "RELIANCE": "26009", ... }
        - builders: { "RELIANCE": CandleBuilder(...) }
        """

        self.symbol_token_map = symbol_token_map
        self.builders = builders

        self.ws = SmartWebSocketV2(
            auth_token,
            api_key,
            client_code,
            feed_token,
        )

        # Bind callbacks
        self.ws.on_open = self._on_open
        self.ws.on_data = self._on_data
        self.ws.on_error = self._on_error
        self.ws.on_close = self._on_close
       

        self.on_candle_closed = on_candle_closed
    
        self.token_symbol_map = {v: k for k, v in symbol_token_map.items()}
        
        if len(self.token_symbol_map) != len(symbol_token_map):
            raise ValueError(
                "Duplicate tokens detected in symbol_token_map. "
                "Each symbol must have a unique token."
                )


    # =========================
    # WebSocket lifecycle
    # =========================

    def start(self) -> None:
        """Connect to Angel WebSocket (blocking)."""
        log("WEBSOCKET_CONNECTING", layer="ingestion", symbol="SYSTEM")
        self.ws.connect()

    def _on_open(self, wsapp) -> None:
        log("WEBSOCKET_CONNECTED", layer="ingestion", symbol="SYSTEM")

        # Reset builders on reconnection - drop incomplete candles
        for symbol, builder in self.builders.items():
            builder.reset_on_reconnect()
        
        log(
            "BUILDERS_RESET_ON_RECONNECT",
            layer="ingestion",
            symbol="SYSTEM",
            payload={"symbols": list(self.builders.keys())}
        )

        token_list = [
            {
                "exchangeType": 1,  # NSE
                "tokens": list(self.symbol_token_map.values()),
            }
        ]

        correlation_id = "market_feed"
        mode = 2  # Quote mode (includes volume)

        self.ws.subscribe(correlation_id, mode, token_list)

        log(
            "WEBSOCKET_SUBSCRIBED",
            layer="ingestion",
            symbol="SYSTEM",
            payload={"symbols": list(self.symbol_token_map.keys())},
        )

    def _on_close(self, wsapp) -> None:
        log("WEBSOCKET_DISCONNECTED", layer="ingestion", symbol="SYSTEM")

    def _on_error(self, wsapp, error) -> None:
        log(
            "WEBSOCKET_ERROR",
            layer="ingestion",
            symbol="SYSTEM",
            error=str(error),
        )

    # =========================
    # Tick handling
    # =========================

    def _on_data(self, wsapp, message: dict) -> None:
        """
        Angel SmartAPI V2 tick structure (subset):

       {
       "token": "26009",
       "last_traded_price": 248550,
       "last_traded_quantity": 100,
       "exchange_timestamp": 1738224902500
        }

        """

        try:
            symbol_token = message.get("token")
            price = message.get("last_traded_price")
            quantity = message.get("last_traded_quantity")
            exchange_ts = message.get("exchange_timestamp")
           

            if symbol_token is None or price is None or exchange_ts is None:
                log(
                    "TICK_DROPPED_MISSING_FIELD",
                    layer="ingestion",
                    symbol="SYSTEM",
                    raw_message=message,
                )
                return
            price=price/100  # Angel gives price in paise, convert to rupees

            symbol = self._symbol_from_token(symbol_token)
            if symbol is None:
                log(
                    "TICK_DROPPED_UNKNOWN_SYMBOL",
                    layer="ingestion",
                    symbol="SYSTEM",
                    symbol_token=symbol_token,
                )
                return

            tick_time = datetime.fromtimestamp(
                exchange_ts / 1000,
                tz=IST,
            )

            """log(
                "TICK_RECEIVED",
                layer="ingestion",
                symbol=symbol,
                price=price,
                quantity=quantity,
                tick_time=tick_time.isoformat(),
            )"""

            builder = self.builders.get(symbol)
            if builder is None:
                return

            closed_candle = builder.add_tick(
                price=price,
                quantity=quantity or 1,
                tick_time=tick_time,
            )

            if closed_candle:
                log(
                    "CANDLE_CLOSED",
                    layer="ingestion",
                    symbol=symbol,
                    start_time=closed_candle.open_time.isoformat(),
                    end_time=closed_candle.close_time.isoformat(),
                    ohlc={
                        "open": closed_candle.open_price,
                        "high": closed_candle.high_price,
                        "low": closed_candle.low_price,
                        "close": closed_candle.close_price,
                        "volume_proxy": closed_candle.volume,
                        "tick_count": closed_candle.number_of_trades,
                    },
                )
                if self.on_candle_closed:
                    self.on_candle_closed(closed_candle)

        except Exception as exc:
            log(
                "TICK_PROCESSING_ERROR",
                layer="ingestion",
                symbol="SYSTEM",
                error=str(exc),
                raw_message=message,
            )

    # =========================
    # Utilities
    # =========================

    def _symbol_from_token(self, token: str) -> Optional[str]:
        return self.token_symbol_map.get(token)


