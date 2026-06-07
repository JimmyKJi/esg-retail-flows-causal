"""Unit tests for the Phase-6 credibility-of-the-null battery.

Covers the two pure cores that carry the inference:
  * power / MDE / equivalence — MDE factor, CI, and the "precise null" verdict
    (does the 95% CI exclude an effect as large as the SESOI on the predicted side);
  * relative-magnitudes sensitivity — robust CIs over M and the breakdown M* at
    which significance first dies.

Values are pinned to the frozen headline numbers so a drift in the formulas is
caught (e.g. the breadth contrast's M* ≈ 0.27, the breadth null being well-powered
while depth is not).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estimate.credibility import (mde, conf_int, power_row, robust_bounds,
                                      breakdown_m, delta_pre,
                                      _contrast_event_study, _MDE_FACTOR)


def test_mde_and_ci_match_closed_form():
    # MDE factor = z_{.975} + z_{.80} = 1.95996 + 0.84162 = 2.80158
    assert _MDE_FACTOR == pytest.approx(2.801585, abs=1e-5)
    assert mde(10.0) == pytest.approx(28.01585, abs=1e-4)
    lo, hi = conf_int(0.0, 10.0)
    assert lo == pytest.approx(-19.59964, abs=1e-4)
    assert hi == pytest.approx(+19.59964, abs=1e-4)


def test_power_row_breadth_is_precise_null_depth_is_not():
    # H2 breadth: significantly negative, CI upper bound far below the SESOI
    # (a quarter of the +149 mechanical effect) -> rules out a meaningful premium.
    breadth = power_row("H2", "n_filers", -121.468, 37.253, 149.023, direction=1)
    assert breadth["mde80"] == pytest.approx(2.801585 * 37.253, rel=1e-4)
    assert breadth["ci_hi"] == pytest.approx(-121.468 + 1.95996 * 37.253, abs=1e-2)
    assert breadth["sesoi"] == pytest.approx(0.25 * 149.023, rel=1e-6)
    assert breadth["rules_out_meaningful"] is True

    # H2 depth: the CI upper bound (+0.48) sits well above the SESOI -> the null is
    # real but imprecise; we must NOT claim it rules out a meaningful premium.
    depth = power_row("H2", "log_shares", -0.3996, 0.4489, 0.3958, direction=1)
    assert depth["ci_hi"] > depth["sesoi"]
    assert depth["rules_out_meaningful"] is False


def test_power_row_negative_direction_uses_lower_bound():
    # H3 decay (predicted negative): underpowered -> CI lower bound far below the
    # negative SESOI, so we cannot rule out a meaningful decay.
    h3 = power_row("H3", "n_filers", -12.084, 18.086, 33.456, direction=-1)
    assert h3["ci_lo"] == pytest.approx(-12.084 - 1.95996 * 18.086, abs=1e-2)
    assert h3["rules_out_meaningful"] is False


def test_robust_bounds_grid_widens_with_M():
    df = robust_bounds(-121.468, 37.253, 183.0, m_grid=(0.0, 1.0)).set_index("M")
    # M=0 is just the ordinary 95% CI
    assert df.loc[0.0, "robust_lo"] == pytest.approx(-121.468 - 1.95996 * 37.253, abs=1e-2)
    assert df.loc[0.0, "robust_hi"] == pytest.approx(-121.468 + 1.95996 * 37.253, abs=1e-2)
    # M=1 adds ±delta_pre to each edge
    assert df.loc[1.0, "robust_lo"] == pytest.approx(df.loc[0.0, "robust_lo"] - 183.0, abs=1e-2)
    assert df.loc[1.0, "robust_hi"] == pytest.approx(df.loc[0.0, "robust_hi"] + 183.0, abs=1e-2)


def test_breakdown_m_matches_headline_and_edge_cases():
    # Breadth contrast: significantly negative; a violation of only M ~ 0.27 of the
    # worst pre-period deviation admits zero. (Honest: the point estimate is fragile.)
    assert breakdown_m(-121.468, 37.253, 183.0) == pytest.approx(0.2648, abs=1e-3)
    # Already non-significant at M=0 (CI spans 0) -> breakdown 0.
    assert breakdown_m(-0.3996, 0.4489, 0.24) == 0.0
    # No pre-period deviation to extrapolate -> infinitely robust.
    assert breakdown_m(-121.468, 37.253, 0.0) == float("inf")
    # Positive, significant estimate uses the lower edge.
    assert breakdown_m(27.555, 9.367, 38.64) == pytest.approx((27.555 - 1.95996 * 9.367) / 38.64, abs=1e-3)


def test_delta_pre_and_contrast_event_study():
    es = pd.DataFrame({
        "estimator": ["sun_abraham"] * 8,
        "outcome": ["n_filers"] * 8,
        "control_pool": ["matched_cem"] * 8,
        "arm": ["esg"] * 4 + ["sp500"] * 4,
        "event_time": [-4, -2, 0, 2] * 2,
        "att": [-38.0, -5.0, 28.0, 28.0, -221.0, -48.0, 128.0, 140.0],
    })
    diff = _contrast_event_study(es, "n_filers")
    # diff at e=-4 is -38 - (-221) = +183 (pre-trends do NOT cancel)
    d = diff.set_index("event_time")["att"]
    assert d.loc[-4] == pytest.approx(183.0)
    assert d.loc[-2] == pytest.approx(43.0)
    # delta_pre takes the max |.| over the pre-periods present ({-4,-2} here)
    assert delta_pre(diff) == pytest.approx(183.0)
