# PROGRESS

Running log, newest first. One entry per working session.

## 2026-06-05 (cont. 2) — SEC UNBLOCKED end-to-end; N-PORT treatment BUILT

**SEC access fully resolved — two stacked filters, both fixed.**
- Cause 1: datacenter/VPN egress IP (Datacamp/Dublin) — fixed by turning the VPN
  off → residential ISP. Cause 2: the UA contact email was non-deliverable
  (`…@users.noreply.github.com`), which SEC *also* 403s — fixed with a real
  contact in the gitignored `.env`. With both fixed, every SEC host returns 200.
  `edgar_session._DEFAULT_UA` now fails closed (no fake contact) and
  `_egress_diagnosis()` flags a datacenter IP so a future clone behind a VPN
  explains itself.

**N-PORT treatment BUILT — `build_inclusion_events()` (task #6 done).**
- Discovery via browse-EDGAR atom by *series* id (SUSL S000065418, SUSA
  S000004436 in iShares Trust CIK 1100663); holdings from each filing's
  `primary_doc.xml`. N-PORT-P is **quarterly**, not monthly (corrected in code,
  README, DATA_LINEAGE). As-of = `repPdDate` (quarter-end, e.g. 2026-02-28) —
  deliberately NOT `repPdEnd` (the fund's Aug-31 fiscal-year end, a constant that
  would collapse quarters).
- Pulled SUSL+SUSA 2020→2026: **946 raw add/drop events** (494 adds). Persisted
  `data/interim/esg_index_holdings.parquet` (membership panel) +
  `esg_inclusion_events.parquet` (treatment). Reconstitution spikes show up as
  expected (SUSL 2023-08: 62 adds, 2022-08: 55).
- **Data-quality finding (matters for identification):** a pure CUSIP diff turns
  corporate actions into fake inclusions — ~20% of adds have a same-quarter
  name-similar drop. Added a conservative `corp_action_suspect` flag (exact
  normalized-name same-quarter add+drop = split/redomicile churn): **27 flagged
  → 481 genuine inclusions.** Changed-name renames/mergers (AXA Equitable→
  Equitable; BB&T+SunTrust→Truist; Arconic→Howmet) evade exact-name matching and
  are a documented Phase-2 reconciliation step (not silently dropped).
- 6 tests still green (pure cores unchanged).

### Next
1. Task #7 — 13F outcome: run the `edgar_13f` half of `make data-sec` (quarterly
   bundles → `aggregate_ownership`; handle the 2023-01 $thousands→$ unit change).
2. Task #8 / Phase 2 — firm×quarter panel: align N-PORT fiscal-quarter as-of
   dates (Feb/May/Aug/Nov) to 13F calendar quarters (Mar/Jun/Sep/Dec); join
   treatment + outcome + prices + FF + S&P 500 placebo; reconcile changed-name
   corp actions; exclude `corp_action_suspect` events.

## 2026-06-05 (cont.) — Phase 0 finalised + pushed; SEC blocker ROOT-CAUSED

**Phase 0 artifacts finished and shipped.**
- `Makefile` with targets `data` / `data-sec` / `panel` / `estimate` / `placebo`
  / `figures` / `test` / `clean` (Phase 2-5 targets fail loudly until data-sec
  lands — by design). `requirements.lock` pins the 128-package Phase-1 env.
  `.gitignore` now also excludes `data/interim/*` and `.virtual_documents/`.
- Committed `91b6582` and **pushed to origin/main**. 6 tests green.

**SEC blocker ROOT-CAUSED — it's a VPN, not a code or SEC-policy problem.**
- The egress IP `149.34.242.15` geolocates to **Datacamp Limited (AS212238),
  Dublin IE, flagged `proxy:true hosting:true`** — i.e. a datacenter VPN exit
  node. SEC's Akamai bot-manager blocks datacenter/VPN/proxy IPs wholesale,
  which is why *every* client got 403 regardless of User-Agent or TLS.
- Ruled out the alternatives this session: `curl_cffi` Chrome **and** Safari TLS
  impersonation still 403 (not a TLS-fingerprint issue); the declared UA is
  transmitted correctly via httpbin (not a UA-clobbering issue). The two block
  pages seen — "Request Rate Threshold Exceeded" (www) and "Undeclared Automated
  Tool" (data) — are Akamai's canned 403s for a flagged IP.
- **Fix (Jimmy's action):** turn off the VPN so traffic egresses from a
  residential ISP, confirm `https://www.sec.gov/` loads in the browser, then
  `make data-sec`. `edgar_session._egress_diagnosis()` now detects a
  datacenter egress IP and appends a "turn off your VPN" line to `EdgarBlocked`,
  so the failure is self-explanatory on any future clone.

### Next
1. Jimmy: disable VPN → `make data-sec` from residential network. Gates Phase 2-5.
2. Phase 2 — build `data/processed/panel.parquet` once 13F + N-PORT land.
3. Phase 3 — freeze `PREREGISTRATION.md`, install the conda econ stack, estimate.

## 2026-06-05 — Phase 0 complete; Phase 1 partial (reachable done, SEC blocked)

**Phase 0 (repo restructure) — DONE.**
- Reconciled the April scaffold (flat `src/`, an older ESG *rating-change → flows*
  design with an IV / reverse-causality framing) to the refined build plan:
  treatment is now **index inclusion itself**, headline is the **S&P 500 placebo**
  (ESG-specific effect = ESG-inclusion − generic-inclusion), plus **post-2022
  legitimacy decay**, using heterogeneity-robust staggered DiD.
- New structure: `src/{ingest,build,estimate,viz,utils}/`, `tests/`, `paper/`.
  Removed stale stubs (`data_loader.py`, `panel_builder.py`, `causal_models.py`,
  `viz.py`). Estimator scaffolds now encode the new design (event study,
  Callaway-Sant'Anna, Sun-Abraham, placebo, structural break, heterogeneity).
- `requirements.txt` re-aligned to the plan stack (added pyfixest, differences,
  polars; dropped dowhy/causalml/econml). `requirements.lock` snapshots the
  working Phase-1 env.

**Phase 1 (data) — reachable sources DONE, SEC sources WRITTEN but BLOCKED.**
- ✅ Fama-French daily factors — 15,813 rows, 1963→2026 (`src/ingest/ff_factors.py`).
- ✅ S&P 500 placebo events — 754 add/drop events, 1976→2026 (`src/ingest/sp500_events.py`).
- ✅ Prices — yfinance verified on a sample (`src/ingest/prices.py`).
- ✅ Tests — 6 pass: 3 reachable-data smoke + 3 SEC-transform unit tests on
  synthetic data (`aggregate_ownership`, `parse_nport_xml`, `compute_inclusion_events`).
- ⛔ **13F (primary outcome) + N-PORT (treatment) — blocked.** SEC returns 403 to
  every client from this environment's IP (`149.34.242.15`); it is IP-level
  Akamai blocking, not a code bug. Code is written, compliant, and its pure cores
  are unit-tested. See `data/DATA_LINEAGE.md` access note.
- 🔒 Index-event source **LOCKED** to SEC N-PORT-P monthly-holdings diff (Wayback
  had no iShares captures; the live CSV has no history).

**Env caveat:** the venv is an Intel/Anaconda Python 3.12 with bleeding-edge
numpy 2.4 / pandas 3.0. `pyfixest`→numba/llvmlite and source-only builds fail
without cmake; **defer with `conda install -c conda-forge pyfixest polars numba`**
on the analysis machine (Phase 3). Ingestion needs none of these.

### Open items / next
1. **Unblock SEC** (owner: Jimmy). Confirm sec.gov loads in your browser; run
   `make data-sec` from an unblocked network, or decide an alternative. This gates
   Phases 2-5.
2. Phase 2 — build `data/processed/panel.parquet` once 13F + N-PORT land.
3. Phase 3 — freeze `PREREGISTRATION.md`, then estimate (needs the conda econ stack).
