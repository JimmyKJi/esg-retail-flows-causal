"""Heterogeneity — who responds to ESG inclusion? (Phase 5).

Splits the institutional flow response to show the effect concentrates where
theory predicts:
  * passive vs active 13F filers (index-tracking demand vs discretionary);
  * ESG-badged funds vs not (classify filer names against known ESG-fund lists).

Concentration in passive/ESG-badged responders corroborates an index/label
mechanism rather than broad re-rating.
"""

from __future__ import annotations

import pandas as pd


def split_passive_active(panel: pd.DataFrame, filer_classes: pd.DataFrame) -> dict:
    """Re-estimate the inclusion effect by filer type. Phase 5."""
    raise NotImplementedError("Phase 5 — needs 13F filer classification.")


def classify_esg_filers(filer_names: pd.Series) -> pd.Series:
    """Flag ESG-badged filers by name against curated ESG-fund lists. Phase 5."""
    raise NotImplementedError("Phase 5.")
