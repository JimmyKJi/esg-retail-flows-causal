# ESG Label or Just the Index? Causal Evidence on Institutional Flows

**Research question.** When a stock enters the MSCI USA (Extended) ESG Leaders
index, does institutional capital *causally* flow in — and is that an
**ESG-specific** response, or merely the mechanical index-inclusion demand shock
that *any* index add produces? And is that response **eroding** as ESG loses
political legitimacy?

**Headline finding (honest null).** Once the mechanical index-inclusion effect is
differenced out with an S&P 500 placebo, there is **no ESG-specific institutional-
flow premium**: ESG-Leaders inclusion draws *less* institutional breadth than a
generic S&P 500 addition (ESG-minus-generic ≈ −121 filers, p = 0.001), and the
mandatory pre-trends test fails for the ESG arm — so even the level estimate is
reported with that caveat, not as clean causal evidence. The full writeup is in
[`paper/paper.md`](paper/paper.md).

**Status:** Phase 3 complete (data → panel → matched controls + placebo → estimation
→ writeup). All sources ingested (Fama-French, S&P 500 changes, prices; SEC N-PORT
treatment + 13F outcome); panel, matched samples, and placebo arm built; the
heterogeneity-robust staggered-DiD battery estimated (`results/`), figures/tables
rendered (`paper/`), and the paper drafted. SEC access resolved — see
[SEC access note](#sec-access). Hypotheses frozen in `PREREGISTRATION.md` before
estimation; per-input provenance in `data/DATA_LINEAGE.md`.

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
   *(Classifier coded, but not estimable on this data: the cached 13F is
   CUSIP×quarter aggregates with no per-filer CIK — see paper §5.4.)*
4. **Normative framing.** EU SFDR, UK SDR and the SEC climate-disclosure regime
   treat ESG ratings as quasi-authoritative signals that *lead* capital. If the
   ESG-specific effect is weak, absent, or decaying, that architecture rests on a
   false premise — a business-ethics finding, not just a finance result.

## Design at a glance
- **Treatment:** firm enters ESG Leaders (proxied via iShares SUSL/SUSA N-PORT
  quarterly-holdings diffs; identifier-churn adds flagged). **Quarterly** event
  time (13F is quarterly).
- **Primary outcomes:** ownership **breadth** (`n_filers`, count of 13F filers) and
  **depth** (`log_shares`, log aggregate shares — unit-immune to the 2023 13F
  value-reporting change). **Secondary:** `log_value` and an FF-adjusted cumulative
  abnormal return (the latter on the S&P 500 placebo arm only — see guardrails).
- **Estimators:** event study + heterogeneity-robust staggered DiD
  (Callaway-Sant'Anna, Sun-Abraham). *Not* naive two-way FE (Goodman-Bacon).
- **Identification checks:** mandatory pre-trends test; S&P 500 placebo; post-2022
  structural break. Hypotheses pre-registered in `PREREGISTRATION.md` (frozen
  before estimation).

## Data
See `data/DATA_LINEAGE.md` for source, URL, date, license, and status of every
input. Reachable & ingested: Fama-French factors, S&P 500 change events, prices.
SEC-hosted: N-PORT holdings (treatment) ✅ pulled; 13F holdings (outcome) — next.

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
> **Econometrics stack note.** `pyfixest`/`differences`/`polars`/`numba` are
> pinned in `requirements.txt` and run in this venv — estimation and the full
> test suite pass locally. If a fresh `pip install` can't build the wheels for
> your numpy/pandas, fall back to
> `conda install -c conda-forge pyfixest polars numba differences`. None are
> needed for ingestion (Phase 1) — only for estimation (Phase 3+).

## <a name="sec-access"></a>SEC access note (resolved)
SEC's Akamai bot-manager 403'd every client until **two stacked filters** were
cleared: (1) a **datacenter/VPN egress IP** (SEC blocks those wholesale — run
from a residential ISP with the VPN off), and (2) a **non-deliverable UA email**
(e.g. a `…@users.noreply.github.com` address — set
`SEC_EDGAR_UA="Name real@email.com"` in `.env`). Both fixed → 200.
`src/ingest/edgar_session.py` raises a clear `EdgarBlocked`, now with a live
egress-IP diagnosis, if either condition recurs.

## Honest guardrails
Institutional (13F) flows, **not retail** (the original retail framing is dropped
— no WRDS/Vanda access; don't overclaim retail behaviour). Quarterly → coarse
event timing. Index membership reconstructed via an ETF/N-PORT proxy, and
treatment is a CUSIP diff — so corporate-action CUSIP changes (splits,
redomiciles, renames, mergers) can masquerade as inclusions; exact-name cases are
auto-flagged (`corp_action_suspect`) and the changed-name remainder is reconciled
in Phase 2. Causal claims rest on the parallel-trends/placebo design holding;
reported when it doesn't.

## About
Built by Jimmy Kaian Ji — KCL Philosophy BA. Applying causal-inference
methodology to capital markets and regulatory design.
Related: [HR Attrition Analytics](https://github.com/JimmyKJi/hr-attrition-analytics).
Contact: [linkedin.com/in/jimmy-kaian-ji](https://www.linkedin.com/in/jimmy-kaian-ji/).

---
*Original analysis. Findings will be reported honestly regardless of whether they
support the initial hypothesis.*
