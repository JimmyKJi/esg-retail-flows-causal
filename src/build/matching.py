"""Matched control construction (Phase 2).

For each treated firm (ESG-Leaders inclusion) pick non-included controls
matched on size, sector, pre-period institutional ownership and liquidity —
via propensity score or coarsened exact matching. The identical routine builds
the matched control pool for the S&P 500 *placebo* inclusions, so the ESG and
generic-inclusion designs are estimated symmetrically.
"""

from __future__ import annotations

import pandas as pd


def build_matched_controls(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    n_controls: int = 5,
    method: str = "psm",  # "psm" | "cem"
) -> pd.DataFrame:
    """Return treated+control rows tagged by event_id and role. Phase 2."""
    raise NotImplementedError("Phase 2 — needs the assembled panel.")
