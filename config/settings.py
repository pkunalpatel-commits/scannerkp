"""
Application settings and configurable defaults.
All thresholds, timeframes and paths are centralized here.
"""

from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "oi_scanner.db"
INSTRUMENT_MASTER_PATH = DATA_DIR / "instrument_master.csv"
SETTINGS_JSON = DATA_DIR / "user_settings.json"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------
# Dhan API
# ---------------------------------------------------------------------
# Fill these via environment variables or UI (never hard-code in repo)
DHAN_CLIENT_ID = ""          # set at runtime
DHAN_ACCESS_TOKEN = ""       # set at runtime (valid ~24h)

# Official endpoints (v2)
DHAN_BASE_URL = "https://api.dhan.co/v2"
DHAN_FEED_WS = "wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"

# Rate limits (official)
MAX_INSTRUMENTS_PER_WS = 5000
MAX_INSTRUMENTS_PER_SUBSCRIBE_MSG = 100
MAX_WS_CONNECTIONS = 5
QUOTE_RATE_LIMIT_PER_SEC = 1

# ---------------------------------------------------------------------
# Timeframes (minutes)
# ---------------------------------------------------------------------
TIMEFRAMES: Dict[str, int] = {
    "1m": 1,
    "2m": 2,
    "3m": 3,
    "5m": 5,
    "10m": 10,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "2H": 120,
    "3H": 180,
    "4H": 240,
    "1D": 1440,
}

DEFAULT_ENABLED_TIMEFRAMES: List[str] = [
    "1m", "5m", "15m", "30m", "60m", "1D"
]

# Default OI Gain % thresholds per timeframe (user-configurable)
DEFAULT_OI_THRESHOLDS: Dict[str, float] = {
    "1m": 5.0,
    "2m": 5.0,
    "3m": 7.0,
    "5m": 10.0,
    "10m": 10.0,
    "15m": 12.0,
    "30m": 15.0,
    "60m": 15.0,
    "2H": 18.0,
    "3H": 18.0,
    "4H": 20.0,
    "1D": 25.0,
}

# ---------------------------------------------------------------------
# ATM / Strike selection
# ---------------------------------------------------------------------
ATM_N_OPTIONS = [0, 1, 2, 3, 5, 10]   # 0 = ATM only
DEFAULT_ATM_N = 3

# ---------------------------------------------------------------------
# Scanner behaviour
# ---------------------------------------------------------------------
MIN_ABSOLUTE_OI_CHANGE = 50          # ignore tiny OI moves
HISTORY_RETENTION_DAYS = 7
SNAPSHOT_INTERVAL_SEC = 5           # how often we persist OI snapshots
STALE_DATA_SECONDS = 30             # mark row as stale after this

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
APP_NAME = "NSE F&O OI Gain Scanner"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900

# Column order for main table
MAIN_TABLE_COLUMNS = [
    "Stock",
    "Expiry",
    "Strike",
    "Type",
    "ATM Dist",
    "LTP",
    "LTP Chg %",
    "Turnover",
    "Curr OI",
    "Prev OI",
    "Δ OI",
    "OI Gain %",
    "LTP × ΔOI",
    "Notional",
    "TF",
    "Updated",
]
