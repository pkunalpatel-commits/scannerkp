# NSE F&O Multi-Stock Options OI Gain Scanner

**Dhan API | Live OI Monitoring | Dynamic ATM ± N | Multi-Timeframe**

Professional desktop scanner that monitors Open Interest changes across all selected NSE F&O stocks, dynamically selects ATM ± N CE/PE strikes, and surfaces OI Gain %, LTP, Turnover and LTP × ΔOI across multiple timeframes (1 minute → 1 day).

> **Scope**: Strictly OI / LTP / Turnover focused. No technical indicators, no buy/sell signals.

---

## Features

- Official **DhanHQ v2** integration (REST + WebSocket Live Market Feed)
- Automatic **instrument master** download & parsing (no hard-coded security IDs / expiries / strike intervals)
- **Dynamic ATM ± N** strike selection (independent CE/PE ranges supported)
- Multi-timeframe OI baselines: 1m, 2m, 3m, 5m, 10m, 15m, 30m, 60m, 2H, 3H, 4H, 1D
- Configurable OI Gain % thresholds per timeframe
- Live scanner table with sorting & filters
- Multi-timeframe comparison view
- Desktop alerts + alert history (de-duplicated)
- SQLite persistence of timestamped OI snapshots
- Clean modular architecture (see `core/` and `ui/`)

---

## Requirements

| Item | Notes |
|------|-------|
| Python | 3.10+ |
| Dhan Account | With **Data API** subscription (₹499/mo approx.) |
| Client ID + Access Token | Generated daily from DhanHQ portal |
| OS | Windows / Linux / macOS (PySide6) |

### Dhan API Limits (official)

- Live Feed: up to **5 concurrent WebSockets**, **5000 instruments** per connection, **100 instruments** per subscribe message
- Market Quote REST: up to 1000 instruments / request, **1 request/second**
- Access token validity ≈ 24 hours
- Full Packet (RequestCode 21) preferred for LTP + Volume + OI

---

## Installation

```bash
git clone https://github.com/<your-username>/nse_fo_oi_scanner.git
cd nse_fo_oi_scanner

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Optional – place instrument master manually

If the automatic download fails, download the latest scrip master CSV from Dhan and save it as:

```
data/instrument_master.csv
```

---

## Configuration

1. Open the application.
2. Enter your **Dhan Client ID** and **Access Token**.
3. Click **Connect**.
4. Type F&O symbols (comma-separated), e.g. `SBIN,INFY,RELIANCE,TCS`.
5. Set **ATM ± N** (default 3).
6. Click **Start Scanner**.

You can also set credentials via environment variables:

```bash
export DHAN_CLIENT_ID=your_client_id
export DHAN_ACCESS_TOKEN=your_access_token
```

---

## Project Structure

```
nse_fo_oi_scanner/
├── main.py                     # Entry point
├── requirements.txt
├── README.md
├── config/
│   └── settings.py             # Thresholds, timeframes, paths
├── core/
│   ├── dhan_auth.py
│   ├── instrument_master.py
│   ├── expiry_manager.py
│   ├── atm_strike_manager.py
│   ├── subscription_manager.py
│   ├── dhan_market_feed.py
│   ├── oi_calculation_engine.py
│   ├── turnover_engine.py
│   ├── timeframe_engine.py
│   ├── scanner_engine.py
│   ├── alert_engine.py
│   └── database_manager.py
├── ui/
│   └── dashboard.py            # PySide6 GUI
├── data/                       # SQLite + instrument CSV
├── logs/
└── docs/
```

---

## Building a Windows EXE

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "NSE_OI_Scanner" ^
  --add-data "config;config" ^
  --add-data "ui;ui" ^
  main.py
```

The executable will appear under `dist/NSE_OI_Scanner/`.

---

## Important Notes & Limitations

1. **Data API subscription is mandatory** for live market feed and quotes.
2. The binary WebSocket parser is intentionally minimal; for production you should use the official `dhanhq.MarketFeed` helper or implement the exact Full-Packet struct from the latest Dhan docs.
3. Underlying equity security IDs must be resolved from the instrument master (or a separate equity master) to fetch accurate LTPs for ATM calculation.
4. 1D baseline uses the last available previous-day snapshot stored in SQLite; for perfect EOD alignment you may want to snapshot at market close.
5. Rate limits are enforced by design – never exceed the official limits.
6. This scanner **does not** place orders or generate trading signals.

---

## Development Roadmap (suggested)

- [ ] Full binary Full-Packet decoder
- [ ] Automatic underlying security-id resolution
- [ ] Option-chain snapshot fallback for previous OI
- [ ] User-defined scanner presets (save/load JSON)
- [ ] Export filtered results to CSV
- [ ] Dark / light theme toggle

---

## License

MIT – use at your own risk. This is educational / research software. Always verify data with your broker terminal before making trading decisions.

---

## Disclaimer

Open Interest and turnover figures are derived from exchange data provided by Dhan. The authors accept no liability for trading losses incurred through use of this software.
