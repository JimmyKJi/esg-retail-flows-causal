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

![ESG-Leaders adds vs. matched S&P 500 placebo adds — institutional-breadth event study](paper/figures/esg_vs_placebo.png)

*Breadth (number of 13F filers) around index inclusion; event time in quarters,
shaded band = pre-period parallel-trends test. **Left:** ESG-Leaders adds draw
≈ +28 filers. **Right:** matched generic S&P 500 adds draw ≈ +149. Differencing
the two isolates the ESG-specific effect: **−121.5 filers (se 37.3, p = 0.001)**
— ESG inclusion draws **less** institutional breadth than an ordinary index add,
not more.*

### Results at a glance

| Hypothesis | Prediction | Headline estimate (breadth, 13F filers) | Verdict |
|:--|:--|:--|:--|
| **H1** — index inclusion moves flows | positive | ESG **+27.6** (se 9.4); S&P placebo **+149.0** (se 36.1) | Mechanical effect present; ESG pre-trend fails |
| **H2** — ESG-*specific* premium | ESG > generic | ESG − generic = **−121.5** (se 37.3), **p = 0.001** | **Not supported — wrong sign** |
| **H3** — legitimacy decay post-2022 | late < early | early +33.5, late +21.4; Δ = **−12.1** (se 18.1), p = 0.50 | Not supported (underpowered late cohort) |
| **H4** — heterogeneity by filer type | concentrated in ESG/passive | re-ingested 13F at CIK grain; ESG-specific < 0 in **0 / 4** filer-type outcomes (best channel `log_shares_esg` **−1.13**, p = 0.026) | **Not supported — null survives decomposition** |
| **Robustness** — 8 pre-registered specs | — | ESG-specific < 0 in **8 / 8**; significant in **7 / 7** that carry inference (−61 to −137 filers) | Null is robust |
| **Credibility** — power / MDE / honest DiD / placebo | — | breadth design well-powered (MDE ≈ **104** filers @80%; 95% CI rules out a positive premium); depth & decay **underpowered** (stated); negative point estimate itself pre-trend-fragile (honest DiD M\* ≈ 0.27); +28-filer level effect not a timing artifact (placebo-in-time p = 0.013) | Breadth null is *evidence of absence*; rests on power, not the negative sign |

*Estimator: heterogeneity-robust Sun-Abraham event study on CEM-matched controls,
windowed post-ATT over event quarters 0–4. Depth (`log_shares`) is negative in
every spec and significant in none. Full numbers in [`results/`](results/) and
[`paper/paper.md`](paper/paper.md).*

**Status:** Phase 6 complete (data → panel → matched controls + placebo →
estimation → pre-registered robustness battery → filer-type heterogeneity →
credibility-of-the-null battery → writeup). All sources ingested (Fama-French,
S&P 500 changes, prices; SEC N-PORT
treatment + 13F outcome); panel, matched samples, and placebo arm built; the
heterogeneity-robust staggered-DiD battery estimated, stress-tested across 8
specifications, decomposed by 13F filer type (H4, re-ingested at CIK grain), and
put through a pre-specified credibility-of-the-null battery (power/MDE +
equivalence + honest DiD [Rambachan-Roth] + placebo-in-time randomization)
(`results/`),
figures/tables rendered (`paper/`), and the paper drafted. SEC access resolved —
see [SEC access note](#sec-access). Hypotheses frozen in `PREREGISTRATION.md`
before estimation; per-input provenance in `data/DATA_LINEAGE.md`.

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
   *(Estimated by re-ingesting the raw 13F at the filer-CIK grain and re-running
   the placebo contrast per filer type. The null survives: no channel — including
   passive-complex depth — shows a positive ESG-specific effect; ESG-named
   managers' depth response is significantly weaker for ESG than generic adds.
   13F is filed at the manager level, so ESG-named = ESG-branded firms, not ESG
   sleeves of large complexes, which surface as passive depth — see paper §5.4.)*
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
SEC-hosted: N-PORT holdings (treatment) ✅ and 13F holdings (outcome) ✅ both
pulled. All raw/interim/processed data is gitignored and rebuilds from source.

## Repository
```
src/ingest/    ff_factors, sp500_events, prices  (reachable);
               edgar_13f, nport_holdings, edgar_session  (SEC, run unblocked);
               edgar_13f_byfiler  (Phase 5 filer-CIK re-ingest, no network)
src/build/     panel, matching, crosswalk, car, placebo   (Phase 2-2b)
src/estimate/  did (CS + Sun-Abraham), robustness, event_study, heterogeneity,
               h4_filer, placebo, structural_break        (Phase 3-5)
               credibility  (Phase 6 — power/MDE + honest DiD + placebo-in-time)
src/viz/       figures
tests/         smoke (reachable data) + SEC-transform + estimator/robustness units
data/          raw/ interim/ processed/ (gitignored) + DATA_LINEAGE.md
results/        *.csv / *.parquet estimates (committed) + run logs (gitignored)
paper/         writeup + figures/ tables/
```

## Reproduce
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt        # ingestion stack; see note on the econ stack
make data            # Fama-French, S&P 500, prices  (works anywhere)
make test            # 56 tests: reachable-data smoke + SEC-transform + estimator/credibility units
# --- the following require an unblocked network (see SEC access note) ---
echo "SEC_EDGAR_UA=Your Name you@email.com" > .env
make data-sec        # 13F + N-PORT
make panel matched estimate robustness
make heterogeneity   # Phase 5 — H4 filer-type re-ingest + ESG/passive contrast
make credibility     # Phase 6 — power/MDE + equivalence + honest DiD + placebo-in-time
make figures         # render all exhibits (incl. H4 + credibility panels)
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
