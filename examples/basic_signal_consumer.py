"""
Basic LeadEdge Signal Consumer
================================

Simplest possible WebSocket consumer. Connects to the LeadEdge API
and prints incoming signals to stdout.

Usage:
    1. Copy .env.example to .env and add your API key
    2. pip install -r requirements.txt
    3. python examples/basic_signal_consumer.py

Get your API key: https://leadedge.dev
"""

import json
import os

import websocket
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LEADEDGE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LEADEDGE_API_KEY in environment. See .env.example")

WS_URL = f"wss://api.leadedge.dev/v1/stream?api_key={API_KEY}"


def on_message(ws, message):
    """Called when a new signal arrives."""
    signal = json.loads(message)

    if signal.get("type") != "signal":
        return  # Skip non-signal messages (heartbeats, etc.)

    print(
        f"[SIGNAL] {signal['asset']} "
        f"direction={signal['direction']} "
        f"magnitude={signal['magnitude']:.4f} "
        f"confidence={signal['confidence']:.3f} "
        f"breakeven_fee={signal['breakeven_fee']:.4f}%"
    )

    # >>> Place your trading logic here <<<
    # Example: only act on high-confidence signals
    if signal["confidence"] > 0.85:
        # place_order(signal)
        pass


def on_error(ws, error):
    print(f"[ERROR] {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[CLOSED] {close_status_code}: {close_msg}")


def on_open(ws):
    print("[CONNECTED] Listening for signals...")


if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()
