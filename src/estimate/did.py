"""Staggered-adoption DiD (Phase 3).

Inclusions occur on different dates, so a naive two-way FE estimator is biased
under treatment-effect heterogeneity (Goodman-Bacon). We use heterogeneity-
robust estimators as the headline:

  * Callaway & Sant'Anna (2021) group-time ATT via the `differences` package;
  * Sun & Abraham (2021) interaction-weighted event study via `pyfixest`.

A pre-trends test is mandatory before trusting any coefficient; if it fails we
document it and fall back to the event-study estimates.
"""

from __future__ import annotations

import pandas as pd


def run_callaway_santanna(panel: pd.DataFrame, outcome: str = "d_inst_own_pct") -> dict:
    """Group-time ATT(g,t) + aggregated event-study ATT. Phase 3 (`differences`)."""
    raise NotImplementedError("Phase 3 — needs panel + frozen pre-registration.")


def run_sun_abraham(panel: pd.DataFrame, outcome: str = "d_inst_own_pct") -> dict:
    """Interaction-weighted Sun-Abraham event study. Phase 3 (`pyfixest`)."""
    raise NotImplementedError("Phase 3 — needs panel + frozen pre-registration.")


def test_pre_trends(estimates: dict) -> dict:
    """Joint test that pre-period event-time coefficients are zero. Phase 3."""
    raise NotImplementedError("Phase 3.")
