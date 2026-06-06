"""ESG-legitimacy decay — the original contribution (H3).

Hypothesis: the ESG-specific flow response *attenuates* after ~2022, as ESG
becomes politically contested (anti-ESG state legislation, asset-manager
rebranding, methodology disputes).

Phase 3 implements the non-parametric version: split the treated firms into
cohorts that enter the index *before* vs *on/after* 2022Q1 and compare their
windowed post-ATT (Sun-Abraham, matched controls). Decay holds iff
ATT(late) - ATT(early) < 0. This is ``src.estimate.did.decay_split``; with only
~3 post-2022 quarters of 13F data and a coarse quarterly panel, the cohort split
is better identified than a treatment x post-2022 interaction on the dynamic
path, and avoids re-using the post-period twice. This module re-exports it.
"""

from __future__ import annotations

import pandas as pd

from src.estimate.did import decay_split

__all__ = ["run_decay_interaction", "decay_split"]


def run_decay_interaction(panel: pd.DataFrame, outcome: str = "n_filers",
                          *, control_pool: str = "matched_cem",
                          break_year: int = 2022) -> dict:
    """Early- vs late-cohort decay (split at 2022Q1) — alias for ``decay_split``.

    ``break_year`` is accepted for signature compatibility; the implemented split
    is the pre-registered 2022Q1 boundary (``did.Q_2022Q1``)."""
    return decay_split(panel, outcome, control_pool=control_pool)
