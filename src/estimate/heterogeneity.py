"""Heterogeneity — who responds to ESG inclusion? (H4).

Splits the institutional-flow response to show the effect concentrates where
theory predicts:
  * passive vs active 13F filers (index-tracking demand vs discretionary);
  * ESG-badged funds vs not (filer names matched to an ESG/SRI/sustainable
    pattern).

Concentration in passive / ESG-badged responders would corroborate an
index/label mechanism rather than broad re-rating.

STATUS: H4 is NOT estimable from the assembled panel. The 13F outcome was cached
as cusip x quarter aggregates, so the per-filer manager (CIK) identity needed to
bucket holders is unavailable (see ``did.H4_NOTE``). The *classification*
methodology below is implemented and unit-testable — only the per-filer holdings
re-ingestion is missing — so ``split_passive_active`` raises an informative error
pointing at the data limitation rather than silently returning nothing.
"""

from __future__ import annotations

import pandas as pd

from src.estimate.did import H4_NOTE

__all__ = ["classify_esg_filers", "classify_passive", "split_passive_active"]

# ESG/SRI/sustainable name heuristic — pre-committed, documented, imperfect.
_ESG_PATTERNS = [
    r"\besg\b", r"\bsri\b", r"sustainab", r"responsib", r"\bimpact\b",
    r"climate", r"\bcarbon\b", r"fossil", r"\bgreen\b", r"clean\s*energy",
    r"renewable", r"ethical", r"stewardship", r"net[\s-]*zero",
    r"low[\s-]*carbon", r"\bparis\b", r"decarbon",
]
_ESG_RE = "|".join(_ESG_PATTERNS)

# Dominant passive / index-fund complexes (manager-name match).
_PASSIVE_PATTERNS = [
    r"vanguard", r"blackrock", r"ishares", r"state\s*street", r"\bssga\b",
    r"\bspdr\b", r"geode", r"northern\s*trust", r"charles\s*schwab",
    r"\bschwab\b", r"xtrackers", r"\bdws\b",
]
_PASSIVE_RE = "|".join(_PASSIVE_PATTERNS)


def classify_esg_filers(filer_names) -> pd.Series:
    """Boolean Series: filer name matches the ESG/SRI/sustainable pattern."""
    s = pd.Series(filer_names, dtype="object").astype(str)
    return s.str.contains(_ESG_RE, case=False, regex=True, na=False)


def classify_passive(filer_names) -> pd.Series:
    """Boolean Series: filer name matches a known passive/index-fund complex."""
    s = pd.Series(filer_names, dtype="object").astype(str)
    return s.str.contains(_PASSIVE_RE, case=False, regex=True, na=False)


def split_passive_active(panel: pd.DataFrame,
                         filer_classes: pd.DataFrame | None = None) -> dict:
    """Re-estimate the inclusion effect by filer type.

    Blocked on data, not on code: the cached panel holds cusip x quarter
    aggregates, so holdings cannot be re-bucketed by filer CIK. Raises with the
    canonical H4 note; enabling it requires re-ingesting the raw 13F INFOTABLE.
    """
    raise NotImplementedError(H4_NOTE)
