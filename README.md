# LeadEdge Examples

Official examples and integration templates for the [LeadEdge](https://leadedge.dev) cross-exchange latency intelligence API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **What is LeadEdge?** A real-time signal API that detects when Binance Futures leads Coinbase Spot. Every signal includes predictions AND tracks actual outcomes after the fact — so you can audit accuracy yourself. Validated at **90.7% follow-through** with **~150ms median lag** on ETH ([full methodology](https://leadedge.dev/blog/validation)).

---

## Why LeadEdge Is Different

Most "trading signal" APIs publish predictions and disappear. LeadEdge tracks the actual outcome of every signal:

```json
"outcome": {
  "coinbase-spot": {
    "followed": true,
    "follow_time_ms": 4982,
    "actual_direction": "down",
    "profitable_at_fee": 0.131401,
    "actual_magnitude_pct": 0.131401
  }
}
```

Every signal grades itself. You can compute accuracy over any window, filter by fee tier profitability, or build your own quality classifier. **The methodology IS the trust layer.**

---

## Quick Start

### 1. Get your API key

Get an API key at [leadedge.dev](https://leadedge.dev) (free tier available).

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
cp .env.example .env
# Edit .env and add your LEADEDGE_API_KEY
```

### 4. Verify your integration (instant data)

```bash
python examples/quick_test.py
```

This fetches the latest signal via REST and prints it — works immediately on free tier with 30-second delay.

### 5. Start the WebSocket stream

```bash
python examples/basic_signal_consumer.py
```

---

## Examples

| File | Description |
|------|-------------|
| [quick_test.py](examples/quick_test.py) | One-shot REST call to verify your API key works — start here |
| [basic_signal_consumer.py](examples/basic_signal_consumer.py) | Simplest WebSocket consumer — connect and print signals |
| [rest_polling.py](examples/rest_polling.py) | REST API polling of `/signals/latest` — alternative to WebSocket |
| [websocket_with_reconnect.py](examples/websocket_with_reconnect.py) | Production-ready WebSocket with reconnect + heartbeat monitoring |
| [signal_history_export.py](examples/signal_history_export.py) | Export historical signals to CSV for analysis |
| [freqtrade_strategy.py](examples/freqtrade_strategy.py) | Drop-in Freqtrade strategy template |

---

## Freqtrade Integration

The `freqtrade_strategy.py` template lets you consume LeadEdge signals directly inside Freqtrade. **Empirically tested with Freqtrade stable in dry-run mode.**

### Tested With

- Freqtrade 2026.4
- Python 3.12
- Docker (custom image with websocket-client added)
- LeadEdge Free tier (connection verified; Pro tier required for real-time signals)

### Requirements

- A working Freqtrade installation (any recent version supporting `IStrategy` V3)
- `websocket-client` Python package (not included by default in Freqtrade)
- LeadEdge **Pro tier** for real-time signal delivery (Free tier connects but doesn't deliver real-time signals)

### Setup

**1. Install websocket-client in your Freqtrade environment:**

```bash
pip install websocket-client
```

If using Docker, add to a custom Dockerfile:
```dockerfile
FROM freqtradeorg/freqtrade:stable
USER root
RUN pip install websocket-client
USER ftuser
```

**2. Copy the strategy file:**

```bash
cp examples/freqtrade_strategy.py /path/to/freqtrade/user_data/strategies/
```

**3. Set your API key as an environment variable:**

```bash
export LEADEDGE_API_KEY="le_live_..."
```

Or in Docker:
```bash
docker run -e LEADEDGE_API_KEY=le_live_... ...
```

**4. Run with dry-run:**

```bash
freqtrade trade --strategy LeadEdgeStrategy --config user_data/config.json --dry-run
```

### Configuration Knobs

Inside the strategy file:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MIN_CONFIDENCE` | 0.85 | Minimum signal confidence to act on |
| `MIN_BREAKEVEN_FEE_PCT` | 0.10 | Minimum breakeven fee for trade profitability |
| `SIGNAL_VALIDITY_SECONDS` | 5 | How fresh a signal must be |

### What the Strategy Does

- Background thread connects to LeadEdge WebSocket on startup
- Listens for `signal` messages on ETH
- Enters **long positions** when:
  - Signal arrived within `SIGNAL_VALIDITY_SECONDS`
  - Predicted direction is `up`
  - Confidence ≥ `MIN_CONFIDENCE`
  - Breakeven fee ≥ `MIN_BREAKEVEN_FEE_PCT`
- Uses Freqtrade's ROI table and stoploss for exits

### Customization

This is a **starting template**, not a complete trading system. Customize:
- Add "down" signal handling for short positions
- Tune ROI/stoploss for your risk profile
- Add additional filters in `populate_entry_trend`
- Adapt for REST polling if you're on Free tier (see `examples/rest_polling.py`)

---

## Sample Signal (Real Payload)

```json
{
  "id": "sig_0e42c6db250ba80d",
  "timestamp": 1778765716833,
  "asset": "ETH",
  "leader_exchange": "binance",
  "leader_market_type": "futures",
  "leader_pair": "ETH/USDT",
  "leader_direction": "down",
  "leader_magnitude_pct": 0.148225,
  "leader_price_before": 2253.335,
  "leader_price_after": 2249.995,
  "signal_quality": "medium",
  "threshold_triggered": 0.100,
  "predictions": [
    {
      "pair": "ETH/USD",
      "exchange": "coinbase",
      "confidence": 0.907,
      "market_type": "spot",
      "breakeven_fee_pct": 0.1223,
      "expected_direction": "down",
      "expected_magnitude_pct": 0.1223,
      "expected_follow_within_ms": 300
    }
  ],
  "outcome": {
    "coinbase-spot": {
      "followed": true,
      "follow_time_ms": 4982,
      "actual_direction": "down",
      "profitable_at_fee": 0.131401,
      "actual_magnitude_pct": 0.131401
    }
  }
}
```

See [docs/signal_schema.md](docs/signal_schema.md) for full schema documentation.

---

## How It Works

1. **Binance Futures moves** — ETH price makes a significant move (≥0.1% by default). LeadEdge detects within milliseconds.
2. **Signal fires** — `leader_*` fields capture what happened on Binance. `predictions[]` captures what's expected on follower exchanges (currently Coinbase Spot).
3. **Outcome resolves** — Within seconds, LeadEdge measures what actually happened on the follower and writes it to `outcome`.
4. **Your bot acts** — Place a maker order on the follower exchange before the price catches up.

---

## Free vs Pro Tier

| Feature | Free | Pro |
|---------|------|-----|
| REST `/signals/latest` | 30-second delayed | Real-time |
| REST `/signals/history` | Last 24 hours | Full history |
| WebSocket stream | Connection only | Real-time signals |
| Rate limits | Lower daily quota | Higher daily quota |

**For testing the integration, free tier is fully sufficient** — `quick_test.py` and `rest_polling.py` work out of the box.

For live trading bots that need sub-second latency, the WebSocket stream requires Pro.

---

## Validation Methodology

LeadEdge was validated with **7 days of live WebSocket data** before any product code was written:

- **9.4M price updates** collected from Binance Futures and Coinbase Spot
- **90.7% follow-through rate** at the 0.1% threshold
- **~150ms median lag** between exchanges
- **92.7% profitability** at ultra-low maker fees (0.04% round-trip)

Full methodology: [leadedge.dev/blog/validation](https://leadedge.dev/blog/validation)

The methodology continues in production — every signal records its actual outcome (`followed`, `follow_time_ms`, `profitable_at_fee`), making accuracy auditable in real time.

---

## Documentation

- [Signal Schema](docs/signal_schema.md) — Full payload format reference
- [Validation Methodology](docs/methodology.md) — How signals are measured and validated
- [Full API Docs](https://leadedge.dev/docs) — Complete API reference

---

## API Access

Examples require an API key from [leadedge.dev](https://leadedge.dev). Free tier available for testing; see [leadedge.dev/pricing](https://leadedge.dev/pricing) for details.

---

## Contributing

These examples are starting points, not production code. Pull requests welcome for:

- Additional language SDKs (JavaScript/TypeScript, Go, Rust)
- Integration templates for other bot frameworks (NautilusTrader, QuantConnect, Backtrader, Hummingbot)
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
