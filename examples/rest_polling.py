"""
LeadEdge REST API Polling
==========================

Polls the LeadEdge REST API for recent signals. Use this if you can't
use WebSockets (firewall restrictions, simpler architecture, etc.).

Note: WebSocket delivery is preferred for low-latency strategies.
REST polling adds 1-5 seconds of latency depending on poll interval.

Usage:
    python examples/rest_polling.py
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LEADEDGE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LEADEDGE_API_KEY in environment.")

API_BASE = "https://api.leadedge.dev/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Track last seen signal ID to avoid reprocessing
last_seen_id = None

POLL_INTERVAL = 5  # seconds


def fetch_recent_signals():
    """Fetch signals since the last seen ID."""
    params = {"limit": 50}
    if last_seen_id:
        params["after_id"] = last_seen_id

    response = requests.get(
        f"{API_BASE}/signals",
        headers=HEADERS,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def main():
    global last_seen_id
    print(f"[STARTED] Polling every {POLL_INTERVAL}s...")

    while True:
        try:
            data = fetch_recent_signals()
            signals = data.get("signals", [])

            for signal in signals:
                print(
                    f"[SIGNAL] {signal['asset']} "
                    f"direction={signal['direction']} "
                    f"confidence={signal['confidence']:.3f}"
                )
                last_seen_id = signal["id"]

                # >>> Place your trading logic here <<<

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
