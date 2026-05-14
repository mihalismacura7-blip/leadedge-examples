"""
LeadEdge REST API Polling
==========================

Polls the LeadEdge REST API for the latest signal. Use this if you can't
use WebSockets (firewall restrictions, simpler architecture) or if you're
on the Free tier (which has full REST access with a 30-second delay).

Note: For real-time low-latency strategies, use the WebSocket stream instead.
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

API_BASE = "https://leadedge.dev/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

POLL_INTERVAL = 5  # seconds

# Track the last signal ID to detect new signals
last_seen_id = None


def fetch_latest_signal():
    """Fetch the latest signal. Returns dict or None."""
    response = requests.get(
        f"{API_BASE}/signals/latest",
        headers=HEADERS,
        timeout=10,
    )

    if response.status_code == 404:
        return None  # No signals available yet

    response.raise_for_status()
    return response.json()


def main():
    global last_seen_id
    print(f"[STARTED] Polling {API_BASE}/signals/latest every {POLL_INTERVAL}s...")

    while True:
        try:
            data = fetch_latest_signal()

            if data is None:
                print("[POLL] No signals available")
            else:
                signal = data.get("signal", {})
                meta = data.get("meta", {})
                signal_id = signal.get("id")

                if signal_id and signal_id != last_seen_id:
                    last_seen_id = signal_id

                    predictions = signal.get("predictions", [])
                    pred = predictions[0] if predictions else {}

                    print(
                        f"[NEW SIGNAL] {signal.get('id')} "
                        f"{signal.get('asset')} "
                        f"{signal.get('leader_direction')} "
                        f"magnitude={signal.get('leader_magnitude_pct', 0):.4f}% "
                        f"confidence={pred.get('confidence', 0):.3f}"
                    )

                    if meta.get("delay_ms"):
                        print(f"  (Free tier: signal is {meta['delay_ms']}ms delayed)")

                    # >>> Place your trading logic here <<<

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"[AUTH ERROR] Check your LEADEDGE_API_KEY: {e.response.text}")
                return
            if e.response.status_code == 429:
                print(f"[RATE LIMITED] {e.response.json().get('message')}")
                time.sleep(60)  # Back off on rate limit
                continue
            print(f"[HTTP ERROR] {e}")
        except requests.exceptions.RequestException as e:
            print(f"[REQUEST ERROR] {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
