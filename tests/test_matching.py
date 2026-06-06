"""Unit tests for matched-control construction (Phase 2b, synthetic inputs).

Verifies the matcher on a tiny hand-built baseline panel where the right answer
is known: baseline is the quarter before the cohort, controls come only from the
eligible never-treated pool (ever-members excluded), weights are 1/k, and the
same routine serves the ESG and S&P 500 arms.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.build.matching import build_matched_controls, match_balance


def _firm(cusip, *, q, n_filers, lv, ls, treated=False, cohort=None,
          member=False, sp_treated=False, sp_cohort=None, sp_member=False):
    return {
        "cusip": cusip, "q_idx": q, "n_filers": n_filers,
        "log_value": lv, "log_shares": ls,
        "treated": treated, "cohort_q_idx": cohort, "esg_member_ever": member,
        "sp500_treated": sp_treated, "sp500_cohort_q_idx": sp_cohort,
        "sp500_member_ever": sp_member,
    }


def _panel(rows):
    # each firm needs a baseline-quarter (q=9) row; add a q=10 row for realism.
    out = []
    for r in rows:
        out.append(r)
        out.append({**r, "q_idx": 10})
    return pd.DataFrame(out)


# Cohort 10 -> baseline quarter 9. CN1 mirrors T1 exactly; CF is far; EM is near
# T1 but an ever-member (must never be a control).
_ROWS = [
    _firm("T1", q=9, n_filers=10, lv=5.0, ls=5.0, treated=True, cohort=10),
    _firm("T2", q=9, n_filers=20, lv=6.0, ls=6.0, treated=True, cohort=10),
    _firm("CN1", q=9, n_filers=10, lv=5.0, ls=5.0),
    _firm("CN2", q=9, n_filers=20, lv=6.0, ls=6.0),
    _firm("CM",  q=9, n_filers=15, lv=5.5, ls=5.5),
    _firm("CF",  q=9, n_filers=1,  lv=1.0, ls=1.0),
    _firm("EM",  q=9, n_filers=10, lv=5.0, ls=5.0, member=True),  # near but excluded
]
_P = _panel(_ROWS)


def test_output_schema_and_weights():
    m = build_matched_controls(_P, n_controls=2, method="cem", arm="esg")
    assert {"event_id", "cohort_qidx", "baseline_qidx", "role", "cusip",
            "distance", "weight", "arm", "method"} <= set(m.columns)
    assert (m.loc[m["role"] == "treated", "weight"] == 1.0).all()
    # each treated firm's control weights sum to 1
    cw = m[m["role"] == "control"].groupby("event_id")["weight"].sum()
    assert np.allclose(cw.to_numpy(), 1.0)


def test_baseline_is_quarter_before_cohort():
    m = build_matched_controls(_P, n_controls=2, method="cem", arm="esg")
    assert (m["cohort_qidx"] == 10).all()
    assert (m["baseline_qidx"] == 9).all()      # g − 1


def test_controls_drawn_only_from_eligible_pool():
    m = build_matched_controls(_P, n_controls=5, method="cem", arm="esg")
    controls = set(m.loc[m["role"] == "control", "cusip"])
    assert "EM" not in controls                 # ever-member excluded
    assert "T1" not in controls and "T2" not in controls
    assert controls <= {"CN1", "CN2", "CM", "CF"}


def test_nearest_control_selected():
    m = build_matched_controls(_P, n_controls=2, method="cem", arm="esg")
    t1 = set(m.loc[(m["event_id"] == "T1") & (m["role"] == "control"), "cusip"])
    assert "CN1" in t1                           # exact covariate twin matched
    assert "CF" not in t1                        # far firm not matched to T1


def test_placebo_arm_runs_through_same_routine():
    rows = [
        _firm("S1", q=9, n_filers=12, lv=5.2, ls=5.2, sp_treated=True, sp_cohort=10),
        _firm("D1", q=9, n_filers=12, lv=5.2, ls=5.2),                       # eligible
        _firm("D2", q=9, n_filers=3,  lv=2.0, ls=2.0),                       # far
        _firm("DM", q=9, n_filers=12, lv=5.2, ls=5.2, sp_member=True),       # excluded
    ]
    m = build_matched_controls(_panel(rows), n_controls=2, method="cem", arm="sp500")
    assert (m["arm"] == "sp500").all()
    assert m.loc[m["role"] == "treated", "event_id"].tolist() == ["S1"]
    controls = set(m.loc[m["role"] == "control", "cusip"])
    assert "DM" not in controls and "D1" in controls


def test_balance_improves_after_matching():
    m = build_matched_controls(_P, n_controls=2, method="cem", arm="esg")
    bal = match_balance(_P, m, arm="esg")
    # matching should not worsen balance on any covariate
    assert (bal["smd_after"].abs() <= bal["smd_before"].abs() + 1e-9).all()
