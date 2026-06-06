"""Heterogeneity — who responds to ESG inclusion? (H4).

Splits the institutional-flow response to show the effect concentrates where
theory predicts:
  * passive vs active 13F filers (index-tracking demand vs discretionary);
  * ESG-badged funds vs not (filer names matched to an ESG/SRI/sustainable
    pattern).

Concentration in passive / ESG-badged responders would corroborate an
index/label mechanism rather than broad re-rating.

STATUS: H4 is now estimable. The classification heuristics below are consumed by
the Phase-5 re-ingest ``src.ingest.edgar_13f_byfiler``, which re-parses the cached
raw 13F INFOTABLE at the filer (CIK) grain and writes per-type breadth/depth
columns; ``src.estimate.h4_filer`` then merges those onto the frozen panel and runs
the matched Sun-Abraham ESG-vs-S&P placebo contrast per filer-type outcome (run
``make heterogeneity``). The legacy ``split_passive_active`` entry point below is
superseded by that pipeline and still raises, redirecting callers to it rather than
silently returning nothing.

Honest finding: the aggregate null survives the decomposition. No filer-type
channel — ESG-named managers, passive complexes, or their dollar depth — shows a
positive ESG-specific pile-in; ``log_shares_esg`` is significantly *negative*
(ESG-branded managers' dollar response is weaker for ESG adds than for the larger
S&P additions). See ``h4_filer`` and ``results/h4_filer.csv``.
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
    """Superseded legacy entry point — use the Phase-5 H4 pipeline instead.

    Filer-type estimation now runs via ``src.ingest.edgar_13f_byfiler`` (re-parses
    the raw 13F INFOTABLE at CIK grain) + ``src.estimate.h4_filer`` (matched
    Sun-Abraham ESG-vs-S&P contrast per filer-type outcome); see ``make
    heterogeneity``. This in-panel re-bucketing was never possible — the frozen
    panel holds cusip x quarter aggregates — so this raises, pointing at the
    pipeline that does the work.
    """
    raise NotImplementedError(H4_NOTE)
