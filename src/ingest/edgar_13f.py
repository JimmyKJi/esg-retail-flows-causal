"""Ingest 13F institutional holdings — the project's PRIMARY outcome source.

Outcome = change in aggregate institutional ownership (and the count of 13F
filers holding) around an index-inclusion event. Built from SEC's quarterly
Form 13F *structured data sets* (TSV bundles), which are cleaner than scraping
individual filings.

Pipeline (three separable stages so the logic is testable without SEC):
  1. download_quarter()  — fetch + cache the quarter's zip   [needs SEC access]
  2. parse_dataset()     — read INFOTABLE.tsv + SUBMISSION.tsv  [pure]
  3. aggregate_ownership() — per CUSIP×quarter rollup           [pure, tested]

NOTE ON ACCESS: SEC blocks this environment's egress IP (see edgar_session).
download_quarter() will raise EdgarBlocked here; run it from an unblocked
network. Stages 2–3 are unit-tested on synthetic frames in tests/.

NOTE ON UNITS: SEC changed INFOTABLE.VALUE from *thousands of dollars* to
*whole dollars* for filings on/after 2023-01. aggregate_ownership() therefore
reports raw summed VALUE; convert to a common unit downstream using FILING_DATE.

Run:  python -m src.ingest.edgar_13f 2024 1
"""

from __future__ import annotations

import sys
import zipfile

import pandas as pd

from src.ingest.edgar_session import edgar_get
from src.utils.paths import DATA_INTERIM, DATA_RAW

# SEC has hosted the 13F data sets under two stems over time; try both.
_DATASET_BASES = (
    "https://www.sec.gov/files/structureddata/data/form-13f-data-sets/",
    "https://www.sec.gov/files/dera/data/form-13f-data-sets/",
)
_RAW = DATA_RAW / "edgar_13f"


def download_quarter(year: int, quarter: int, refresh: bool = False):
    """Fetch the quarterly 13F structured-data zip; return the cached path.

    Raises EdgarBlocked if SEC refuses (as it does from this environment).
    """
    _RAW.mkdir(parents=True, exist_ok=True)
    fname = f"{year}q{quarter}_form13f.zip"
    cache = _RAW / fname
    if cache.exists() and not refresh:
        return cache
    last = None
    for base in _DATASET_BASES:
        try:
            resp = edgar_get(base + fname)
            cache.write_bytes(resp.content)
            return cache
        except Exception as exc:  # try the next base, remember the error
            last = exc
    raise last


def parse_dataset(zip_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read INFOTABLE and SUBMISSION tables from a 13F dataset zip."""
    with zipfile.ZipFile(zip_path) as zf:
        names = {n.upper(): n for n in zf.namelist()}
        with zf.open(names["INFOTABLE.TSV"]) as f:
            info = pd.read_csv(f, sep="\t", dtype=str)
        with zf.open(names["SUBMISSION.TSV"]) as f:
            sub = pd.read_csv(f, sep="\t", dtype=str)
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


def build_13f_panel(quarters: list[tuple[int, int]], refresh: bool = False) -> pd.DataFrame:
    """Aggregate institutional ownership across quarters -> long CUSIP×quarter."""
    frames = []
    for year, q in quarters:
        info, sub = parse_dataset(download_quarter(year, q, refresh))
        agg = aggregate_ownership(info, sub)
        agg["quarter"] = f"{year}Q{q}"
        frames.append(agg)
    panel = pd.concat(frames, ignore_index=True)
    out = DATA_INTERIM / "holdings_13f.parquet"
    try:
        panel.to_parquet(out)
    except Exception:
        panel.to_pickle(out.with_suffix(".pkl"))
    return panel


def main() -> None:
    year, q = int(sys.argv[1]), int(sys.argv[2])
    panel = build_13f_panel([(year, q)])
    print(f"13F {year}Q{q}: {len(panel)} securities, "
          f"{panel['n_filers'].max()} max filers on one name")


if __name__ == "__main__":
    main()
