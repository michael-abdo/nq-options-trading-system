"""Databento API wrapper for IFD v3 – placeholder implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

__all__ = [
    "DatabentoAPI",
]


class DatabentoAPI:
    """Minimal client skeleton that imitates the public interface used by v3."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or "<unset>"

    # ---------------------------------------------------------------------
    # Public helpers (no real network interaction yet)
    # ---------------------------------------------------------------------

    def get_mbo_events(
        self, symbol: str, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        """Return an empty list – to be replaced with real MBO fetching."""

        # TODO: Integrate with Databento SDK
        return []


    def get_historical_bars(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        """Return fake OHLCV data until real endpoint is ready."""

        return []
