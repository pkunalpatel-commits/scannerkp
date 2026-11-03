"""
Live alert engine.
Generates alerts when OI Gain % crosses the configured threshold for a timeframe.
Includes de-duplication and optional desktop notification / sound.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional, Set, Tuple

from loguru import logger

try:
    from plyer import notification
except ImportError:
    notification = None


@dataclass
class Alert:
    stock: str
    expiry: str
    strike: float
    option_type: str
    atm_distance: float
    ltp: float
    ltp_change_pct: float
    turnover: float
    current_oi: int
    previous_oi: int
    oi_change: int
    oi_gain_pct: float
    ltp_x_oi_change: float
    timeframe: str
    timestamp: datetime
    message: str = ""


class AlertEngine:
    def __init__(self, cooldown_seconds: int = 120):
        self.enabled = True
        self.cooldown = timedelta(seconds=cooldown_seconds)
        # key = (security_id, timeframe) → last alert time
        self._last_alert: Dict[Tuple[str, str], datetime] = {}
        self.history: Deque[Alert] = deque(maxlen=500)
        self.sound_enabled = True
        self.desktop_notify = True

    def check_and_emit(
        self,
        security_id: str,
        row_data: dict,
        threshold: float,
    ) -> Optional[Alert]:
        if not self.enabled:
            return None

        oi_gain = row_data.get("oi_gain_pct", 0.0)
        if abs(oi_gain) < threshold:
            return None

        key = (security_id, row_data["timeframe"])
        now = datetime.now()
        last = self._last_alert.get(key)
        if last and (now - last) < self.cooldown:
            return None  # de-dupe

        alert = Alert(
            stock=row_data["stock"],
            expiry=row_data["expiry"],
            strike=row_data["strike"],
            option_type=row_data["option_type"],
            atm_distance=row_data.get("atm_distance", 0),
            ltp=row_data["ltp"],
            ltp_change_pct=row_data.get("ltp_change_pct", 0),
            turnover=row_data.get("turnover", 0),
            current_oi=row_data["current_oi"],
            previous_oi=row_data["previous_oi"],
            oi_change=row_data["oi_change"],
            oi_gain_pct=oi_gain,
            ltp_x_oi_change=row_data.get("ltp_x_oi_change", 0),
            timeframe=row_data["timeframe"],
            timestamp=now,
            message=(
                f"{row_data['stock']} {row_data['strike']}{row_data['option_type']} "
                f"[{row_data['timeframe']}] OI {oi_gain:+.1f}% "
                f"(Δ {row_data['oi_change']:+,})"
            ),
        )
        self._last_alert[key] = now
        self.history.appendleft(alert)
        self._notify(alert)
        return alert

    def _notify(self, alert: Alert) -> None:
        logger.info(f"ALERT: {alert.message}")
        if self.desktop_notify and notification:
            try:
                notification.notify(
                    title="OI Gain Alert",
                    message=alert.message,
                    app_name="NSE OI Scanner",
                    timeout=8,
                )
            except Exception as exc:
                logger.debug(f"Desktop notify failed: {exc}")

    def clear_history(self) -> None:
        self.history.clear()
