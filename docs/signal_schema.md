# Signal Schema Reference

LeadEdge signals are delivered as JSON objects via WebSocket and REST API. The schema is the same across both transports.

## Full Signal Payload

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
  },
  "outcome_resolved_at": "2026-05-14T13:35:21.928+00:00",
  "created_at": "2026-05-14T13:35:16.844563+00:00"
}
```

---

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique signal identifier (e.g., `sig_abc123...`) |
| `timestamp` | integer | Unix milliseconds when the leader move was detected |
| `asset` | string | Underlying asset (currently `"ETH"`) |
| `leader_exchange` | string | Exchange that moved first (currently `"binance"`) |
| `leader_market_type` | string | Market type on leader (`"futures"`, `"spot"`) |
| `leader_pair` | string | Trading pair on leader (e.g., `"ETH/USDT"`) |
| `leader_direction` | string | Direction of the leader move: `"up"` or `"down"` |
| `leader_magnitude_pct` | float | Size of the leader move (% as decimal: 0.148225 = 0.148%) |
| `leader_price_before` | float | Price on leader just before the move |
| `leader_price_after` | float | Price on leader just after the move |
| `signal_quality` | string | LeadEdge's quality classification: `"strong"`, `"medium"`, `"weak"` |
| `threshold_triggered` | float | The threshold % that triggered this signal (e.g., 0.100 = 0.1%) |
| `predictions` | array | List of follower predictions (see below) |
| `outcome` | object | Actual outcome after the signal fired (see below). May be `null` while pending. |
| `outcome_resolved_at` | string | ISO-8601 UTC timestamp when the outcome was determined. May be `null`. |
| `created_at` | string | ISO-8601 UTC timestamp when the signal was created |

---

## `predictions[]` Schema

Each element represents a predicted move on a follower exchange:

| Field | Type | Description |
|-------|------|-------------|
| `pair` | string | Trading pair on follower (e.g., `"ETH/USD"`) |
| `exchange` | string | Follower exchange (e.g., `"coinbase"`) |
| `market_type` | string | Follower market type (e.g., `"spot"`) |
| `confidence` | float | Historical follow-through probability (0.0–1.0) |
| `breakeven_fee_pct` | float | Max total round-trip fee for profitability (% as decimal) |
| `expected_direction` | string | Predicted direction on follower: `"up"` or `"down"` |
| `expected_magnitude_pct` | float | Predicted magnitude of the follower move |
| `expected_follow_within_ms` | integer | Expected time for follower to catch up (ms) |

---

## `outcome` Schema

The `outcome` object is keyed by `"{exchange}-{market_type}"` (e.g., `"coinbase-spot"`). For each follower:

| Field | Type | Description |
|-------|------|-------------|
| `followed` | boolean | Did the follower actually move in the predicted direction? |
| `follow_time_ms` | integer | How long after the signal the follower moved |
| `actual_direction` | string | What the follower actually did (`"up"` or `"down"`) |
| `actual_magnitude_pct` | float | How much the follower actually moved (%) |
| `profitable_at_fee` | float | The maximum round-trip fee at which this trade would have been profitable, OR 0 if unprofitable at all fee levels |

**Why this matters:** Every signal grades itself after the fact. You can audit accuracy over any window, filter by what's actually been profitable, or build your own quality classifier on top of these stats.

---

## WebSocket Message Types

The WebSocket stream sends three types of JSON messages:

### `connected` (on connection)
```json
{
  "type": "connected",
  "client_id": "client_1778792469406_xgsn",
  "tier": "pro",
  "delay_ms": 0,
  "message": "Connected to LeadEdge signal stream",
  "server_time": 1778792469406
}
```

`tier` is `"free"` or `"pro"`. `delay_ms` is the delay applied to signals for this tier (30000 for free, 0 for pro).

### `heartbeat` (every ~15 seconds)
```json
{
  "type": "heartbeat",
  "timestamp": 1778792483211,
  "clients_connected": 1
}
```

Use heartbeats to detect silent staleness. If you don't receive any message (including heartbeats) for >60 seconds, reconnect.

### `signal` (when a signal fires)
The signal payload uses the schema documented above, with `"type": "signal"` added. Signal data may be inlined or under a `signal` key; the example code handles both cases defensively.

---

## REST Response Wrappers

### `GET /api/v1/signals/latest`
```json
{
  "signal": { /* full signal payload */ },
  "meta": {
    "tier": "free",
    "delay_ms": 30000
  }
}
```

### `GET /api/v1/signals/history`
```json
{
  "signals": [ /* array of full signal payloads */ ],
  "total": 1234,
  "limit": 50,
  "offset": 0,
  "meta": {
    "tier": "free",
    "history_window_hours": 24,
    "history_window_note": "Free tier limited to last 24 hours."
  }
}
```

### `GET /api/v1/signals/{id}`
```json
{
  "signal": { /* full signal payload */ }
}
```

---

## Filtering Recommendations

When consuming signals, common filters:

### By confidence
```python
predictions = signal["predictions"]
if predictions and predictions[0]["confidence"] >= 0.85:
    # high-confidence signal
```

### By breakeven fee (most important for profitability)
```python
# Your total round-trip fee in % (e.g., maker on both sides = 0.08)
MY_ROUND_TRIP_FEE_PCT = 0.08

pred = signal["predictions"][0]
if pred["breakeven_fee_pct"] >= MY_ROUND_TRIP_FEE_PCT:
    # Signal is profitable at your fee level
```

### By signal quality
```python
if signal["signal_quality"] in ("strong", "medium"):
    # Skip "weak" signals
```

### By past outcome (audit your own performance)
```python
outcomes = []
for sig in historical_signals:
    if sig["outcome"]:
        for follower, result in sig["outcome"].items():
            outcomes.append(result["followed"])

follow_rate = sum(outcomes) / len(outcomes) if outcomes else 0
```
