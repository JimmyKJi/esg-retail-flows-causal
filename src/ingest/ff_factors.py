"""Ingest Fama–French factors from the Kenneth French Data Library.

Source (free, no key): https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/
Confirmed reachable from this environment (unlike SEC EDGAR).

Pulls the daily 5-factor file and the daily momentum file, parses the
quirky French CSV layout (preamble text, then a header row, then dated
rows, then a trailing annual section), and merges them into one tidy
frame indexed by date with factor returns in **decimal** units
(the source publishes percent; we divide by 100).

Run:  python -m src.ingest.ff_factors
"""

from __future__ import annotations

import io
import re
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from src.utils.paths import DATA_INTERIM, DATA_RAW

BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FF5_ZIP = "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
MOM_ZIP = "F-F_Momentum_Factor_daily_CSV.zip"

# Polite identification; Dartmouth does not require it but it is good manners.
_UA = "esg-flows-causal academic research (github.com/JimmyKJi)"

_RAW_DIR = DATA_RAW / "fama_french"
_DATE_ROW = re.compile(r"^\s*(\d{8})\s*,")


def _download(zip_name: str, refresh: bool = False) -> bytes:
    """Fetch a French-library zip, caching the raw bytes under data/raw."""
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = _RAW_DIR / zip_name
    if cache.exists() and not refresh:
        return cache.read_bytes()
    req = urllib.request.Request(BASE + zip_name, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    cache.write_bytes(data)
    return data


def _parse_french_csv(raw_zip: bytes) -> pd.DataFrame:
    """Parse the daily section of a French CSV zip into a date-indexed frame.

    French files carry a free-text preamble, then a header row beginning
    with a comma, then `YYYYMMDD, v, v, ...` rows. A second (annual or
    copyright) section often follows; we stop at the first non-dated line
    after the data block begins.
    """
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        text = zf.read(csv_name).decode("latin-1")

    lines = text.splitlines()
    header_idx = next(
        i for i, ln in enumerate(lines)
        if ln.lstrip().startswith(",") and any(c.isalpha() for c in ln)
    )
    columns = [c.strip() for c in lines[header_idx].split(",")][1:]

    rows: list[list] = []
    started = False
    for ln in lines[header_idx + 1:]:
        if _DATE_ROW.match(ln):
            started = True
            parts = [p.strip() for p in ln.split(",")]
            rows.append([parts[0]] + [float(p) for p in parts[1: len(columns) + 1]])
        elif started:
            break  # reached the trailing annual / copyright block

    df = pd.DataFrame(rows, columns=["date"] + columns)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    factor_cols = [c for c in df.columns if c != "date"]
    df[factor_cols] = df[factor_cols] / 100.0  # percent -> decimal
    return df.set_index("date").sort_index()


def load_ff_factors(refresh: bool = False) -> pd.DataFrame:
    """Return daily FF5 + momentum + risk-free, indexed by date.

    Columns: mkt_rf, smb, hml, rmw, cma, rf, mom  (decimal daily returns)
    Cached to data/interim/ff_factors_daily.parquet.
    """
    cache = DATA_INTERIM / "ff_factors_daily.parquet"
    if cache.exists() and not refresh:
        return pd.read_parquet(cache)

    ff5 = _parse_french_csv(_download(FF5_ZIP, refresh)).rename(
        columns={
            "Mkt-RF": "mkt_rf", "SMB": "smb", "HML": "hml",
            "RMW": "rmw", "CMA": "cma", "RF": "rf",
        }
    )
    mom = _parse_french_csv(_download(MOM_ZIP, refresh))
    mom = mom.rename(columns={mom.columns[0]: "mom"})

    out = ff5.join(mom[["mom"]], how="left")
    try:
        out.to_parquet(cache)
    except Exception:
        out.to_pickle(cache.with_suffix(".pkl"))  # pyarrow not yet installed
    return out


def main() -> None:
    df = load_ff_factors(refresh=True)
    print(f"Fama-French daily factors: {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"date coverage: {df.index.min().date()} -> {df.index.max().date()}")
    print(f"columns: {list(df.columns)}")
    print(df.tail(3).round(4).to_string())


if __name__ == "__main__":
    main()
