"""Ingest the S&P 500 placebo sample from Wikipedia.

The placebo is the project's identification centrepiece: re-running the
estimator on *generic* (non-ESG) index inclusions isolates the ESG-specific
flow response (ESG effect = ESG-inclusion effect − generic-inclusion effect).
S&P 500 additions are the canonical generic index-inclusion event.

Wikipedia's "List of S&P 500 companies" carries two useful tables, both free
and reachable from this environment (unlike SEC):
  * current constituents — Symbol, Security, GICS Sector, CIK, Date added;
  * "Selected changes" — dated Added/Removed tickers with a reason.

Limitation (documented in DATA_LINEAGE.md): the changes table is a curated
subset, reliable from ~2000 onward; for a fuller event list one would diff the
page's revision history. Good enough for a matched placebo sample.

Run:  python -m src.ingest.sp500_events
"""

from __future__ import annotations

import io

import pandas as pd
import requests

from src.utils.paths import DATA_INTERIM, DATA_RAW

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_UA = "esg-flows-causal academic research (github.com/JimmyKJi)"
_OUT = DATA_RAW / "sp500"


def _fetch_tables() -> list[pd.DataFrame]:
    resp = requests.get(WIKI_URL, headers={"User-Agent": _UA}, timeout=60)
    resp.raise_for_status()
    return pd.read_html(io.StringIO(resp.text))


def _find(tables: list[pd.DataFrame], *needles: str) -> pd.DataFrame:
    """Return the first table whose flattened column names contain all needles."""
    for t in tables:
        flat = " ".join(str(c).lower() for c in t.columns)
        if all(n.lower() in flat for n in needles):
            return t
    raise ValueError(f"no table matching {needles!r} on the page")


def load_sp500_changes(refresh: bool = False) -> pd.DataFrame:
    """Return dated S&P 500 add/drop events in long form.

    Columns: date, ticker, action ('added'|'removed'), security, reason.
    Caches the raw constituents + changes tables under data/raw/sp500/.
    """
    _OUT.mkdir(parents=True, exist_ok=True)
    changes_csv = _OUT / "sp500_changes.csv"
    if changes_csv.exists() and not refresh:
        return pd.read_csv(changes_csv, parse_dates=["date"])

    tables = _fetch_tables()

    constituents = _find(tables, "symbol", "cik")
    constituents.to_csv(_OUT / "sp500_constituents.csv", index=False)

    raw = _find(tables, "added", "removed").copy()
    raw.columns = ["_".join(str(x) for x in c).strip() if isinstance(c, tuple) else str(c)
                   for c in raw.columns]

    def col(*cands: str) -> str | None:
        for cand in cands:
            for c in raw.columns:
                if cand.lower() in c.lower():
                    return c
        return None

    date_c = col("date")
    add_t = col("added_ticker", "added_symbol")
    rem_t = col("removed_ticker", "removed_symbol")
    add_s = col("added_security", "added_company")
    rem_s = col("removed_security", "removed_company")
    reason_c = col("reason")

    raw["_date"] = pd.to_datetime(raw[date_c], errors="coerce")
    events = []
    for _, r in raw.iterrows():
        if pd.isna(r["_date"]):
            continue
        if add_t and pd.notna(r.get(add_t)) and str(r[add_t]).strip():
            events.append((r["_date"], str(r[add_t]).strip(), "added",
                           str(r.get(add_s, "")).strip(), str(r.get(reason_c, "")).strip()))
        if rem_t and pd.notna(r.get(rem_t)) and str(r[rem_t]).strip():
            events.append((r["_date"], str(r[rem_t]).strip(), "removed",
                           str(r.get(rem_s, "")).strip(), str(r.get(reason_c, "")).strip()))

    out = pd.DataFrame(events, columns=["date", "ticker", "action", "security", "reason"])
    out = out.sort_values("date").reset_index(drop=True)
    out.to_csv(changes_csv, index=False)
    return out


def load_constituents(refresh: bool = False) -> pd.DataFrame:
    """Current S&P 500 constituents (Symbol, Security, GICS Sector, CIK, …).

    GICS Sector here is the only free sector classification in the project, used
    as a matching covariate. Cached under data/raw/sp500/.
    """
    path = _OUT / "sp500_constituents.csv"
    if not path.exists() or refresh:
        load_sp500_changes(refresh=True)  # writes the constituents CSV as a side effect
    return pd.read_csv(path)


def build_sp500_events(refresh: bool = False) -> pd.DataFrame:
    """Persist the placebo treatment to interim, with GICS sector attached.

    Joins each change event to the current-constituents GICS Sector by ticker
    (a slowly-varying firm attribute; NaN for firms that have since left, which
    is acceptable for a covariate). Writes data/interim/sp500_events.parquet.
    """
    changes = load_sp500_changes(refresh=refresh)
    con = load_constituents(refresh=refresh)
    sym_c = next(c for c in con.columns if "symbol" in c.lower())
    gics_c = next((c for c in con.columns if "gics sector" in c.lower()), None)
    if gics_c is not None:
        sector = con.set_index(sym_c)[gics_c]
        changes = changes.assign(gics_sector=changes["ticker"].map(sector))
    out = DATA_INTERIM / "sp500_events.parquet"
    changes.to_parquet(out, index=False)
    return changes


def main() -> None:
    df = build_sp500_events(refresh=True)
    adds = (df["action"] == "added").sum()
    drops = (df["action"] == "removed").sum()
    print(f"S&P 500 change events: {len(df)} ({adds} adds, {drops} drops)")
    print(f"date coverage: {df['date'].min().date()} -> {df['date'].max().date()}")
    if "gics_sector" in df:
        n_sec = df["gics_sector"].notna().sum()
        print(f"GICS sector attached: {n_sec}/{len(df)} events")
    print(f"persisted -> {DATA_INTERIM / 'sp500_events.parquet'}")


if __name__ == "__main__":
    main()
