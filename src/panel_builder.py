"""
Panel construction module.

Takes raw pulls from data_loader and produces the firm-quarter panel used in
all downstream causal analysis.
"""

from __future__ import annotations

import pandas as pd


def build_firm_quarter_panel(
    prices: pd.DataFrame,
    esg_scores: pd.DataFrame,
    holdings_13f: pd.DataFrame,
    index_members: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assemble the main firm-quarter panel.

    Output columns:
        ticker, quarter, esg_score, esg_delta, esg_rating_change_flag,
        institutional_ownership_pct, delta_institutional_ownership,
        esg_index_member_flag, esg_index_added_flag, esg_index_dropped_flag,
        mkt_cap, log_mkt_cap, quarterly_return, industry_code
    """
    raise NotImplementedError("Implement in notebook 02_panel_construction.")


def identify_rating_change_events(
    panel: pd.DataFrame,
    threshold: float = 1.0,
) -> pd.DataFrame:
    """
    Identify rating-change events in the panel. An event is a firm-quarter
    where the absolute ESG score change exceeds the threshold (default 1.0
    point on the 0-10 MSCI scale).

    Returns DataFrame with columns [ticker, event_quarter, event_direction,
    pre_score, post_score, magnitude].
    """
    raise NotImplementedError("Implement in notebook 03_event_study.")


def build_matched_control_pool(
    events: pd.DataFrame,
    panel: pd.DataFrame,
    n_controls_per_event: int = 5,
) -> pd.DataFrame:
    """
    For each event, identify matched control firms with similar pre-event
    ESG scores, industry code, and size decile. Used for stacked DiD.

    Returns DataFrame with columns [event_id, ticker, role (treated/control),
    event_quarter, ...panel columns].
    """
    raise NotImplementedError("Implement in notebook 03_event_study.")
