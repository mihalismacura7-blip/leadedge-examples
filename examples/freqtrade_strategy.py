"""
LeadEdge Freqtrade Strategy Template
=====================================

A Freqtrade strategy that consumes LeadEdge signals via WebSocket and uses them
to trigger long entries on ETH when a high-confidence "up" signal arrives.

This is a STARTING POINT, not production code. Customize the signal filtering,
entry/exit logic, and risk management for your specific needs.

Note: WebSocket signal delivery requires LeadEdge Pro tier. On Free tier,
adapt this strategy to use REST polling of `/signals/latest` instead.

Installation:
    1. Place this file in your Freqtrade `user_data/strategies/` directory
    2. Set LEADEDGE_API_KEY environment variable
    3. Run: freqtrade trade --strategy LeadEdgeStrategy

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
    Strategy that enters long positions on LeadEdge "up" predictions
    above a configurable confidence threshold.
    """

    INTERFACE_VERSION = 3

    timeframe = "1m"

    # Tune these for your risk tolerance
    minimal_roi = {
        "0": 0.005,
        "5": 0.002,
        "30": 0,
    }

    stoploss = -0.005

    # LeadEdge configuration
    LEADEDGE_API_KEY = os.getenv("LEADEDGE_API_KEY", "")
    LEADEDGE_WS_URL = "wss://api.leadedge.dev/v1/stream"
    MIN_CONFIDENCE = 0.85
    MIN_BREAKEVEN_FEE_PCT = 0.10  # Only trade if breakeven fee > your total round-trip fee
    SIGNAL_VALIDITY_SECONDS = 5

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        self.latest_signal: Optional[dict] = None
        self.signal_lock = threading.Lock()

        if not self.LEADEDGE_API_KEY:
            logger.warning("LEADEDGE_API_KEY not set — signals will not be received")
            return

        self._start_signal_listener()

    def _start_signal_listener(self):
        """Start background thread that consumes LeadEdge signals."""
        def on_message(ws, message):
            try:
                msg = json.loads(message)
                msg_type = msg.get("type")

                if msg_type == "connected":
                    logger.info(
                        f"LeadEdge connected: tier={msg.get('tier')}, "
                        f"delay_ms={msg.get('delay_ms')}"
                    )
                    return

                if msg_type != "signal":
                    return  # Skip heartbeats and other message types

                # Signal data might be inlined or wrapped
                signal_data = msg.get("signal") or msg

                with self.signal_lock:
                    self.latest_signal = {
                        **signal_data,
                        "received_at": datetime.now(timezone.utc),
                    }

                logger.info(f"LeadEdge signal: {signal_data.get('id')}")
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
        - Asset matches (default: ETH)
        - LeadEdge signal is fresh (within validity window)
        - Predicted direction is 'up' on the follower exchange
        - Prediction confidence >= MIN_CONFIDENCE
        - Breakeven fee > your round-trip fee threshold
        """
        if metadata["pair"].split("/")[0] != "ETH":
            dataframe["enter_long"] = 0
            return dataframe

        signal = self._get_active_signal()
        if not signal:
            dataframe["enter_long"] = 0
            return dataframe

        predictions = signal.get("predictions") or []
        if not predictions:
            dataframe["enter_long"] = 0
            return dataframe

        pred = predictions[0]
        expected_direction = pred.get("expected_direction")
        confidence = pred.get("confidence", 0)
        breakeven_fee = pred.get("breakeven_fee_pct", 0)

        if (
            expected_direction == "up"
            and confidence >= self.MIN_CONFIDENCE
            and breakeven_fee >= self.MIN_BREAKEVEN_FEE_PCT
        ):
            dataframe.loc[dataframe.index[-1], "enter_long"] = 1
        else:
            dataframe["enter_long"] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exits are handled by ROI table and stoploss."""
        dataframe["exit_long"] = 0
        return dataframe
