"""
Export LeadEdge Signal History to CSV
======================================

Fetches historical signals from the REST `/signals/history` endpoint and
saves them to a CSV file for analysis in Python, Excel, R, etc.

Free tier: limited to last 24 hours.
Pro tier: full history.

Use cases:
- Train custom signal filters
- Backtest your strategy against historical signals
- Audit signal accuracy yourself (the `outcome` field tracks real follow-through)

Usage:
    python examples/signal_history_export.py
    python examples/signal_history_export.py --output my_signals.csv --limit 200
    python examples/signal_history_export.py --quality strong
    python examples/signal_history_export.py --min-threshold 0.15
"""

import argparse
import csv
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LEADEDGE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LEADEDGE_API_KEY in environment.")

API_BASE = "https://leadedge.dev/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def fetch_history(limit=200, quality=None, min_threshold=None, since=None):
    """Paginate through signal history."""
    all_signals = []
    offset = 0
    page_size = min(limit, 200)  # Server caps at 200 per request

    while True:
        params = {"limit": page_size, "offset": offset}
        if quality:
            params["quality"] = quality
        if min_threshold is not None:
            params["min_threshold"] = min_threshold
        if since is not None:
            params["since"] = since

        response = requests.get(
            f"{API_BASE}/signals/history",
            headers=HEADERS,
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise SystemExit(f"Auth error: {response.text}")

        response.raise_for_status()
        data = response.json()

        signals = data.get("signals", [])
        total = data.get("total", 0)
        meta = data.get("meta", {})

        if offset == 0:
            print(f"Total signals available: {total}")
            print(f"Tier: {meta.get('tier')}")
            if meta.get("history_window_note"):
                print(f"Note: {meta['history_window_note']}")
            print()

        all_signals.extend(signals)

        if len(signals) < page_size or len(all_signals) >= total:
            break

        offset += page_size
        if len(all_signals) >= limit:
            break

        print(f"  Fetched {len(all_signals)}/{total}...")

    return all_signals[:limit]


def flatten_signal(signal):
    """Flatten the nested signal structure for CSV export."""
    flat = {
        "id": signal.get("id"),
        "timestamp": signal.get("timestamp"),
        "asset": signal.get("asset"),
        "leader_exchange": signal.get("leader_exchange"),
        "leader_market_type": signal.get("leader_market_type"),
        "leader_pair": signal.get("leader_pair"),
        "leader_direction": signal.get("leader_direction"),
        "leader_magnitude_pct": signal.get("leader_magnitude_pct"),
        "leader_price_before": signal.get("leader_price_before"),
        "leader_price_after": signal.get("leader_price_after"),
        "signal_quality": signal.get("signal_quality"),
        "threshold_triggered": signal.get("threshold_triggered"),
        "created_at": signal.get("created_at"),
        "outcome_resolved_at": signal.get("outcome_resolved_at"),
    }

    # Flatten first prediction (most use cases only have one)
    predictions = signal.get("predictions") or []
    if predictions:
        p = predictions[0]
        flat.update({
            "prediction_pair": p.get("pair"),
            "prediction_exchange": p.get("exchange"),
            "prediction_confidence": p.get("confidence"),
            "prediction_market_type": p.get("market_type"),
            "prediction_breakeven_fee_pct": p.get("breakeven_fee_pct"),
            "prediction_expected_direction": p.get("expected_direction"),
            "prediction_expected_magnitude_pct": p.get("expected_magnitude_pct"),
            "prediction_expected_follow_within_ms": p.get("expected_follow_within_ms"),
        })

    # Flatten first outcome (coinbase-spot in current implementation)
    outcome = signal.get("outcome") or {}
    if outcome:
        # Use the first key in outcome dict
        outcome_key = next(iter(outcome.keys()), None)
        if outcome_key:
            o = outcome[outcome_key]
            flat.update({
                "outcome_follower": outcome_key,
                "outcome_followed": o.get("followed"),
                "outcome_follow_time_ms": o.get("follow_time_ms"),
                "outcome_actual_direction": o.get("actual_direction"),
                "outcome_profitable_at_fee": o.get("profitable_at_fee"),
                "outcome_actual_magnitude_pct": o.get("actual_magnitude_pct"),
            })

    # Keep raw JSON columns as backup
    flat["predictions_json"] = json.dumps(predictions)
    flat["outcome_json"] = json.dumps(outcome)

    return flat


def main():
    parser = argparse.ArgumentParser(description="Export LeadEdge signal history to CSV")
    parser.add_argument("--output", default="signals.csv", help="Output CSV file")
    parser.add_argument("--limit", type=int, default=1000, help="Max signals to fetch")
    parser.add_argument("--quality", choices=["strong", "medium", "weak"], help="Filter by quality")
    parser.add_argument("--min-threshold", type=float, help="Minimum leader_magnitude_pct")
    parser.add_argument("--since", type=int, help="Unix ms timestamp — only signals after this")
    args = parser.parse_args()

    print(f"Fetching up to {args.limit} signals...")
    signals = fetch_history(
        limit=args.limit,
        quality=args.quality,
        min_threshold=args.min_threshold,
        since=args.since,
    )
    print(f"Total fetched: {len(signals)}")

    if not signals:
        print("No signals in this query.")
        return

    # Flatten and write CSV
    flattened = [flatten_signal(s) for s in signals]
    all_keys = list(flattened[0].keys())

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(flattened)

    print(f"Exported to {args.output}")


if __name__ == "__main__":
    main()
