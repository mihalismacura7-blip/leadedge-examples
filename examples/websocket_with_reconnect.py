"""
Production-Ready WebSocket Consumer
====================================

Includes:
- Automatic reconnection with exponential backoff
- Message-level heartbeat monitoring (detects silent staleness)
- Defensive signal parsing
- Graceful error handling

This is the recommended starting point for production bots on Pro tier.

Note: Free tier WebSocket connects but does not deliver real-time signals.
Use rest_polling.py on Free tier.

Usage:
    python examples/websocket_with_reconnect.py
"""

import json
import os
import threading
import time

import websocket
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LEADEDGE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LEADEDGE_API_KEY in environment.")

WS_URL = f"wss://api.leadedge.dev/v1/stream?api_key={API_KEY}"

# Configuration
STALENESS_TIMEOUT = 60  # seconds without any message before reconnecting
BASE_RECONNECT_DELAY = 1  # initial reconnect delay in seconds
MAX_RECONNECT_DELAY = 60  # maximum reconnect delay


class LeadEdgeClient:
    def __init__(self):
        self.last_message_time = time.time()
        self.reconnect_delay = BASE_RECONNECT_DELAY
        self.should_run = True
        self.ws = None

    def on_message(self, ws, message):
        self.last_message_time = time.time()

        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            print(f"[RAW] {message}")
            return

        msg_type = msg.get("type")

        if msg_type == "connected":
            print(
                f"[WELCOME] tier={msg.get('tier')} "
                f"delay_ms={msg.get('delay_ms')} "
                f"client_id={msg.get('client_id')}"
            )
            return

        if msg_type == "heartbeat":
            # Heartbeat acknowledged via last_message_time update
            return

        if msg_type == "signal":
            signal = msg.get("signal") or msg
            self.process_signal(signal)
            return

        print(f"[UNKNOWN MSG] type={msg_type}")

    def process_signal(self, signal):
        """Override this method with your trading logic."""
        predictions = signal.get("predictions", [])
        pred = predictions[0] if predictions else {}

        print(
            f"[SIGNAL] {signal.get('asset')} "
            f"direction={signal.get('leader_direction')} "
            f"magnitude={signal.get('leader_magnitude_pct', 0):.4f}% "
            f"confidence={pred.get('confidence', 0):.3f}"
        )

    def on_error(self, ws, error):
        print(f"[ERROR] {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"[CLOSED] code={close_status_code}")

    def on_open(self, ws):
        print("[CONNECTED] WebSocket stream active")
        self.last_message_time = time.time()
        self.reconnect_delay = BASE_RECONNECT_DELAY  # Reset on successful connect

    def staleness_monitor(self):
        """Watchdog thread that detects silent staleness.

        TCP keepalive isn't enough — the connection can stay "alive"
        while message flow has stopped. Message-level monitoring catches this.
        Heartbeats arrive every ~15 seconds from the LeadEdge server.
        """
        while self.should_run:
            time.sleep(5)
            if not self.ws:
                continue

            elapsed = time.time() - self.last_message_time
            if elapsed > STALENESS_TIMEOUT:
                print(f"[STALE] No messages for {elapsed:.0f}s — forcing reconnect")
                try:
                    self.ws.close()
                except Exception:
                    pass

    def run(self):
        """Main loop with reconnect logic."""
        monitor = threading.Thread(target=self.staleness_monitor, daemon=True)
        monitor.start()

        while self.should_run:
            try:
                self.ws = websocket.WebSocketApp(
                    WS_URL,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"[ERROR] Connection loop: {e}")

            if not self.should_run:
                break

            print(f"[RECONNECT] Sleeping {self.reconnect_delay}s before retry")
            time.sleep(self.reconnect_delay)

            self.reconnect_delay = min(
                self.reconnect_delay * 2,
                MAX_RECONNECT_DELAY,
            )


if __name__ == "__main__":
    client = LeadEdgeClient()
    try:
        client.run()
    except KeyboardInterrupt:
        client.should_run = False
        print("\n[SHUTDOWN] Stopping client...")
