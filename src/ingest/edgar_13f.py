"""Ingest 13F institutional holdings — the project's PRIMARY outcome source.

Outcome = change in aggregate institutional ownership (and the count of 13F
filers holding) around an index-inclusion event. Built from SEC's quarterly
Form 13F *structured data sets* (TSV bundles), which are cleaner than scraping
individual filings.

Pipeline (separable stages so the transforms are testable without SEC):
  1. list_datasets()     — discover the available bundle zips     [needs SEC]
  2. download_dataset()  — fetch + cache one bundle               [needs SEC]
  3. parse_dataset()     — read INFOTABLE.tsv + SUBMISSION.tsv    [pure]
  4. aggregate_ownership() — per-CUSIP rollup of one quarter      [pure, tested]
  build_13f_panel() drives 1–4 across quarters (modal-period filter +
  amendment dedup) into the long CUSIP×quarter outcome panel.

ACCESS: the fetch stages need SEC. SEC blocks datacenter/VPN IPs and
non-deliverable UA emails; from a residential network with SEC_EDGAR_UA set to a
real contact, EDGAR returns 200 (see edgar_session). Stages 3–4 are pure and
unit-tested on synthetic frames in tests/.

NAMING: SEC names the bundles two ways across time — an old calendar-quarter form
(2019q1_form13f.zip, back to 2013Q2) and a newer filing-receipt-window form
(01mar2024-31may2024_form13f.zip). list_datasets() matches both; the report
quarter each bundle covers is taken from the data (modal PERIODOFREPORT), not the
filename.

NOTE ON UNITS: SEC changed INFOTABLE.VALUE from *thousands of dollars* to *whole
dollars* for filings on/after 2023-01. aggregate_ownership() reports raw summed
VALUE; convert to a common unit downstream using the period (Phase 2).

Run:  python -m src.ingest.edgar_13f 2019-01-01
"""

from __future__ import annotations

import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.ingest.edgar_session import edgar_download, edgar_get
from src.utils.paths import DATA_INTERIM, DATA_RAW

# The 13F structured-data sets are listed here and hosted under /files/...; the
# zips are named by the *filing-receipt* window, not a calendar quarter.
_LANDING = "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
_FILES = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/"
# SEC names the zips two ways over time: an old calendar-quarter form
# (2019q1_form13f.zip, back to 2013Q2) and a newer filing-receipt-window form
# (01mar2024-31may2024_form13f.zip). Match both; the report quarter each bundle
# covers is taken from the data (modal PERIODOFREPORT), not the filename.
_RANGE_RE = re.compile(r"(\d{2})([a-z]{3})(\d{4})-(\d{2})([a-z]{3})(\d{4})_form13f\.zip", re.I)
_QQ_RE = re.compile(r"(\d{4})q([1-4])_form13f\.zip", re.I)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_QEND = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
_RAW = DATA_RAW / "edgar_13f"
# Per-bundle aggregate checkpoints. build_13f_panel writes one parquet per bundle
# here as it parses, so a killed run (e.g. the Mac sleeping) loses at most the
# bundle in flight and a rerun resumes from disk instead of re-parsing 30 zips.
_PARTS = DATA_INTERIM / "_13f_parts"

# Only the columns aggregate_ownership needs — INFOTABLE is tens of millions of
# rows per quarter, so dropping the ~11 unused columns cuts parse memory severalfold.
_INFO_COLS = {"ACCESSION_NUMBER", "CUSIP", "VALUE", "SSHPRNAMT"}
_SUB_COLS = {"ACCESSION_NUMBER", "CIK", "FILING_DATE", "PERIODOFREPORT"}


def _date(dd: str, mon: str, yyyy: str) -> pd.Timestamp:
    return pd.Timestamp(int(yyyy), _MONTHS[mon.lower()], int(dd))


def list_datasets() -> pd.DataFrame:
    """Scrape SEC's 13F data-sets page for every available dataset zip.

    Matches both naming conventions (see module NAMING note) and assigns each a
    ``nominal`` quarter-end Timestamp: the calendar quarter-end for the qQ form,
    the filing-receipt window-end for the range form (only a rough sort key — the
    report quarter is confirmed per-bundle from the data's modal PERIODOFREPORT,
    not the filename). Returns columns filename/url/nominal, newest first, one row
    per quarter. Needs SEC access.
    """
    html = edgar_get(_LANDING).text
    rows: dict[str, dict] = {}
    for m in _RANGE_RE.finditer(html):
        fn = m.group(0)
        rows[fn] = {"filename": fn, "url": _FILES + fn,
                    "nominal": _date(*m.group(4, 5, 6))}
    for m in _QQ_RE.finditer(html):
        fn = m.group(0)
        mo, dd = _QEND[int(m.group(2))]
        rows[fn] = {"filename": fn, "url": _FILES + fn,
                    "nominal": pd.Timestamp(int(m.group(1)), mo, dd)}
    df = pd.DataFrame(rows.values()).sort_values("nominal", ascending=False)
    return df.drop_duplicates("nominal").reset_index(drop=True)


def download_dataset(filename: str, url: str, refresh: bool = False):
    """Fetch + cache one 13F dataset zip; return the cached path. Needs SEC.

    Streams to disk (see edgar_download) so an ~90 MB bundle never sits in memory
    and a stalled connection times out and retries rather than hanging. The write
    is atomic, so a cached file is always a *complete* file.
    """
    _RAW.mkdir(parents=True, exist_ok=True)
    cache = _RAW / filename
    if cache.exists() and not refresh:
        return cache
    edgar_download(url, cache)
    return cache


def parse_dataset(zip_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the needed INFOTABLE + SUBMISSION columns from a 13F dataset zip.

    Reads only the columns aggregate_ownership uses (see _INFO_COLS / _SUB_COLS)
    and upper-cases the headers, which guards against the dataset's occasional
    casing changes across quarters. Members are matched by *basename*: most
    bundles store the TSVs at the zip root, but some (e.g. 01jun2025-31aug2025)
    nest them under a top-level folder.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = {n.rsplit("/", 1)[-1].upper(): n for n in zf.namelist()}
        with zf.open(names["INFOTABLE.TSV"]) as f:
            info = pd.read_csv(f, sep="\t", dtype=str,
                               usecols=lambda c: c.upper() in _INFO_COLS).rename(columns=str.upper)
        with zf.open(names["SUBMISSION.TSV"]) as f:
            sub = pd.read_csv(f, sep="\t", dtype=str,
                              usecols=lambda c: c.upper() in _SUB_COLS).rename(columns=str.upper)
    return info, sub


def aggregate_ownership(infotable: pd.DataFrame, submission: pd.DataFrame) -> pd.DataFrame:
    """Roll holdings up to one row per security (CUSIP).

    Returns columns: cusip, total_value, total_shares, n_filers, filing_date.
    `n_filers` counts distinct filer CIKs holding the CUSIP — the key flow
    proxy (breadth of institutional ownership). Pure function: unit-tested.
    """
    info = infotable.copy()
    info["VALUE"] = pd.to_numeric(info["VALUE"], errors="coerce")
    info["SSHPRNAMT"] = pd.to_numeric(info["SSHPRNAMT"], errors="coerce")

    sub = submission[["ACCESSION_NUMBER", "CIK"]].drop_duplicates()
    merged = info.merge(sub, on="ACCESSION_NUMBER", how="left")

    g = merged.groupby("CUSIP")
    out = pd.DataFrame({
        "total_value": g["VALUE"].sum(),
        "total_shares": g["SSHPRNAMT"].sum(),
        "n_filers": g["CIK"].nunique(),
    }).reset_index().rename(columns={"CUSIP": "cusip"})

    fdate = pd.to_datetime(submission.get("FILING_DATE"), errors="coerce")
    out["filing_date"] = fdate.max() if fdate.notna().any() else pd.NaT
    return out


def _aggregate_bundle(zip_path) -> pd.DataFrame | None:
    """One bundle zip -> a single-quarter ownership rollup (or None if unparseable).

    Computes the modal PERIODOFREPORT — the quarter the bundle predominantly
    reports (receipt-window bundles mix in a few straggler/amendment filings for
    adjacent quarters) — keeps only that period's filings, dedups to the latest
    filing per CIK (an amendment supersedes its original, so n_filers counts
    distinct institutions not filings), and rolls up per CUSIP. Pure given the
    file: no network.
    """
    info, sub = parse_dataset(zip_path)
    per = pd.to_datetime(sub["PERIODOFREPORT"].str.title(),
                         format="%d-%b-%Y", errors="coerce")
    if per.dropna().empty:
        return None
    period = per.mode().iloc[0]
    keep = sub[per == period].copy()
    keep["_fdate"] = pd.to_datetime(keep["FILING_DATE"].str.title(),
                                    format="%d-%b-%Y", errors="coerce")
    keep = keep.sort_values("_fdate").drop_duplicates("CIK", keep="last")
    info_q = info[info["ACCESSION_NUMBER"].isin(set(keep["ACCESSION_NUMBER"]))]
    agg = aggregate_ownership(info_q, keep.drop(columns="_fdate"))
    agg["period"] = period.normalize()
    return agg


def build_13f_panel(since: str = "2019-01-01", refresh: bool = False,
                    workers: int = 5) -> pd.DataFrame:
    """Build the institutional-ownership outcome panel (long CUSIP×quarter).

    Three resumable stages over every bundle with a nominal quarter-end on/after
    ``since`` (minus a lookback, so a quarter split across receipt windows isn't
    missed):
      1. download all bundles in parallel (``workers`` threads) — cached + atomic,
         so reruns skip what's on disk;
      2. parse + aggregate each via _aggregate_bundle, checkpointing one parquet
         per bundle under _PARTS — a killed run resumes here instead of re-parsing;
      3. concat the checkpoints, trim to periods on/after ``since``, and persist
         data/interim/holdings_13f.parquet.
    Returns the panel. Needs SEC access for stage 1; run it under ``caffeinate``
    so the machine can't sleep mid-pull.
    """
    since_ts = pd.Timestamp(since)
    cat = list_datasets()
    cat = cat[cat["nominal"] >= since_ts - pd.Timedelta(days=100)].reset_index(drop=True)
    _RAW.mkdir(parents=True, exist_ok=True)
    _PARTS.mkdir(parents=True, exist_ok=True)

    # 1) download (parallel, resumable) ------------------------------------
    to_get = [(r.filename, r.url) for r in cat.itertuples(index=False)
              if refresh or not (_RAW / r.filename).exists()]
    print(f"[13f] {len(cat)} bundles since {since_ts.date()}; "
          f"{len(to_get)} to download with {workers} workers", flush=True)
    if to_get:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for _ in ex.map(lambda fu: download_dataset(*fu, refresh=refresh), to_get):
                pass
    print("[13f] downloads complete; parsing", flush=True)

    # 2) parse + aggregate (checkpoint per bundle) -------------------------
    for row in cat.itertuples(index=False):
        part = _PARTS / f"{row.filename}.parquet"
        if part.exists() and not refresh:
            continue
        agg = _aggregate_bundle(_RAW / row.filename)
        if agg is None or agg.empty:
            print(f"[13f] {row.filename}: no parseable period, skipped", flush=True)
            continue
        agg.to_parquet(part, index=False)
        print(f"[13f] {row.filename} -> {agg['period'].iloc[0].date()} "
              f"({len(agg)} cusips, max {int(agg['n_filers'].max())} filers)", flush=True)

    # 3) concat checkpoints -> panel ---------------------------------------
    parts = [pd.read_parquet(_PARTS / f"{r.filename}.parquet")
             for r in cat.itertuples(index=False)
             if (_PARTS / f"{r.filename}.parquet").exists()]
    panel = pd.concat(parts, ignore_index=True)
    panel = (panel[panel["period"] >= since_ts]
             .sort_values(["period", "cusip"]).reset_index(drop=True))
    out = DATA_INTERIM / "holdings_13f.parquet"
    try:
        panel.to_parquet(out, index=False)
    except Exception:
        panel.to_pickle(out.with_suffix(".pkl"))
    return panel


def main() -> None:
    since = sys.argv[1] if len(sys.argv) > 1 else "2019-01-01"
    panel = build_13f_panel(since=since)
    print(f"13F panel: {len(panel)} CUSIP×quarter rows across "
          f"{panel['period'].nunique()} quarters "
          f"({panel['period'].min().date()}…{panel['period'].max().date()}); "
          f"max {panel['n_filers'].max()} filers on one name")


if __name__ == "__main__":
    main()
