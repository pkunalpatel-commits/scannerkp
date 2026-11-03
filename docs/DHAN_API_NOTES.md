# DhanHQ API Notes for this Scanner

## Authentication
- Client ID + Access Token (JWT)
- Token typically valid ~24 hours – regenerate daily from web.dhan.co → Access DhanHQ APIs

## Required Subscription
- **Data API** (live feed, quotes, option chain) – paid plan
- Trading APIs alone are free but insufficient for this scanner

## Key Endpoints Used
| Purpose | Endpoint / Method |
|---------|-------------------|
| Instrument master | Public CSV (or Dhan instrument download) |
| Live ticks + OI | WebSocket `wss://api-feed.dhan.co?...` Full Packet (code 21) |
| Snapshot quotes | POST `/v2/marketfeed/quote` |
| Option chain (fallback) | POST `/v2/optionchain` |
| Previous day OI | Available in Prev Close packet & Option Chain response |

## Rate Limits (approximate – always check latest docs)
- Live Feed: 5 connections × 5000 instruments
- Subscribe message: max 100 instruments
- Market Quote REST: 1 request / second, up to 1000 instruments

## Binary Packet Layout
Refer to the official Live Market Feed documentation for the exact byte layout of:
- Response Header
- Full Packet (LTP, Volume, OI, OHLC, depth…)
- OI Packet
- Prev Close Packet

The `dhan_market_feed.py` module contains a pragmatic placeholder parser. For production, either:
1. Use the official `dhanhq.MarketFeed` class, or
2. Implement the exact struct according to the current Dhan annexure.

## Security ID Mapping
Never hard-code. Always derive from the instrument master CSV after filtering `OPTSTK` / `OPTIDX`.
