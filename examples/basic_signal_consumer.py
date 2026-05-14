"""
Basic LeadEdge Signal Consumer
================================

Simplest WebSocket consumer. Connects to the LeadEdge stream and prints
incoming signals to stdout.

Note: On Free tier, the WebSocket connects but real signals are not delivered
(they're available via REST `/signals/latest` with a 30-second delay).
For testing the integration on Free tier, use quick_test.py or rest_polling.py.

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
    """Called when a new message arrives. Handles signal, heartbeat, and welcome messages."""
    try:
        msg = json.loads(message)
    except json.JSONDecodeError:
        print(f"[RAW] {message}")
        return

    msg_type = msg.get("type")

    # Welcome message on connect
    if msg_type == "connected":
        print(
            f"[WELCOME] tier={msg.get('tier')} "
            f"delay_ms={msg.get('delay_ms')} "
            f"client_id={msg.get('client_id')}"
        )
        return

    # Heartbeats — skip (printing them is noisy)
    if msg_type == "heartbeat":
        return

    # Signal — process it
    if msg_type == "signal":
        # Defensive: the signal data might be inlined or wrapped
        signal = msg.get("signal") or msg

        predictions = signal.get("predictions", [])
        pred = predictions[0] if predictions else {}

        print(
            f"[SIGNAL] {signal.get('asset')} "
            f"direction={signal.get('leader_direction')} "
            f"magnitude={signal.get('leader_magnitude_pct', 0):.4f}% "
            f"quality={signal.get('signal_quality')} "
            f"confidence={pred.get('confidence', 0):.3f} "
            f"breakeven_fee={pred.get('breakeven_fee_pct', 0):.4f}%"
        )

        # >>> Place your trading logic here <<<
        # Example: only act on high-confidence signals where the breakeven fee covers your costs
        if pred.get("confidence", 0) > 0.85:
            # if pred["breakeven_fee_pct"] > YOUR_ROUND_TRIP_FEE_PCT:
            #     place_order(signal)
            pass
        return

    # Unknown message type
    print(f"[UNKNOWN MSG] type={msg_type} raw={message[:200]}")


def on_error(ws, error):
    print(f"[ERROR] {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[CLOSED] code={close_status_code} msg={close_msg}")


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
