"""MBO (Market-By-Order) event processing utilities – placeholder."""

from __future__ import annotations

from typing import Any, Dict, List

__all__ = ["process_mbo_events"]


def process_mbo_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return simplified aggregation structure until real logic is added."""

    return {
        "total_events": len(events),
        "buy_volume": 0,
        "sell_volume": 0,
    }
