"""S&P 500 placebo arm — generic (non-ESG) index inclusions (Phase 2b).

The identification centrepiece: re-running the estimator on *generic* index
inclusions nets the mechanical index-inclusion effect out of the ESG estimate
(ESG-specific effect = ESG-inclusion ATT − S&P-500-inclusion ATT). S&P 500
additions are the canonical generic event.

The S&P 500 events are ticker/name-keyed (Wikipedia); the outcome panel is
CUSIP-keyed (13F). This module bridges them via the 13F name crosswalk
(src/build/crosswalk.py) and exposes:

  * build_sp500_cusip_events()  — S&P 500 *additions* mapped to CUSIP (treatment);
  * sp500_member_cusips()       — every CUSIP ever in the S&P 500 (constituents +
    all dated adds/drops), so those firms can be excluded from the *placebo's*
    never-treated control pool, exactly as left-censored ESG members are.

Coverage is reported by `match` (exact | subset | miss), not assumed — name
matching is imperfect, so the miss rate is a documented data-quality figure.
"""

from __future__ import annotations

import pandas as pd

from src.build.crosswalk import build_cusip_crosswalk, match_names_to_cusip
from src.ingest.sp500_events import build_sp500_events, load_constituents
from src.utils.paths import DATA_INTERIM


def _events() -> pd.DataFrame:
    path = DATA_INTERIM / "sp500_events.parquet"
    return pd.read_parquet(path) if path.exists() else build_sp500_events()


def build_sp500_cusip_events(since: str = "2019-01-01") -> pd.DataFrame:
    """S&P 500 additions on/after ``since``, mapped to CUSIP via the crosswalk.

    Returns: cusip, event_date, ticker, security, gics_sector, match. Rows whose
    name could not be resolved to a CUSIP are dropped (and counted by the caller).
    """
    adds = _events().query("action == 'added'").copy()
    adds["event_date"] = pd.to_datetime(adds["date"])
    adds = adds[adds["event_date"] >= pd.Timestamp(since)]

    xwalk = build_cusip_crosswalk()
    m = match_names_to_cusip(adds["security"].fillna(""), xwalk)
    adds["cusip"] = m["cusip"].to_numpy()
    adds["match"] = m["match"].to_numpy()

    keep = [c for c in ["cusip", "event_date", "ticker", "security", "gics_sector", "match"]
            if c in adds.columns]
    return adds.dropna(subset=["cusip"])[keep].reset_index(drop=True)


def sp500_member_cusips() -> set[str]:
    """Every CUSIP that was ever in the S&P 500 (constituents ∪ all change events).

    Used to keep ever-members out of the placebo's never-treated control pool —
    the S&P analogue of excluding left-censored ESG members.
    """
    xwalk = build_cusip_crosswalk()
    pool: set[str] = set()

    ev = _events()
    sec = ev["security"].dropna()
    if not sec.empty:
        pool |= set(match_names_to_cusip(sec, xwalk)["cusip"].dropna())

    con = load_constituents()
    sec_c = next((c for c in con.columns if "security" in c.lower()), None)
    if sec_c is not None:
        pool |= set(match_names_to_cusip(con[sec_c].dropna(), xwalk)["cusip"].dropna())
    return pool
