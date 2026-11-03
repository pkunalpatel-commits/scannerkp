"""
PySide6 professional dashboard for the OI Gain Scanner.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)

from config.settings import (
    APP_NAME,
    APP_VERSION,
    MAIN_TABLE_COLUMNS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    ATM_N_OPTIONS,
    DEFAULT_ATM_N,
)
from core.scanner_engine import ScannerRow


class Dashboard(QMainWindow):
    credentials_submitted = Signal(str, str)          # client_id, token
    start_scan = Signal()
    stop_scan = Signal()
    symbols_changed = Signal(list)
    atm_n_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._build_ui()
        self._rows_cache: List[ScannerRow] = []

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # ---- Top bar: credentials + controls ----
        top = QHBoxLayout()
        self.client_id_edit = QLineEdit()
        self.client_id_edit.setPlaceholderText("Dhan Client ID")
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("Access Token")
        self.token_edit.setEchoMode(QLineEdit.Password)
        btn_connect = QPushButton("Connect")
        btn_connect.clicked.connect(self._on_connect)

        top.addWidget(QLabel("Client ID:"))
        top.addWidget(self.client_id_edit)
        top.addWidget(QLabel("Token:"))
        top.addWidget(self.token_edit)
        top.addWidget(btn_connect)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        top.addWidget(self.status_label)
        top.addStretch()
        root.addLayout(top)

        # ---- Control panel ----
        ctrl = QHBoxLayout()

        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("Symbols (comma separated) e.g. SBIN,INFY,RELIANCE")
        self.symbol_edit.setMinimumWidth(320)
        btn_apply_sym = QPushButton("Apply Symbols")
        btn_apply_sym.clicked.connect(self._on_symbols)

        self.atm_spin = QSpinBox()
        self.atm_spin.setRange(0, 20)
        self.atm_spin.setValue(DEFAULT_ATM_N)
        self.atm_spin.setPrefix("ATM ± ")
        self.atm_spin.valueChanged.connect(lambda v: self.atm_n_changed.emit(v))

        self.btn_start = QPushButton("Start Scanner")
        self.btn_start.clicked.connect(lambda: self.start_scan.emit())
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(lambda: self.stop_scan.emit())
        self.btn_stop.setEnabled(False)

        ctrl.addWidget(QLabel("Stocks:"))
        ctrl.addWidget(self.symbol_edit)
        ctrl.addWidget(btn_apply_sym)
        ctrl.addWidget(self.atm_spin)
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addStretch()
        root.addLayout(ctrl)

        # ---- Tabs ----
        tabs = QTabWidget()
        root.addWidget(tabs)

        # Main scanner table
        self.table = QTableWidget(0, len(MAIN_TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(MAIN_TABLE_COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        tabs.addTab(self.table, "Live Scanner")

        # Multi-TF comparison placeholder
        self.mtf_table = QTableWidget(0, 8)
        self.mtf_table.setHorizontalHeaderLabels(
            ["Stock", "Contract", "1m", "5m", "15m", "30m", "1H", "1D"]
        )
        tabs.addTab(self.mtf_table, "Multi-Timeframe")

        # Alerts
        self.alert_log = QTextEdit()
        self.alert_log.setReadOnly(True)
        tabs.addTab(self.alert_log, "Alerts")

        # Status bar
        self.statusBar().showMessage("Ready – enter Dhan credentials and select stocks")

    def _on_connect(self) -> None:
        cid = self.client_id_edit.text().strip()
        tok = self.token_edit.text().strip()
        if not cid or not tok:
            QMessageBox.warning(self, "Missing credentials", "Enter Client ID and Access Token")
            return
        self.credentials_submitted.emit(cid, tok)

    def _on_symbols(self) -> None:
        raw = self.symbol_edit.text().strip()
        symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
        self.symbols_changed.emit(symbols)

    @Slot(bool)
    def set_connected(self, ok: bool) -> None:
        if ok:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.btn_start.setEnabled(True)
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: #c0392b; font-weight: bold;")

    @Slot(bool)
    def set_scanning(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def update_rows(self, rows: List[ScannerRow]) -> None:
        self._rows_cache = rows
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            values = [
                row.stock,
                row.expiry,
                f"{row.strike:.0f}",
                row.option_type,
                f"{row.atm_distance:.0f}",
                f"{row.ltp:.2f}",
                f"{row.ltp_change_pct:+.2f}%",
                f"{row.turnover:,.0f}" + ("*" if row.turnover_estimated else ""),
                f"{row.current_oi:,}",
                f"{row.previous_oi:,}",
                f"{row.oi_change:+,}",
                f"{row.oi_gain_pct:+.2f}%",
                f"{row.ltp_x_oi_change:,.0f}",
                f"{row.notional:,.0f}",
                row.timeframe,
                row.updated.strftime("%H:%M:%S"),
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                # Colour OI Gain
                if c == 11:  # OI Gain %
                    if row.oi_gain_pct > 0:
                        item.setForeground(QColor("#27ae60"))
                    elif row.oi_gain_pct < 0:
                        item.setForeground(QColor("#c0392b"))
                self.table.setItem(r, c, item)

        self.table.setSortingEnabled(True)
        self.statusBar().showMessage(
            f"Updated {len(rows)} rows @ {datetime.now().strftime('%H:%M:%S')}"
        )

    def append_alert(self, text: str) -> None:
        self.alert_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")


def run_app(dashboard: Dashboard) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    dashboard.show()
    return app.exec()
