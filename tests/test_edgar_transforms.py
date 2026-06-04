"""Unit tests for the SEC transform cores.

SEC blocks this environment's egress IP, so the *fetch* stages can't run here.
But the parse/aggregate/diff logic is pure and is verified on synthetic inputs
that mimic the real schemas — so the analysis logic is trustworthy before we
ever touch live EDGAR.
"""

from __future__ import annotations

import pandas as pd

from src.ingest.edgar_13f import aggregate_ownership
from src.ingest.nport_holdings import compute_inclusion_events, parse_nport_xml


def test_aggregate_ownership_counts_distinct_filers():
    infotable = pd.DataFrame({
        "ACCESSION_NUMBER": ["a1", "a1", "a2", "a2"],
        "CUSIP": ["XXX", "YYY", "XXX", "XXX"],  # a2 lists XXX twice (two lots)
        "VALUE": ["100", "50", "200", "25"],
        "SSHPRNAMT": ["10", "5", "20", "2"],
    })
    submission = pd.DataFrame({
        "ACCESSION_NUMBER": ["a1", "a2"],
        "CIK": ["111", "222"],
        "FILING_DATE": ["2024-05-15", "2024-05-15"],
    })
    out = aggregate_ownership(infotable, submission).set_index("cusip")

    assert out.loc["XXX", "n_filers"] == 2      # filers 111 and 222
    assert out.loc["XXX", "total_value"] == 325  # 100 + 200 + 25
    assert out.loc["YYY", "n_filers"] == 1
    assert out.loc["XXX", "total_shares"] == 32  # 10 + 20 + 2


_NPORT_XML = b"""<?xml version='1.0'?>
<edgarSubmission xmlns='http://www.sec.gov/edgar/nport'>
  <formData><invstOrSecs>
    <invstOrSec>
      <name>Apple Inc</name><cusip>037833100</cusip>
      <identifiers><ticker value='AAPL'/></identifiers>
      <pctVal>5.25</pctVal><valUSD>1000000</valUSD>
    </invstOrSec>
    <invstOrSec>
      <name>Microsoft Corp</name><cusip>594918104</cusip>
      <identifiers><ticker value='MSFT'/></identifiers>
      <pctVal>4.10</pctVal><valUSD>800000</valUSD>
    </invstOrSec>
  </invstOrSecs></formData>
</edgarSubmission>"""


def test_parse_nport_xml_namespace_and_attributes():
    df = parse_nport_xml(_NPORT_XML)
    assert len(df) == 2
    aapl = df.set_index("cusip").loc["037833100"]
    assert aapl["ticker"] == "AAPL"          # read from an XML attribute
    assert aapl["pct_value"] == 5.25         # numeric coercion
    assert aapl["value_usd"] == 1_000_000


def test_compute_inclusion_events_diffs_months():
    monthly = {
        "2023-01-31": pd.DataFrame({"cusip": ["A", "B"], "ticker": ["A", "B"], "name": ["A", "B"]}),
        "2023-02-28": pd.DataFrame({"cusip": ["B", "C"], "ticker": ["B", "C"], "name": ["B", "C"]}),
    }
    ev = compute_inclusion_events(monthly)
    actions = {(r.cusip, r.action) for r in ev.itertuples()}

    assert ("C", "added") in actions     # new in Feb -> inclusion
    assert ("A", "removed") in actions   # gone in Feb -> exclusion
    assert ("B", "added") not in actions  # held throughout -> no event
    assert len(ev) == 2                   # Jan seeds membership, no events
