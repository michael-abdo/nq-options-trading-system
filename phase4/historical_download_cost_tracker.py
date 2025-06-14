"""Databento historical download cost tracker – placeholder (Phase 4)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict

__all__ = ["CostTracker"]


ALERT_THRESHOLD_PCT = 0.8  # 80 % of budget


def _alert(message: str) -> None:
    print(f"🚨 [cost-tracker] {message}")


class CostTracker:
    """Tracks Databento download costs and emits budget alerts."""

    def __init__(self, daily_budget_usd: float, monthly_budget_usd: float):
        self.daily_budget = daily_budget_usd
        self.monthly_budget = monthly_budget_usd
        self.daily_cost: Dict[date, float] = {}
        self.monthly_cost: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, amount_usd: float, day: date | None = None) -> None:
        day = day or date.today()
        self.daily_cost[day] = self.daily_cost.get(day, 0.0) + amount_usd
        month_key = day.strftime("%Y-%m")
        self.monthly_cost[month_key] = self.monthly_cost.get(month_key, 0.0) + amount_usd

        # Alerts – fire immediately when thresholds are crossed
        if self.is_daily_budget_exceeded(day):
            _alert(
                f"Daily cost {self.daily_cost[day]:.2f} USD exceeds {ALERT_THRESHOLD_PCT*100:.0f}% of budget ({self.daily_budget} USD)."
            )

        if self.is_monthly_budget_exceeded(month_key):
            _alert(
                f"Monthly cost {self.monthly_cost[month_key]:.2f} USD exceeds {ALERT_THRESHOLD_PCT*100:.0f}% of budget ({self.monthly_budget} USD)."
            )

    # ------------------------------------------------------------------
    # Budget checks
    # ------------------------------------------------------------------

    def is_daily_budget_exceeded(self, day: date | None = None) -> bool:
        day = day or date.today()
        return self.daily_cost.get(day, 0.0) >= ALERT_THRESHOLD_PCT * self.daily_budget

    def is_monthly_budget_exceeded(self, month_key: str | None = None) -> bool:
        month_key = month_key or date.today().strftime("%Y-%m")
        return self.monthly_cost.get(month_key, 0.0) >= ALERT_THRESHOLD_PCT * self.monthly_budget

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def daily_summary(self, day: date | None = None) -> dict:
        day = day or date.today()
        spent = self.daily_cost.get(day, 0.0)
        return {
            "day": day.isoformat(),
            "spent_usd": spent,
            "budget_usd": self.daily_budget,
            "pct_of_budget": spent / self.daily_budget if self.daily_budget else 0.0,
        }

    def monthly_summary(self, month_key: str | None = None) -> dict:
        month_key = month_key or date.today().strftime("%Y-%m")
        spent = self.monthly_cost.get(month_key, 0.0)
        return {
            "month": month_key,
            "spent_usd": spent,
            "budget_usd": self.monthly_budget,
            "pct_of_budget": spent / self.monthly_budget if self.monthly_budget else 0.0,
        }

    def overall_summary(self) -> dict:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "today": self.daily_summary(),
            "month": self.monthly_summary(),
        }
