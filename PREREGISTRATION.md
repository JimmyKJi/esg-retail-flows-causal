# Pre-Registration  —  DRAFT (freeze before Phase 3 estimation)

> Status: **DRAFT**. Per the build plan, this file is frozen and committed
> *before* any estimation is run, so the specification cannot be tuned to the
> result. Do not edit after the freeze commit; record deviations in PROGRESS.md.

## Research question
When a stock enters the MSCI USA (Extended) ESG Leaders index, does institutional
capital *causally* flow in — and is that an **ESG-specific** response, or merely
the mechanical index-inclusion demand shock that any index add produces?

## Hypotheses
- **H1 (inclusion → flows).** ESG-Leaders inclusion raises aggregate institutional
  ownership and the number of 13F filers holding the stock, over quarters 0…+4.
- **H2 (ESG-specific effect — primary).** The inclusion effect for ESG adds exceeds
  the effect for matched generic (S&P 500) adds. Estimand:
  `ESG-specific = ATT(ESG inclusion) − ATT(S&P 500 inclusion)`. H2 holds iff > 0.
- **H3 (legitimacy decay — original contribution).** The ESG-specific effect
  *attenuates* after 2022. Estimand: coefficient on `treatment × post-2022 < 0`.
- **H4 (heterogeneity).** The response concentrates in passive and ESG-badged 13F
  filers relative to active/non-badged.

## Sample
- Treated: firms added to ESG-Leaders (via iShares SUSL/SUSA N-PORT diffs), ~2019–2026.
- Placebo: S&P 500 additions over the same window, matched 1:k.
- Controls: non-included firms matched on size, GICS sector, pre-period
  institutional ownership, and liquidity (PSM or coarsened exact matching).
- Unit/timing: firm × **quarter** (13F is quarterly — coarse by design).

## Outcomes
- **Primary:** Δ aggregate institutional ownership %; Δ number of 13F filers holding.
- **Secondary:** Fama-French-adjusted cumulative abnormal return around inclusion.

## Specification (frozen at freeze time)
- **Baseline event study:** event-time dummies q = −4…+4, ref = −1; firm and
  calendar-quarter FE; SEs clustered by firm (`pyfixest`).
- **Staggered DiD (headline):** Callaway-Sant'Anna group-time ATT (`differences`)
  and Sun-Abraham interaction-weighted event study (`pyfixest`). Naive two-way FE
  is **not** used as the headline (Goodman-Bacon bias).
- **Pre-trends:** joint test of pre-period coefficients = 0 is mandatory; if it
  fails, prefer the heterogeneity-robust event-study estimates and say so.
- **Placebo (H2):** identical estimator on the S&P 500 sample; report the difference.
- **Decay (H3):** `treatment × post-2022` interaction; Quandt-Andrews break test.

## Inference & robustness (pre-committed)
- Cluster-robust (firm) SEs throughout; 95% CIs on all event-study coefficients.
- Robustness: alternative matching (PSM ↔ CEM), alternative windows (±3, ±6
  quarters), winsorising outcomes at 1/99%, excluding crisis quarters (2020Q1-Q2).
- Decision rule: H1/H2/H3 "supported" only if signed as predicted **and** the
  pre-trends test passes for the relevant sample.

## Known limitations (stated, not hidden)
Institutional (13F) flows, **not retail**; quarterly (coarse) event timing; index
membership reconstructed via an ETF/N-PORT proxy; causal claims rest on the
parallel-trends/placebo design holding — reported when it does not.
