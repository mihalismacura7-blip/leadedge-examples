"""
Quick Integration Test
=======================

Single REST call to verify your API key works and show what a signal looks like.

Works on Free tier (returns 30-second delayed signal). Start here before trying
the WebSocket examples.

Usage:
    python examples/quick_test.py
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LEADEDGE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LEADEDGE_API_KEY in environment. See .env.example")

API_BASE = "https://leadedge.dev/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def main():
    print("Fetching latest signal from LeadEdge...")
    print(f"Endpoint: {API_BASE}/signals/latest")
    print("-" * 60)

    response = requests.get(
        f"{API_BASE}/signals/latest",
        headers=HEADERS,
        timeout=10,
    )

    if response.status_code == 401:
        print(f"[AUTH ERROR] {response.json().get('message', 'Unauthorized')}")
        print("Check your LEADEDGE_API_KEY in .env")
        return

    if response.status_code == 404:
        print("[NO SIGNALS] No signals available yet. Try again later.")
        return

    if response.status_code == 429:
        body = response.json()
        print(f"[RATE LIMITED] {body.get('message')}")
        print(f"Limit: {body.get('limit')}, resets: {body.get('reset_at')}")
        return

    response.raise_for_status()
    data = response.json()

    signal = data.get("signal", {})
    meta = data.get("meta", {})

    print(f"Tier: {meta.get('tier', 'unknown')}")
    if meta.get("delay_ms"):
        print(f"Delay: {meta['delay_ms']}ms (free tier)")
    print("-" * 60)
    print()
    print("Latest signal:")
    print(json.dumps(signal, indent=2))
    print()
    print("-" * 60)

    # Pretty-print key fields
    if signal:
        print("Summary:")
        print(f"  ID: {signal.get('id')}")
        print(f"  Asset: {signal.get('asset')}")
        print(f"  Leader: {signal.get('leader_exchange')} ({signal.get('leader_market_type')})")
        print(f"  Direction: {signal.get('leader_direction')}")
        print(f"  Magnitude: {signal.get('leader_magnitude_pct'):.4f}%")
        print(f"  Quality: {signal.get('signal_quality')}")

        predictions = signal.get("predictions", [])
        if predictions:
            pred = predictions[0]
            print(f"  Prediction confidence: {pred.get('confidence'):.3f}")
            print(f"  Breakeven fee: {pred.get('breakeven_fee_pct'):.4f}%")

        outcome = signal.get("outcome", {})
        if outcome:
            for follower, result in outcome.items():
                print(f"  Outcome ({follower}):")
                print(f"    Followed: {result.get('followed')}")
                print(f"    Follow time: {result.get('follow_time_ms')}ms")
                print(f"    Profitable at fee: {result.get('profitable_at_fee'):.4f}%")
        else:
            print("  Outcome: (not yet resolved)")

    print()
    print("Integration verified. You can now run the WebSocket examples.")


if __name__ == "__main__":
    main()
