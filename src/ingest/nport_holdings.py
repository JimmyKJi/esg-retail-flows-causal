"""Reconstruct ESG-index inclusion/exclusion events — the TREATMENT.

The treatment is a firm entering the MSCI USA (Extended) ESG Leaders index.
MSCI's official constituent history is paywalled, so we proxy it with the
holdings of an ETF that tracks the index — iShares **SUSL** (ESG MSCI USA
Leaders) and **SUSA** (MSCI USA ESG Select) — and detect adds/drops by diffing
consecutive *quarterly* holdings.

Why N-PORT rather than the iShares website CSV or the Wayback Machine
(the build plan's first suggestions)?
  * Wayback has no usable capture history for the iShares holdings endpoint
    (verified empty during Phase 1 discovery), and the live CSV is a single
    current snapshot — no history.
  * SEC Form **N-PORT-P** publishes every registered fund's *quarterly*
    portfolio holdings as structured XML, free, back to ~2019. Diffing quarter
    t vs t-1 yields dated add/drop events directly. This is the robust source.

Pipeline (separable + testable):
  1. find_nport_filings()  — locate the ETF's N-PORT-P accessions  [needs SEC]
  2. parse_nport_xml()     — holdings out of one filing's XML       [pure, tested]
  3. compute_inclusion_events() — diff the quarterly series -> events [pure, tested]

ACCESS: the live-fetch stages (find_nport_filings, build_inclusion_events) need
SEC. SEC blocks datacenter/VPN IPs and non-deliverable UA emails; from a
residential network with SEC_EDGAR_UA set to a real contact, EDGAR returns 200
(see edgar_session). Stages 2–3 are pure and unit-tested.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

import pandas as pd

from src.ingest.edgar_session import edgar_get
from src.utils.paths import DATA_INTERIM

# iShares ETFs tracking the ESG Leaders / Select indices (treatment proxies),
# mapped to their SEC fund-series IDs (from company_tickers_mf.json). SUSL tracks
# MSCI USA (Extended) ESG Leaders — the primary treatment; SUSA tracks MSCI USA
# ESG Select — kept separate as a distinct index (robustness, not the same add).
ETF_TICKERS = ("SUSL", "SUSA")
SERIES_IDS = {"SUSL": "S000065418", "SUSA": "S000004436"}
INDEX_NAME = {"SUSL": "MSCI USA ESG Leaders", "SUSA": "MSCI USA ESG Select"}
_TRUST_CIK = "1100663"  # iShares Trust
_BROWSE = "https://www.sec.gov/cgi-bin/browse-edgar"


def find_nport_filings(series_id: str) -> pd.DataFrame:
    """List a fund series' public NPORT-P filings via EDGAR browse (atom feed).

    Keyed by SEC *series* id (e.g. S000065418) so we get exactly that ETF's
    filings, not every fund in the iShares-Trust registrant. Pages through all
    results. Returns columns: accession, filing_date. Needs SEC access.

    (Public N-PORT-P is filed quarterly — the fiscal-quarter-end month of each
    quarter — so consecutive filings are one quarter apart.)
    """
    rows: list[dict] = []
    start = 0
    while True:
        params = {"action": "getcompany", "CIK": series_id, "type": "NPORT-P",
                  "owner": "include", "count": "100", "start": str(start),
                  "output": "atom"}
        root = ET.fromstring(edgar_get(_BROWSE, params=params).content)
        n = 0
        for e in root.iter():
            if e.tag.rsplit("}", 1)[-1] != "content":
                continue
            acc = e.findtext("{*}accession-number")
            if acc:
                rows.append({"accession": acc,
                             "filing_date": e.findtext("{*}filing-date")})
                n += 1
        if n < 100:
            break
        start += 100
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


def compute_inclusion_events(snapshots: dict) -> pd.DataFrame:
    """Diff a dated series of holdings snapshots into add/drop events.

    `snapshots` maps an as-of date (str/Timestamp) -> holdings DataFrame
    (must have a 'cusip' column). A CUSIP present at snapshot t but absent at the
    prior snapshot is an 'added' (inclusion) event dated t; the reverse is a
    'removed' event. The earliest snapshot seeds membership (no events).

    Returns: event_date, cusip, ticker, name, action. Pure: unit-tested.
    """
    dates = sorted(pd.to_datetime(list(snapshots.keys())))
    keyed = {pd.to_datetime(k): v for k, v in snapshots.items()}

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

    For each fund in ``ETF_TICKERS`` this pulls the quarterly NPORT-P holdings
    from live SEC, assembles a dated snapshot series, diffs it into
    inclusion/exclusion events, and writes two interim tables:
      * ``esg_index_holdings.parquet`` — the membership panel (one row per CUSIP
        per as-of date per ETF), and
      * ``esg_inclusion_events.parquet`` — the dated add/drop events (treatment).
    Returns the events table. Needs live SEC (residential network + real-email
    UA — see edgar_session); cached unless ``refresh``.
    """
    events_path = DATA_INTERIM / "esg_inclusion_events.parquet"
    holdings_path = DATA_INTERIM / "esg_index_holdings.parquet"
    if not refresh and events_path.exists():
        return pd.read_parquet(events_path)

    all_holdings: list[pd.DataFrame] = []
    all_events: list[pd.DataFrame] = []
    for ticker in ETF_TICKERS:
        filings = find_nport_filings(SERIES_IDS[ticker]).sort_values("filing_date")
        snapshots: dict[str, pd.DataFrame] = {}
        for acc in filings["accession"]:
            repdate, holdings = _fetch_snapshot(acc)
            if not repdate or holdings.empty:
                continue
            snapshots[repdate] = holdings  # later filing wins => amendment over original
            all_holdings.append(holdings.assign(
                as_of=pd.to_datetime(repdate), etf=ticker, index_name=INDEX_NAME[ticker]))
        ev = compute_inclusion_events(snapshots)
        all_events.append(ev.assign(etf=ticker, index_name=INDEX_NAME[ticker]))

    holdings_df = pd.concat(all_holdings, ignore_index=True)
    events_df = _fill_event_meta(pd.concat(all_events, ignore_index=True), holdings_df)
    events_df = _flag_corp_actions(events_df)

    holdings_df.to_parquet(holdings_path, index=False)
    events_df.to_parquet(events_path, index=False)
    return events_df


_NAME_JUNK = re.compile(
    r"\b(INC|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED|PLC|THE|CLASS [A-C]|CL [A-C])\b")


def _norm_name(s) -> str:
    """Issuer name -> punctuation/suffix-stripped key for matching same-firm rows."""
    s = str(s or "").upper()
    s = re.sub(r"[.,/&'-]", " ", s)
    s = _NAME_JUNK.sub(" ", s)
    return re.sub(r"\s+", "", s)


def _flag_corp_actions(events: pd.DataFrame) -> pd.DataFrame:
    """Mark events that are identifier churn, not genuine index entry/exit.

    A stock split, redomicile or reorganization mints a *new* CUSIP for the same
    firm, so a pure CUSIP diff sees a same-quarter add **and** drop of one issuer.
    We flag (not drop) those: within an (etf, event_date) an exact normalized-name
    match on the opposite action sets ``corp_action_suspect=True`` on both rows.
    Conservative by design — exact-name only, so it won't false-flag genuine
    inclusions. Changed-name renames/mergers (e.g. AXA Equitable -> Equitable,
    BB&T+SunTrust -> Truist) survive this filter and are reconciled in Phase 2.
    """
    ev = events.copy()
    ev["corp_action_suspect"] = False
    if ev.empty:
        return ev
    key = ev["name"].map(_norm_name)
    for (etf, d), g in ev.groupby(["etf", "event_date"]):
        k = key.loc[g.index]
        added = set(k[g["action"] == "added"]) - {""}
        removed = set(k[g["action"] == "removed"]) - {""}
        churn = added & removed
        if churn:
            ev.loc[g.index[k.isin(churn)], "corp_action_suspect"] = True
    return ev


def _extract_repdate(xml_bytes: bytes):
    """The holdings as-of date from an N-PORT filing (genInfo/repPdDate).

    Namespace-agnostic. This is the quarter-end the public holdings are reported
    as of (e.g. 2026-02-28) — deliberately NOT ``repPdEnd``, which is the fund's
    fiscal-year end (a constant, e.g. 2026-08-31) and would collapse quarters.
    Returns None if absent, so the caller skips the filing rather than mis-dating
    it.
    """
    root = ET.fromstring(xml_bytes)
    for e in root.iter():
        if e.tag.rsplit("}", 1)[-1] == "repPdDate":
            txt = (e.text or "").strip()
            if txt:
                return txt
    return None


def _fetch_snapshot(accession: str):
    """One filing's primary_doc.xml -> (as_of_date_str, holdings DataFrame)."""
    acc = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{_TRUST_CIK}/{acc}/primary_doc.xml"
    xml = edgar_get(url).content
    return _extract_repdate(xml), parse_nport_xml(xml)


def _fill_event_meta(events: pd.DataFrame, holdings: pd.DataFrame) -> pd.DataFrame:
    """Backfill ticker/name on 'removed' events, which carry only a CUSIP.

    A removed CUSIP is by construction absent from the current snapshot, so
    compute_inclusion_events leaves its ticker/name null. Recover them from the
    holdings panel (most-recent non-null wins) for readability; the downstream
    panel join is on CUSIP regardless.
    """
    if events.empty:
        return events
    meta = (holdings.dropna(subset=["cusip"]).sort_values("as_of")
            .groupby("cusip")[["ticker", "name"]].last())
    events = events.copy()
    for col in ("ticker", "name"):
        backfill = events["cusip"].map(meta[col])
        events[col] = events[col].where(events[col].notna(), backfill)
    return events


def _num(txt: str):
    try:
        return float(txt)
    except ValueError:
        return None


def _first(v):
    if isinstance(v, pd.Series):
        v = v.iloc[0]
    return None if pd.isna(v) else v
