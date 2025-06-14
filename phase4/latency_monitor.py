"""Real-time latency monitor – placeholder implementation (Phase 4)."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict

from monitoring.performance_tracker import record_latency

__all__ = [
    "measure",
    "LatencyMonitor",
]


ALERT_THRESHOLD_MS = 100.0  # Trigger alert when latency > 100 ms


def _alert(message: str) -> None:
    """Simple alert hook – replace with real PagerDuty / Slack integration."""

    print(f"🚨 [latency-monitor] {message}")


def measure(stage: str, fn: Callable[[], None]) -> float:
    """Measure latency of `fn` in a standalone way.

    This helper is convenient for ad-hoc timing of self-contained stages. Use
    `LatencyMonitor` for correlated MBO-to-signal latency tracking.
    """

    start = time.perf_counter()
    fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    record_latency(elapsed_ms)
    if elapsed_ms > ALERT_THRESHOLD_MS:
        _alert(f"{stage} latency {elapsed_ms:.2f} ms exceeds {ALERT_THRESHOLD_MS} ms")
    else:
        print(f"[latency-monitor] {stage}: {elapsed_ms:.2f} ms")
    return elapsed_ms


class LatencyMonitor:
    """Correlates MBO ingestion timestamps with signal emission events."""

    def __init__(self, threshold_ms: float = ALERT_THRESHOLD_MS):
        self._mbo_timestamps: Dict[str, float] = {}
        self._latencies: list[float] = []
        self.threshold_ms = threshold_ms

    # ------------------------------------------------------------------
    # Ingestion / signal hooks
    # ------------------------------------------------------------------

    def record_mbo(self, order_id: str) -> None:
        """Register the arrival timestamp of a Market-By-Order event."""

        self._mbo_timestamps[order_id] = time.perf_counter()

    def record_signal(self, order_id: str) -> float | None:
        """Register when a trading signal has been produced for *order_id*.

        The latency between MBO and signal is computed and returned. If the
        corresponding MBO event was not recorded, *None* is returned.
        """

        start = self._mbo_timestamps.pop(order_id, None)
        if start is None:
            return None

        latency_ms = (time.perf_counter() - start) * 1000.0
        self._latencies.append(latency_ms)
        record_latency(latency_ms)

        if latency_ms > self.threshold_ms:
            _alert(
                f"MBO→Signal latency {latency_ms:.2f} ms for {order_id} exceeds {self.threshold_ms} ms"
            )
        return latency_ms

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    def average_latency(self) -> float:
        return sum(self._latencies) / len(self._latencies) if self._latencies else 0.0

    def stats(self) -> dict:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "avg_latency_ms": self.average_latency(),
            "samples": len(self._latencies),
            "threshold_ms": self.threshold_ms,
        }
