# Data Lineage

Every input: exact source, URL, date pulled, license, status. Raw files live
under `data/raw/` (gitignored — never committed). Reproduce with `make data`
(reachable sources) and `make data-sec` (SEC sources — run from a residential
network with a real-email UA; see the access note).

_Last updated: 2026-06-06 (Phase 1 — 13F outcome panel pulled; data sources complete)._

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
