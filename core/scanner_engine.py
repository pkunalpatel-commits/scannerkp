"""
Central scanner orchestration.
Combines ATM selection → subscription → OI calc → filtering → results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

from loguru import logger

from core.atm_strike_manager import ATMStrikeManager, ATMSelection
from core.instrument_master import InstrumentMaster, OptionContract
from core.oi_calculation_engine import OICalculationEngine, OIResult
from core.timeframe_engine import TimeframeEngine
from core.turnover_engine import TurnoverEngine, TurnoverResult
from config.settings import MIN_ABSOLUTE_OI_CHANGE


@dataclass
class ScannerRow:
    stock: str
    expiry: str
    strike: float
    option_type: str
    atm_distance: float
    ltp: float
    ltp_change_pct: float
    turnover: float
    turnover_estimated: bool
    current_oi: int
    previous_oi: int
    oi_change: int
    oi_gain_pct: float
    ltp_x_oi_change: float
    notional: float
    timeframe: str
    updated: datetime
    security_id: str
    lot_size: int


class ScannerEngine:
    def __init__(
        self,
        master: InstrumentMaster,
        atm_mgr: ATMStrikeManager,
        oi_engine: OICalculationEngine,
        tf_engine: TimeframeEngine,
        turnover_engine: TurnoverEngine,
    ):
        self.master = master
        self.atm_mgr = atm_mgr
        self.oi_engine = oi_engine
        self.tf_engine = tf_engine
        self.turnover_engine = turnover_engine

        self.selected_symbols: Set[str] = set()
        self.atm_n: int = 3
        self.expiry_mode: str = "current"
        self.min_oi_change: int = MIN_ABSOLUTE_OI_CHANGE
        self.positive_only: bool = False
        self.negative_only: bool = False

        # symbol → ATMSelection
        self._selections: Dict[str, ATMSelection] = {}
        # security_id → OptionContract
        self._contracts: Dict[str, OptionContract] = {}

    def set_symbols(self, symbols: List[str]) -> None:
        self.selected_symbols = {s.upper() for s in symbols}

    def set_atm_n(self, n: int) -> None:
        self.atm_n = max(0, n)

    def update_underlying_ltp(self, symbol: str, ltp: float) -> Optional[ATMSelection]:
        if symbol.upper() not in self.selected_symbols:
            return None
        sel = self.atm_mgr.select_strikes(
            symbol, ltp, n=self.atm_n, expiry_mode=self.expiry_mode
        )
        if sel:
            self._selections[symbol.upper()] = sel
            for c in sel.all_contracts:
                self._contracts[c.security_id] = c
        return sel

    def on_option_tick(
        self,
        security_id: str,
        oi: int,
        ltp: float,
        volume: int = 0,
        avg_price: float = 0.0,
    ) -> None:
        self.oi_engine.update_snapshot(security_id, oi, ltp, volume)

    def build_rows(self) -> List[ScannerRow]:
        rows: List[ScannerRow] = []
        active_tfs = self.tf_engine.active_list()

        for sid, contract in self._contracts.items():
            lot = contract.lot_size
            for tf in active_tfs:
                result = self.oi_engine.calculate(sid, tf, lot_size=lot)
                if not result:
                    continue

                # Filters
                if abs(result.oi_change) < self.min_oi_change:
                    continue
                if self.positive_only and result.oi_change <= 0:
                    continue
                if self.negative_only and result.oi_change >= 0:
                    continue

                threshold = self.tf_engine.get_threshold(tf)
                # We still emit the row; UI can highlight threshold crossings
                # (caller can filter further if desired)

                turn = self.turnover_engine.compute(
                    sid, volume=0, ltp=result.ltp  # volume from snapshot if needed
                )

                sel = self._selections.get(contract.symbol)
                atm_dist = abs(contract.strike - sel.atm_strike) if sel else 0.0

                rows.append(
                    ScannerRow(
                        stock=contract.symbol,
                        expiry=str(contract.expiry),
                        strike=contract.strike,
                        option_type=contract.option_type,
                        atm_distance=atm_dist,
                        ltp=result.ltp,
                        ltp_change_pct=result.ltp_change_pct,
                        turnover=turn.turnover,
                        turnover_estimated=turn.is_estimated,
                        current_oi=result.current_oi,
                        previous_oi=result.previous_oi,
                        oi_change=result.oi_change,
                        oi_gain_pct=result.oi_gain_pct,
                        ltp_x_oi_change=result.ltp_x_oi_change,
                        notional=result.notional,
                        timeframe=tf,
                        updated=result.updated_at,
                        security_id=sid,
                        lot_size=lot,
                    )
                )
        return rows

    def desired_security_ids(self) -> List[str]:
        ids = []
        for sel in self._selections.values():
            ids.extend(c.security_id for c in sel.all_contracts)
        return list(set(ids))
