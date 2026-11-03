"""
OI Change & OI Gain % calculation engine.
Each timeframe maintains its own baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from loguru import logger

from config.settings import TIMEFRAMES


@dataclass
class OISnapshot:
    security_id: str
    oi: int
    ltp: float
    volume: int
    timestamp: datetime


@dataclass
class OIResult:
    security_id: str
    timeframe: str
    current_oi: int
    previous_oi: int
    oi_change: int
    oi_gain_pct: float
    ltp: float
    ltp_change_pct: float
    ltp_x_oi_change: float
    notional: float          # LTP × ΔOI × lot_size
    updated_at: datetime
    is_valid: bool = True


class OICalculationEngine:
    def __init__(self):
        # security_id → timeframe → baseline OISnapshot
        self._baselines: Dict[str, Dict[str, OISnapshot]] = {}
        # security_id → latest snapshot
        self._latest: Dict[str, OISnapshot] = {}
        # security_id → previous LTP for % change
        self._prev_ltp: Dict[str, float] = {}

    def update_snapshot(
        self,
        security_id: str,
        oi: int,
        ltp: float,
        volume: int = 0,
        ts: Optional[datetime] = None,
    ) -> None:
        ts = ts or datetime.now()
        snap = OISnapshot(security_id, oi, ltp, volume, ts)
        self._latest[security_id] = snap

        # Initialise baselines if missing
        if security_id not in self._baselines:
            self._baselines[security_id] = {}
        for tf in TIMEFRAMES:
            if tf not in self._baselines[security_id]:
                self._baselines[security_id][tf] = snap

    def set_baseline(self, security_id: str, timeframe: str, snap: OISnapshot) -> None:
        if security_id not in self._baselines:
            self._baselines[security_id] = {}
        self._baselines[security_id][timeframe] = snap

    def maybe_roll_baseline(self, security_id: str, timeframe: str) -> None:
        """
        Roll the baseline when the timeframe window has elapsed.
        Simple wall-clock approach; production can align to exchange bars.
        """
        latest = self._latest.get(security_id)
        base = self._baselines.get(security_id, {}).get(timeframe)
        if not latest or not base:
            return
        minutes = TIMEFRAMES.get(timeframe, 1)
        if (latest.timestamp - base.timestamp) >= timedelta(minutes=minutes):
            self._baselines[security_id][timeframe] = latest

    def calculate(
        self,
        security_id: str,
        timeframe: str,
        lot_size: int = 1,
    ) -> Optional[OIResult]:
        latest = self._latest.get(security_id)
        if not latest:
            return None

        self.maybe_roll_baseline(security_id, timeframe)
        base = self._baselines.get(security_id, {}).get(timeframe)
        if not base:
            # First observation – treat as zero change
            base = latest

        prev_oi = base.oi
        curr_oi = latest.oi
        oi_change = curr_oi - prev_oi

        if prev_oi == 0:
            oi_gain_pct = 0.0 if oi_change == 0 else 100.0
        else:
            oi_gain_pct = (oi_change / prev_oi) * 100.0

        prev_ltp = self._prev_ltp.get(security_id, latest.ltp)
        if prev_ltp == 0:
            ltp_chg_pct = 0.0
        else:
            ltp_chg_pct = ((latest.ltp - prev_ltp) / prev_ltp) * 100.0
        self._prev_ltp[security_id] = latest.ltp

        ltp_x_oi = latest.ltp * oi_change
        notional = ltp_x_oi * lot_size

        return OIResult(
            security_id=security_id,
            timeframe=timeframe,
            current_oi=curr_oi,
            previous_oi=prev_oi,
            oi_change=oi_change,
            oi_gain_pct=round(oi_gain_pct, 2),
            ltp=latest.ltp,
            ltp_change_pct=round(ltp_chg_pct, 2),
            ltp_x_oi_change=round(ltp_x_oi, 2),
            notional=round(notional, 2),
            updated_at=latest.timestamp,
            is_valid=True,
        )

    def calculate_all_timeframes(
        self, security_id: str, lot_size: int = 1
    ) -> Dict[str, OIResult]:
        results = {}
        for tf in TIMEFRAMES:
            r = self.calculate(security_id, tf, lot_size)
            if r:
                results[tf] = r
        return results
