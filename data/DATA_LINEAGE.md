# Data Lineage

Every input: exact source, URL, date pulled, license, status. Raw files live
under `data/raw/` (gitignored — never committed). Reproduce with `make data`
(reachable sources) and `make data-sec` (SEC sources — run from a residential
network with a real-email UA; see the access note).

_Last updated: 2026-06-06 (Phase 3 — heterogeneity-robust staggered-DiD estimates, placebo contrast, and decay split written to `results/`; figures/tables to `paper/`)._

## Treatment — ESG-index inclusion events  **(LOCKED: SEC Form N-PORT-P)**

| field | value |
|---|---|
| What | Firm enters the MSCI USA (Extended) ESG Leaders index. Proxied by the holdings of iShares **SUSL** (ESG MSCI USA Leaders) and **SUSA** (MSCI USA ESG Select), which track the index. An add into the ETF ≈ an inclusion event. |
| Source | SEC EDGAR, Form **N-PORT-P** (public fund portfolio holdings, structured XML — filed **quarterly**, as-of the fiscal-quarter-end `repPdDate`) |
| URL | browse-EDGAR atom by fund *series* id (`?action=getcompany&CIK=S000065418&type=NPORT-P&output=atom`) → `https://www.sec.gov/Archives/edgar/data/1100663/<accession>/primary_doc.xml` |
| Method | Diff consecutive quarterly snapshots; CUSIP present at quarter *t* but not *t−1* = inclusion. Same-quarter exact-name add+drop pairs (split/redomicile CUSIP churn) flagged `corp_action_suspect`. Code: `src/ingest/nport_holdings.py`. |
| License | US Government work — public domain |
| Date pulled | 2026-06-05 — SUSL+SUSA quarterly N-PORT (2020→2026): 946 raw events (494 adds); 27 rows flagged as identifier churn (flagged on both the add and the drop side of each pair; 13 add-side) → 494 − 13 = **481 genuine inclusions**. CUSIP is the join key (tickers absent in N-PORT). |
| Caveat | As-of dates are fiscal-quarter-ends (Feb/May/Aug/Nov for SUSL) — offset ~1 month from 13F calendar quarters (Mar/Jun/Sep/Dec); aligned in Phase 2. **Changed-name** renames/mergers (AXA Equitable→Equitable; BB&T+SunTrust→Truist) evade the exact-name flag and are reconciled in Phase 2 before events become treatment. |

**Why N-PORT, not the build plan's first suggestions?** The plan offered (1) an
iShares-holdings-CSV-via-Wayback proxy and (2) MSCI press releases. During Phase 1
discovery the Wayback Machine returned **no usable captures** of the iShares
holdings endpoint, and the live iShares CSV is a single current snapshot with no
history. N-PORT-P gives free, structured *quarterly* holdings back to ~2019 and is
the robust source. This is the locked Phase 1 decision.

## Primary outcome — institutional flows (13F)

| field | value |
|---|---|
| What | Δ aggregate institutional ownership and Δ count of 13F filers holding a security, around inclusion |
| Source | SEC EDGAR **Form 13F structured data sets** (quarterly TSV bundles) |
| URL | Landing page `https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets`, scraped for bundle zips under `https://www.sec.gov/files/structureddata/data/form-13f-data-sets/`. Two naming conventions: `YYYYqQ_form13f.zip` (older, back to 2013Q2) and `DDmonYYYY-DDmonYYYY_form13f.zip` (newer, filing-receipt window). |
| Method | `list_datasets()` discovers both conventions; bundles download in parallel (streaming, atomic `.part`, resumable). Per bundle: parse `INFOTABLE.tsv`+`SUBMISSION.tsv`, take the **modal `PERIODOFREPORT`** (bundles are keyed by receipt window, not report quarter, so each mixes a little adjacent-quarter straggler/amendment noise), dedup to the **latest filing per CIK** (amendment supersedes original → `n_filers` = distinct institutions, not filings), roll up per CUSIP. Per-bundle checkpoints in `data/interim/_13f_parts/`. Code: `src/ingest/edgar_13f.py`. **Unit-tested** (`tests/test_edgar_transforms.py`). |
| Caveat | `VALUE` units changed $thousands→whole-$ on/after 2023-01 — normalise by period in Phase 2. 13F is quarterly → event time is in **quarters**. Modal-period filtering drops the ~3% late filings that land in an adjacent receipt window (slight `n_filers` undercount). Zip layout varies (some bundles nest the TSVs in a subfolder) — matched by basename. Run under `caffeinate` so the machine can't sleep mid-pull. |
| License | US Government work — public domain |
| Date pulled | **2026-06-06** — 32 quarterly bundles pulled (~24 MB/s, 5 parallel workers); after trimming pre-`since` periods: **988,292 CUSIP×quarter rows, 29 quarters (2019Q1→2026Q1), 97,660 distinct CUSIPs**. CUSIP coverage of the 481 genuine inclusion events = **334/335 (99.7%)**; the sole miss is an `N/A` placeholder CUSIP in the treatment (drop in Phase 2). Persisted `data/interim/holdings_13f.parquet`. |

## Placebo sample — generic (non-ESG) index inclusions  ✅ pulled

| field | value |
|---|---|
| What | S&P 500 additions/deletions — the generic index-inclusion benchmark for the placebo |
| Source | Wikipedia, "List of S&P 500 companies" (constituents + "Selected changes") |
| URL | https://en.wikipedia.org/wiki/List_of_S%26P_500_companies |
| License | CC BY-SA 4.0 |
| Date pulled | 2026-06-05 — **754 change events** (379 adds / 375 drops), 1976→2026 |
| Caveat | "Selected changes" is a curated subset, reliable from ~2000; a fuller list would diff the page's revision history. |

## Risk factors — Fama–French  ✅ pulled

| field | value |
|---|---|
| What | Daily FF 5-factor + momentum + risk-free, for the abnormal-return (secondary) outcome |
| Source | Kenneth R. French Data Library (Dartmouth) |
| URL | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/ |
| License | Free for academic use |
| Date pulled | 2026-06-05 — **15,813 daily rows**, 1963-07-01 → 2026-04-30 |

## Prices — Yahoo Finance  ✅ pulled (sample)

| field | value |
|---|---|
| What | Daily adjusted close + volume, for abnormal-return computation |
| Source | Yahoo Finance via `yfinance` |
| URL | (yfinance API) |
| License | Yahoo terms — personal/research use |
| Date pulled | 2026-06-05 — sample (AAPL/MSFT/NVDA, 2020-2024) verified; full pull keyed to the event sample |

## Processed output — firm×quarter analysis panel  ✅ built (Phase 2)

| field | value |
|---|---|
| What | The analysis dataset: one row per (CUSIP, calendar quarter) with the 13F outcomes, the ESG-inclusion treatment structure, and a sample role. |
| Source | Derived — joins `holdings_13f.parquet` (outcome) + `esg_inclusion_events.parquet` (treatment) + `esg_index_holdings.parquet` (membership flags). Code: `src/build/panel.py`, unit-tested (`tests/test_panel.py`). |
| Method | Both treatment as-of dates (N-PORT fiscal quarter-ends, Feb/May/Aug/Nov) and outcome dates (13F calendar quarter-ends) folded onto the **containing calendar quarter** so they join. Cohort = first genuine inclusion quarter (staggered-DiD timing); `event_time` in quarters; `post`/`esg_inclusion` absorbing from cohort. VALUE normalised ×1000 for periods ≤ 2022-09-30 (2023 unit change; `n_filers`/`total_shares` immune). Junk CUSIPs (non-9-char, issuer-base `000000`, the `N/A` placeholder) dropped. |
| Output | `data/processed/panel.parquet` (gitignored) — **904,589 rows, 95,572 CUSIPs, 29 quarters (2019Q1→2026Q1)**. Roles: **334 treated**, 95,035 clean controls, **203 esg_excluded** (left-censored members + corp-action-suspect adds, kept OUT of the control pool). 332/334 treated CUSIPs have both pre- and post-inclusion quarters observed. |
| Caveat | **Treatment is non-absorbing:** 177/334 treated firms later exit the index (`ever_dropped`) — canonical Callaway-Sant'Anna assumes absorbing treatment, so the headline is an event study around *first* inclusion (ITT); long-horizon ATT is attenuated by exits. The raw treated-group breadth shows a mild **pre-trend** (event-time −3→−1: 806→836), so the placebo (S&P 500) and clean-control DiD + a pre-trends test are what isolate any ESG-specific effect — not the raw means. The panel now also carries the symmetric `sp500_*` placebo arm (see below). |
| License | Derived from US-Government-work + CC-BY-SA inputs (see above). |

## Processed output — CUSIP↔name crosswalk (placebo bridge)  ✅ built (Phase 2b)

| field | value |
|---|---|
| What | A CUSIP→issuer-name map so the ticker/name-keyed S&P 500 placebo can be matched onto the CUSIP-keyed 13F panel (CUSIP is licensed — no free authoritative ticker→CUSIP table exists). |
| Source | Derived — pools the `NAMEOFISSUER`+`CUSIP` columns from **every cached 13F INFOTABLE** (equity rows only, PUTCALL blank), taking each CUSIP's modal name by filer-row support. Code: `src/build/crosswalk.py` (match coverage validated by the reported exact/subset/miss rates, not a dedicated unit test). |
| Output | `data/interim/cusip_names.parquet` (gitignored) — **79,944 equity CUSIPs**. |
| Caveat | Name matching is imperfect: exact-normalised first, then a **prominence-tie-break token-subset** fallback (highest-13F-support superset wins). On S&P 500 adds since 2019 this gives **92% coverage (124/135: 105 exact + 19 subset + 11 miss)**; misses are recent spin-offs/IPOs/renames. These 124 matched add-events resolve to **123 unique CUSIPs** (one issuer, CUSIP 35137L105, was S&P-added twice in-window) — exactly the placebo-treated count the panel carries. Coverage is reported by `match` ∈ {exact, subset, miss}, not assumed. |

## Processed output — S&P 500 placebo arm  ✅ built (Phase 2b)

| field | value |
|---|---|
| What | The generic (non-ESG) index-inclusion benchmark: S&P 500 additions mapped to CUSIP, with the **identical cohort/event-time/post structure** as the ESG arm (`sp500_*` columns on the panel). The ESG-specific effect = ESG ATT − S&P-500 ATT. |
| Source | Derived — `src/build/placebo.py` maps S&P adds→CUSIP via the crosswalk; `src/ingest/sp500_events.py` persists the dated changes (+GICS); `src/build/panel.py` applies the placebo cohort symmetrically. |
| Output | `sp500_*` columns in `data/processed/panel.parquet`: **123 placebo-treated, 787 ever-S&P-members** (kept out of the placebo's control pool), **99 estimable**. **58 firms are both ESG- and S&P-treated** (`both_treated`, a contamination flag), leaving **65 clean-generic** (S&P-add but never-ESG) firms for the contrast. |
| Caveat | The "Selected changes" table is reliable from ~2000; pre-2019 adds (cohort baseline before the 2019Q1 panel start) and the 11 unmatched names reduce the usable count. The clean-generic comparison (65 firms) is modest but real. |

## Processed output — matched controls  ✅ built (Phase 2b)

| field | value |
|---|---|
| What | Per-cohort matched comparison samples for both arms — a robustness design alongside the full clean-control set. |
| Source | Derived — `src/build/matching.py` (PSM = pooled propensity with baseline-quarter FE + nearest-neighbour on the logit; CEM = quantile-bin exact strata), run symmetrically for ESG and S&P. Unit-tested (`tests/test_matching.py`). |
| Method | Matched at the **baseline quarter g−1** (calendar/level confounding differenced out by the match) on pre-treatment institutional-ownership covariates the CUSIP panel carries directly: `log_value` (size proxy), `log_shares`, `n_filers` (breadth). Controls are never-treated for the arm (ESG: clean_control; S&P: never-member). |
| Output | `data/processed/matched_{esg,sp500}_{psm,cem}.parquet` (gitignored). ESG **332/332** matched (of 334 treated; 2 lack an estimable baseline g−1), S&P **101/101** matched (of 123 placebo-treated; 22 lack a baseline g−1), 0 unmatched. The 101 matched S&P firms still include the 58 `both_treated`; the headline H2 contrast in `did.py` runs only on the **65 clean-generic** firms (`both_treated` excluded), which is the `n_treated` reported in `results/summary.csv`. Balance: the naive pool sits **>2 SDs** from treated on size (|SMD| ≈ 2.1–2.5); matching collapses this to **\|SMD\| < 0.05 (CEM) / < 0.15 (PSM)**. |
| Caveat | Sector (GICS, free only for current S&P members) and a price-based liquidity measure are **not** in the CUSIP panel — accepted as optional covariates when joined in, not silently omitted. |

## Processed output — FF-adjusted CAR (secondary outcome)  ✅ built (Phase 2b)

| field | value |
|---|---|
| What | The *price* reaction to inclusion: a Fama-French five-factor event-study cumulative abnormal return, triangulating the primary 13F-flow outcome. |
| Source | Derived — `src/build/car.py` (market model on excess returns over a ≈1yr pre-event estimation window; abnormal = actual−predicted; CAR = sum over the event window). Prices from `yfinance`, factors from the FF table. Unit-tested (`tests/test_car.py`). |
| Output | `data/processed/car_sp500.parquet` (gitignored); headline committed to `results/car_summary.csv` so the figure is reproducible from the repo. Recovers the **modern S&P 500 index effect**: CAR[−5,+5] = **+1.35% (t=1.55, n=99, 54% positive)**; tight windows ≈0. Coverage (124 add-events): 99 ok, 20 insufficient pre-history (recent IPOs), 3 no-prices/delisted (CTLT/FRC/CDAY), 2 date-edge (event window out-of-bounds / event after data end). |
| Caveat | **Runs on the S&P placebo arm, not the ESG arm — by data necessity, stated plainly.** A daily event study needs a priceable ticker *and* a precise date; S&P adds have both (Wikipedia effective dates + tickers), but the ESG inclusions have **neither at resolution**: there is no free CUSIP→ticker bridge for ESG-only firms, and N-PORT dates inclusion only at the fund's *fiscal quarter-end* (quarterly, not daily). So the generic-inclusion CAR is the deliverable; the ESG question stays on the fully-covered quarterly flow design. |
| License | Derived from Yahoo (research use) + FF (academic) inputs. |

## Estimation output — Phase 3 staggered-DiD results  ✅ built (Phase 3)

| field | value |
|---|---|
| What | The frozen Phase-3 estimates: dynamic event studies, the windowed-ATT summary, the H2 ESG-specific contrast, and the H3 decay split (H4 filer-type heterogeneity is its own Phase-5 output, below). Unlike the gitignored `data/` artefacts, these are **small and committed** so the figures are reproducible from the repo. |
| Source | Derived — `src/estimate/did.py` on `panel.parquet` + `matched_{esg,sp500}_cem.parquet`. Estimators: Callaway-Sant'Anna 2021 (`differences`, headline dynamics), Sun-Abraham 2021 (manual interaction-weighted event study via `pyfixest`, carries the windowed inference), and a naive two-way-FE event study (`pyfixest i()`, Goodman-Bacon baseline only). Unit-tested (`tests/test_did.py`). |
| Method | Each estimator runs on the **full clean-control pool** (pre-registered headline, but confounded — treated firms are large, controls are micro-caps on a steep secular uptrend → pre-trends fail) and the **CEM-matched pool** (credible; level balanced at g−1). Mandatory joint pre-trends Wald test on event times {−4,−3,−2}. H2 = ATT(ESG)−ATT(S&P), H3 = ATT(late)−ATT(early) split at 2022Q1, both Sun-Abraham windowed post-ATT (e=0..+4) on matched controls. |
| Output | `results/event_studies.parquet` (tidy event-time coefficients: estimator × arm × outcome × control_pool), `results/summary.csv` (per outcome×arm windowed ATT + pre-trend p/pass), `results/h2_esg_specific.csv`, `results/h3_decay.csv`. Figures `paper/figures/{event_study,esg_vs_placebo,decay}.png` and markdown tables `paper/tables/*.md` via `src/viz/figures.py`. **Committed** (only `results/*.log` is gitignored). |
| Caveat | All causal claims are gated on the pre-trends test per the frozen decision rule — reported honestly when it fails. (H4 filer-type heterogeneity, once a data limitation, is now estimated in Phase 5 below.) |
| License | Derived from the inputs above (US-Government-work + CC-BY-SA + research-use). |

## Estimation output — Phase 4 robustness battery  ✅ built (Phase 4)

| field | value |
|---|---|
| What | The pre-registered robustness sweep: re-estimates the **H2 ESG-specific contrast** (ATT_ESG − ATT_S&P) under each perturbation named in `PREREGISTRATION.md`, varying one dimension at a time off the credible baseline (CEM controls, post horizon 0..+4). |
| Source | Derived — `src/estimate/robustness.py` (reuses the frozen `did.py` estimators; the baseline row reproduces `h2_esg_specific.csv` exactly). Unit-tested (`tests/test_robustness.py`, incl. a check that the windowed-ATT recompute matches the estimator's own number). |
| Method | Eight specifications per primary outcome: baseline; alt. averaging horizons (0..+2 / 0..+6, recomputed from the same fit's covariance); PSM-matched controls; winsorise the level outcome 1/99; exclude COVID quarters (2020Q1–Q2 = q_idx 8081/8082); drop the 177 `ever_dropped` ESG firms; and the full clean-control pool via Callaway-Sant'Anna point estimate (Sun-Abraham is infeasible on ~95k controls). |
| Output | `results/robustness.csv` (16 rows = 8 specs × 2 outcomes) + `results/robustness_notes.txt`. **Committed.** Headline: the ESG-specific **breadth** effect is negative in all 8 specs and significant in all 7 carrying inference (−61 to −137 filers); **depth** negative in all 8, significant in none. The sign never flips. |
| Caveat | Two pre-registered variants are **not estimable** and recorded (not faked): Sun-Abraham on the full pool (dense ~1.4 GB saturated design → CS point estimate instead), and treatment-definition (b) "restrict post window to before first exit" (panel carries `ever_dropped` but no per-firm exit quarter). Winsorising is applied to the *level* outcome the headline uses, a stated deviation from the pre-registration's "change outcomes". |
| License | Derived from the inputs above (US-Government-work + CC-BY-SA + research-use). |

## Filer-type re-ingest — Phase 5 H4 heterogeneity  ✅ built (Phase 5)

| field | value |
|---|---|
| What | Per-(cusip, quarter) ownership broken out by **filer type** — counts of distinct ESG-named / passive managers (breadth) and shares they hold (depth) — so the H2 ESG-vs-S&P placebo contrast can be re-run per type to test whether the flat aggregate hides a composition shift toward ESG/passive buyers. |
| Source | Derived — `src/ingest/edgar_13f_byfiler.py` **re-parses the already-cached raw 13F bundles** (`data/raw/edgar_13f/*.zip`, no network) at the manager (CIK) grain. Filer type comes from the manager name via the pre-committed heuristics in `src/estimate/heterogeneity.py` (`classify_esg_filers`, `classify_passive`). Pure aggregation step unit-tested (`tests/test_h4_filer.py`). |
| Method | For each bundle: take the modal `PERIODOFREPORT`, dedup to the latest filing per CIK, restrict to the 1,507-CUSIP analysis universe (matched + treated names). Breadth counts *distinct* CIKs per type (one row per (cusip, CIK) before the boolean-sum, so amendments / multiple share-class rows don't inflate it); depth sums `SSHPRNAMT` per type. `src/estimate/h4_filer.py` merges these onto the frozen panel on (cusip, q_idx), 0-fills genuine absences, derives `log_shares_*` = log1p(shares), and runs the identical matched Sun-Abraham contrast (`did.esg_specific_contrast`) per outcome. |
| Output | `data/interim/holdings_13f_byfiler.parquet` (38,088 rows, gitignored like all `data/`); `results/h4_filer.csv`, `paper/figures/h4_filer.png`, `paper/tables/h4_filer.md` (**committed**). Reconciles **exactly** against the frozen `holdings_13f` breadth measure: max \|Δ(n_filers_total − n_filers)\| = 0 across all 38,088 (cusip, period) rows. |
| Caveat | **13F is filed at the manager level**, so an ESG sleeve inside BlackRock/Vanguard files under the parent name — `*_esg` columns capture ESG-*branded* firms (boutiques) only, while the mechanical ESG-ETF channel surfaces as **passive depth**. Name heuristics are imperfect (documented regex, not a fund database). Finding: the null survives — ESG-specific contrast < 0 in **0/4** outcomes; the one with passing pre-trends (`log_shares_esg`) is significantly negative. |
| License | Derived from the inputs above (US-Government-work + CC-BY-SA + research-use). |

## Estimation output — Phase 6 credibility of the null  ✅ built (Phase 6)

| field | value |
|---|---|
| What | Three pre-specified stress-tests of the headline null: **(A)** power / minimum-detectable-effect + **equivalence** (does the 95% CI exclude an economically meaningful effect, SESOI = ¼ of the mechanical inclusion benchmark); **(B)** relative-magnitudes / **honest DiD** (Rambachan-Roth 2023) — how large a post-treatment pre-trends violation, in units of the worst pre-period deviation δ, would overturn each estimate (breakdown M\*); **(C)** **placebo-in-time** randomization inference — re-assign treated names fake inclusion quarters and locate the real effect in the placebo distribution. |
| Source | Derived — `src/estimate/credibility.py`. **A and B are pure, deterministic post-processing of the frozen result files** (`h2_esg_specific.csv`, `h3_decay.csv`, `h4_filer.csv`, `event_studies.parquet`, `summary.csv`) — no re-estimation; fully unit-tested (`tests/test_credibility.py`, 6 tests pinned to the headline numbers). **C re-fits** the frozen Sun-Abraham estimator (`did.run_sun_abraham`) on the treated∪matched-control sub-panel, 300 seeded draws per outcome (`seed=12345`, reproducible). |
| Method | A: MDE = (z₀.₉₇₅ + z₀.₈₀)·se = 2.80·se; `rules_out_meaningful` ⇔ the 95% CI lies entirely on the non-premium side of the SESOI. B: conservative additive worst-case robust CI = point ± 1.96·se ± M·δ over an M-grid {0,…,2}; M\* = smallest M admitting 0 (deliberately looser than the exact ARP set — the against-our-own-result choice). C: fake cohorts drawn (with replacement) from the observed treated-cohort distribution; empirical two-sided p = share of placebo \|post-ATT\| ≥ \|real\|. |
| Output | `results/credibility_power.csv` (8 contrasts), `results/credibility_honest_did.csv` (4 targets) + `..._curve.csv` (24 rows = 4×6 M-grid), `results/credibility_placebo.csv` (2 outcomes) + `..._draws.parquet` (600 draws); `paper/figures/credibility.png`, `paper/tables/credibility_*.md`. **Committed.** Finding: the ESG-specific **breadth** null is well-powered (MDE ≈ **104** filers; 95% CI rules out a positive premium), **depth & H3 decay are underpowered** (stated), the significantly-negative breadth point estimate is itself pre-trend-fragile (M\* ≈ 0.26), and the +28-filer breadth level is **not** a timing artifact (placebo p = 0.013). |
| Caveat | The honest-DiD bound is the conservative additive worst-case, weakly looser than the exact Rambachan-Roth ARP confidence set — chosen deliberately against our own result. Placebo-in-time tests **timing**, a question logically distinct from the differential-pre-trend bias (B) that motivates the design's main caveat. No new raw data; deterministic given the frozen results + seed. |
| License | Derived from the inputs above (US-Government-work + CC-BY-SA + research-use). |

---

## SEC EDGAR access note (resolved)

SEC's Akamai bot-manager initially returned **HTTP 403 / "Undeclared Automated
Tool"** to every client from this setup. Root cause was **two stacked filters**,
both now resolved:

1. **Datacenter/VPN egress IP.** The egress IP at first testing
   (`149.34.242.15` — Datacamp/Dublin, flagged `proxy+hosting`) is a datacenter
   exit node, which SEC blocks wholesale. Fix: run from a residential ISP with
   the VPN off (verified once egress became a residential IP).
2. **Non-deliverable User-Agent email.** SEC also 403s a UA whose contact email
   is undeliverable (e.g. a `…@users.noreply.github.com` address). Fix: set
   `SEC_EDGAR_UA="Your Name your-real@email.com"` in a gitignored `.env`.

With both fixed, every SEC host returns 200 and the N-PORT treatment is pulled;
13F (outcome) ingestion runs the same way via `make data-sec`.
`src/ingest/edgar_session.py` still raises a clear `EdgarBlocked` — now with a
live egress-IP diagnosis — if either condition recurs, so a future clone behind a
VPN explains itself rather than looking like a code bug.
