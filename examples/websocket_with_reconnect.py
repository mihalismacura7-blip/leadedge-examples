"""
Production-Ready WebSocket Consumer
====================================

Includes:
- Automatic reconnection with exponential backoff
- Message-level heartbeat monitoring (detects silent staleness)
- Graceful error handling
- Configurable timeout for stale connections

This is the recommended starting point for production bots.

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
STALENESS_TIMEOUT = 30  # seconds without any message before reconnecting
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
        signal = json.loads(message)

        if signal.get("type") == "heartbeat":
            return  # Heartbeat acknowledged via last_message_time update

        if signal.get("type") == "signal":
            self.process_signal(signal)

    def process_signal(self, signal):
        """Override this method with your trading logic."""
        print(
            f"[SIGNAL] {signal['asset']} "
            f"direction={signal['direction']} "
            f"confidence={signal['confidence']:.3f}"
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
        while message flow has stopped. Message-level heartbeats catch this.
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
        # Start staleness monitor in background
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

            # Exponential backoff with cap
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
