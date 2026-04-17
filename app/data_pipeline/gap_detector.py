

from datetime import datetime, timedelta
from typing import List, Tuple


def detect_gaps(
    timestamps: List[datetime],
    interval_minutes: int,
) -> List[Tuple[datetime, datetime]]:
    """
    Detect missing candle ranges from timestamps.

    Args:
        timestamps: List of candle open timestamps (unsorted, may contain duplicates)
        interval_minutes: Candle interval in minutes

    Returns:
        List of (gap_start, gap_end) tuples
    """

    # --- Edge cases ---
    if not timestamps or len(timestamps) < 2:
        return []

    # --- Normalize input ---
    timestamps = sorted(set(timestamps))

    expected_delta = timedelta(minutes=interval_minutes)
    gaps: List[Tuple[datetime, datetime]] = []

    # --- Detect gaps ---
    for i in range(len(timestamps) - 1):
        current = timestamps[i]
        next_ts = timestamps[i + 1]

        diff = next_ts - current

        if diff > expected_delta:
            gap_start = current + expected_delta
            gap_end = next_ts - expected_delta

            if gap_start <= gap_end:
                gaps.append((gap_start, gap_end))

    return gaps


def filter_market_hours(
    gaps: List[Tuple[datetime, datetime]],
    market_start: Tuple[int, int] = (9, 15),
    market_end: Tuple[int, int] = (15, 30),
) -> List[Tuple[datetime, datetime]]:
    """
    Filters gaps to only include valid NSE market hours.
    Handles multi-day gaps by splitting across days.

    Args:
        gaps: List of (gap_start, gap_end)
        market_start: (hour, minute)
        market_end: (hour, minute)

    Returns:
        Filtered gaps within market hours (may span multiple days)
    """

    filtered: List[Tuple[datetime, datetime]] = []

    for gap_start, gap_end in gaps:
        # Handle multi-day gaps by iterating through each day
        current_day = gap_start.date()
        end_day = gap_end.date()
        
        while current_day <= end_day:
            # Market window for current day
            day_market_start = gap_start.replace(
                year=current_day.year,
                month=current_day.month,
                day=current_day.day,
                hour=market_start[0],
                minute=market_start[1],
                second=0,
                microsecond=0,
            )

            day_market_end = gap_start.replace(
                year=current_day.year,
                month=current_day.month,
                day=current_day.day,
                hour=market_end[0],
                minute=market_end[1],
                second=0,
                microsecond=0,
            )

            # Clip gap to this day's market window
            new_start = max(gap_start, day_market_start)
            new_end = min(gap_end, day_market_end)

            if new_start <= new_end:
                filtered.append((new_start, new_end))

            # Move to next day
            current_day += timedelta(days=1)
            gap_start = day_market_end + timedelta(seconds=1)  # Start after market close

    return filtered


def detect_and_filter_gaps(
    timestamps: List[datetime],
    interval_minutes: int = 5,
) -> List[Tuple[datetime, datetime]]:
    """
    Full pipeline: detect gaps + filter market hours
    """

    raw_gaps = detect_gaps(timestamps, interval_minutes)
    return filter_market_hours(raw_gaps)