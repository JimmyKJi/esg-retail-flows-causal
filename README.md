# ESG Label or Just the Index? Causal Evidence on Institutional Flows

**Research question.** When a stock enters the MSCI USA (Extended) ESG Leaders
index, does institutional capital *causally* flow in — and is that an
**ESG-specific** response, or merely the mechanical index-inclusion demand shock
that *any* index add produces? And is that response **eroding** as ESG loses
political legitimacy?

**The headline you're building toward.** *Causal evidence on whether the market
prices the ESG label or merely the index — and whether that pricing is decaying
as ESG loses political legitimacy.*

**Status:** Phase 1 (data). Reachable sources ingested; SEC-hosted sources
(13F, N-PORT) written and unit-tested but pending an unblocked network — see
[SEC access note](#sec-access). Strategy in
`Jimmy - Quant Projects Plan (ESG + HR).md`; build spec drives the phases.

---

## Why this is rigorous, not just another ESG regression

1. **Placebo identification.** Any index addition moves flows mechanically
   (Shleifer 1986; Harris-Gurel 1986; Wurgler-Zhuravskaya). Running the *same*
   estimator on matched non-ESG inclusions (S&P 500 adds) isolates the
   ESG-specific component:
   `ESG-specific effect = ESG-inclusion effect − generic-inclusion effect`.
2. **ESG-legitimacy decay (the original contribution).** Test whether the
   institutional-flow response to ESG inclusion *weakens after ~2022*, as ESG
   becomes politically contested.
3. **Heterogeneity.** Split responders: passive vs active 13F filers; ESG-badged
   funds vs not — the effect should concentrate where theory predicts.
4. **Normative framing.** EU SFDR, UK SDR and the SEC climate-disclosure regime
   treat ESG ratings as quasi-authoritative signals that *lead* capital. If the
   ESG-specific effect is weak, absent, or decaying, that architecture rests on a
   false premise — a business-ethics finding, not just a finance result.

## Design at a glance
- **Treatment:** firm enters ESG Leaders (proxied via iShares SUSL/SUSA N-PORT
  monthly-holdings diffs). **Quarterly** event time (13F is quarterly).
- **Primary outcome:** Δ aggregate institutional ownership and Δ # of 13F filers.
  **Secondary:** FF-adjusted cumulative abnormal return.
- **Estimators:** event study + heterogeneity-robust staggered DiD
  (Callaway-Sant'Anna, Sun-Abraham). *Not* naive two-way FE (Goodman-Bacon).
- **Identification checks:** mandatory pre-trends test; S&P 500 placebo; post-2022
  structural break. Hypotheses pre-registered in `PREREGISTRATION.md` (frozen
  before estimation).

## Data
See `data/DATA_LINEAGE.md` for source, URL, date, license, and status of every
input. Reachable & ingested: Fama-French factors, S&P 500 change events, prices.
SEC-hosted & pending: 13F holdings (outcome), N-PORT holdings (treatment).

## Repository
```
src/ingest/    ff_factors, sp500_events, prices  (reachable);
               edgar_13f, nport_holdings, edgar_session  (SEC, run unblocked)
src/build/     panel, matching                   (Phase 2)
src/estimate/  event_study, did, placebo, structural_break, heterogeneity (Phase 3-5)
src/viz/       figures
tests/         smoke (reachable data) + SEC transform unit tests
data/          raw/ interim/ processed/ (gitignored) + DATA_LINEAGE.md
paper/         writeup + figures/ tables/
```

## Reproduce
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt        # ingestion stack; see note on the econ stack
make data            # Fama-French, S&P 500, prices  (works anywhere)
make test            # 6 tests: reachable-data smoke + SEC-transform units
# --- the following require an unblocked network (see SEC access note) ---
echo "SEC_EDGAR_UA=Your Name you@email.com" > .env
make data-sec        # 13F + N-PORT
make panel estimate placebo figures
```
> **Econometrics stack note.** `pyfixest`/`differences`/`polars` need prebuilt
> binaries; on the bleeding-edge numpy/pandas in this venv they try (and fail) to
> build from source. Install them on the analysis machine via
> `conda install -c conda-forge pyfixest polars numba differences`. None are
> needed for ingestion (Phase 1).

## <a name="sec-access"></a>⚠️ SEC access note
SEC's bot-manager returns **HTTP 403 to every client from the build
environment's IP** (curl, urllib, requests, WebFetch) across all SEC hosts —
even the homepage — while non-SEC sources work. The 13F + N-PORT ingestion is
therefore written and unit-tested but must be **run from a normal residential
connection** (no datacenter VPN). `src/ingest/edgar_session.py` raises a clear
`EdgarBlocked` with guidance when the block is in effect.

## Honest guardrails
Institutional (13F) flows, **not retail** (the original retail framing is dropped
— no WRDS/Vanda access; don't overclaim retail behaviour). Quarterly → coarse
event timing. Index membership reconstructed via an ETF/N-PORT proxy. Causal
claims rest on the parallel-trends/placebo design holding; reported when it
doesn't.

## About
Built by Jimmy Kaian Ji — KCL Philosophy BA. Applying causal-inference
methodology to capital markets and regulatory design.
Related: [HR Attrition Analytics](https://github.com/JimmyKJi/hr-attrition-analytics).
Contact: [linkedin.com/in/jimmy-kaian-ji](https://www.linkedin.com/in/jimmy-kaian-ji/).

---
*Original analysis. Findings will be reported honestly regardless of whether they
support the initial hypothesis.*
