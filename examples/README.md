# Examples

Working code examples for integrating with the LeadEdge API.

## Files

- **basic_signal_consumer.py** — Minimal WebSocket consumer. Start here.
- **rest_polling.py** — REST API alternative for environments where WebSockets aren't viable.
- **websocket_with_reconnect.py** — Production-ready WebSocket with automatic reconnection, exponential backoff, and silent staleness detection.
- **signal_history_export.py** — Export historical signals to CSV for analysis or training your own filters.
- **freqtrade_strategy.py** — Drop-in Freqtrade strategy template.

## Setup

```bash
# From the repo root
pip install -r requirements.txt
cp .env.example .env
# Edit .env to add your LEADEDGE_API_KEY
```

## Running

```bash
python examples/basic_signal_consumer.py
```

All examples expect `LEADEDGE_API_KEY` in your environment (loaded from `.env` automatically via python-dotenv).

## Note on Production Use

These examples prioritize clarity over robustness. Before using in production:

1. Add proper error handling for your environment
2. Implement appropriate logging for your monitoring stack
3. Tune timeouts and retry logic for your latency requirements
4. Handle exchange-specific quirks (rate limits, order book gaps, etc.)
5. Add monitoring/alerting for stale connections

`websocket_with_reconnect.py` is the closest to production-ready — start from that one if you're building real bots.
