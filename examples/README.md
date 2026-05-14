# Examples

Working code examples for integrating with the LeadEdge API.

## Files

- **quick_test.py** — One-shot REST call to verify your API key and see a real signal. **Start here.**
- **basic_signal_consumer.py** — Minimal WebSocket consumer (requires Pro tier for real-time signals).
- **rest_polling.py** — REST polling of `/signals/latest` — works on Free tier with 30-second delay.
- **websocket_with_reconnect.py** — Production-ready WebSocket with automatic reconnection, exponential backoff, and silent staleness detection.
- **signal_history_export.py** — Export historical signals to CSV for analysis (Free tier: last 24h; Pro: full history).
- **freqtrade_strategy.py** — Drop-in Freqtrade strategy template.

## Setup

```bash
# From the repo root
pip install -r requirements.txt
cp .env.example .env
# Edit .env to add your LEADEDGE_API_KEY
```

## Recommended Order

1. **quick_test.py** — confirms your API key works (instant feedback, works on Free tier)
2. **rest_polling.py** — see signals arrive in a loop (Free tier compatible)
3. **basic_signal_consumer.py** — WebSocket stream (Pro tier required for real-time signals)
4. **websocket_with_reconnect.py** — production-ready WebSocket
5. **signal_history_export.py** — pull historical data for analysis
6. **freqtrade_strategy.py** — template for integrating into Freqtrade

All examples expect `LEADEDGE_API_KEY` in your environment (loaded from `.env` automatically via python-dotenv).

## Note on Production Use

These examples prioritize clarity over robustness. Before using in production:

1. Add proper error handling for your environment
2. Implement appropriate logging for your monitoring stack
3. Tune timeouts and retry logic for your latency requirements
4. Handle exchange-specific quirks (rate limits, order book gaps, etc.)
5. Add monitoring/alerting for stale connections

`websocket_with_reconnect.py` is the closest to production-ready — start from that one if you're building real bots.
