"""Placebo identification — the project's centrepiece (H2).

Any index addition moves flows mechanically (Shleifer 1986; Harris-Gurel 1986;
Wurgler-Zhuravskaya 2002). Running the *identical* estimator on matched non-ESG
inclusions (S&P 500 adds) isolates the ESG-specific component:

    ESG-specific effect  =  ESG-inclusion effect  −  generic-inclusion effect

If the two are indistinguishable (or ESG is smaller), the market prices the
*index*, not the *ESG label* — the normative punchline.

Phase 3 consolidated this into ``src.estimate.did.esg_specific_contrast``, which
runs the Sun-Abraham estimator on both arms over matched controls and returns
the windowed post-ATT difference with a contrast SE. NOTE: the contrast takes
the single combined ``panel`` (it carries both arms' treatment flags), not two
separate frames as the original draft signature assumed. This module re-exports.
"""

from __future__ import annotations

import pandas as pd

from src.estimate.did import esg_specific_contrast

__all__ = ["run_placebo_contrast", "esg_specific_contrast"]


def run_placebo_contrast(panel: pd.DataFrame, outcome: str = "n_filers",
                         *, control_pool: str = "matched_cem") -> dict:
    """ESG vs S&P 500 inclusion contrast — alias for ``esg_specific_contrast``."""
    return esg_specific_contrast(panel, outcome, control_pool=control_pool)
