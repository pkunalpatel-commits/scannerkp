"""
Expiry selection helpers.
Supports Current / Next / Any available expiry with automatic updates.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from core.logger import logger

from core.instrument_master import InstrumentMaster


class ExpiryManager:
    def __init__(self, master: InstrumentMaster):
        self.master = master

    def current_expiry(self, symbol: str, as_of: Optional[date] = None) -> Optional[date]:
        """Nearest expiry that is still active (today or future)."""
        as_of = as_of or date.today()
        expiries = self.master.get_expiries(symbol)
        future = [e for e in expiries if e >= as_of]
        return min(future) if future else None

    def next_expiry(self, symbol: str, as_of: Optional[date] = None) -> Optional[date]:
        as_of = as_of or date.today()
        expiries = self.master.get_expiries(symbol)
        future = sorted(e for e in expiries if e >= as_of)
        return future[1] if len(future) > 1 else (future[0] if future else None)

    def all_expiries(self, symbol: str) -> List[date]:
        return self.master.get_expiries(symbol)

    def select(
        self,
        symbol: str,
        mode: str = "current",          # current | next | specific
        specific: Optional[date] = None,
    ) -> Optional[date]:
        if mode == "specific" and specific:
            return specific
        if mode == "next":
            return self.next_expiry(symbol)
        return self.current_expiry(symbol)

    def is_expired(self, expiry: date, as_of: Optional[date] = None) -> bool:
        as_of = as_of or date.today()
        return expiry < as_of
