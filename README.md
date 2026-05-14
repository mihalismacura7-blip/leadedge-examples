# LeadEdge Examples

Official examples and integration templates for the [LeadEdge](https://leadedge.dev) cross-exchange latency intelligence API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **What is LeadEdge?** A real-time signal API that detects when Binance Futures leads Coinbase Spot. Validated at **90.7% follow-through** with **~150ms median lag** on ETH across 7 days of live data ([full methodology](https://leadedge.dev/blog/validation)).

---

## Quick Start

### 1. Get your API key

Sign up free at [leadedge.dev](https://leadedge.dev) and grab your API key from the dashboard.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
cp .env.example .env
# Edit .env and add your LEADEDGE_API_KEY
```

### 4. Run an example

```bash
python examples/basic_signal_consumer.py
```

You should start receiving signals in real-time.

---

## Examples

| File | Description |
|------|-------------|
| [basic_signal_consumer.py](examples/basic_signal_consumer.py) | Simplest WebSocket consumer — connect and print signals |
| [rest_polling.py](examples/rest_polling.py) | REST API polling alternative if WebSocket isn't available |
| [websocket_with_reconnect.py](examples/websocket_with_reconnect.py) | Production-ready WebSocket with reconnect + heartbeat monitoring |
| [signal_history_export.py](examples/signal_history_export.py) | Export historical signals to CSV for analysis |
| [freqtrade_strategy.py](examples/freqtrade_strategy.py) | Drop-in Freqtrade strategy template |

---

## Sample Signal

```json
{
  "type": "signal",
  "asset": "ETH",
  "direction": "up",
  "magnitude": 0.1654,
  "confidence": 0.907,
  "follow_within_ms": 300,
  "breakeven_fee": 0.1223
}
```

See [docs/signal_schema.md](docs/signal_schema.md) for full schema documentation.

---

## How It Works

1. **Binance Futures moves** — ETH price makes a significant move (≥0.1%). LeadEdge detects within milliseconds.
2. **Signal fires** — Direction, magnitude, confidence, and expected follow-through time are pushed via WebSocket.
3. **Your bot acts** — Place a maker order on the follower exchange before the price catches up.

---

## Validation Methodology

LeadEdge was validated with **7 days of live WebSocket data** before any product code was written:

- **9.4M price updates** collected from Binance Futures and Coinbase Spot
- **90.7% follow-through rate** at the 0.1% threshold
- **~150ms median lag** between exchanges
- **92.7% profitability** at ultra-low maker fees (0.04% round-trip)

Full methodology: [leadedge.dev/blog/validation](https://leadedge.dev/blog/validation)

The methodology IS the trust layer — anyone with a CCXT install can detect cross-exchange lag. The moat is the rigor of measurement, validation, and continuous monitoring.

---

## Documentation

- [Signal Schema](docs/signal_schema.md) — Payload format reference
- [Validation Methodology](docs/methodology.md) — How signals are measured and validated
- [Full API Docs](https://leadedge.dev/docs) — Complete API reference

---

## Pricing

| Tier | Price | Use Case |
|------|-------|----------|
| Free | $0 | 30-second delayed signals — test the integration |
| Pro | $99/mo | Real-time WebSocket — built for live bots |

Compare plans: [leadedge.dev/pricing](https://leadedge.dev/pricing)

---

## Contributing

These examples are starting points, not production code. Pull requests welcome for:

- Additional language SDKs (JavaScript/TypeScript, Go, Rust)
- Integration templates for other bot frameworks (NautilusTrader, QuantConnect, Backtrader)
- Bug fixes and improvements

Please open an issue first to discuss substantial changes.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Support

- Documentation: [leadedge.dev/docs](https://leadedge.dev/docs)
- Email: support@leadedge.dev
- Issues: Open a GitHub issue in this repo
