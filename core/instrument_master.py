"""
Instrument Master management.
Downloads and parses the official Dhan / NSE instrument list.
No hard-coded security IDs, expiries or strike intervals.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
from loguru import logger

from config.settings import INSTRUMENT_MASTER_PATH, DATA_DIR


# Official compact instrument list (update URL if Dhan changes it)
# Users can also drop a CSV manually into data/
INSTRUMENT_CSV_URLS = [
    "https://images.dhan.co/api-data/api-scrip-master.csv",  # common public location
]


@dataclass
class OptionContract:
    security_id: str
    symbol: str                 # underlying e.g. SBIN
    trading_symbol: str
    exchange_segment: str       # NSE_FNO
    instrument: str             # OPTSTK / OPTIDX
    option_type: str            # CE / PE
    strike: float
    expiry: date
    lot_size: int
    tick_size: float
    underlying_security_id: Optional[str] = None


@dataclass
class UnderlyingInfo:
    symbol: str
    security_id: str            # equity / index security id
    exchange_segment: str
    lot_size: int
    strike_interval: float      # derived from available strikes
    option_contracts: List[OptionContract] = field(default_factory=list)
    expiries: List[date] = field(default_factory=list)


class InstrumentMaster:
    """
    Loads, caches and queries the instrument master.
    """

    def __init__(self, csv_path: Path = INSTRUMENT_MASTER_PATH):
        self.csv_path = csv_path
        self.underlyings: Dict[str, UnderlyingInfo] = {}
        self.security_id_map: Dict[str, OptionContract] = {}
        self._raw_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Download / Load
    # ------------------------------------------------------------------
    def download_master(self, force: bool = False) -> bool:
        """Download latest instrument master if missing or forced."""
        if self.csv_path.exists() and not force:
            logger.info(f"Using existing instrument master: {self.csv_path}")
            return True

        for url in INSTRUMENT_CSV_URLS:
            try:
                logger.info(f"Downloading instrument master from {url}")
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                self.csv_path.write_bytes(resp.content)
                logger.success(f"Instrument master saved → {self.csv_path}")
                return True
            except Exception as exc:
                logger.warning(f"Failed to download from {url}: {exc}")

        logger.error(
            "Could not download instrument master. "
            "Place a CSV manually at data/instrument_master.csv"
        )
        return False

    def load(self, force_download: bool = False) -> bool:
        if force_download or not self.csv_path.exists():
            if not self.download_master(force=force_download):
                return False

        try:
            # Dhan CSV columns vary slightly; we normalise
            df = pd.read_csv(self.csv_path, low_memory=False)
            self._raw_df = df
            self._parse(df)
            logger.info(
                f"Loaded {len(self.underlyings)} underlyings, "
                f"{len(self.security_id_map)} option contracts"
            )
            return True
        except Exception as exc:
            logger.exception(f"Failed to parse instrument master: {exc}")
            return False

    def _parse(self, df: pd.DataFrame) -> None:
        # Normalise column names (Dhan uses mixed case)
        col_map = {c.lower().strip(): c for c in df.columns}
        def col(name: str) -> Optional[str]:
            return col_map.get(name.lower())

        required = ["sem_smst_security_id", "sem_trading_symbol", "sem_instrument_name",
                    "sem_expiry_code", "sem_strike_price", "sem_option_type",
                    "sem_exm_exch_id", "sem_segment", "sem_lot_units"]
        # Fallback names used by some Dhan dumps
        alt = {
            "security_id": "SEM_SMST_SECURITY_ID",
            "trading_symbol": "SEM_TRADING_SYMBOL",
            "instrument": "SEM_INSTRUMENT_NAME",
            "expiry": "SEM_EXPIRY_CODE",
            "strike": "SEM_STRIKE_PRICE",
            "option_type": "SEM_OPTION_TYPE",
            "exchange": "SEM_EXM_EXCH_ID",
            "segment": "SEM_SEGMENT",
            "lot_size": "SEM_LOT_UNITS",
            "symbol": "SEM_CUSTOM_SYMBOL",  # sometimes underlying
        }

        # Try to detect columns flexibly
        sid_col = next((c for c in df.columns if "security_id" in c.lower() or "smst_security" in c.lower()), None)
        tsym_col = next((c for c in df.columns if "trading_symbol" in c.lower()), None)
        inst_col = next((c for c in df.columns if "instrument" in c.lower()), None)
        exp_col = next((c for c in df.columns if "expiry" in c.lower()), None)
        strike_col = next((c for c in df.columns if "strike" in c.lower()), None)
        opt_col = next((c for c in df.columns if "option_type" in c.lower() or "opt_type" in c.lower()), None)
        lot_col = next((c for c in df.columns if "lot" in c.lower()), None)
        seg_col = next((c for c in df.columns if "segment" in c.lower()), None)
        under_col = next((c for c in df.columns if "underly" in c.lower() or "custom_symbol" in c.lower() or "symbol_name" in c.lower()), None)

        if not all([sid_col, tsym_col, inst_col]):
            raise ValueError("Instrument CSV missing critical columns. Check format.")

        # Filter F&O options only
        fno_mask = df[inst_col].astype(str).str.upper().isin(["OPTSTK", "OPTIDX", "OPT"])
        if seg_col:
            fno_mask &= df[seg_col].astype(str).str.upper().str.contains("FNO|FO|F&O", na=False)

        options_df = df[fno_mask].copy()
        logger.info(f"Found {len(options_df)} option rows in master")

        underlyings: Dict[str, UnderlyingInfo] = {}
        sec_map: Dict[str, OptionContract] = {}

        for _, row in options_df.iterrows():
            try:
                security_id = str(int(float(row[sid_col])))
                trading_symbol = str(row[tsym_col]).strip()
                instrument = str(row[inst_col]).upper()
                option_type = str(row[opt_col]).upper() if opt_col else ""
                if option_type not in ("CE", "PE", "CALL", "PUT"):
                    # try to parse from trading symbol
                    if trading_symbol.endswith("CE"):
                        option_type = "CE"
                    elif trading_symbol.endswith("PE"):
                        option_type = "PE"
                    else:
                        continue
                if option_type in ("CALL", "C"):
                    option_type = "CE"
                if option_type in ("PUT", "P"):
                    option_type = "PE"

                strike = float(row[strike_col]) if strike_col else 0.0
                lot_size = int(float(row[lot_col])) if lot_col else 1

                # Expiry parsing – Dhan sometimes gives epoch or YYYY-MM-DD
                expiry_raw = row[exp_col] if exp_col else None
                expiry = self._parse_expiry(expiry_raw)
                if expiry is None:
                    continue

                # Underlying symbol
                if under_col and pd.notna(row[under_col]):
                    symbol = str(row[under_col]).strip().upper()
                else:
                    # Heuristic: strip expiry & strike from trading symbol
                    symbol = trading_symbol.split("-")[0].split(" ")[0]
                    # Clean common suffixes
                    for s in ["CE", "PE", "FUT"]:
                        if symbol.endswith(s):
                            symbol = symbol[:-len(s)]
                    symbol = "".join(c for c in symbol if c.isalpha()).upper()

                if not symbol:
                    continue

                contract = OptionContract(
                    security_id=security_id,
                    symbol=symbol,
                    trading_symbol=trading_symbol,
                    exchange_segment="NSE_FNO",
                    instrument=instrument,
                    option_type=option_type,
                    strike=strike,
                    expiry=expiry,
                    lot_size=lot_size,
                    tick_size=0.05,
                )
                sec_map[security_id] = contract

                if symbol not in underlyings:
                    underlyings[symbol] = UnderlyingInfo(
                        symbol=symbol,
                        security_id="",          # filled later if equity master present
                        exchange_segment="NSE_EQ",
                        lot_size=lot_size,
                        strike_interval=0.0,
                    )
                underlyings[symbol].option_contracts.append(contract)
                if expiry not in underlyings[symbol].expiries:
                    underlyings[symbol].expiries.append(expiry)

            except Exception:
                continue

        # Compute strike intervals and sort expiries
        for u in underlyings.values():
            u.expiries.sort()
            strikes = sorted({c.strike for c in u.option_contracts})
            if len(strikes) >= 2:
                diffs = [round(strikes[i+1] - strikes[i], 2) for i in range(len(strikes)-1)]
                # Most common positive diff
                from collections import Counter
                pos = [d for d in diffs if d > 0]
                if pos:
                    u.strike_interval = Counter(pos).most_common(1)[0][0]
            u.lot_size = u.option_contracts[0].lot_size if u.option_contracts else 1

        self.underlyings = underlyings
        self.security_id_map = sec_map

    @staticmethod
    def _parse_expiry(raw) -> Optional[date]:
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return None
        try:
            # epoch seconds
            if isinstance(raw, (int, float)) and raw > 1e9:
                return datetime.utcfromtimestamp(raw).date()
            s = str(raw).strip()
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%Y%m%d"):
                try:
                    return datetime.strptime(s[:10], fmt).date()
                except ValueError:
                    continue
            # Excel serial
            if s.replace(".", "").isdigit():
                from datetime import timedelta
                return (datetime(1899, 12, 30) + timedelta(days=float(s))).date()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def list_fno_symbols(self) -> List[str]:
        return sorted(self.underlyings.keys())

    def get_underlying(self, symbol: str) -> Optional[UnderlyingInfo]:
        return self.underlyings.get(symbol.upper())

    def get_expiries(self, symbol: str) -> List[date]:
        u = self.get_underlying(symbol)
        return u.expiries if u else []

    def get_contracts(
        self,
        symbol: str,
        expiry: date,
        option_type: Optional[str] = None,
    ) -> List[OptionContract]:
        u = self.get_underlying(symbol)
        if not u:
            return []
        result = [
            c for c in u.option_contracts
            if c.expiry == expiry and (option_type is None or c.option_type == option_type)
        ]
        return sorted(result, key=lambda c: c.strike)

    def get_contract_by_id(self, security_id: str) -> Optional[OptionContract]:
        return self.security_id_map.get(str(security_id))

    def get_strike_interval(self, symbol: str) -> float:
        u = self.get_underlying(symbol)
        return u.strike_interval if u else 0.0
