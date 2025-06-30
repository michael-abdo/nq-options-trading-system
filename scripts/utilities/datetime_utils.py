#!/usr/bin/env python3
"""
Centralized DateTime Utilities
Consolidates all date/time formatting and parsing logic from across the codebase
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Union

logger = logging.getLogger(__name__)


class DateTimeFormats:
    """Standard datetime formats used across the codebase"""
    
    # API and data exchange formats
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"
    ISO_FORMAT_MS = "%Y-%m-%dT%H:%M:%S.%f"
    
    # File naming formats
    FILE_TIMESTAMP = "%Y%m%d_%H%M%S"
    FILE_DATE_ONLY = "%Y%m%d"
    
    # Display formats
    DISPLAY_FULL = "%Y-%m-%d %H:%M:%S"
    DISPLAY_DATE = "%Y-%m-%d"
    DISPLAY_TIME = "%H:%M:%S"
    
    # Barchart specific formats
    BARCHART_DATE = "%m/%d/%y"  # 06/27/25
    
    # Log formats
    LOG_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_timestamp(format_type: str = "file") -> str:
    """Get current timestamp in specified format
    
    Args:
        format_type: One of 'file', 'api', 'display', 'date_only'
        
    Returns:
        Formatted timestamp string
    """
    now = datetime.now()
    
    format_map = {
        "file": DateTimeFormats.FILE_TIMESTAMP,
        "api": DateTimeFormats.ISO_FORMAT,
        "display": DateTimeFormats.DISPLAY_FULL,
        "date_only": DateTimeFormats.FILE_DATE_ONLY,
        "iso": DateTimeFormats.ISO_FORMAT,
        "iso_ms": DateTimeFormats.ISO_FORMAT_MS
    }
    
    format_string = format_map.get(format_type, DateTimeFormats.FILE_TIMESTAMP)
    return now.strftime(format_string)


def parse_timestamp(timestamp: str, format_type: Optional[str] = None) -> datetime:
    """Parse timestamp string to datetime object
    
    Args:
        timestamp: Timestamp string to parse
        format_type: Expected format type. If None, tries common formats
        
    Returns:
        datetime object
        
    Raises:
        ValueError: If timestamp cannot be parsed
    """
    if format_type:
        format_map = {
            "file": DateTimeFormats.FILE_TIMESTAMP,
            "api": DateTimeFormats.ISO_FORMAT,
            "display": DateTimeFormats.DISPLAY_FULL,
            "barchart": DateTimeFormats.BARCHART_DATE,
            "iso": DateTimeFormats.ISO_FORMAT,
            "iso_ms": DateTimeFormats.ISO_FORMAT_MS
        }
        format_string = format_map.get(format_type)
        if format_string:
            return datetime.strptime(timestamp, format_string)
    
    # Try common formats
    formats_to_try = [
        DateTimeFormats.ISO_FORMAT_MS,
        DateTimeFormats.ISO_FORMAT,
        DateTimeFormats.FILE_TIMESTAMP,
        DateTimeFormats.DISPLAY_FULL,
        DateTimeFormats.BARCHART_DATE,
        "%Y-%m-%d",
        "%Y%m%d"
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse timestamp: {timestamp}")


def format_timedelta(td: timedelta) -> str:
    """Format timedelta to human-readable string
    
    Args:
        td: timedelta object
        
    Returns:
        Human-readable duration string
    """
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"


def get_trading_day(date: datetime, option_type: str = "weekly") -> datetime:
    """Get the trading day for options expiration
    
    Args:
        date: Base date
        option_type: 'weekly' (Tuesday), 'friday' (Friday), 'monthly' (3rd Friday)
        
    Returns:
        datetime of the trading day
    """
    if option_type == "weekly":
        # Find next Tuesday (weekday 1)
        days_ahead = 1 - date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return date + timedelta(days=days_ahead)
    
    elif option_type == "friday":
        # Find next Friday (weekday 4)
        days_ahead = 4 - date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return date + timedelta(days=days_ahead)
    
    elif option_type == "monthly":
        # Find 3rd Friday of next month
        if date.day > 15:
            # Move to next month
            if date.month == 12:
                date = date.replace(year=date.year + 1, month=1, day=1)
            else:
                date = date.replace(month=date.month + 1, day=1)
        else:
            date = date.replace(day=1)
        
        # Find first Friday
        first_friday = date
        while first_friday.weekday() != 4:
            first_friday += timedelta(days=1)
        
        # Add 2 weeks to get 3rd Friday
        return first_friday + timedelta(weeks=2)
    
    else:
        raise ValueError(f"Unknown option type: {option_type}")


def is_trading_day(date: datetime) -> bool:
    """Check if date is a valid trading day
    
    Args:
        date: Date to check
        
    Returns:
        True if trading day, False otherwise
    """
    # Markets closed on weekends
    if date.weekday() in [5, 6]:  # Saturday, Sunday
        return False
    
    # TODO: Add holiday calendar check
    # For now, assume all weekdays are trading days
    
    return True


def get_market_hours(date: datetime) -> tuple[datetime, datetime]:
    """Get market open and close times for a given date
    
    Args:
        date: Trading date
        
    Returns:
        Tuple of (market_open, market_close) datetime objects
    """
    # Regular market hours: 9:30 AM - 4:00 PM ET
    market_open = date.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = date.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open, market_close


def format_for_filename(dt: Optional[datetime] = None) -> str:
    """Format datetime for use in filename
    
    Args:
        dt: datetime to format (defaults to now)
        
    Returns:
        Filename-safe timestamp string
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(DateTimeFormats.FILE_TIMESTAMP)


def format_for_display(dt: Optional[datetime] = None) -> str:
    """Format datetime for display to user
    
    Args:
        dt: datetime to format (defaults to now)
        
    Returns:
        Human-readable datetime string
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(DateTimeFormats.DISPLAY_FULL)


# Backward compatibility aliases
def get_current_timestamp() -> str:
    """Get current timestamp for filenames - backward compatible"""
    return get_timestamp("file")


def get_iso_timestamp() -> str:
    """Get current ISO format timestamp - backward compatible"""
    return datetime.now().isoformat()