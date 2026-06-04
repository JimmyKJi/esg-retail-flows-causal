# Data Lineage

Every input: exact source, URL, date pulled, license, status. Raw files live
under `data/raw/` (gitignored — never committed). Reproduce with `make data`
(reachable sources) and `make data-sec` (SEC sources, requires an unblocked
network — see the access note).

_Last updated: 2026-06-05 (Phase 1)._

## Treatment — ESG-index inclusion events  **(LOCKED: SEC Form N-PORT-P)**

| field | value |
|---|---|
| What | Firm enters the MSCI USA (Extended) ESG Leaders index. Proxied by the holdings of iShares **SUSL** (ESG MSCI USA Leaders) and **SUSA** (MSCI USA ESG Select), which track the index. An add into the ETF ≈ an inclusion event. |
| Source | SEC EDGAR, Form **N-PORT-P** (monthly fund portfolio holdings, structured XML) |
| URL | `https://efts.sec.gov/LATEST/search-index` (locate filings) → `https://www.sec.gov/Archives/edgar/data/...` (XML) |
| Method | Diff consecutive monthly snapshots; CUSIP present at month *t* but not *t−1* = inclusion. Code: `src/ingest/nport_holdings.py`. |
| License | US Government work — public domain |
| Date pulled | **Not yet pulled** — blocked from this environment (see access note) |

**Why N-PORT, not the build plan's first suggestions?** The plan offered (1) an
iShares-holdings-CSV-via-Wayback proxy and (2) MSCI press releases. During Phase 1
discovery the Wayback Machine returned **no usable captures** of the iShares
holdings endpoint, and the live iShares CSV is a single current snapshot with no
history. N-PORT-P gives free, structured *monthly* holdings back to ~2019 and is
the robust source. This is the locked Phase 1 decision.

## Primary outcome — institutional flows (13F)

| field | value |
|---|---|
| What | Δ aggregate institutional ownership and Δ count of 13F filers holding a security, around inclusion |
| Source | SEC EDGAR **Form 13F structured data sets** (quarterly TSV bundles) |
| URL | `https://www.sec.gov/files/structureddata/data/form-13f-data-sets/{YYYY}q{Q}_form13f.zip` (fallback stem `.../dera/data/...`) |
| Method | Parse `INFOTABLE.tsv` + `SUBMISSION.tsv`; aggregate per CUSIP×quarter. Code: `src/ingest/edgar_13f.py`. **Unit-tested** (`tests/test_edgar_transforms.py`). |
| Caveat | SEC changed `VALUE` from $thousands to whole $ on/after 2023-01 — normalise by `FILING_DATE`. 13F is quarterly → event time is in **quarters**. |
| License | US Government work — public domain |
| Date pulled | **Not yet pulled** — blocked (see access note) |

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

## ⚠️ SEC EDGAR access note (Phase 1 blocker)

From the build environment, **every** SEC host (`www.sec.gov`, `data.sec.gov`,
`efts.sec.gov`) returns **HTTP 403 / "Undeclared Automated Tool"** for **every**
client tried (curl, Python urllib, Python requests, WebFetch) — even the bare
homepage — while non-SEC sources (Dartmouth, Wikipedia, Yahoo, GitHub) work.
Egress IP at time of testing: `149.34.242.15`. This is **IP-level blocking by
SEC's Akamai bot-manager**, not a code or User-Agent bug.

Consequence: the two SEC-hosted inputs (13F outcome, N-PORT treatment) cannot be
pulled here. Their ingestion code is written, compliant, and (for the
parse/aggregate/diff cores) unit-tested; it must be **run from an unblocked
network** — a normal residential connection with no datacenter VPN. Set your
contact UA via `.env` (`SEC_EDGAR_UA=Your Name you@email.com`) and run
`make data-sec`. `src/ingest/edgar_session.py` raises a clear `EdgarBlocked`
with guidance if the block persists.
