from typing import List
from datetime import datetime

from app.data.historical import HistoricalDataFetcher
from app.data.models import Candle


class BackfillService:

    def __init__(self, fetcher: HistoricalDataFetcher):
        self.fetcher = fetcher

    def fetch_gap_data(
        self,
        exchange: str,
        symbol: str,
        symbol_token: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> List[Candle]:
        """
        Fetch missing candles for a given gap.
        """

        candles = self.fetcher.fetch_candles(
            exchange=exchange,
            symbol=symbol,
            symbol_token=symbol_token,
            interval=interval,
            from_date=start,
            to_date=end,
        )

        return candles