"""Baseline event study around ESG-Leaders inclusion (Phase 3).

Coefficients on event-time dummies q = -4..+4 (quarters), firm and
calendar-quarter fixed effects, SEs clustered by firm — estimated with
`pyfixest`. The q = -1 quarter is the omitted baseline. The pre-period
coefficients double as the visual pre-trends check.

Headline outcome: Δ aggregate institutional ownership; secondary: Δ #filers.
Freeze PREREGISTRATION.md before running (Phase 3 DoD).
"""

from __future__ import annotations

import pandas as pd


def run_event_study(
    panel: pd.DataFrame,
    outcome: str = "d_inst_own_pct",
    window: tuple[int, int] = (-4, 4),
) -> dict:
    """Fit the event-study spec; return coefficients, SEs, CIs, fit object.

    Implemented in Phase 3 with pyfixest:
        feols("y ~ i(event_time, ref=-1) | firm + quarter", vcov={"CRV1": "firm"})
    """
    raise NotImplementedError("Phase 3 — needs panel + frozen pre-registration.")
