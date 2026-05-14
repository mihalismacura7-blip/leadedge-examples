# Validation Methodology

LeadEdge was validated with **7 days of live WebSocket data** before any product code was written. This document summarizes the methodology — full writeup is at [leadedge.dev/blog/validation](https://leadedge.dev/blog/validation).

## Initial Validation (7-Day Pre-Build Study)

### Data Collection

- **Sources:** Binance Futures (leader candidate), Coinbase Spot (follower candidate)
- **Asset:** ETH/USDT
- **Duration:** 7 continuous days
- **Method:** Live WebSocket streams, timestamps normalized to microsecond precision
- **Volume:** 9.4M price updates

### Key Question Answered

> "When Binance Futures moves >X%, what % of the time does Coinbase Spot move in the same direction within Y milliseconds, and is it profitable to trade after fees?"

### Results

| Metric | Value |
|--------|-------|
| Median lag | ~150ms |
| Follow-through rate (0.1% threshold) | **90.7%** |
| Signals per week (0.05% threshold) | 315+ |
| Profitability at ultra-low maker fees (0.04% RT) | 92.7% |
| Profitability at standard maker fees (0.08% RT) | 89.7% |
| Profitability at mixed fees (0.12% RT) | 43.9% |
| Profitability at standard taker fees (0.20% RT) | 0.9% |

### Why This Matters

Anyone can claim a trading edge. **The methodology behind measurement is what makes the claim defensible.**

LeadEdge's approach:

1. **Validate before build** — No product code until empirical evidence shows the edge exists
2. **Live data only** — No backtests, no simulations
3. **Out-of-sample testing** — Findings verified on fresh data not used in initial analysis
4. **Continuous monitoring** — Production signals are tracked and reported transparently

This is the trust layer: not the algorithm, but the rigor of measurement.

---

## Continuous Validation in Production

The initial 7-day study answered the question "does the edge exist?" Production monitoring answers a more important one: **"does it still exist today?"**

Every signal LeadEdge fires gets graded after the fact. The `outcome` field on each signal records:

- `followed`: did the follower exchange actually move in the predicted direction?
- `follow_time_ms`: how long did it take?
- `actual_direction`: what really happened?
- `actual_magnitude_pct`: how big was the actual move?
- `profitable_at_fee`: at what fee level would this trade have been profitable?

This means:

1. **Anyone can audit accuracy** — pull the `/signals/history` endpoint, compute follow-through rates on your own machine.
2. **Regime drift is visible** — if the edge degrades, the rolling follow-through rate drops. You'll see it before we tell you.
3. **Fee-aware filtering is built in** — `profitable_at_fee` lets you screen out signals that wouldn't have made money at your specific cost basis.

See `examples/signal_history_export.py` for a CSV exporter that lets you compute your own statistics.

---

## Why Maker Fees Matter

The profitability breakdown above shows the strategy is **only viable at maker fee levels**:

- At ultra-low maker fees (Coinbase Advanced VIP, Binance Futures market maker programs): 92.7% profitable
- At standard taker fees (~0.20% round-trip): only 0.9% profitable — essentially negative expected value

**If you're not using maker-only orders, this signal will not be profitable for you.** Plan accordingly. The `breakeven_fee_pct` field on each prediction tells you the maximum total fee at which that specific signal would have been profitable.

---

## Caveats

- **Validated on ETH only** — other assets in development
- **Initial study was 7 days** — longer-horizon stability requires ongoing monitoring (which is exactly what the production outcome tracking provides)
- **Past performance does not guarantee future results**
- **Trading involves substantial risk** — see [Terms of Service](https://leadedge.dev/terms) for full disclaimers
- **No financial advice** — LeadEdge provides data, not investment recommendations
