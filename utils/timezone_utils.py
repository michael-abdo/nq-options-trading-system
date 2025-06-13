#!/usr/bin/env python3
"""
Timezone Utilities for Consistent Eastern Time Usage
Provides centralized timezone handling for the entire codebase
"""

import pytz
from datetime import datetime
from typing import Union

# Standard timezone objects
EASTERN_TZ = pytz.timezone('US/Eastern')
UTC_TZ = pytz.UTC


def get_eastern_time() -> datetime:
    """
    Get current time in Eastern timezone

    Returns:
        datetime: Current time in Eastern timezone (aware)
    """
    return datetime.now(EASTERN_TZ)


def get_utc_time() -> datetime:
    """
    Get current time in UTC

    Returns:
        datetime: Current time in UTC (aware)
    """
    return datetime.now(UTC_TZ)


def to_eastern_time(dt: datetime) -> datetime:
    """
    Convert any datetime to Eastern timezone

    Args:
        dt: datetime object (aware or naive)

    Returns:
        datetime: datetime converted to Eastern timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = UTC_TZ.localize(dt)
    return dt.astimezone(EASTERN_TZ)


def to_utc_time(dt: datetime) -> datetime:
    """
    Convert any datetime to UTC

    Args:
        dt: datetime object (aware or naive)

    Returns:
        datetime: datetime converted to UTC
    """
    if dt.tzinfo is None:
        # Assume naive datetime is local time
        dt = EASTERN_TZ.localize(dt)
    return dt.astimezone(UTC_TZ)


def format_eastern_timestamp() -> str:
    """
    Get Eastern time formatted for file timestamps

    Returns:
        str: Timestamp in format YYYYMMDD_HHMMSS
    """
    return get_eastern_time().strftime('%Y%m%d_%H%M%S')


def format_eastern_display() -> str:
    """
    Get Eastern time formatted for display

    Returns:
        str: Time in format HH:MM:SS
    """
    return get_eastern_time().strftime('%H:%M:%S')


def format_eastern_full() -> str:
    """
    Get Eastern time formatted for full display

    Returns:
        str: Full timestamp with timezone info
    """
    return get_eastern_time().strftime('%Y-%m-%d %H:%M:%S %Z')


def is_market_hours() -> bool:
    """
    Check if current Eastern time is during market hours

    Returns:
        bool: True if current time is during market hours (9:30 AM - 4:00 PM ET)
    """
    now_et = get_eastern_time()

    # Check if weekend
    if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # Check if within market hours (9:30 AM - 4:00 PM ET)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now_et <= market_close


def get_market_open_time(date: Union[datetime, None] = None) -> datetime:
    """
    Get market open time (9:30 AM ET) for a given date

    Args:
        date: Date to get market open for (default: today)

    Returns:
        datetime: Market open time in Eastern timezone
    """
    if date is None:
        date = get_eastern_time().date()

    return EASTERN_TZ.localize(
        datetime.combine(date, datetime.strptime("09:30", "%H:%M").time())
    )


def get_market_close_time(date: Union[datetime, None] = None) -> datetime:
    """
    Get market close time (4:00 PM ET) for a given date

    Args:
        date: Date to get market close for (default: today)

    Returns:
        datetime: Market close time in Eastern timezone
    """
    if date is None:
        date = get_eastern_time().date()

    return EASTERN_TZ.localize(
        datetime.combine(date, datetime.strptime("16:00", "%H:%M").time())
    )


# Convenience aliases for backward compatibility
now_eastern = get_eastern_time
now_utc = get_utc_time
