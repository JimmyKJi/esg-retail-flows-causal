"""Placebo identification — the project's centrepiece (Phase 4).

Any index addition moves flows mechanically (Shleifer 1986; Harris-Gurel 1986;
Wurgler-Zhuravskaya). Running the *identical* estimator on matched non-ESG
inclusions (S&P 500 adds) isolates the ESG-specific component:

    ESG-specific effect  =  ESG-inclusion effect  −  generic-inclusion effect

If the two are indistinguishable, the market prices the *index*, not the *ESG
label* — the normative punchline.
"""

from __future__ import annotations

import pandas as pd


def run_placebo_contrast(
    esg_panel: pd.DataFrame,
    sp500_panel: pd.DataFrame,
    outcome: str = "d_inst_own_pct",
) -> dict:
    """Estimate both inclusion effects and their difference (+ SE). Phase 4."""
    raise NotImplementedError("Phase 4 — needs ESG + S&P500 matched panels.")
