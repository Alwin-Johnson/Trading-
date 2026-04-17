from typing import List
from app.data.models import Candle


class DBWriter:
    """
    Responsible ONLY for inserting candles safely.
    """

    def __init__(self, db):
        self.db = db  # your DB connection/wrapper

    def insert_candles(self, candles: List[Candle]):
        """
        Insert candles into DB with conflict protection.
        """

        if not candles:
            return

        query = """
        INSERT INTO candles (
            symbol,
            timeframe,
            open_time,
            close_time,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            number_of_trades,
            is_closed,
            mode
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timeframe, open_time) DO NOTHING
        """

        values = [
            (
                c.symbol,
                c.timeframe,
                c.open_time,
                c.close_time,
                c.open_price,
                c.high_price,
                c.low_price,
                c.close_price,
                c.volume,
                c.number_of_trades,
                c.is_closed,
                c.mode,
            )
            for c in candles
        ]

        self.db.execute_many(query, values)