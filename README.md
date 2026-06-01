# LeadEdge Examples

Official examples and integration templates for the [LeadEdge](https://leadedge.dev) cross-exchange latency intelligence API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **What is LeadEdge?** A real-time signal API that detects when Binance Futures leads the spot market. Every signal includes predictions AND tracks actual outcomes after the fact — so you can audit accuracy yourself. Live across ETH, BTC, and LINK, validated at 83–91% follow-through on live data ([full methodology](https://leadedge.dev/blog/validation)).
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

### Verification

This strategy was validated in **Freqtrade dry-run** across ETH, BTC, and LINK, both
long and short — signals consumed over WebSocket, entries and exits placed, stop-loss
and ROI triggered, and PnL recorded in Freqtrade's own trades database. That exercises
the entire integration path: signal → strategy decision → trade lifecycle → PnL.

Dry-run simulates fills against live market data rather than sending orders to an
exchange, so the one leg it doesn't exercise is "the order physically fills on an
exchange." That leg is Freqtrade's own mature, CCXT-based execution code — used by
thousands of people — not anything this integration introduces.

**On the Binance Futures testnet specifically:** real-fill verification there isn't
practical, and not because of this strategy. Freqtrade's market-loading calls CCXT's
`fetch_currencies`, which on Binance uses the spot `sapi` endpoint. The Binance futures
testnet has no `sapi` equivalent, so the call is misrouted to live spot and the testnet
key is rejected (`-2008`) — even with `sandbox: true` and URL overrides. This is a
long-standing framework limitation, not a fixable config:

- [freqtrade/freqtrade#6909](https://github.com/freqtrade/freqtrade/issues/6909) — "binance does not have a testnet/sandbox URL for sapi endpoints"
- [ccxt/ccxt#26487](https://github.com/ccxt/ccxt/issues/26487) — the underlying CCXT routing issue

On **mainnet** (which has the `sapi` endpoint) Freqtrade's live trading works normally;
the gap is testnet-only.

### Tested With

- Freqtrade 2026.4
- Python 3.12
- Docker (custom image with websocket-client added)
- Free tier connection verified; dry-run validation run on Pro.

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

## Hummingbot Integration

The `leadedge_signal_strategy.py` template consumes LeadEdge signals inside [Hummingbot](https://hummingbot.org) as a Strategy V2 script. On each fresh signal it opens a barrier-managed `PositionExecutor` in the signal's direction (BUY on `up`, SELL on `down`) with take-profit, stop-loss, and time-limit exits. Because Hummingbot acts the moment a signal arrives over WebSocket — rather than on a candle loop — it's the better technical fit for capturing the lead/lag window.

### Verification

This strategy was validated on the Binance Futures testnet with confirmed fills in **both directions** — a live LeadEdge signal opening a real position on `testnet.binancefuture.com`, with the full PositionExecutor lifecycle (entry → barrier-managed exit via take-profit, stop-loss, or time limit). That exercises the entire path: signal → strategy decision → order placement → fill → managed exit, against a real exchange connector.

One known wrinkle is testnet-only and cosmetic. On the Binance Futures testnet, Hummingbot logs a repeating `start_trade_monitor failed` error — a known framework bug (hummingbot/hummingbot#7842) where the `binance_perpetual_testnet` connector reports an inconsistent name, which breaks the status-bar P&L display. It does **not** affect order execution: the PositionExecutor places and manages orders independently of that UI component. It's testnet-only — the mainnet `binance_perpetual` connector reports its name consistently and never hits this. Confirm fills via the strategy logs and the testnet Positions tab rather than the status bar.

### Tested With

- Hummingbot `dev-2.15.0` (Strategy V2)
- Binance Futures testnet (`binance_perpetual_testnet`)
- No extra dependencies — uses `aiohttp`, which ships with Hummingbot
- Confirmed both-direction fills; validation run on Pro.

### Requirements

- A working Hummingbot installation with Strategy V2 support.
- A connector: Binance Futures testnet keys (free, no KYC, from `testnet.binancefuture.com`) for testing, or your `binance_perpetual` keys for mainnet.
- LeadEdge Pro tier for real-time signal delivery (Free tier connects but doesn't deliver real-time signals).

### Setup

**1. Copy the strategy file into your Hummingbot `scripts/` directory:**

```bash
cp examples/leadedge_signal_strategy.py /path/to/hummingbot/scripts/
```

**2. Connect your exchange in the Hummingbot client (paste key + secret):**

```bash
connect binance_perpetual_testnet
```

Use `binance_perpetual` for mainnet.

**3. Create a script config:**

```bash
create --script-config leadedge_signal_strategy
```

Set `leadedge_api_key` to your `le_live_...` key, `connector` to `binance_perpetual_testnet` (or `binance_perpetual`), and `asset` / `trading_pair` (e.g. `ETH` / `ETH-USDT`).

**4. Start it:**

```bash
start --script leadedge_signal_strategy --conf conf_leadedge_signal_strategy_1.yml
```

**5. Confirm it's armed:**

Watch for `LeadEdge: subscription confirmed` in the logs — that's when it's listening for signals.

### Configuration Knobs

Set when you create the script config:

| Field | Default | Purpose |
|------|---------|---------|
| `asset` | `ETH` | Which LeadEdge asset to act on (ETH, BTC, LINK) |
| `min_signal_quality` | `weak` | Minimum signal quality to trade (weak / medium / strong) |
| `max_signal_age_ms` | `5000` | Ignore signals older than this |
| `connector` | `binance_perpetual_testnet` | Exchange connector to trade on |
| `trading_pair` | `ETH-USDT` | Pair to trade |
| `order_amount_quote` | `50` | Position size in quote currency |
| `leverage` | `1` | Leverage (perp supports higher) |
| `take_profit` / `stop_loss` | `0.003` | Barrier exits (0.003 = 0.3%) |
| `time_limit` | `60` | Max seconds per position |
| `cooldown_seconds` | `10` | Pause after a trade |

### What the Strategy Does

- A background task connects to the LeadEdge WebSocket on startup and subscribes to all signal qualities plus outcomes.
- On a fresh signal for the configured `asset`, it checks direction, quality, and freshness (`max_signal_age_ms`).
- If it passes, it opens a single `PositionExecutor` — BUY on `up`, SELL on `down` — sized by `order_amount_quote`, with take-profit / stop-loss / time-limit barriers.
- `cooldown_seconds` plus a one-position-at-a-time guard prevent over-trading.

### Customization

This is a reference integration, not a turnkey money-maker — the edge lives in a ~60–400 ms window, so it's only profitable with the real-time (Pro) signal and low-latency execution at maker fees. Test on testnet first, measure your own fills, and tune the barriers, sizing, and quality filter before considering mainnet.

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

1. **Binance Futures moves** — ETH, BTC, or LINK makes a significant move (as small as 0.05%). LeadEdge detects within milliseconds.
2. **Signal fires** — `leader_*` fields capture what happened on Binance. predictions[] captures what's expected on follower exchanges (Coinbase Spot and Bybit Spot).
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

LeadEdge was validated on live **WebSocket data** before any product code was written, starting with ETH:

- **90.7% follow-through** on ETH at the 0.1% threshold (Binance Futures → Coinbase Spot, 7-day live measurement)
- **92.7% profitability** on ETH at ultra-low maker fees (0.04% round-trip)
- **BTC and LINK** since validated at ~88.6% and ~83% follow-through on Bybit Spot
- **Single-digit-millisecond** signal delivery to a co-located client

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
