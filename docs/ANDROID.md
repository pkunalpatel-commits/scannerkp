# Android APK Status

## Short answer
There is **no working Android APK** for this scanner yet.

## Why
The application is built with **PySide6 (Qt for desktop)**.  
A real Android APK that keeps live WebSocket subscriptions for many F&O contracts, maintains multi-timeframe OI baselines, and shows a dense sortable table is a different product. It requires:

- New UI framework (Kivy, Flutter, or native Android)
- Foreground service + careful battery handling
- Different networking and background execution model
- Possibly a client-server design (scanner runs on PC/VPS, phone only displays)

## Practical options

| Option | Effort | Recommendation |
|--------|--------|----------------|
| Run the Python app on a Windows/Linux PC | Low | Best for full features |
| Build Windows EXE via GitHub Actions | Low | Already provided |
| Lightweight mobile viewer that talks to a running scanner | Medium | Good next step |
| Full native Android rewrite | High | Only if you need offline mobile trading desk |

## GitHub Actions
- `build-windows.yml` → produces a downloadable Windows EXE artifact
- `build-apk-note.yml` → documents why a full APK is not produced

## Next step if you want mobile
Open an issue describing whether you prefer:
1. A simple Flutter/Kivy companion that shows alerts + top OI movers, or
2. A full Android rewrite of the scanner.

We can then add the corresponding workflow and code structure.
