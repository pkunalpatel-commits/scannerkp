"""
Manages WebSocket instrument subscriptions.
- Prevents duplicates
- Batches ≤100 instruments per message
- Respects 5000 limit per connection
- Auto add / remove when ATM range changes
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from core.logger import logger

from config.settings import MAX_INSTRUMENTS_PER_SUBSCRIBE_MSG, MAX_INSTRUMENTS_PER_WS
from core.instrument_master import OptionContract


class SubscriptionManager:
    def __init__(self):
        # security_id → (ExchangeSegment, SecurityId)
        self._subscribed: Set[str] = set()
        self._pending_add: Set[str] = set()
        self._pending_remove: Set[str] = set()

    @property
    def current_count(self) -> int:
        return len(self._subscribed)

    def is_subscribed(self, security_id: str) -> bool:
        return str(security_id) in self._subscribed

    def plan_update(self, desired_contracts: List[OptionContract]) -> Tuple[List[str], List[str]]:
        """
        Returns (to_subscribe, to_unsubscribe) security_id lists.
        """
        desired_ids = {c.security_id for c in desired_contracts}
        to_add = list(desired_ids - self._subscribed)
        to_remove = list(self._subscribed - desired_ids)
        return to_add, to_remove

    def mark_subscribed(self, security_ids: List[str]) -> None:
        for sid in security_ids:
            self._subscribed.add(str(sid))
            self._pending_add.discard(str(sid))

    def mark_unsubscribed(self, security_ids: List[str]) -> None:
        for sid in security_ids:
            self._subscribed.discard(str(sid))
            self._pending_remove.discard(str(sid))

    def batch(self, security_ids: List[str], batch_size: int = MAX_INSTRUMENTS_PER_SUBSCRIBE_MSG) -> List[List[str]]:
        """Split into chunks safe for one WebSocket message."""
        return [security_ids[i:i + batch_size] for i in range(0, len(security_ids), batch_size)]

    def can_add(self, count: int) -> bool:
        return (self.current_count + count) <= MAX_INSTRUMENTS_PER_WS

    def build_subscribe_payload(self, security_ids: List[str], request_code: int = 21) -> dict:
        """
        Full packet = 21, Quote = 17, Ticker = 15
        Official JSON structure.
        """
        instruments = [
            {"ExchangeSegment": "NSE_FNO", "SecurityId": str(sid)}
            for sid in security_ids
        ]
        return {
            "RequestCode": request_code,
            "InstrumentCount": len(instruments),
            "InstrumentList": instruments,
        }

    def build_unsubscribe_payload(self, security_ids: List[str], request_code: int = 22) -> dict:
        instruments = [
            {"ExchangeSegment": "NSE_FNO", "SecurityId": str(sid)}
            for sid in security_ids
        ]
        return {
            "RequestCode": request_code,
            "InstrumentCount": len(instruments),
            "InstrumentList": instruments,
        }

    def reset(self) -> None:
        self._subscribed.clear()
        self._pending_add.clear()
        self._pending_remove.clear()
