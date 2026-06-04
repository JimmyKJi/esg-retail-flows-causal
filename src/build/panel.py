"""Build the firm × quarter analysis panel (Phase 2).

Combines the ingested pieces into one tidy panel keyed on (cusip/ticker,
quarter):

  treatment   esg_inclusion: 1 from the quarter a firm enters the ESG Leaders
              index (from nport_holdings.compute_inclusion_events), with the
              event quarter recorded for staggered-DiD cohort timing.
  outcomes    d_inst_own_pct  (primary: Δ aggregate institutional ownership),
              d_n_filers      (primary: Δ count of 13F filers holding),
              car_ff          (secondary: FF-adjusted cumulative abnormal return).
  controls    log_mktcap, sector (GICS), pre-period ownership, liquidity.
  fixed eff.  sector × quarter, baked in as columns for the estimators.

13F is quarterly, so event time is measured in QUARTERS, not days — a coarse-
timing caveat carried through to the writeup.

DoD (Phase 2): data/processed/panel.parquet exists; no post-treatment leakage
into pre-period columns; balanced pre-trend columns present; treated/control
counts reported. See tests/test_panel.py (added in Phase 2).
"""

from __future__ import annotations

import pandas as pd


def build_panel(
    inclusion_events: pd.DataFrame,
    holdings_13f: pd.DataFrame,
    prices: pd.DataFrame,
    ff_factors: pd.DataFrame,
    sp500_constituents: pd.DataFrame,
) -> pd.DataFrame:
    """Assemble the firm×quarter panel. Implemented in Phase 2 (needs 13F data)."""
    raise NotImplementedError("Phase 2 — blocked until 13F + N-PORT data are pulled.")
