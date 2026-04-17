import os
from urllib.parse import quote
from dotenv import load_dotenv

from app.core.db import DBConnection
from app.data_pipeline.db_reader import DBReader
from app.data_pipeline.db_writer import DBWriter
from app.data_pipeline.gap_detector import detect_and_filter_gaps
from app.data_pipeline.backfill_service import BackfillService
from app.data.historical import HistoricalDataFetcher
from app.data.symbols import SYMBOL_TOKEN_MAP

load_dotenv()

# =========================
# CONFIG
# =========================

SYMBOLS = [
    {"symbol": symbol, "token": token, "exchange": "NSE"}
    for symbol, token in SYMBOL_TOKEN_MAP.items()
]

# Support multiple timeframes
TIMEFRAMES = [
    {"name": "ONE_MINUTE", "minutes": 1},
    {"name": "FIVE_MINUTE", "minutes": 5},
    {"name": "FIFTEEN_MINUTE", "minutes": 15},
    {"name": "THIRTY_MINUTE", "minutes": 30},
    {"name": "ONE_HOUR", "minutes": 60},
    {"name": "ONE_DAY", "minutes": 1440},
]

# Build DSN from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not DB_NAME or not DB_USER or not DB_PASSWORD:
    raise RuntimeError(
        "Missing database environment variables. "
        "Set: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
    )

DB_DSN = (
    f"postgresql://{quote(DB_USER, safe='')}:{quote(DB_PASSWORD, safe='')}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# =========================
# MAIN PIPELINE
# =========================

def run_pipeline(smart, timeframe: str = None):
    """
    Runs full gap detection + backfill pipeline.
    
    Args:
        smart: Already authenticated SmartAPI session
        timeframe: Optional specific timeframe to process
                  If None, processes all timeframes in TIMEFRAMES config
    """

    print("🚀 PIPELINE STARTED")

    # -------------------------
    # 1. DB Setup
    # -------------------------
    db = DBConnection(DB_DSN)

    reader = DBReader(db)
    writer = DBWriter(db)

    # -------------------------
    # 2. Historical + Backfill
    # -------------------------
    fetcher = HistoricalDataFetcher(smart)
    backfill_service = BackfillService(fetcher)

    # -------------------------
    # 3. Process Symbols & Timeframes
    # -------------------------
    # If specific timeframe requested, filter to only that one
    timeframes_to_process = TIMEFRAMES
    if timeframe:
        timeframes_to_process = [tf for tf in TIMEFRAMES if tf["name"] == timeframe]
        if not timeframes_to_process:
            print(f"❌ Timeframe not found: {timeframe}")
            db.close()
            return
    
    for timeframe_meta in timeframes_to_process:
        timeframe_name = timeframe_meta["name"]
        timeframe_minutes = timeframe_meta["minutes"]

        print(f"\n⏱ Processing timeframe: {timeframe_name}")

        for meta in SYMBOLS:

            symbol = meta["symbol"]
            token = meta["token"]
            exchange = meta["exchange"]

            print(f"\n📊 Processing {symbol} ({timeframe_name})")

            # -------------------------
            # 4. Get timestamps
            # -------------------------
            timestamps = reader.get_timestamps(
                symbol=symbol,
                timeframe=timeframe_name,
                lookback_hours=48
            )

            # -------------------------
            # 5. Detect gaps
            # -------------------------
            gaps = detect_and_filter_gaps(timestamps, interval_minutes=timeframe_minutes)

            if not gaps:
                print(f"✅ No gaps for {symbol} ({timeframe_name})")
                continue

            print(f"⚠ Found {len(gaps)} gaps")

            # -------------------------
            # 6. Process each gap
            # -------------------------
            for start, end in gaps:

                print(f"🔄 Backfilling {symbol} ({timeframe_name}): {start} → {end}")

                candles = backfill_service.fetch_gap_data(
                    exchange=exchange,
                    symbol=symbol,
                    symbol_token=token,
                    interval=timeframe_name,
                    start=start,
                    end=end,
                )

                if not candles:
                    print("⚠ No data returned")
                    continue

                # -------------------------
                # 7. Insert into DB
                # -------------------------
                writer.insert_candles(candles)

                print(f"✅ Inserted {len(candles)} candles")

    # -------------------------
    # 8. Cleanup
    # -------------------------
    db.close()

    print("\n🏁 PIPELINE COMPLETED")