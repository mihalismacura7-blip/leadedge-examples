"""
Export LeadEdge Signal History to CSV
======================================

Fetches historical signals from the REST API and saves them to a CSV file
for analysis in Python, Excel, R, etc.

Use cases:
- Train custom signal filters
- Backtest your strategy against historical signals
- Audit signal accuracy yourself

Usage:
    python examples/signal_history_export.py --days 7 --output signals.csv
"""

import argparse
import csv
import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LEADEDGE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LEADEDGE_API_KEY in environment.")

API_BASE = "https://api.leadedge.dev/v1"


def fetch_signals(start_time, end_time, limit=1000):
    """Paginate through signals in the time range."""
    cursor = None
    all_signals = []

    while True:
        params = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            f"{API_BASE}/signals/history",
            headers={"Authorization": f"Bearer {API_KEY}"},
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        signals = data.get("signals", [])
        all_signals.extend(signals)

        cursor = data.get("next_cursor")
        if not cursor or not signals:
            break

        print(f"  Fetched {len(all_signals)} signals so far...")

    return all_signals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Days of history to fetch")
    parser.add_argument("--output", default="signals.csv", help="Output CSV file")
    args = parser.parse_args()

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=args.days)

    print(f"Fetching signals from {start_time} to {end_time}...")
    signals = fetch_signals(start_time, end_time)
    print(f"Total signals fetched: {len(signals)}")

    if not signals:
        print("No signals in this time range.")
        return

    # Write CSV
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=signals[0].keys())
        writer.writeheader()
        writer.writerows(signals)

    print(f"Exported to {args.output}")


if __name__ == "__main__":
    main()
