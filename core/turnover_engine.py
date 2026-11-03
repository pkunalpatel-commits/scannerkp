"""
Turnover calculation.
Prefers actual traded turnover when available; otherwise estimates
and clearly labels the value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TurnoverResult:
    security_id: str
    turnover: float
    is_estimated: bool
    volume: int
    avg_price: float


class TurnoverEngine:
    def compute(
        self,
        security_id: str,
        volume: int,
        ltp: float,
        avg_price: Optional[float] = None,
        actual_turnover: Optional[float] = None,
    ) -> TurnoverResult:
        if actual_turnover is not None and actual_turnover > 0:
            return TurnoverResult(
                security_id=security_id,
                turnover=actual_turnover,
                is_estimated=False,
                volume=volume,
                avg_price=avg_price or ltp,
            )

        # Estimate: Volume × average traded price (or LTP as proxy)
        px = avg_price if avg_price and avg_price > 0 else ltp
        estimated = volume * px
        return TurnoverResult(
            security_id=security_id,
            turnover=round(estimated, 2),
            is_estimated=True,
            volume=volume,
            avg_price=px,
        )
