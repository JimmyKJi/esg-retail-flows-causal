"""Unit tests for the Phase-5 filer-type re-ingest (H4).

Two load-bearing claims:
  1. ``aggregate_by_filer_type`` counts *distinct filers* by type (so amendments /
     multiple share-class rows for one manager don't inflate breadth) while summing
     shares over every holding row — and the type columns *partition* the total
     (n_filers_esg + n_filers_nonesg == n_filers_total), which is what lets the
     re-ingest reconcile against the frozen ``edgar_13f`` breadth measure.
  2. ``load_h4_panel`` merges the type columns onto the panel on (cusip, q_idx),
     0-fills genuine absences, and derives the log1p depth + complement columns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.ingest.edgar_13f_byfiler import aggregate_by_filer_type
from src.estimate.h4_filer import load_h4_panel


def _toy_tables():
    """Three filers: an ESG boutique, a passive giant, a plain manager.
    CUSIP AAA held by all three; BBB held only by the passive giant, via two rows
    (two share classes) — so BBB must count 1 filer but sum both share rows."""
    submission = pd.DataFrame({
        "ACCESSION_NUMBER": ["A1", "A2", "A3"],
        "CIK": ["1001", "1002", "1003"],
    })
    coverpage = pd.DataFrame({
        "ACCESSION_NUMBER": ["A1", "A2", "A3"],
        "FILINGMANAGER_NAME": ["Trillium ESG Global Equity",
                               "BlackRock Inc", "Joe Stock Picking LLC"],
    })
    infotable = pd.DataFrame({
        "ACCESSION_NUMBER": ["A1", "A2", "A3", "A2", "A2"],
        "CUSIP": ["AAA", "AAA", "AAA", "BBB", "BBB"],
        "SSHPRNAMT": ["100", "200", "300", "50", "50"],
    })
    return infotable, submission, coverpage


def test_aggregate_by_filer_type_reconciles_and_partitions():
    agg = aggregate_by_filer_type(*_toy_tables()).set_index("cusip")

    # AAA: three distinct filers, one each esg/passive; shares summed by type.
    assert agg.loc["AAA", "n_filers_total"] == 3
    assert agg.loc["AAA", "n_filers_esg"] == 1
    assert agg.loc["AAA", "n_filers_passive"] == 1
    assert agg.loc["AAA", "shares_total"] == 600
    assert agg.loc["AAA", "shares_esg"] == 100
    assert agg.loc["AAA", "shares_passive"] == 200

    # BBB: one filer (the passive giant) with two share-class rows → breadth 1,
    # depth summed over both rows. This is the amendment/multi-class guard.
    assert agg.loc["BBB", "n_filers_total"] == 1
    assert agg.loc["BBB", "n_filers_passive"] == 1
    assert agg.loc["BBB", "shares_passive"] == 100

    # Type columns partition the total breadth (the reconciliation property).
    nonesg = agg["n_filers_total"] - agg["n_filers_esg"]
    active = agg["n_filers_total"] - agg["n_filers_passive"]
    assert (agg["n_filers_esg"] <= agg["n_filers_total"]).all()
    assert (nonesg >= 0).all() and (active >= 0).all()


def test_aggregate_handles_no_esg_or_passive():
    # only the plain manager holds CCC → zero esg, zero passive, but one filer.
    info = pd.DataFrame({"ACCESSION_NUMBER": ["A3"], "CUSIP": ["CCC"], "SSHPRNAMT": ["10"]})
    sub = pd.DataFrame({"ACCESSION_NUMBER": ["A3"], "CIK": ["1003"]})
    cov = pd.DataFrame({"ACCESSION_NUMBER": ["A3"],
                        "FILINGMANAGER_NAME": ["Joe Stock Picking LLC"]})
    agg = aggregate_by_filer_type(info, sub, cov).set_index("cusip")
    assert agg.loc["CCC", "n_filers_total"] == 1
    assert agg.loc["CCC", "n_filers_esg"] == 0
    assert agg.loc["CCC", "n_filers_passive"] == 0
    assert agg.loc["CCC", "shares_esg"] == 0 and agg.loc["CCC", "shares_passive"] == 0


def test_load_h4_panel_merges_fills_and_derives(tmp_path):
    panel = pd.DataFrame({
        "cusip": ["AAA", "AAA", "ZZZ"],
        "q_idx": [8089, 8090, 8089],          # AAA@8090 and ZZZ@8089 have no byfiler row
        "n_filers": [5, 4, 2],
    })
    byfiler = pd.DataFrame({
        "cusip": ["AAA"],
        "period": [pd.Timestamp("2022-03-31")],   # -> q_idx 2022*4+1 = 8089
        "n_filers_total": [5], "n_filers_esg": [2], "n_filers_passive": [3],
        "shares_total": [1000.0], "shares_esg": [200.0], "shares_passive": [500.0],
    })
    pp = tmp_path / "panel.parquet"
    bp = tmp_path / "byfiler.parquet"
    panel.to_parquet(pp)
    byfiler.to_parquet(bp)

    m = load_h4_panel(str(pp), str(bp)).set_index(["cusip", "q_idx"])

    # matched row carries the byfiler values + derived columns
    row = m.loc[("AAA", 8089)]
    assert row["n_filers_passive"] == 3 and row["n_filers_esg"] == 2
    assert row["n_filers_active"] == 5 - 3 and row["n_filers_nonesg"] == 5 - 2
    assert row["log_shares_passive"] == np.log1p(500.0)
    assert row["log_shares_esg"] == np.log1p(200.0)

    # genuine absences 0-fill (not NaN), and log1p(0) == 0
    for key in [("AAA", 8090), ("ZZZ", 8089)]:
        assert m.loc[key, "n_filers_passive"] == 0
        assert m.loc[key, "shares_passive"] == 0
        assert m.loc[key, "log_shares_passive"] == 0.0
