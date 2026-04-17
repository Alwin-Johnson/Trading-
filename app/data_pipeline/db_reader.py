from typing import List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


class DBReader:
    """
    Responsible ONLY for reading data from DB.
    """

    def __init__(self, db):
        self.db = db  # your DB connection/wrapper

    def get_timestamps(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime = None,
        lookback_hours: int = 48,
    ) -> List[datetime]:
        """
        Fetch ordered candle open timestamps for a symbol.
        
        Args:
            symbol: Symbol name (e.g., 'HDFCBANK')
            timeframe: Timeframe name (e.g., 'FIVE_MINUTE')
            start_time: Optional explicit start time (overrides lookback_hours)
            lookback_hours: Default lookback window in hours (default: 48 = 2 days)
        
        Returns:
            List of open_time timestamps in ascending order
        """

        query = """
        SELECT open_time
        FROM candles
        WHERE symbol = %s
          AND timeframe = %s
        """

        params = [symbol, timeframe]

        # Use explicit start_time if provided, otherwise use lookback window
        if start_time:
            query += " AND open_time >= %s"
            params.append(start_time)
        else:
            # Default: fetch last N hours only
            cutoff_time = datetime.now(IST) - timedelta(hours=lookback_hours)
            query += " AND open_time >= %s"
            params.append(cutoff_time)

        query += " ORDER BY open_time ASC"

        rows = self.db.fetch_all(query, params)

        # Assuming row is dict-like: {"open_time": datetime}
        return [row["open_time"] for row in rows]