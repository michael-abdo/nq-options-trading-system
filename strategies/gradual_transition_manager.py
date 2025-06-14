"""Manager handling gradual transition to IFD v3 signals – placeholder."""

from __future__ import annotations

from typing import List

__all__ = ["GradualTransitionManager"]


class GradualTransitionManager:
    """Coordinates stage-by-stage transition from v1 to v3 signals."""

    def __init__(self):
        self.active = False
        self.transition_complete = False
        self.enabled_percentage = 0.0  # 0 → 1.0

    def start(self):
        print("[transition] Starting gradual transition to IFD v3…")
        self.active = True
        self.enabled_percentage = 0.2

    def step(self):
        if not self.active:
            return
        if self.transition_complete:
            return
        self.enabled_percentage = min(1.0, self.enabled_percentage + 0.1)
        print(f"[transition] Enabled percentage: {self.enabled_percentage:.0%}")
        if self.enabled_percentage >= 1.0:
            self.transition_complete = True
            print("[transition] Transition complete – IFD v3 fully live.")

    def status(self) -> dict:
        return {
            "active": self.active,
            "enabled_percentage": self.enabled_percentage,
            "transition_complete": self.transition_complete,
        }
