"""
Timeframe coordination – which TFs are active and their thresholds.
"""

from __future__ import annotations

from typing import Dict, List, Set

from config.settings import DEFAULT_ENABLED_TIMEFRAMES, DEFAULT_OI_THRESHOLDS, TIMEFRAMES


class TimeframeEngine:
    def __init__(self):
        self.enabled: Set[str] = set(DEFAULT_ENABLED_TIMEFRAMES)
        self.thresholds: Dict[str, float] = dict(DEFAULT_OI_THRESHOLDS)

    def enable(self, tf: str) -> None:
        if tf in TIMEFRAMES:
            self.enabled.add(tf)

    def disable(self, tf: str) -> None:
        self.enabled.discard(tf)

    def set_all(self, enabled: bool = True) -> None:
        if enabled:
            self.enabled = set(TIMEFRAMES.keys())
        else:
            self.enabled.clear()

    def set_threshold(self, tf: str, pct: float) -> None:
        if tf in TIMEFRAMES:
            self.thresholds[tf] = abs(pct)

    def get_threshold(self, tf: str) -> float:
        return self.thresholds.get(tf, 10.0)

    def active_list(self) -> List[str]:
        # Preserve logical order
        return [tf for tf in TIMEFRAMES if tf in self.enabled]
