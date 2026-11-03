"""
DhanHQ authentication helper.
Access tokens are short-lived (~24h). User must supply Client ID + Access Token.
Never store secrets in source control.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from loguru import logger

try:
    from dhanhq import DhanContext, dhanhq
except ImportError:
    DhanContext = None  # type: ignore
    dhanhq = None       # type: ignore
    logger.warning("dhanhq package not installed. Run: pip install dhanhq")


@dataclass
class DhanCredentials:
    client_id: str
    access_token: str


class DhanAuth:
    """
    Thin wrapper around official DhanContext.
    """

    def __init__(self, client_id: str = "", access_token: str = ""):
        self.client_id = client_id or os.getenv("DHAN_CLIENT_ID", "")
        self.access_token = access_token or os.getenv("DHAN_ACCESS_TOKEN", "")
        self._context: Optional[DhanContext] = None
        self._client: Optional[dhanhq] = None

    def is_configured(self) -> bool:
        return bool(self.client_id and self.access_token)

    def set_credentials(self, client_id: str, access_token: str) -> None:
        self.client_id = client_id.strip()
        self.access_token = access_token.strip()
        self._context = None
        self._client = None

    def get_context(self) -> DhanContext:
        if not self.is_configured():
            raise RuntimeError(
                "Dhan credentials not set. Provide Client ID and Access Token."
            )
        if self._context is None:
            if DhanContext is None:
                raise RuntimeError("dhanhq package is missing")
            self._context = DhanContext(self.client_id, self.access_token)
        return self._context

    def get_client(self) -> dhanhq:
        if self._client is None:
            self._client = dhanhq(self.get_context())
        return self._client

    def test_connection(self) -> bool:
        """Quick sanity check – fetch fund limits or holdings."""
        try:
            client = self.get_client()
            # Lightweight call
            _ = client.get_fund_limits()
            logger.info("Dhan API connection successful")
            return True
        except Exception as exc:
            logger.error(f"Dhan API connection failed: {exc}")
            return False
