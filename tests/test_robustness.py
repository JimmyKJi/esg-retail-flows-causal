"""Unit tests for the Phase-4 robustness battery (src/estimate/robustness.py).

The load-bearing claim is that ``_window_att`` recomputes the windowed post-ATT
and its delta-method SE from a Sun-Abraham fit's stored coefficients/covariance,
and that with the pre-registered POST_WINDOW it reproduces the *same* number the
frozen estimator reports. We pin that against ``run_sun_abraham`` on a tiny
homogeneous DGP, then check the H2 contrast gating and the winsorise helper.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estimate.did import POST_WINDOW, run_sun_abraham
from src.estimate.robustness import _contrast, _window_att, _winsorize


def _toy_panel(tau: float = 3.0, noise: float = 0.05, seed: int = 0) -> pd.DataFrame:
    """Balanced firm x quarter panel with a known constant ATT (mirrors
    test_did._toy_panel): 30 treated early, 30 late, 40 never-treated controls."""
    rng = np.random.default_rng(seed)
    base, periods = 8082, list(range(8082, 8096))
    rows, fid = [], 0
    for g, k in [(8088, 30), (8090, 30), (None, 40)]:
        for _ in range(k):
            uid, fid = f"U{fid:04d}", fid + 1
            alpha = rng.normal(0, 1.0)
            for t in periods:
                post = 1.0 if (g is not None and t >= g) else 0.0
                y = alpha + 0.3 * (t - base) + tau * post + rng.normal(0, noise)
                rows.append({"cusip": uid, "q_idx": t, "y": float(y),
                             "treated": g is not None,
                             "cohort_q_idx": float(g) if g is not None else np.nan,
                             "clean_control": g is None})
    return pd.DataFrame(rows)


def _fake_res(att_level, var, passes=True, events=(0, 1, 2, 3, 4)):
    n = len(events)
    return {"events": list(events),
            "event_study": pd.DataFrame({"event_time": list(events),
                                         "att": [att_level] * n}),
            "cov": np.eye(n) * var,
            "pre_trends": {"passes": passes},
            "post_att": att_level, "post_se": float(np.sqrt(var / n)),
            "n_treated": 10}


# ── _window_att reproduces the frozen estimator's own windowed ATT/SE ──────────
def test_window_att_matches_run_sun_abraham():
    res = run_sun_abraham(_toy_panel(), "y", arm="esg", control_pool="full")
    att, se = _window_att(res, POST_WINDOW)
    assert att == pytest.approx(res["post_att"], rel=1e-9, abs=1e-9)
    assert se == pytest.approx(res["post_se"], rel=1e-9, abs=1e-9)


def test_window_att_handles_alternative_horizon():
    res = _fake_res(5.0, 1.0)                 # events 0..4, att=5 each, var=1
    att, se = _window_att(res, (0, 2))        # average over 3 cells
    assert att == pytest.approx(5.0)
    assert se == pytest.approx(np.sqrt(3 * (1 / 3) ** 2))     # = sqrt(1/3)


def test_window_att_empty_window_is_nan():
    att, se = _window_att(_fake_res(5.0, 1.0), (20, 30))
    assert np.isnan(att) and np.isnan(se)


# ── H2 contrast arithmetic + pre-registered gating ────────────────────────────
def test_contrast_arithmetic_and_support():
    r = _contrast(_fake_res(30.0, 25.0, True), _fake_res(10.0, 16.0, True))
    assert r["esg_specific"] == pytest.approx(20.0)
    assert r["se_diff"] == pytest.approx(np.hypot(np.sqrt(25 / 5), np.sqrt(16 / 5)))
    assert r["supported"] is True            # diff>0, p<.05, ESG pre-trend passes


def test_contrast_not_supported_when_esg_pretrend_fails():
    r = _contrast(_fake_res(30.0, 1.0, False), _fake_res(10.0, 1.0, True))
    assert r["esg_specific"] > 0 and r["supported"] is False   # gated by pre-trends


def test_contrast_negative_effect_not_supported():
    # the actual ESG-vs-S&P finding: ESG draws *less* -> negative, not supported
    r = _contrast(_fake_res(28.0, 9.0, True), _fake_res(149.0, 36.0 ** 2, True))
    assert r["esg_specific"] < 0 and r["supported"] is False


# ── winsorise helper ──────────────────────────────────────────────────────────
def test_winsorize_clips_to_quantiles():
    df = pd.DataFrame({"q_idx": range(100), "y": list(range(100))})
    w = _winsorize(df, "y", lo=0.05, hi=0.95)
    assert w["y"].min() == pytest.approx(df["y"].quantile(0.05))
    assert w["y"].max() == pytest.approx(df["y"].quantile(0.95))
    assert len(w) == len(df)                 # winsorise clips, never drops rows
