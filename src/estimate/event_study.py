"""Baseline event study around ESG-Leaders inclusion (Phase 3).

Phase 3 consolidated every estimator into ``src.estimate.did`` (one source of
truth). The baseline two-way-FE event study described here — event-time dummies
q=-4..+6, reference q=-1, firm and calendar-quarter fixed effects, SEs clustered
by firm (pyfixest ``i(event_time, ref=-1)``) — is ``did.run_twfe_event_study``.

It is the *naive* Goodman-Bacon baseline, NOT the headline: under treatment-
effect heterogeneity it is biased, so the headline is the Callaway-Sant'Anna and
Sun-Abraham estimators (also in ``did``). The pre-registered outcomes are
``n_filers`` / ``log_shares`` (PREREGISTRATION.md), not the original draft's
``d_inst_own_pct`` (a percentage that needs shares-outstanding the panel lacks).

This module re-exports the canonical function for backward compatibility.
"""

from __future__ import annotations

import pandas as pd

from src.estimate.did import DISPLAY_WINDOW, run_twfe_event_study

__all__ = ["run_event_study", "run_twfe_event_study"]


def run_event_study(panel: pd.DataFrame, outcome: str = "n_filers",
                    arm: str = "esg", *, control_pool: str = "full",
                    window: tuple[int, int] = DISPLAY_WINDOW) -> dict:
    """Baseline TWFE event study — thin alias for ``did.run_twfe_event_study``."""
    return run_twfe_event_study(panel, outcome, arm=arm,
                                control_pool=control_pool, window=window)
