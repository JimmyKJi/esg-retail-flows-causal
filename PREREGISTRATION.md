# Pre-Registration  —  FROZEN 2026-06-06 (before any Phase 3 estimation)

> Status: **FROZEN**. This specification is committed *before* any treatment
> effect is estimated, so it cannot be tuned to the result. It was finalised
> *after* the data was assembled (Phases 1–2b), so the outcomes, sample, and
> design below reflect what the data actually supports — informed by data
> **structure**, never by treatment-effect **results** (none have been run).
> Do not edit after this freeze commit; record any deviation in PROGRESS.md.

## Research question
When a stock enters the MSCI USA (Extended) ESG Leaders index, does institutional
capital *causally* flow in — and is that an **ESG-specific** response, or merely
the mechanical index-inclusion demand shock that any index add produces? Is it
**decaying** as ESG investing matures post-2022?

## Hypotheses
- **H1 (inclusion → flows).** ESG-Leaders inclusion raises institutional ownership
  breadth (number of 13F filers) and depth (shares held), over quarters 0…+4.
- **H2 (ESG-specific effect — primary).** The inclusion effect for ESG adds exceeds
  the effect for generic (S&P 500) adds. Estimand:
  `ESG-specific = ATT(ESG inclusion) − ATT(S&P 500 inclusion)`. H2 holds iff > 0.
- **H3 (legitimacy decay — original contribution).** The ESG-specific effect
  *attenuates* after 2022. Estimand: coefficient on `treatment × post-2022 < 0`.
- **H4 (heterogeneity).** The response concentrates in passive and ESG-badged 13F
  filers relative to active / non-badged.

## Outcomes (reconciled to what the CUSIP-keyed 13F panel supports)
- **Primary:**
  1. `n_filers` — institutional-ownership **breadth** (count of 13F filers holding
     the CUSIP that quarter); and its one-quarter change `d_n_filers`.
  2. `log_shares` — ownership **depth** (log aggregate shares held); change
     `dlog_shares`. Shares are **unit-immune** to the 2023 VALUE reporting change.
- **Secondary:**
  3. `log_value` / `dlog_value` — aggregate dollar holdings (after the
     ×1000 pre-2023 unit normalisation); moves with price, so secondary.
  4. **FF-adjusted CAR** around inclusion — the *price* reaction. Computed on the
     **S&P 500 placebo arm only** (see Limitations): a daily event study needs a
     priceable ticker and a precise date, which the ESG arm lacks.
- **Deviation from the original draft, stated:** the draft named "Δ aggregate
  institutional ownership **%**". A percentage needs shares-outstanding, which is
  not in any free CUSIP-keyed source we have; breadth + share-depth are the
  measurable analogues and are the pre-committed primary outcomes.

## Sample (as assembled — `data/processed/panel.parquet`)
- **Unit/timing:** firm (CUSIP) × **calendar quarter**; 2019Q1–2026Q1, 29 quarters.
  13F is quarterly, so event time is in **quarters** — coarse by design.
- **Treated (ESG):** firms added to ESG-Leaders via iShares SUSL/SUSA N-PORT diffs
  — **334** with a datable inclusion; cohort = **first** inclusion quarter.
- **Controls (ESG):** the **95,035 clean controls** — never in the index. Firms
  already in the index at the 2019Q4 window start (left-censored members) and
  corp-action-suspect adds (**203 total**) are flagged `esg_excluded` and held
  **out** of the control pool.
- **Placebo (generic):** S&P 500 additions over the same window — **123** treated
  CUSIPs; controls are firms never in the S&P 500 (`~sp500_member_ever`).
- **Matched samples (robustness):** per-cohort PSM and CEM at baseline quarter
  g−1, on the pre-treatment ownership covariates the panel carries (`log_value`
  size proxy, `log_shares`, `n_filers`). Built symmetrically for both arms.

## Treatment definition (pre-committed; this is the key identification call)
- **Treatment = FIRST inclusion (ITT), absorbing by construction.** Treatment is
  **non-absorbing in reality**: **177/334** treated firms later exit the index
  (`ever_dropped`). Canonical Callaway-Sant'Anna assumes absorbing treatment, so
  the headline estimand is the dynamic ATT around the **first** inclusion (an
  intention-to-treat: post-period firms that later exit are *kept* treated).
  Long-horizon ATT is therefore attenuated by exits — reported, not corrected away.
- **Robustness:** (a) drop `ever_dropped` firms; (b) restrict the post window to
  quarters before the first exit.

## Specification (frozen)
- **Baseline event study:** event-time dummies q = −4…+4, reference q = −1; firm
  and calendar-quarter fixed effects; SEs clustered by firm (`pyfixest`).
- **Staggered DiD (headline):** Callaway & Sant'Anna (2021) group-time ATT(g,t)
  via `differences` (never-treated/clean controls as the comparison), aggregated
  to a dynamic event study; Sun & Abraham (2021) interaction-weighted event study
  via `pyfixest`. **Naive two-way FE is not the headline** (Goodman-Bacon bias).
- **Pre-trends:** a joint test that pre-period (q < −1) coefficients = 0 is
  **mandatory**. Note: raw treated-group breadth already drifts up pre-inclusion
  (event-time −3→−1: 806→836 filers), so this test is load-bearing — if it fails
  we prefer the heterogeneity-robust event-study estimates and **say so plainly**.
- **Placebo / H2:** the identical estimator on the S&P 500 arm; report
  `ATT(ESG) − ATT(S&P)`. **Primary placebo = S&P-only adds** (the **65** firms
  that are S&P-added but never ESG-treated), excluding the **58** `both_treated`
  firms whose inclusion conflates the two shocks; **robustness = full S&P arm**.
- **Decay / H3:** `treatment × post-2022` interaction on the dynamic ATT;
  cohort-split (pre-/post-2022 cohorts) as the non-parametric version.
- **Heterogeneity / H4:** re-aggregate the cached 13F INFOTABLE by filer CIK into
  filer-type buckets and re-run the breadth/depth outcomes per bucket:
  - **passive** = the index-fund complexes (Vanguard, BlackRock/iShares, State
    Street, etc., by manager-name match) vs. **active** = the rest;
  - **ESG-badged** = filers whose name matches an ESG/SRI/sustainable pattern.
  Pre-committed as a name-heuristic classification (documented, imperfect).

## Inference & robustness (pre-committed)
- Cluster-robust (firm) SEs throughout; 95% CIs on all event-study coefficients.
- Robustness battery: alternative matching (PSM ↔ CEM ↔ full clean-control),
  alternative windows (±3, ±6 quarters), winsorising the change outcomes at
  1/99%, excluding the COVID crisis quarters (2020Q1–Q2), and the two treatment
  definitions above.
- **Decision rule:** H1/H2/H3 are "supported" only if signed as predicted **and**
  the pre-trends test passes for the relevant sample. H4 is descriptive.

## Known limitations (stated, not hidden)
Institutional (13F) flows, **not retail**; quarterly (coarse) event timing; index
membership reconstructed via an iShares ETF / N-PORT proxy, not the MSCI index
itself; the ESG-arm price CAR is not estimable (no free CUSIP→ticker bridge +
quarterly N-PORT dating), so the CAR is a placebo-arm benchmark only; matching
covariates are size + pre-ownership (sector/GICS and a price-based liquidity
measure are not in the CUSIP panel). All causal claims rest on the
parallel-trends / placebo design holding — and are reported when it does not.
