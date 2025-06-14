"""Signal accuracy and quality metrics tracker – placeholder (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

__all__ = ["SuccessMetricsTracker"]


@dataclass
class SuccessMetricsTracker:
    """Collects and aggregates signal quality metrics."""

    target_hit_rate: float = 0.65
    max_false_positive_rate: float = 0.2

    hits: int = 0
    total: int = 0
    false_positives: int = 0
    returns: List[float] = field(default_factory=list)

    def record_signal(self, success: bool, is_false_positive: bool, return_value: float) -> None:
        self.total += 1
        if success:
            self.hits += 1
        if is_false_positive:
            self.false_positives += 1
        self.returns.append(return_value)

        # Immediate alerting if quality drops below thresholds
        if self.total >= 20:  # Wait for at least 20 samples
            if not self.is_quality_acceptable():
                print(
                    "🚨 [quality-tracker] Quality thresholds breached "
                    f"(hit_rate={self.hit_rate:.2%}, false_pos={self.false_positive_rate:.2%})"
                )

    # ------------------------------------------------------------------
    # Quick-look KPIs
    # ------------------------------------------------------------------

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.false_positives / self.total if self.total else 0.0

    @property
    def risk_adjusted_return(self) -> float:
        if not self.returns:
            return 0.0
        avg = sum(self.returns) / len(self.returns)
        # Very rough Sharpe-like metric, no risk-free rate
        std = (sum((r - avg) ** 2 for r in self.returns) / len(self.returns)) ** 0.5
        return avg / std if std else 0.0

    # ------------------------------------------------------------------
    # High-level assessment
    # ------------------------------------------------------------------

    def is_quality_acceptable(self) -> bool:
        return (
            self.hit_rate >= self.target_hit_rate
            and self.false_positive_rate <= self.max_false_positive_rate
        )

    def summary(self) -> dict:  # noqa: D401 – short label
        """Return a snapshot of the KPIs."""

        return {
            "hit_rate": self.hit_rate,
            "false_positive_rate": self.false_positive_rate,
            "risk_adjusted_return": self.risk_adjusted_return,
            "quality_ok": self.is_quality_acceptable(),
        }
