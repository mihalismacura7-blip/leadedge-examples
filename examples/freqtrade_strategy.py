"""
LeadEdge Freqtrade Strategy Template
=====================================

A Freqtrade strategy that consumes LeadEdge signals via WebSocket
and uses them to trigger buy/sell decisions on ETH.

This is a STARTING POINT, not production code. Customize the signal
filtering, entry/exit logic, and risk management for your specific needs.

Installation:
    1. Place this file in your Freqtrade `user_data/strategies/` directory
    2. Set LEADEDGE_API_KEY environment variable
    3. Run: freqtrade trade --strategy LeadEdgeStrategy

Note: This strategy assumes Coinbase Spot pair as follower.
Freqtrade docs: https://www.freqtrade.io
LeadEdge docs: https://leadedge.dev/docs
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

import websocket
from pandas import DataFrame
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class LeadEdgeStrategy(IStrategy):
    """
    Strategy that enters long positions on LeadEdge "up" signals
    above a configurable confidence threshold.
    """

    INTERFACE_VERSION = 3

    # Strategy parameters
    timeframe = "1m"

    # ROI and stoploss — tune for your risk tolerance
    minimal_roi = {
        "0": 0.005,   # 0.5% target
        "5": 0.002,   # 0.2% after 5 min
        "30": 0,      # Exit at break-even after 30 min
    }

    stoploss = -0.005  # 0.5% stop loss

    # LeadEdge configuration
    LEADEDGE_API_KEY = os.getenv("LEADEDGE_API_KEY", "")
    LEADEDGE_WS_URL = "wss://api.leadedge.dev/v1/stream"
    MIN_CONFIDENCE = 0.85
    SIGNAL_VALIDITY_SECONDS = 5

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        if not self.LEADEDGE_API_KEY:
            logger.warning("LEADEDGE_API_KEY not set — signals will not be received")
            return

        # Latest signal state (shared between WebSocket thread and strategy)
        self.latest_signal: Optional[dict] = None
        self.signal_lock = threading.Lock()

        # Start WebSocket listener
        self._start_signal_listener()

    def _start_signal_listener(self):
        """Start background thread that consumes LeadEdge signals."""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get("type") != "signal":
                    return

                with self.signal_lock:
                    self.latest_signal = {
                        **data,
                        "received_at": datetime.now(timezone.utc),
                    }

                logger.info(f"LeadEdge signal received: {data}")
            except Exception as e:
                logger.error(f"Error processing signal: {e}")

        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")

        def run_ws():
            url = f"{self.LEADEDGE_WS_URL}?api_key={self.LEADEDGE_API_KEY}"
            ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
            )
            ws.run_forever(reconnect=5)

        thread = threading.Thread(target=run_ws, daemon=True)
        thread.start()
        logger.info("LeadEdge WebSocket listener started")

    def _get_active_signal(self) -> Optional[dict]:
        """Return the latest signal if still valid (within validity window)."""
        with self.signal_lock:
            if not self.latest_signal:
                return None

            age_seconds = (
                datetime.now(timezone.utc) - self.latest_signal["received_at"]
            ).total_seconds()

            if age_seconds > self.SIGNAL_VALIDITY_SECONDS:
                return None

            return self.latest_signal

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Enter long when:
        - LeadEdge signal direction is 'up'
        - Confidence > MIN_CONFIDENCE threshold
        - Signal is still within validity window
        - Asset matches (default: ETH)
        """
        # Only trade ETH pairs
        if metadata["pair"].split("/")[0] != "ETH":
            dataframe["enter_long"] = 0
            return dataframe

        signal = self._get_active_signal()

        if (
            signal
            and signal.get("direction") == "up"
            and signal.get("confidence", 0) >= self.MIN_CONFIDENCE
        ):
            # Trigger entry on the most recent candle
            dataframe.loc[dataframe.index[-1], "enter_long"] = 1
        else:
            dataframe["enter_long"] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exits are handled by ROI table and stoploss."""
        dataframe["exit_long"] = 0
        return dataframe
