#!/usr/bin/env python3
"""
NSE F&O Multi-Stock Options OI Gain Scanner
Entry point – wires all modules together.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from config.settings import LOG_DIR, APP_NAME
from core.logger import logger, _HAS_LOGURU
from core.dhan_auth import DhanAuth
from core.instrument_master import InstrumentMaster
from core.expiry_manager import ExpiryManager
from core.atm_strike_manager import ATMStrikeManager
from core.oi_calculation_engine import OICalculationEngine
from core.turnover_engine import TurnoverEngine
from core.timeframe_engine import TimeframeEngine
from core.scanner_engine import ScannerEngine
from core.alert_engine import AlertEngine
from core.database_manager import DatabaseManager
from core.dhan_market_feed import DhanMarketFeed
from ui.dashboard import Dashboard, run_app


# ---------------------------------------------------------------------
# Logging (file handler only when loguru is present)
# ---------------------------------------------------------------------
if _HAS_LOGURU:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            LOG_DIR / "scanner_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="14 days",
            level="INFO",
        )
    except Exception:
        pass
else:
    logger.info("loguru not available – using standard logging")


class ScannerWorker(QObject):
    """
    Background worker that owns the heavy lifting.
    Runs inside a QThread so the GUI never freezes.
    """

    rows_ready = Signal(list)
    alert_ready = Signal(str)
    status = Signal(str)
    connected = Signal(bool)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.auth = DhanAuth()
        self.master = InstrumentMaster()
        self.expiry_mgr = ExpiryManager(self.master)
        self.atm_mgr = ATMStrikeManager(self.master, self.expiry_mgr)
        self.oi_engine = OICalculationEngine()
        self.turnover_engine = TurnoverEngine()
        self.tf_engine = TimeframeEngine()
        self.scanner = ScannerEngine(
            self.master, self.atm_mgr, self.oi_engine, self.tf_engine, self.turnover_engine
        )
        self.alerts = AlertEngine()
        self.db = DatabaseManager()
        self.feed: DhanMarketFeed | None = None
        self._running = False
        self._poll_timer: QTimer | None = None

    @Slot(str, str)
    def connect_dhan(self, client_id: str, token: str) -> None:
        try:
            self.auth.set_credentials(client_id, token)
            ok = self.auth.test_connection()
            self.connected.emit(ok)
            if ok:
                self.status.emit("Dhan API connected")
                # Load instrument master
                if self.master.load(force_download=False):
                    self.status.emit(
                        f"Instrument master loaded – {len(self.master.list_fno_symbols())} F&O stocks"
                    )
                else:
                    self.error.emit("Failed to load instrument master")
            else:
                self.error.emit("Dhan connection test failed – check credentials / Data API subscription")
        except Exception as exc:
            self.error.emit(str(exc))
            logger.exception(exc)

    @Slot(list)
    def set_symbols(self, symbols: list) -> None:
        self.scanner.set_symbols(symbols)
        self.status.emit(f"Selected symbols: {', '.join(symbols) or '(none)'}")

    @Slot(int)
    def set_atm_n(self, n: int) -> None:
        self.scanner.set_atm_n(n)
        self.status.emit(f"ATM ± {n}")

    @Slot()
    def start(self) -> None:
        if not self.auth.is_configured():
            self.error.emit("Connect with valid Dhan credentials first")
            return
        if not self.scanner.selected_symbols:
            self.error.emit("Select at least one stock")
            return

        self._running = True
        self.status.emit("Scanner started")

        # Bootstrap: fetch underlying LTPs via REST quote and seed ATM
        try:
            client = self.auth.get_client()
            # For demo we use a simple quote call for a few underlyings
            # In production expand to full list + WebSocket for underlyings
            for sym in list(self.scanner.selected_symbols)[:20]:
                # Placeholder – real implementation maps symbol → equity security_id
                # and calls marketfeed/quote or option-chain for underlying LTP
                # Here we seed with a dummy LTP so ATM logic can be exercised offline
                dummy_ltp = 1000.0
                sel = self.scanner.update_underlying_ltp(sym, dummy_ltp)
                if sel:
                    logger.info(
                        f"{sym} ATM={sel.atm_strike} CE={len(sel.ce_contracts)} PE={len(sel.pe_contracts)}"
                    )
        except Exception as exc:
            logger.warning(f"Bootstrap LTP failed (continuing): {exc}")

        # Start polling timer (GUI-thread safe via Qt)
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(3000)  # 3 s refresh
        self._poll_timer.timeout.connect(self._poll_once)
        self._poll_timer.start()

    @Slot()
    def stop(self) -> None:
        self._running = False
        if self._poll_timer:
            self._poll_timer.stop()
        if self.feed:
            self.feed.stop()
        self.status.emit("Scanner stopped")

    def _poll_once(self) -> None:
        if not self._running:
            return
        try:
            # In a full implementation this would:
            # 1. Batch-fetch quotes for all desired security_ids via Market Quote API
            # 2. Update oi_engine + scanner
            # 3. Emit rows + alerts
            rows = self.scanner.build_rows()
            self.rows_ready.emit(rows)

            for row in rows:
                threshold = self.tf_engine.get_threshold(row.timeframe)
                alert = self.alerts.check_and_emit(
                    row.security_id,
                    {
                        "stock": row.stock,
                        "expiry": row.expiry,
                        "strike": row.strike,
                        "option_type": row.option_type,
                        "atm_distance": row.atm_distance,
                        "ltp": row.ltp,
                        "ltp_change_pct": row.ltp_change_pct,
                        "turnover": row.turnover,
                        "current_oi": row.current_oi,
                        "previous_oi": row.previous_oi,
                        "oi_change": row.oi_change,
                        "oi_gain_pct": row.oi_gain_pct,
                        "ltp_x_oi_change": row.ltp_x_oi_change,
                        "timeframe": row.timeframe,
                    },
                    threshold,
                )
                if alert:
                    self.alert_ready.emit(alert.message)
        except Exception as exc:
            logger.exception(exc)
            self.error.emit(str(exc))


class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.dashboard = Dashboard()
        self.worker = ScannerWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # Signals
        self.dashboard.credentials_submitted.connect(self.worker.connect_dhan)
        self.dashboard.symbols_changed.connect(self.worker.set_symbols)
        self.dashboard.atm_n_changed.connect(self.worker.set_atm_n)
        self.dashboard.start_scan.connect(self.worker.start)
        self.dashboard.stop_scan.connect(self.worker.stop)

        self.worker.connected.connect(self.dashboard.set_connected)
        self.worker.rows_ready.connect(self.dashboard.update_rows)
        self.worker.alert_ready.connect(self.dashboard.append_alert)
        self.worker.status.connect(lambda m: self.dashboard.statusBar().showMessage(m))
        self.worker.error.connect(self._on_error)

        self.thread.start()

    def _on_error(self, msg: str) -> None:
        logger.error(msg)
        QMessageBox.critical(self.dashboard, "Error", msg)

    def run(self) -> int:
        self.dashboard.show()
        code = self.app.exec()
        self.worker.stop()
        self.thread.quit()
        self.thread.wait(2000)
        return code


def main() -> int:
    logger.info(f"Starting {APP_NAME}")
    try:
        application = Application()
        return application.run()
    except Exception:
        logger.exception("Fatal error")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
