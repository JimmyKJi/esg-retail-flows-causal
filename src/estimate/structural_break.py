"""ESG-legitimacy decay — the original contribution (Phase 5).

Hypothesis: the ESG-specific flow response *attenuates* after ~2022, as ESG
becomes politically contested (anti-ESG state legislation, asset-manager
rebranding, methodology disputes). Tested two ways:

  * interact the inclusion treatment with a post-2022 indicator;
  * a Quandt-Andrews / Chow break test on the inclusion-effect series
    (statsmodels), break date unknown vs imposed at 2022.

A negative, significant post-2022 interaction is the headline decay result and
the empirical hook for the legitimacy thesis.
"""

from __future__ import annotations

import pandas as pd


def run_decay_interaction(panel: pd.DataFrame, outcome: str = "d_inst_own_pct",
                          break_year: int = 2022) -> dict:
    """Treatment × post-break interaction effect. Phase 5."""
    raise NotImplementedError("Phase 5 — needs panel.")


def run_break_test(effect_series: pd.Series) -> dict:
    """Quandt-Andrews unknown-breakpoint test on the effect series. Phase 5."""
    raise NotImplementedError("Phase 5.")
