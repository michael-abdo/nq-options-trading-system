"""Staged rollout framework for IFD v3 signals – placeholder."""

from __future__ import annotations

from typing import Callable

__all__ = ["StagedRollout"]


class StagedRollout:
    """Manage percentage-based rollout of new algorithm signals."""

    def __init__(self, initial_pct: float = 0.2) -> None:
        self.current_pct = initial_pct

    def should_activate(self, signal_hash: str) -> bool:  # noqa: D401
        """Return *True* if the given signal should be executed live."""

        # Very naive: activate for first N% of alphabetic range
        bucket = (hash(signal_hash) % 100) / 100.0
        return bucket < self.current_pct

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def update_percentage(self, pct: float) -> None:
        self.current_pct = max(0.0, min(1.0, pct))

    # ------------------------------------------------------------------
    # Decorator helper
    # ------------------------------------------------------------------

    def gated(self, fn: Callable[..., None]):
        def _wrapper(signal_hash: str, *args, **kwargs):
            if self.should_activate(signal_hash):
                return fn(signal_hash, *args, **kwargs)
            print(f"[staged-rollout] Skipped signal {signal_hash} – outside rollout percentage")

        return _wrapper
