


from datetime import datetime
import pyotp

from SmartApi import SmartConnect

from app.data.historical import HistoricalDataFetcher
from app.data.persistence import PostgresCandleRepository
from app.data.symbols import SYMBOL_TOKEN_MAP

import os
from dotenv import load_dotenv


load_dotenv()
# =========================
# 1. CREDENTIALS
# =========================

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PIN = os.getenv("ANGEL_PIN")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

# Database credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "trading")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")



EXCHANGE = "NSE"

INTERVAL = "FIFTEEN_MINUTE"
FROM_DATE = datetime(2024, 1, 1, 9, 0)
TO_DATE   = datetime(2026, 4, 19, 18, 45)


# =========================
# 2. LOGIN
# =========================

smart = SmartConnect(API_KEY)

totp = pyotp.TOTP(TOTP_SECRET).now()
session = smart.generateSession(CLIENT_CODE, PIN, totp)

if not session["status"]:
    raise RuntimeError("Login failed")

print("✅ Login successful")


# =========================
# 2.5. DATABASE CONNECTION
# =========================

try:
    repo = PostgresCandleRepository(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    print("✅ Database connected")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    repo = None


# =========================
# 3. FETCH HISTORICAL DATA & INSERT TO DB
# =========================

fetcher = HistoricalDataFetcher(smart)
total_candles = 0

for symbol, token in SYMBOL_TOKEN_MAP.items():
    current_interval = "ONE_DAY" if symbol == "NIFTY" else INTERVAL
    candles = fetcher.fetch_candles(
        exchange=EXCHANGE,
        symbol=symbol,
        symbol_token=token,
        interval=current_interval,
        from_date=FROM_DATE,
        to_date=TO_DATE,
    )
    
    total_candles += len(candles)
    
    # Insert candles to database
    if repo and candles:
        for candle in candles:
            try:
                repo.insert_candle(candle)
            except Exception as e:
                print(f"❌ Failed to insert {symbol} candle: {e}")
    
    print(f"✅ {symbol}: Fetched {len(candles)} candles")


print(f"\n📊 Fetched and saved {total_candles} total candles")


# =========================
# 3.5. CLOSE DATABASE
# =========================

if repo:
    repo.close()
    print("🔒 Database connection closed")

# =========================
# 4. LOGOUT
# =========================

smart.terminateSession(CLIENT_CODE)
print("\n🔒 Angel session terminated")
