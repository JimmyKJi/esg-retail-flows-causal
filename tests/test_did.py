"""Unit tests for the Phase-3 staggered-DiD estimators (synthetic inputs).

The strategy mirrors test_matching.py: build a tiny panel whose data-generating
process has a *known* constant treatment effect (homogeneous ATT = tau, common
time trend, unit fixed effects, flat pre-trends) and check that every estimator
recovers tau, that the mandatory pre-trends test behaves, that build_frame keys
cohorts/controls correctly, and that the H2/H3 decision arithmetic is right.

Because the DGP is homogeneous, even the (biased-under-heterogeneity) TWFE
estimator is unbiased here — so all three estimators must agree on tau. That is
the point: the test pins the *plumbing*, the real data supplies the heterogeneity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estimate import did
from src.estimate.did import (
    Q_2022Q1,
    build_frame,
    decay_split,
    esg_specific_contrast,
    pre_trends_test,
    run_callaway_santanna,
    run_sun_abraham,
    run_twfe_event_study,
    _post_point,
)

# Quarter indices straddling the 2022Q1 H3 split (Q_2022Q1 == 8089).
BASE = 8082
PERIODS = list(range(BASE, BASE + 14))      # 8082..8095 (14 quarters)
COHORT_EARLY = 8088                          # < 8089  -> "early"
COHORT_LATE = 8090                           # >= 8089 -> "late"
TAU = 3.0                                     # the true constant ATT


def _toy_panel(tau: float = TAU, noise: float = 0.05, seed: int = 0) -> pd.DataFrame:
    """Balanced firm x quarter panel: 30 treated at COHORT_EARLY, 30 at
    COHORT_LATE, 40 never-treated controls. y = unit FE + time trend + tau*post."""
    rng = np.random.default_rng(seed)
    rows = []
    fid = 0
    spec = [(COHORT_EARLY, 30), (COHORT_LATE, 30), (None, 40)]
    for g, k in spec:
        for _ in range(k):
            uid = f"U{fid:04d}"
            fid += 1
            alpha = rng.normal(0, 1.0)                       # unit FE
            for t in PERIODS:
                trend = 0.3 * (t - BASE)                     # common time effect
                post = 1.0 if (g is not None and t >= g) else 0.0
                y = alpha + trend + tau * post + rng.normal(0, noise)
                rows.append({
                    "cusip": uid, "q_idx": t, "y": float(y),
                    "treated": g is not None,
                    "cohort_q_idx": float(g) if g is not None else np.nan,
                    "clean_control": g is None,
                })
    return pd.DataFrame(rows)


# ── build_frame ───────────────────────────────────────────────────────────────
def test_build_frame_keys_cohorts_and_controls():
    f = build_frame(_toy_panel(), "esg", "y", control_pool="full")
    assert f.loc[f["treated_unit"], "g"].notna().all()      # treated carry cohort
    assert f.loc[~f["treated_unit"], "g"].isna().all()      # controls -> never (NaN)
    assert f.loc[f["treated_unit"], "cusip"].nunique() == 60
    assert f.loc[~f["treated_unit"], "cusip"].nunique() == 40
    t = f[f["treated_unit"]].iloc[0]
    assert t["event_time"] == t["q_idx"] - t["g"]           # event time = t - g
    assert f.loc[~f["treated_unit"], "event_time"].isna().all()


def test_build_frame_drops_missing_outcome():
    p = _toy_panel()
    p.loc[p.index[:25], "y"] = np.nan
    f = build_frame(p, "esg", "y", control_pool="full")
    assert f["y"].notna().all()
    assert len(f) == len(p) - 25


def test_build_frame_matched_pool_filters_controls(monkeypatch):
    p = _toy_panel()
    keep = set(p.loc[~p["treated"], "cusip"].unique()[:5])
    monkeypatch.setattr(did, "_matched_control_cusips", lambda arm, method: keep)
    f = build_frame(p, "esg", "y", control_pool="matched_cem")
    assert f.loc[~f["treated_unit"], "cusip"].nunique() == 5      # restricted
    assert f.loc[f["treated_unit"], "cusip"].nunique() == 60      # treated untouched


def test_build_frame_cohort_subset_splits_at_2022q1():
    p = _toy_panel()
    assert COHORT_EARLY < Q_2022Q1 <= COHORT_LATE                 # guard the design
    early = build_frame(p, "esg", "y", control_pool="full", cohort_subset="early")
    late = build_frame(p, "esg", "y", control_pool="full", cohort_subset="late")
    assert set(early.loc[early["treated_unit"], "g"].unique()) == {COHORT_EARLY}
    assert set(late.loc[late["treated_unit"], "g"].unique()) == {COHORT_LATE}
    # controls retained in both subsets
    assert early.loc[~early["treated_unit"], "cusip"].nunique() == 40
    assert late.loc[~late["treated_unit"], "cusip"].nunique() == 40


# ── pre-trends Wald test (pure function) ──────────────────────────────────────
def test_pre_trends_passes_when_flat():
    ev = pd.DataFrame({"event_time": [-4, -3, -2, 0, 1],
                       "att": [0.0, 0.0, 0.0, 2.0, 2.0]})
    cov = np.eye(5) * 0.5
    r = pre_trends_test(ev, cov, [-4, -3, -2, 0, 1])
    assert r["df"] == 3 and r["passes"] is True and r["p_value"] > 0.05


def test_pre_trends_fails_on_pretrend():
    ev = pd.DataFrame({"event_time": [-4, -3, -2, 0, 1],
                       "att": [1.0, 1.0, 1.0, 2.0, 2.0]})
    cov = np.eye(5) * 0.01                                       # tight SEs
    r = pre_trends_test(ev, cov, [-4, -3, -2, 0, 1])
    assert r["passes"] is False and r["p_value"] < 0.05


def test_post_point_averages_window():
    ev = pd.DataFrame({"event_time": [-1, 0, 1, 2, 3, 4, 5],
                       "att": [99.0, 10.0, 10.0, 10.0, 10.0, 10.0, 99.0]})
    assert _post_point(ev) == pytest.approx(10.0)               # mean over e in [0,4]


# ── estimator recovery on the homogeneous DGP ─────────────────────────────────
def test_callaway_santanna_recovers_constant_att():
    r = run_callaway_santanna(_toy_panel(), "y", arm="esg", control_pool="full")
    assert r["post_att"] == pytest.approx(TAU, abs=0.4)
    assert r["n_treated"] == 60 and r["n_control"] == 40


def test_sun_abraham_recovers_constant_att():
    r = run_sun_abraham(_toy_panel(), "y", arm="esg", control_pool="full")
    assert r["post_att"] == pytest.approx(TAU, abs=0.4)
    assert r["pre_trends"]["passes"] is True                    # DGP has no pre-trend


def test_twfe_recovers_constant_att():
    r = run_twfe_event_study(_toy_panel(), "y", arm="esg", control_pool="full")
    assert r["post_att"] == pytest.approx(TAU, abs=0.4)
    assert r["pre_trends"]["passes"] is True


# ── H2 / H3 decision arithmetic (Sun-Abraham fits monkeypatched) ──────────────
def test_esg_specific_contrast_logic(monkeypatch):
    def fake_sa(panel, outcome, arm="esg", *, control_pool="matched_cem", **kw):
        pos = {"post_att": 30.0, "post_se": 5.0, "pre_trends": {"passes": True}}
        neg = {"post_att": 10.0, "post_se": 4.0, "pre_trends": {"passes": True}}
        return pos if arm == "esg" else neg
    monkeypatch.setattr(did, "run_sun_abraham", fake_sa)
    r = esg_specific_contrast(pd.DataFrame(), "n_filers")
    assert r["esg_specific"] == pytest.approx(20.0)
    assert r["se"] == pytest.approx(np.hypot(5.0, 4.0))
    assert r["supported"] is True                              # diff>0, p<.05, pretrend ok


def test_esg_specific_not_supported_when_pretrend_fails(monkeypatch):
    def fake_sa(panel, outcome, arm="esg", *, control_pool="matched_cem", **kw):
        return {"post_att": 30.0 if arm == "esg" else 10.0, "post_se": 1.0,
                "pre_trends": {"passes": arm != "esg"}}        # ESG pretrend fails
    monkeypatch.setattr(did, "run_sun_abraham", fake_sa)
    r = esg_specific_contrast(pd.DataFrame(), "n_filers")
    assert r["esg_specific"] > 0 and r["supported"] is False   # gated by pre-trends


def test_decay_split_logic(monkeypatch):
    def fake_sa(panel, outcome, arm="esg", *, control_pool="matched_cem",
                cohort_subset=None, **kw):
        att = 10.0 if cohort_subset == "early" else 4.0        # late < early -> decay
        return {"post_att": att, "post_se": 2.0, "pre_trends": {"passes": True}}
    monkeypatch.setattr(did, "run_sun_abraham", fake_sa)
    r = decay_split(pd.DataFrame(), "n_filers")
    assert r["decay"] == pytest.approx(-6.0)                   # late - early
    assert r["supported"] is True                             # diff<0 and p<.05
