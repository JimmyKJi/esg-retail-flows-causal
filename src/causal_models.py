"""
Causal estimation module.

Wraps DoWhy / linearmodels to estimate the primary treatment effect (rating
change -> institutional flows) and the reverse (lagged flows -> future rating
change).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def estimate_stacked_did(
    matched_panel: pd.DataFrame,
    outcome_col: str = "delta_institutional_ownership",
    event_window: tuple[int, int] = (-4, 8),
) -> dict:
    """
    Estimate stacked difference-in-differences with stock and calendar-time
    fixed effects following Cengiz et al. (2019).

    Returns a dictionary with:
        coefficients: per event-time coefficient estimates
        std_errors: clustered at firm level
        confidence_intervals: 95% CIs
        summary: regression summary object
    """
    raise NotImplementedError("Implement in notebook 03_event_study.")


def estimate_iv_effect(
    panel: pd.DataFrame,
    instrument_col: str = "esg_index_added_flag",
    treatment_col: str = "esg_rating_change_flag",
    outcome_col: str = "delta_institutional_ownership",
) -> dict:
    """
    Two-stage least squares estimation with ESG index inclusion as the
    instrument for rating change.

    Returns dict with first-stage F-stat, LATE estimate, standard errors,
    and overidentification / weak-instrument diagnostics.
    """
    raise NotImplementedError("Implement in notebook 04_instrumental_vars.")


def estimate_reverse_causality(
    panel: pd.DataFrame,
    lag_quarters: int = 4,
) -> dict:
    """
    Test the reverse causal direction: do lagged institutional flows predict
    future ESG rating changes? Uses panel fixed-effects OLS with the lagged
    flow as the treatment variable.

    Returns dict with coefficient on lagged flow, standard error, and p-value.
    """
    raise NotImplementedError("Implement in notebook 04_instrumental_vars.")


def run_placebo_tests(
    panel: pd.DataFrame,
    placebo_event_col: str = "russell_rebalance_flag",
) -> dict:
    """
    Run placebo tests using non-ESG index rebalancing events as placebo
    treatments. A clean causal design should show null effects here.

    Returns dict of placebo coefficient, SE, and pass/fail indicator.
    """
    raise NotImplementedError("Implement in notebook 04_instrumental_vars.")
