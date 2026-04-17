"""
Backfill Pipeline Scheduler

Runs gap detection + backfill at regular intervals during market hours.
Ensures data completeness by filling gaps shortly after each candle closes.

Phase-1:
- Interval-based execution
- Market hours gating (09:15-15:30 IST)
- 2-day lookback window
- Thread-based scheduling
"""

import schedule
import time
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from app.data_pipeline.pipeline_runner import run_pipeline
from app.data.logger import log

IST = ZoneInfo("Asia/Kolkata")

# =========================
# CONFIGURATION
# =========================

# Schedule offsets to allow candle closure before backfilling
SCHEDULE_CONFIG = [
    {
        "timeframe_name": "FIVE_MINUTE",
        "timeframe_minutes": 5,
        "run_interval_seconds": 420,  # 7 minutes
    },
    {
        "timeframe_name": "FIFTEEN_MINUTE",
        "timeframe_minutes": 15,
        "run_interval_seconds": 1080,  # 18 minutes
    },
    {
        "timeframe_name": "THIRTY_MINUTE",
        "timeframe_minutes": 30,
        "run_interval_seconds": 1860,  # 31 minutes
    },
    {
        "timeframe_name": "ONE_HOUR",
        "timeframe_minutes": 60,
        "run_interval_seconds": 3900,  # 65 minutes
    },
]

# Market hours (IST)
MARKET_OPEN = (9, 15)   # 09:15
MARKET_CLOSE = (15, 30)  # 15:30

# Historical lookback window
LOOKBACK_HOURS = 48  # 2 days


# =========================
# MARKET HOURS GATE
# =========================

def is_market_hours() -> bool:
    """Check if current time is within NSE market hours."""
    now = datetime.now(IST)
    market_open = now.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0)
    
    return market_open <= now <= market_close


# =========================
# PIPELINE EXECUTION
# =========================

def run_scheduled_backfill(smart, timeframe_config: dict) -> None:
    """
    Run backfill for a specific timeframe.
    
    Args:
        smart: Authenticated SmartAPI session
        timeframe_config: Config dict with timeframe_name, timeframe_minutes, etc.
    """
    
    # Gate: Only during market hours
    if not is_market_hours():
        log(
            "BACKFILL_SKIPPED_MARKET_CLOSED",
            layer="scheduler",
            symbol="SYSTEM",
            payload={
                "reason": "outside_market_hours",
                "timeframe": timeframe_config["timeframe_name"],
            }
        )
        return
    
    timeframe_name = timeframe_config["timeframe_name"]
    
    log(
        "BACKFILL_SCHEDULED_START",
        layer="scheduler",
        symbol="SYSTEM",
        payload={
            "timeframe": timeframe_name,
            "timestamp": datetime.now(IST).isoformat(),
        }
    )
    
    try:
        # Run pipeline for this timeframe
        run_pipeline(smart, timeframe=timeframe_name)
        
        log(
            "BACKFILL_SCHEDULED_SUCCESS",
            layer="scheduler",
            symbol="SYSTEM",
            payload={
                "timeframe": timeframe_name,
                "timestamp": datetime.now(IST).isoformat(),
            }
        )
    except Exception as e:
        log(
            "BACKFILL_SCHEDULED_ERROR",
            layer="scheduler",
            symbol="SYSTEM",
            payload={
                "timeframe": timeframe_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(IST).isoformat(),
            }
        )
        print(f"❌ BACKFILL ERROR ({timeframe_name}): {e}")  # Also print for visibility


# =========================
# SCHEDULER LIFECYCLE
# =========================

class BackfillScheduler:
    """
    Manages scheduled backfill execution during market hours.
    """
    
    def __init__(self, smart):
        """
        Initialize scheduler with SmartAPI session.
        
        Args:
            smart: Authenticated SmartAPI session
        """
        self.smart = smart
        self.scheduler = schedule.Scheduler()
        self.thread = None
        self.running = False
    
    def setup_jobs(self) -> None:
        """Configure scheduled jobs for all timeframes."""
        
        log(
            "SCHEDULER_SETUP",
            layer="scheduler",
            symbol="SYSTEM",
            payload={
                "timeframes": len(SCHEDULE_CONFIG),
                "lookback_hours": LOOKBACK_HOURS,
            }
        )
        
        for config in SCHEDULE_CONFIG:
            timeframe_name = config["timeframe_name"]
            interval_seconds = config["run_interval_seconds"]
            
            # Schedule job
            self.scheduler.every(interval_seconds).seconds.do(
                run_scheduled_backfill,
                smart=self.smart,
                timeframe_config=config,
            )
            
            log(
                "SCHEDULER_JOB_REGISTERED",
                layer="scheduler",
                symbol="SYSTEM",
                payload={
                    "timeframe": timeframe_name,
                    "interval_seconds": interval_seconds,
                }
            )
    
    def start(self) -> None:
        """Start scheduler in background thread."""
        if self.running:
            log(
                "SCHEDULER_ALREADY_RUNNING",
                layer="scheduler",
                symbol="SYSTEM",
            )
            return
        
        self.running = True
        
        # Setup jobs
        self.setup_jobs()
        
        # Start thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        log(
            "SCHEDULER_STARTED",
            layer="scheduler",
            symbol="SYSTEM",
            payload={
                "timestamp": datetime.now(IST).isoformat(),
            }
        )
    
    def stop(self) -> None:
        """Stop scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        log(
            "SCHEDULER_STOPPED",
            layer="scheduler",
            symbol="SYSTEM",
            payload={
                "timestamp": datetime.now(IST).isoformat(),
            }
        )
    
    def _run_scheduler(self) -> None:
        """Run scheduler loop (internal)."""
        while self.running:
            try:
                pending = self.scheduler.run_pending()
                if pending:
                    print(f"🔄 Scheduler executing {len(pending)} job(s)...")
                time.sleep(1)  # Check every second
            except Exception as e:
                log(
                    "SCHEDULER_ERROR",
                    layer="scheduler",
                    symbol="SYSTEM",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                print(f"❌ SCHEDULER ERROR: {e}")
                time.sleep(5)


# =========================
# Usage Example
# =========================

"""
In your live test runner:

from app.data_pipeline.scheduler import BackfillScheduler

# After logging in
scheduler = BackfillScheduler(smart)
scheduler.start()

# During ingestion
# ... ingestion runs normally ...
# ... scheduler runs backfill in parallel every interval ...

# On shutdown
scheduler.stop()
"""
