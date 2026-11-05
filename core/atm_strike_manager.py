"""
Dynamic ATM ± N strike selection.
- Calculates ATM from underlying LTP
- Uses real strike interval from instrument master
- Supports independent CE / PE ranges
- Returns list of OptionContract objects to subscribe
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from core.logger import logger

from core.instrument_master import InstrumentMaster, OptionContract
from core.expiry_manager import ExpiryManager


@dataclass
class ATMSelection:
    symbol: str
    expiry: date
    underlying_ltp: float
    atm_strike: float
    n: int
    ce_contracts: List[OptionContract]
    pe_contracts: List[OptionContract]
    strike_interval: float

    @property
    def all_contracts(self) -> List[OptionContract]:
        return self.ce_contracts + self.pe_contracts

    def distance(self, strike: float) -> float:
        return abs(strike - self.atm_strike)


class ATMStrikeManager:
    def __init__(self, master: InstrumentMaster, expiry_mgr: ExpiryManager):
        self.master = master
        self.expiry_mgr = expiry_mgr
        # Cache last selection per symbol to detect changes
        self._last: Dict[str, ATMSelection] = {}

    def compute_atm(self, ltp: float, interval: float) -> float:
        if interval <= 0:
            return round(ltp)
        # Nearest strike
        return round(ltp / interval) * interval

    def select_strikes(
        self,
        symbol: str,
        underlying_ltp: float,
        n: int = 3,
        expiry_mode: str = "current",
        specific_expiry: Optional[date] = None,
        ce_n: Optional[int] = None,
        pe_n: Optional[int] = None,
    ) -> Optional[ATMSelection]:
        """
        Returns ATMSelection containing CE & PE contracts for ATM ± N.
        Total strikes per side = (2 * N) + 1
        """
        symbol = symbol.upper()
        u = self.master.get_underlying(symbol)
        if not u:
            logger.warning(f"Unknown underlying: {symbol}")
            return None

        expiry = self.expiry_mgr.select(symbol, expiry_mode, specific_expiry)
        if not expiry:
            logger.warning(f"No valid expiry for {symbol}")
            return None

        interval = u.strike_interval or 50.0   # fallback, should be rare
        atm = self.compute_atm(underlying_ltp, interval)

        ce_n = ce_n if ce_n is not None else n
        pe_n = pe_n if pe_n is not None else n

        ce_all = self.master.get_contracts(symbol, expiry, "CE")
        pe_all = self.master.get_contracts(symbol, expiry, "PE")

        def pick(contracts: List[OptionContract], side_n: int) -> List[OptionContract]:
            if not contracts:
                return []
            # Find closest to ATM
            sorted_c = sorted(contracts, key=lambda c: abs(c.strike - atm))
            # Take the ATM one + side_n above + side_n below
            atm_contract = sorted_c[0]
            above = [c for c in contracts if c.strike > atm_contract.strike]
            below = [c for c in contracts if c.strike < atm_contract.strike]
            above = sorted(above, key=lambda c: c.strike)[:side_n]
            below = sorted(below, key=lambda c: c.strike, reverse=True)[:side_n]
            selected = below[::-1] + [atm_contract] + above
            # Deduplicate by strike
            seen: Set[float] = set()
            result = []
            for c in selected:
                if c.strike not in seen:
                    seen.add(c.strike)
                    result.append(c)
            return result

        ce_sel = pick(ce_all, ce_n)
        pe_sel = pick(pe_all, pe_n)

        selection = ATMSelection(
            symbol=symbol,
            expiry=expiry,
            underlying_ltp=underlying_ltp,
            atm_strike=atm,
            n=n,
            ce_contracts=ce_sel,
            pe_contracts=pe_sel,
            strike_interval=interval,
        )
        self._last[symbol] = selection
        return selection

    def get_last(self, symbol: str) -> Optional[ATMSelection]:
        return self._last.get(symbol.upper())

    def needs_resubscribe(self, symbol: str, new_ltp: float, n: int) -> bool:
        """True if ATM changed enough to alter the strike set."""
        last = self.get_last(symbol)
        if not last:
            return True
        new_atm = self.compute_atm(new_ltp, last.strike_interval)
        return abs(new_atm - last.atm_strike) >= last.strike_interval * 0.5
