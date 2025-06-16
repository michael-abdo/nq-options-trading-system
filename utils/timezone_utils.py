#!/usr/bin/env python3
"""
Timezone Utilities for Consistent Eastern Time Usage
Provides centralized timezone handling for the entire codebase
"""

import pytz
from datetime import datetime, timedelta
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


def is_futures_market_hours() -> bool:
    """
    Check if current Eastern time is during futures market hours

    Futures trade Sunday 6 PM ET to Friday 5 PM ET

    Returns:
        bool: True if current time is during futures market hours
    """
    now_et = get_eastern_time()
    weekday = now_et.weekday()
    hour = now_et.hour

    # Sunday (6) - market opens at 6 PM
    if weekday == 6:
        return hour >= 18

    # Monday-Thursday (0-3) - market open all day
    elif weekday in [0, 1, 2, 3]:
        return True

    # Friday (4) - market closes at 5 PM
    elif weekday == 4:
        return hour < 17

    # Saturday (5) - market closed all day
    else:
        return False


def get_futures_market_open_time(date: Union[datetime, None] = None) -> datetime:
    """
    Get futures market open time for a given date

    Futures open Sunday 6 PM ET and run continuously until Friday 5 PM ET

    Args:
        date: Date to get market open for (default: today)

    Returns:
        datetime: Market open time in Eastern timezone
    """
    if date is None:
        date = get_eastern_time()

    # Convert to date if datetime passed
    if hasattr(date, 'date'):
        date_only = date.date()
    else:
        date_only = date

    # Get day of week
    weekday = date_only.weekday()

    # If Monday-Friday, market opened previous Sunday at 6 PM
    if weekday in [0, 1, 2, 3, 4]:
        days_since_sunday = (weekday + 1) % 7
        sunday = date_only - timedelta(days=days_since_sunday)
        return EASTERN_TZ.localize(
            datetime.combine(sunday, datetime.strptime("18:00", "%H:%M").time())
        )

    # If Sunday, market opens at 6 PM same day
    elif weekday == 6:
        return EASTERN_TZ.localize(
            datetime.combine(date_only, datetime.strptime("18:00", "%H:%M").time())
        )

    # If Saturday, next market open is Sunday 6 PM
    else:
        sunday = date_only + timedelta(days=1)
        return EASTERN_TZ.localize(
            datetime.combine(sunday, datetime.strptime("18:00", "%H:%M").time())
        )


def get_futures_market_close_time(date: Union[datetime, None] = None) -> datetime:
    """
    Get futures market close time for a given date

    Futures close Friday 5 PM ET

    Args:
        date: Date to get market close for (default: today)

    Returns:
        datetime: Market close time in Eastern timezone
    """
    if date is None:
        date = get_eastern_time()

    # Convert to date if datetime passed
    if hasattr(date, 'date'):
        date_only = date.date()
    else:
        date_only = date

    # Get day of week
    weekday = date_only.weekday()

    # Find next Friday
    days_until_friday = (4 - weekday) % 7
    if days_until_friday == 0 and weekday == 4:
        # It's Friday, use same day
        friday = date_only
    else:
        # Find next Friday
        friday = date_only + timedelta(days=days_until_friday)

    return EASTERN_TZ.localize(
        datetime.combine(friday, datetime.strptime("17:00", "%H:%M").time())
    )


def get_last_futures_trading_session_end(et_time: datetime = None) -> datetime:
    """
    Get the end time of the last futures trading session

    Args:
        et_time: Eastern time to check from (default: now)

    Returns:
        datetime: End time of last trading session in UTC
    """
    if et_time is None:
        et_time = get_eastern_time()

    weekday = et_time.weekday()

    # If it's Saturday or Sunday before 6 PM, last session ended Friday 5 PM
    if weekday == 5 or (weekday == 6 and et_time.hour < 18):
        # Go back to Friday 5 PM
        days_back = weekday - 4 if weekday == 5 else 2
        last_friday = et_time - timedelta(days=days_back)
        last_close = last_friday.replace(hour=17, minute=0, second=0, microsecond=0)
        return last_close.astimezone(UTC_TZ)

    # If it's Sunday after 6 PM, market is open - use current time minus buffer
    elif weekday == 6 and et_time.hour >= 18:
        return to_utc_time(et_time - timedelta(minutes=10))

    # If it's Monday through Thursday, check if we're in the first session
    # Markets open Sunday 6 PM, so Monday morning is part of continuous session
    elif weekday in [0, 1, 2, 3]:
        # For Monday specifically, if markets aren't open yet (shouldn't happen),
        # return Friday 5 PM
        if weekday == 0 and not is_futures_market_hours():
            last_friday = et_time - timedelta(days=3)
            last_close = last_friday.replace(hour=17, minute=0, second=0, microsecond=0)
            return last_close.astimezone(UTC_TZ)
        # Otherwise use current time minus buffer for continuous trading
        return to_utc_time(et_time - timedelta(minutes=10))

    # If it's Friday before 5 PM, market is open
    elif weekday == 4 and et_time.hour < 17:
        return to_utc_time(et_time - timedelta(minutes=10))

    # If it's Friday after 5 PM, market just closed
    elif weekday == 4 and et_time.hour >= 17:
        last_close = et_time.replace(hour=17, minute=0, second=0, microsecond=0)
        return last_close.astimezone(UTC_TZ)

    # Default fallback (shouldn't reach here)
    return to_utc_time(et_time - timedelta(minutes=10))


# Convenience aliases for backward compatibility
now_eastern = get_eastern_time
now_utc = get_utc_time
