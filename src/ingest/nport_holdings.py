"""Reconstruct ESG-index inclusion/exclusion events — the TREATMENT.

The treatment is a firm entering the MSCI USA (Extended) ESG Leaders index.
MSCI's official constituent history is paywalled, so we proxy it with the
holdings of an ETF that tracks the index — iShares **SUSL** (ESG MSCI USA
Leaders) and **SUSA** (MSCI USA ESG Select) — and detect adds/drops by diffing
consecutive *monthly* holdings.

Why N-PORT rather than the iShares website CSV or the Wayback Machine
(the build plan's first suggestions)?
  * Wayback has no usable capture history for the iShares holdings endpoint
    (verified empty during Phase 1 discovery), and the live CSV is a single
    current snapshot — no history.
  * SEC Form **N-PORT-P** gives every registered fund's *monthly* portfolio
    holdings as structured XML, free, back to ~2019. Diffing month t vs t-1
    yields dated add/drop events directly. This is the robust source.

Pipeline (separable + testable):
  1. find_nport_filings()  — locate the ETF's N-PORT-P accessions  [needs SEC]
  2. parse_nport_xml()     — holdings out of one filing's XML       [pure, tested]
  3. compute_inclusion_events() — diff the monthly series -> events [pure, tested]

ACCESS: SEC blocks this environment (see edgar_session); stage 1 raises
EdgarBlocked here. Run from an unblocked network. Stages 2–3 are unit-tested.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

import pandas as pd

from src.ingest.edgar_session import edgar_get
from src.utils.paths import DATA_INTERIM

# iShares ETFs tracking the ESG Leaders / Select indices (treatment proxies).
ETF_TICKERS = ("SUSL", "SUSA")
_EFTS = "https://efts.sec.gov/LATEST/search-index"


def find_nport_filings(ticker: str) -> pd.DataFrame:
    """Locate an ETF's N-PORT-P filings via EDGAR full-text search.

    Returns columns: accession, filing_date, cik. Needs SEC access.
    """
    resp = edgar_get(_EFTS, params={"q": f'"{ticker}"', "forms": "NPORT-P"})
    hits = resp.json().get("hits", {}).get("hits", [])
    rows = []
    for h in hits:
        src = h.get("_source", {})
        rows.append({
            "accession": h.get("_id", "").split(":")[0],
            "filing_date": src.get("file_date"),
            "cik": (src.get("ciks") or [None])[0],
        })
    return pd.DataFrame(rows)


def parse_nport_xml(xml_bytes: bytes) -> pd.DataFrame:
    """Extract holdings from one N-PORT filing's XML.

    Returns columns: cusip, ticker, name, pct_value, value_usd. Namespace-
    agnostic (matches on local tag names) so it survives N-PORT schema bumps.
    Pure function: unit-tested on a synthetic filing.
    """
    root = ET.fromstring(xml_bytes)

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    rows = []
    for sec in root.iter():
        if local(sec.tag) != "invstOrSec":
            continue
        rec = {"cusip": None, "ticker": None, "name": None,
               "pct_value": None, "value_usd": None}
        for child in sec.iter():
            t = local(child.tag)
            txt = (child.text or "").strip()
            if t == "name" and rec["name"] is None:
                rec["name"] = txt
            elif t == "cusip" and txt:
                rec["cusip"] = txt
            elif t == "ticker":
                val = txt or child.attrib.get("value", "").strip()
                if val:
                    rec["ticker"] = val
            elif t == "pctVal" and txt:
                rec["pct_value"] = _num(txt)
            elif t == "valUSD" and txt:
                rec["value_usd"] = _num(txt)
        if rec["cusip"] or rec["ticker"]:
            rows.append(rec)
    return pd.DataFrame(rows, columns=["cusip", "ticker", "name", "pct_value", "value_usd"])


def compute_inclusion_events(monthly: dict) -> pd.DataFrame:
    """Diff a dated series of holdings snapshots into add/drop events.

    `monthly` maps an as-of date (str/Timestamp) -> holdings DataFrame
    (must have a 'cusip' column). A CUSIP present at month t but absent at the
    prior snapshot is an 'added' (inclusion) event dated t; the reverse is a
    'removed' event. The earliest snapshot seeds membership (no events).

    Returns: event_date, cusip, ticker, name, action. Pure: unit-tested.
    """
    dates = sorted(pd.to_datetime(list(monthly.keys())))
    keyed = {pd.to_datetime(k): v for k, v in monthly.items()}

    events = []
    prev_set: set | None = None
    for d in dates:
        snap = keyed[d]
        cur_set = set(snap["cusip"].dropna())
        if prev_set is not None:
            meta = snap.set_index("cusip")
            for cusip in cur_set - prev_set:
                r = meta.loc[cusip]
                events.append((d, cusip, _first(r.get("ticker")),
                               _first(r.get("name")), "added"))
            for cusip in prev_set - cur_set:
                events.append((d, cusip, None, None, "removed"))
        prev_set = cur_set

    out = pd.DataFrame(events,
                       columns=["event_date", "cusip", "ticker", "name", "action"])
    return out.sort_values("event_date").reset_index(drop=True)


def build_inclusion_events(refresh: bool = False) -> pd.DataFrame:
    """Full treatment build: fetch every ETF's N-PORT history, diff, persist.

    Needs SEC access; raises EdgarBlocked from this environment. Implementation
    of the fetch/loop is completed on first unblocked run (the monthly-snapshot
    assembly depends on the live N-PORT index, which cannot be probed here).
    """
    raise NotImplementedError(
        "Run from an unblocked network: assembles monthly N-PORT snapshots per "
        "ETF in ETF_TICKERS via find_nport_filings()+parse_nport_xml(), then "
        "calls compute_inclusion_events(). Blocked by SEC egress filter here."
    )


def _num(txt: str):
    try:
        return float(txt)
    except ValueError:
        return None


def _first(v):
    if isinstance(v, pd.Series):
        v = v.iloc[0]
    return None if pd.isna(v) else v
