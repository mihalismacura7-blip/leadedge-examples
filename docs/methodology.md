# Validation Methodology

LeadEdge was validated with **7 days of live WebSocket data** before any product code was written. This document summarizes the methodology — full writeup is at [leadedge.dev/blog/validation](https://leadedge.dev/blog/validation).

## Data Collection

- **Sources:** Binance Futures (leader candidate), Coinbase Spot (follower candidate)
- **Asset:** ETH/USDT
- **Duration:** 7 continuous days
- **Method:** Live WebSocket streams, timestamps normalized to microsecond precision
- **Volume:** 9.4M price updates

## Key Question Answered

> "When Binance Futures moves >X%, what % of the time does Coinbase Spot move in the same direction within Y milliseconds?"

## Results

| Metric | Value |
|--------|-------|
| Median lag | ~150ms |
| Follow-through rate (0.1% threshold) | **90.7%** |
| Signals per week (0.05% threshold) | 315+ |
| Profitability at ultra-low maker fees (0.04% RT) | 92.7% |
| Profitability at standard maker fees (0.08% RT) | 89.7% |
| Profitability at mixed fees (0.12% RT) | 43.9% |
| Profitability at standard taker fees (0.20% RT) | 0.9% |

## Why This Matters

Anyone can claim a trading edge. **The methodology behind measurement is what makes the claim defensible.**

LeadEdge's approach:

1. **Validate before build** — No product code until empirical evidence shows the edge exists
2. **Live data only** — No backtests, no simulations
3. **Out-of-sample testing** — Findings verified on fresh data not used in initial analysis
4. **Continuous monitoring** — Production signals are tracked and reported transparently

This is the trust layer: not the algorithm, but the rigor of measurement.

## Why Maker Fees Matter

The profitability breakdown above shows the strategy is **only viable at maker fee levels**. This is critical:

- At ultra-low maker fees (e.g., Coinbase Advanced VIP, Binance Futures market maker programs): 92.7% profitable
- At standard taker fees (~0.20% round-trip): only 0.9% profitable — essentially negative expected value

If you're not using maker-only orders, this signal will not be profitable for you. Plan accordingly.

## Caveats

- **Validated on ETH only** — other assets in development
- **7-day window** — longer-horizon stability requires ongoing monitoring
- **Past performance does not guarantee future results**
- **Trading involves substantial risk** — see [Terms of Service](https://leadedge.dev/terms) for full disclaimers
- **No financial advice** — LeadEdge provides data, not investment recommendations

## Continuous Validation

LeadEdge continuously monitors signal performance in production. The methodology isn't a one-time validation exercise — it's a sustained measurement infrastructure that:

- Tracks real-time follow-through rates
- Detects regime shifts where the signal degrades
- Adjusts confidence calibrations based on rolling performance
- Publishes performance updates transparently

If the signal stops working, you'll know — not from us telling you, but because the confidence scores will drop and the dashboard will show it.
