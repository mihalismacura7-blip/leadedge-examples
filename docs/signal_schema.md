# Signal Schema Reference

LeadEdge signals are delivered as JSON objects via WebSocket or REST API.

## Signal Format

```json
{
  "type": "signal",
  "id": "sig_abc123",
  "timestamp": "2026-05-14T12:34:56.789Z",
  "asset": "ETH",
  "leader_exchange": "binance_futures",
  "follower_exchange": "coinbase_spot",
  "direction": "up",
  "magnitude": 0.1654,
  "confidence": 0.907,
  "follow_within_ms": 300,
  "breakeven_fee": 0.1223
}
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"signal"` for signal messages |
| `id` | string | Unique signal identifier |
| `timestamp` | string | ISO 8601 UTC timestamp when signal was generated |
| `asset` | string | Trading asset (e.g., `"ETH"`) |
| `leader_exchange` | string | Exchange where the move was detected first |
| `follower_exchange` | string | Exchange expected to follow |
| `direction` | string | `"up"` or `"down"` — predicted direction on follower |
| `magnitude` | float | Size of move on leader exchange (% as decimal) |
| `confidence` | float | Historical follow-through probability (0.0–1.0) |
| `follow_within_ms` | integer | Expected time for follower to catch up (milliseconds) |
| `breakeven_fee` | float | Maximum total trading fee for profitability (% as decimal) |

## Message Types

In addition to `signal` messages, the WebSocket stream sends:

- **`heartbeat`** — Periodic message to confirm connection is alive (every ~15s)
- **`error`** — Error notifications (rate limits, auth issues, etc.)

Always check `signal.type` before processing — non-signal messages should be handled separately.

## Confidence Filtering Recommendations

| Confidence Range | Recommended Use |
|------------------|-----------------|
| `< 0.60` | Skip — too low |
| `0.60–0.80` | Test with small position sizes |
| `0.80–0.90` | Standard production threshold |
| `> 0.90` | High-confidence — full position size |

These are starting points. Tune based on your strategy's risk profile and your own backtests.

## Filtering by Breakeven Fee

Only act on signals where your total round-trip fee is **below** `breakeven_fee`:

```python
# Example: maker fees of 0.04% on Coinbase, 0.04% on Binance = 0.08% round-trip
MY_ROUND_TRIP_FEE = 0.08  # %

if signal["breakeven_fee"] > MY_ROUND_TRIP_FEE:
    # Signal is profitable at your fee level — proceed
    pass
```

This ensures you only trade signals where the expected move exceeds your transaction costs.
