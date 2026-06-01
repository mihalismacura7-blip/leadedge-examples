# ─────────────────────────────────────────────────────────────────────────────
#  LeadEdge → Hummingbot  (Strategy V2 reference script)  — v4  (real-connector)
#
#  This is the canonical, idiomatic V2 version: it opens a barrier-managed
#  PositionExecutor in the signal's direction (BUY on "up", SELL on "down").
#  It runs against any connector that exposes trading_rules — i.e. real
#  exchanges, Binance Futures TESTNET, and paper_trade on STABLE Hummingbot.
#  (It does NOT run on paper_trade in dev-2.15.0, whose PaperTradeExchange is
#  missing the .trading_rules attribute PositionExecutor needs — a Hummingbot
#  dev-build bug, not an integration flaw. Use the Binance Futures testnet for
#  zero-risk trials instead.)
#
#  v4 change (THE fix for "received but no trade"):
#   - Added an on_tick() override. StrategyV2Base only auto-calls
#     determine_executor_actions when CONTROLLERS are configured; a plain
#     no-controller script must override on_tick to drive its own actions.
#
#  REFERENCE INTEGRATION, not a turnkey money-maker: the edge lives in a
#  ~60-400ms window, so it's only tradeable with the REAL-TIME (Pro) signal AND
#  low-latency execution. Test on testnet first.
#
#  ── TESTNET SETUP (Binance Futures testnet) ─────────────────────────────────
#   1. Get free testnet keys at testnet.binancefuture.com (fake money, no KYC).
#   2. In Hummingbot:  connect binance_perpetual_testnet   → paste key + secret.
#   3. Create a config:  create --script-config leadedge_signal_strategy
#      - connector:  binance_perpetual_testnet
#      - trading_pair: ETH-USDT
#      - leverage: 1 (or higher; perp supports it)
#   4. start --script leadedge_signal_strategy --conf conf_...yml
#  VERSION-SENSITIVE lines to verify against your build are marked below.
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import time
import asyncio
from decimal import Decimal
from typing import List, Optional, Set

import aiohttp
from pydantic import Field

# ── IMPORTS (version-sensitive) ──────────────────────────────────────────────
from hummingbot.core.data_type.common import OrderType, PriceType, TradeType
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.strategy.strategy_v2_base import StrategyV2Base, StrategyV2ConfigBase
from hummingbot.strategy_v2.executors.position_executor.data_types import (
    PositionExecutorConfig,
    TripleBarrierConfig,
)
from hummingbot.strategy_v2.models.executor_actions import (
    CreateExecutorAction,
    ExecutorAction,
)

_QUALITY_RANK = {"weak": 0, "medium": 1, "strong": 2}


class LeadEdgeConfig(StrategyV2ConfigBase):
    """Generate a config with:  create --script-config leadedge_signal_strategy"""
    script_file_name: str = Field(default=os.path.basename(__file__))
    candles_config: List = []
    controllers_config: List[str] = []
    markets: dict = {}

    leadedge_ws_url: str = Field(
        default="wss://api.leadedge.dev",
        json_schema_extra={"prompt": "LeadEdge WebSocket URL", "prompt_on_new": True},
    )
    leadedge_api_key: str = Field(
        default="le_live_xxx",
        json_schema_extra={"prompt": "Your LeadEdge API key (le_live_...)", "prompt_on_new": True},
    )
    asset: str = Field(
        default="ETH",
        json_schema_extra={"prompt": "Which LeadEdge asset to act on (ETH, BTC, ...)", "prompt_on_new": True},
    )
    min_signal_quality: str = Field(
        default="weak",
        json_schema_extra={"prompt": "Minimum signal quality to trade (weak/medium/strong)", "prompt_on_new": True},
    )
    max_signal_age_ms: int = Field(
        default=5000,
        json_schema_extra={"prompt": "Max age (ms) of a signal to still act on it", "prompt_on_new": True},
    )
    connector: str = Field(
        default="binance_perpetual_testnet",
        json_schema_extra={"prompt": "Connector to trade on", "prompt_on_new": True},
    )
    trading_pair: str = Field(
        default="ETH-USDT",
        json_schema_extra={"prompt": "Trading pair (e.g. ETH-USDT)", "prompt_on_new": True},
    )
    order_amount_quote: Decimal = Field(
        default=Decimal("50"),
        json_schema_extra={"prompt": "Position size in quote currency", "prompt_on_new": True},
    )
    leverage: int = Field(
        default=1,
        json_schema_extra={"prompt": "Leverage (1 for spot; perp supports higher)", "prompt_on_new": True},
    )
    take_profit: Decimal = Field(
        default=Decimal("0.003"),
        json_schema_extra={"prompt": "Take profit (decimal, 0.003 = 0.3%)", "prompt_on_new": True},
    )
    stop_loss: Decimal = Field(
        default=Decimal("0.003"),
        json_schema_extra={"prompt": "Stop loss (decimal, 0.003 = 0.3%)", "prompt_on_new": True},
    )
    time_limit: int = Field(
        default=60,
        json_schema_extra={"prompt": "Time limit per position in seconds", "prompt_on_new": True},
    )
    cooldown_seconds: int = Field(
        default=10,
        json_schema_extra={"prompt": "Cooldown (s) after a trade", "prompt_on_new": True},
    )


class LeadEdgeSignalStrategy(StrategyV2Base):
    """Opens a PositionExecutor in the direction of each fresh LeadEdge signal."""

    @classmethod
    def init_markets(cls, config: LeadEdgeConfig):
        cls.markets = {config.connector: {config.trading_pair}}

    def __init__(self, connectors, config: LeadEdgeConfig):
        super().__init__(connectors, config)
        self.config = config
        self._latest_signal: Optional[dict] = None
        self._latest_recv_ms: int = 0
        self._acted_ids: Set[str] = set()
        self._last_trade_ts: float = 0.0
        self._ws_task = safe_ensure_future(self._listen_leadedge())

    # ── WebSocket consumer ───────────────────────────────────────────────────
    async def _listen_leadedge(self):
        url = f"{self.config.leadedge_ws_url}?api_key={self.config.leadedge_api_key}"
        channels = ["signal:strong", "signal:medium", "signal:weak", "outcome"]
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url, heartbeat=20) as ws:
                        self.logger().info("LeadEdge: WebSocket open, waiting for server ready...")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                except Exception:
                                    continue
                                mtype = data.get("type")
                                if mtype == "connected":
                                    await ws.send_json({"type": "subscribe", "channels": channels})
                                    self.logger().info("LeadEdge: connected to signal stream — sent subscription (incl. weak)")
                                elif mtype == "subscribed":
                                    self.logger().info(f"LeadEdge: subscription confirmed: {data.get('channels')}")
                                elif mtype == "signal":
                                    self._handle_signal(data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"LeadEdge WS error: {e}. Reconnecting in 5s.")
            await asyncio.sleep(5)

    def _handle_signal(self, msg: dict):
        sig = msg.get("data") or {}
        asset = sig.get("asset")
        if asset != self.config.asset:
            return
        sig_id = sig.get("id")
        quality = sig.get("signal_quality")
        direction = (sig.get("leader") or {}).get("direction")
        self.logger().info(f"LeadEdge: received {asset} signal {sig_id} dir={direction} quality={quality}")
        if not self._quality_ok(quality):
            return
        self._latest_signal = sig
        self._latest_recv_ms = int(time.time() * 1000)

    def _quality_ok(self, q: Optional[str]) -> bool:
        return _QUALITY_RANK.get(q, -1) >= _QUALITY_RANK.get(self.config.min_signal_quality, 1)

    # ── Robust mid-price fetch ───────────────────────────────────────────────
    def _get_mid(self) -> Optional[float]:
        # 1) Market data provider (V2 standard path)
        try:
            p = self.market_data_provider.get_price_by_type(
                self.config.connector, self.config.trading_pair, PriceType.MidPrice
            )
            if p is not None and float(p) > 0:
                return float(p)
            self.logger().info(f"LeadEdge: market_data_provider price = {p}")
        except Exception as e:
            self.logger().info(f"LeadEdge: market_data_provider.get_price_by_type failed: {e}")
        # 2) Connector directly (fallback)
        conn = self.connectors.get(self.config.connector)
        if conn is not None:
            for getter in ("get_price_by_type", "get_mid_price"):
                try:
                    fn = getattr(conn, getter, None)
                    if fn is None:
                        continue
                    p = fn(self.config.trading_pair, PriceType.MidPrice) if getter == "get_price_by_type" else fn(self.config.trading_pair)
                    if p is not None and float(p) > 0:
                        return float(p)
                except Exception as e:
                    self.logger().info(f"LeadEdge: connector.{getter} failed: {e}")
        return None

    # ── Clean shutdown ───────────────────────────────────────────────────────
    # Cancel the WS listener on stop so repeated start/stop cycles don't leak
    # reconnecting tasks that pile up and flood the engine's connection slots.
    def on_stop(self):
        task = getattr(self, "_ws_task", None)
        if task is not None and not task.done():
            task.cancel()
        self._ws_task = None
        super().on_stop()

    # ── Per-tick driver (REQUIRED for a no-controller script) ────────────────
    # StrategyV2Base only auto-runs executor orchestration when *controllers*
    # are configured. A plain script like this MUST override on_tick to drive
    # its own actions — otherwise determine_executor_actions is never called.
    def on_tick(self):
        if getattr(self, "_is_stop_triggered", False):
            return
        for action in self.determine_executor_actions():
            self.executor_orchestrator.execute_action(action)

    # ── Strategy logic: turn a fresh signal into one PositionExecutor ────────
    def determine_executor_actions(self) -> List[ExecutorAction]:
        actions: List[ExecutorAction] = []
        signal = self._latest_signal
        if signal is None:
            return actions

        sig_id = signal.get("id")
        if not sig_id or sig_id in self._acted_ids:
            return actions

        age = int(time.time() * 1000) - self._latest_recv_ms
        self.logger().info(f"LeadEdge: evaluating signal {sig_id} (age={age}ms)")

        if age > self.config.max_signal_age_ms:
            self.logger().info(f"LeadEdge: signal {sig_id} stale ({age}ms > {self.config.max_signal_age_ms}ms) — dropping")
            self._latest_signal = None
            return actions

        now = time.time()
        if now - self._last_trade_ts < self.config.cooldown_seconds:
            self.logger().info("LeadEdge: in cooldown — skipping")
            return actions

        try:
            if any(getattr(e, "is_active", False) for e in self.get_all_executors()):
                self.logger().info("LeadEdge: an executor is already active — skipping")
                return actions
        except Exception as e:
            self.logger().error(f"LeadEdge: get_all_executors error: {e}")

        direction = (signal.get("leader") or {}).get("direction")
        if direction == "up":
            side = TradeType.BUY
        elif direction == "down":
            side = TradeType.SELL
        else:
            self.logger().info(f"LeadEdge: unknown direction {direction!r} — skipping")
            return actions

        mid = self._get_mid()
        self.logger().info(f"LeadEdge: mid price {self.config.connector} {self.config.trading_pair} = {mid}")
        if not mid or mid <= 0:
            self.logger().warning("LeadEdge: no usable mid price this tick — cannot size order")
            return actions

        amount = self.config.order_amount_quote / Decimal(str(mid))
        triple_barrier = TripleBarrierConfig(
            take_profit=self.config.take_profit,
            stop_loss=self.config.stop_loss,
            time_limit=self.config.time_limit,
            open_order_type=OrderType.MARKET,
            take_profit_order_type=OrderType.LIMIT,
            stop_loss_order_type=OrderType.MARKET,
            time_limit_order_type=OrderType.MARKET,
        )
        executor_config = PositionExecutorConfig(
            timestamp=self.current_timestamp,
            connector_name=self.config.connector,
            trading_pair=self.config.trading_pair,
            side=side,
            entry_price=Decimal(str(mid)),
            amount=amount,
            triple_barrier_config=triple_barrier,
            leverage=self.config.leverage,
        )

        self._acted_ids.add(sig_id)
        self._last_trade_ts = now
        self._latest_signal = None
        self.logger().info(
            f"LeadEdge: {side.name} {self.config.trading_pair} on signal {sig_id} (quality={signal.get('signal_quality')})"
        )
        actions.append(CreateExecutorAction(executor_config=executor_config))
        return actions

    def format_status(self) -> str:
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = [
            "",
            "  LeadEdge → Hummingbot (PositionExecutor)",
            f"  Asset:           {self.config.asset}  (min quality: {self.config.min_signal_quality})",
            f"  Trading:         {self.config.connector} {self.config.trading_pair}",
            f"  Signals acted:   {len(self._acted_ids)}",
            f"  Last signal id:  {(self._latest_signal or {}).get('id', '—')}",
        ]
        try:
            active = [e for e in self.get_all_executors() if getattr(e, "is_active", False)]
            lines.append(f"  Active positions:{len(active)}")
        except Exception:
            pass
        return "\n".join(lines)