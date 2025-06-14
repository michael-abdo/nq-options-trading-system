"""System-level performance tracker – placeholder implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

__all__ = ["record_latency", "record_cost", "get_metrics"]

_METRICS: Dict[str, Any] = {
    "latencies_ms": [],
    "api_costs": [],
}


# ------------------------------------------------------------------
# Recording helpers
# ------------------------------------------------------------------


def record_latency(value_ms: float) -> None:
    _METRICS["latencies_ms"].append(value_ms)


def record_cost(cost_usd: float) -> None:
    _METRICS["api_costs"].append(cost_usd)


# ------------------------------------------------------------------
# KPI calculation
# ------------------------------------------------------------------


def _avg(seq):
    return sum(seq) / len(seq) if seq else 0.0


def get_metrics() -> Dict[str, Any]:
    """Return a snapshot of live performance KPIs."""

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "avg_latency_ms": _avg(_METRICS["latencies_ms"]),
        "p95_latency_ms": percentile(_METRICS["latencies_ms"], 95),
        "total_api_cost_usd": sum(_METRICS["api_costs"]),
        "samples": len(_METRICS["latencies_ms"]),
    }


# ------------------------------------------------------------------
# Utility: percentile (simple, no numpy dependency)
# ------------------------------------------------------------------


def percentile(data, pct):
    if not data:
        return 0.0
    data = sorted(data)
    k = (len(data) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[f]
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return d0 + d1
