"""Phase 1 smoke tests: the reachable sources landed with sane shape/coverage.

These read the caches written during ingestion (no network), so they double as
a Phase 1 DoD check. SEC-dependent data is covered by transform unit tests in
test_edgar_transforms.py, since SEC blocks this environment's IP.
"""

from __future__ import annotations

import pytest

from src.ingest.ff_factors import load_ff_factors
from src.ingest.sp500_events import load_sp500_changes
from src.utils.paths import DATA_RAW

FACTORS = {"mkt_rf", "smb", "hml", "rmw", "cma", "rf", "mom"}


def test_ff_factors_shape_and_coverage():
    df = load_ff_factors()
    assert FACTORS <= set(df.columns)
    assert len(df) > 10_000
    assert df.index.min().year <= 1964
    assert df.index.max().year >= 2024
    assert df["mkt_rf"].abs().median() < 0.05  # decimal daily returns, not percent


def test_sp500_changes_have_both_actions():
    df = load_sp500_changes()
    assert len(df) > 100
    assert {"added", "removed"} <= set(df["action"])
    assert df["date"].notna().all()
    assert df["ticker"].str.len().gt(0).all()


def test_prices_cache_present():
    files = list((DATA_RAW / "prices").glob("prices_*"))
    if not files:
        pytest.skip("no cached prices file (run: python -m src.ingest.prices)")
    assert files
