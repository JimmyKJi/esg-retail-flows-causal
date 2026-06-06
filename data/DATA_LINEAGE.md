# Data Lineage

Every input: exact source, URL, date pulled, license, status. Raw files live
under `data/raw/` (gitignored — never committed). Reproduce with `make data`
(reachable sources) and `make data-sec` (SEC sources — run from a residential
network with a real-email UA; see the access note).

_Last updated: 2026-06-06 (Phase 2b — S&P 500 placebo arm, matched controls, and the FF-adjusted CAR secondary outcome added on top of the Phase 2 panel)._

## Treatment — ESG-index inclusion events  **(LOCKED: SEC Form N-PORT-P)**

| field | value |
|---|---|
| What | Firm enters the MSCI USA (Extended) ESG Leaders index. Proxied by the holdings of iShares **SUSL** (ESG MSCI USA Leaders) and **SUSA** (MSCI USA ESG Select), which track the index. An add into the ETF ≈ an inclusion event. |
| Source | SEC EDGAR, Form **N-PORT-P** (public fund portfolio holdings, structured XML — filed **quarterly**, as-of the fiscal-quarter-end `repPdDate`) |
| URL | browse-EDGAR atom by fund *series* id (`?action=getcompany&CIK=S000065418&type=NPORT-P&output=atom`) → `https://www.sec.gov/Archives/edgar/data/1100663/<accession>/primary_doc.xml` |
| Method | Diff consecutive quarterly snapshots; CUSIP present at quarter *t* but not *t−1* = inclusion. Same-quarter exact-name add+drop pairs (split/redomicile CUSIP churn) flagged `corp_action_suspect`. Code: `src/ingest/nport_holdings.py`. |
| License | US Government work — public domain |
| Date pulled | 2026-06-05 — SUSL+SUSA quarterly N-PORT (2020→2026): 946 raw events (494 adds); 27 flagged as identifier churn → **481 genuine inclusions**. CUSIP is the join key (tickers absent in N-PORT). |
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
| Source | Derived — pools the `NAMEOFISSUER`+`CUSIP` columns from **every cached 13F INFOTABLE** (equity rows only, PUTCALL blank), taking each CUSIP's modal name by filer-row support. Code: `src/build/crosswalk.py`, unit-tested via the placebo path. |
| Output | `data/interim/cusip_names.parquet` (gitignored) — **79,944 equity CUSIPs**. |
| Caveat | Name matching is imperfect: exact-normalised first, then a **prominence-tie-break token-subset** fallback (highest-13F-support superset wins). On S&P 500 adds since 2019 this gives **92% coverage (124/135: 105 exact + 19 subset + 11 miss)**; misses are recent spin-offs/IPOs/renames. Coverage is reported by `match` ∈ {exact, subset, miss}, not assumed. |

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
| Output | `data/processed/matched_{esg,sp500}_{psm,cem}.parquet` (gitignored). ESG **332/332**, S&P **101/101** matched, 0 unmatched. Balance: the naive pool sits **>2 SDs** from treated on size (|SMD| ≈ 2.1–2.5); matching collapses this to **\|SMD\| < 0.05 (CEM) / < 0.15 (PSM)**. |
| Caveat | Sector (GICS, free only for current S&P members) and a price-based liquidity measure are **not** in the CUSIP panel — accepted as optional covariates when joined in, not silently omitted. |

## Processed output — FF-adjusted CAR (secondary outcome)  ✅ built (Phase 2b)

| field | value |
|---|---|
| What | The *price* reaction to inclusion: a Fama-French five-factor event-study cumulative abnormal return, triangulating the primary 13F-flow outcome. |
| Source | Derived — `src/build/car.py` (market model on excess returns over a ≈1yr pre-event estimation window; abnormal = actual−predicted; CAR = sum over the event window). Prices from `yfinance`, factors from the FF table. Unit-tested (`tests/test_car.py`). |
| Output | `data/processed/car_sp500.parquet` (gitignored). Recovers the **modern S&P 500 index effect**: CAR[−5,+5] = **+1.35% (t=1.55, n=99, 54% positive)**; tight windows ≈0. Coverage: 99 ok, 20 insufficient pre-history (recent IPOs), 3 delisted (CTLT/FRC/CDAY). |
| Caveat | **Runs on the S&P placebo arm, not the ESG arm — by data necessity, stated plainly.** A daily event study needs a priceable ticker *and* a precise date; S&P adds have both (Wikipedia effective dates + tickers), but the ESG inclusions have **neither at resolution**: there is no free CUSIP→ticker bridge for ESG-only firms, and N-PORT dates inclusion only at the fund's *fiscal quarter-end* (quarterly, not daily). So the generic-inclusion CAR is the deliverable; the ESG question stays on the fully-covered quarterly flow design. |
| License | Derived from Yahoo (research use) + FF (academic) inputs. |

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
