"""Unit tests for the Phase 2 panel builder (pure logic on synthetic inputs).

Mirrors the real interim schemas so the treatment-timing, quarter-alignment,
VALUE-unit-normalisation and sample-role logic is verified before it touches the
988k-row live panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.build.panel import build_panel

# ── synthetic inputs (schemas match the interim parquets) ──────────────────────

_EVENTS = pd.DataFrame({
    "event_date": pd.to_datetime([
        "2020-02-29",  # AAA genuine add  -> cohort 2020Q1
        "2021-05-31",  # AAA later drop   -> ever_dropped
        "2020-02-29",  # DDD suspect add  -> NOT treated
        "2020-02-29",  # 'N/A' junk add   -> filtered out, never treated
    ]),
    "cusip":  ["AAA111111", "AAA111111", "DDD444444", "N/A"],
    "ticker": [None, None, None, None],
    "name":   ["A Co", "A Co", "D Co", "junk"],
    "action": ["added", "removed", "added", "added"],
    "etf":    ["SUSL", "SUSL", "SUSL", "SUSL"],
    "index_name": ["MSCI USA ESG Leaders"] * 4,
    "corp_action_suspect": [False, False, True, False],
})

_MEMBERSHIP = pd.DataFrame({
    "cusip":  ["AAA111111", "CCC333333", "DDD444444"],
    "ticker": [None, None, None],
    "name":   ["A Co", "C Co", "D Co"],
    "pct_value": [1.0, 1.0, 1.0],
    "value_usd": [1.0, 1.0, 1.0],
    "as_of":  pd.to_datetime(["2020-02-29", "2019-11-30", "2020-02-29"]),
    "etf":    ["SUSL", "SUSL", "SUSL"],
    "index_name": ["MSCI USA ESG Leaders"] * 3,
})


def _h(cusip, period, n_filers, shares=100, value=100):
    return {"cusip": cusip, "total_value": value, "total_shares": shares,
            "n_filers": n_filers, "filing_date": pd.Timestamp("2020-01-01"),
            "period": pd.Timestamp(period)}


_HOLDINGS = pd.DataFrame([
    # AAA — treated cohort 2020Q1: two pre quarters, two post; breadth jumps.
    _h("AAA111111", "2019-09-30", 10),
    _h("AAA111111", "2019-12-31", 11),
    _h("AAA111111", "2020-03-31", 20),
    _h("AAA111111", "2020-06-30", 25),
    # BBB — clean control: also probes the unit change and the gap rule.
    _h("BBB222222", "2022-09-30", 3, shares=5, value=100),   # thousands -> *1000
    _h("BBB222222", "2022-12-31", 3, shares=5, value=100),   # whole-$   -> as-is
    _h("BBB222222", "2023-06-30", 4, shares=5, value=100),   # gap (skips 2023Q1)
    # CCC — left-censored member (in membership, no event) -> esg_excluded.
    _h("CCC333333", "2020-03-31", 7),
    # DDD — corp-action-suspect add -> NOT treated; member_ever -> esg_excluded.
    _h("DDD444444", "2020-03-31", 8),
    # junk CUSIP family -> dropped entirely.
    _h("000000000", "2020-03-31", 99),
])


# S&P 500 placebo arm (CUSIP-keyed adds + ever-member pool). AAA is *also* an ESG
# inclusion (overlap → both_treated); BBB is S&P-only (a "clean generic" placebo
# treatment); CCC is an ever-member but not a dated add (control-pool exclusion).
_SP500_EVENTS = pd.DataFrame({
    "cusip":      ["AAA111111", "BBB222222"],
    "event_date": pd.to_datetime(["2020-01-15", "2022-08-15"]),  # -> 2020Q1, 2022Q3
})
_SP500_MEMBERS = {"AAA111111", "BBB222222", "CCC333333"}


def _panel():
    return build_panel(_EVENTS, _HOLDINGS, _MEMBERSHIP).set_index(["cusip", "period"])


def _panel_placebo():
    return build_panel(
        _EVENTS, _HOLDINGS, _MEMBERSHIP,
        sp500_events=_SP500_EVENTS, sp500_member_cusips=_SP500_MEMBERS,
    ).set_index(["cusip", "period"])


def test_junk_cusips_dropped():
    p = build_panel(_EVENTS, _HOLDINGS, _MEMBERSHIP)
    assert "000000000" not in set(p["cusip"])
    assert "N/A" not in set(p["cusip"])


def test_cohort_event_time_and_post_are_absorbing():
    p = _panel()
    aaa = p.xs("AAA111111")
    assert (aaa["cohort"] == pd.Timestamp("2020-03-31")).all()        # Feb-29 -> Q1
    assert aaa.loc["2019-12-31", "event_time"] == -1
    assert aaa.loc["2020-03-31", "event_time"] == 0
    assert aaa.loc["2020-06-30", "event_time"] == 1
    assert not aaa.loc["2019-12-31", "post"]                          # pre  -> off
    assert aaa.loc["2020-03-31", "post"]                             # post -> on
    assert aaa.loc["2020-06-30", "post"]                            # absorbing


def test_quarter_alignment_joins_treatment_to_13f():
    # The Feb-29 inclusion must land in the same quarter as the Mar-31 13F snapshot.
    aaa = _panel().xs("AAA111111")
    assert aaa.loc["2020-03-31", "esg_inclusion"]


def test_value_unit_normalised_but_breadth_and_shares_immune():
    bbb = _panel().xs("BBB222222")
    assert bbb.loc["2022-09-30", "value_unit_normalized"]
    assert not bbb.loc["2022-12-31", "value_unit_normalized"]
    assert bbb.loc["2022-09-30", "total_value_usd"] == 100 * 1000     # thousands ->$
    assert bbb.loc["2022-12-31", "total_value_usd"] == 100            # already $
    assert bbb.loc["2022-09-30", "n_filers"] == bbb.loc["2022-12-31", "n_filers"]
    assert bbb.loc["2022-09-30", "total_shares"] == bbb.loc["2022-12-31", "total_shares"]


def test_one_quarter_change_only_across_adjacent_quarters():
    bbb = _panel().xs("BBB222222")
    assert bbb.loc["2022-12-31", "d_n_filers"] == 0          # 3 -> 3, adjacent
    assert pd.isna(bbb.loc["2023-06-30", "d_n_filers"])      # 2-quarter gap -> NaN
    aaa = _panel().xs("AAA111111")
    assert aaa.loc["2020-03-31", "d_n_filers"] == 9          # 11 -> 20, adjacent


def test_sample_roles_separate_controls_from_contaminated_members():
    p = _panel()
    assert p.xs("AAA111111").iloc[0]["sample_role"] == "treated"
    assert p.xs("BBB222222").iloc[0]["sample_role"] == "clean_control"
    # left-censored member: in the index but no datable inclusion -> excluded
    assert p.xs("CCC333333").iloc[0]["sample_role"] == "esg_excluded"
    # corp-action-suspect add: not a genuine inclusion -> excluded, not a control
    ddd = p.xs("DDD444444").iloc[0]
    assert not ddd["treated"]
    assert ddd["sample_role"] == "esg_excluded"


def test_treatment_reversal_flagged():
    # AAA is dropped in 2021Q2, after its 2020Q1 cohort -> ever_dropped.
    assert _panel().xs("AAA111111")["ever_dropped"].all()
    assert not _panel().xs("BBB222222")["ever_dropped"].any()


# ── placebo arm (S&P 500 generic-inclusion benchmark) ─────────────────────────

def test_placebo_columns_absent_unless_requested():
    # Backward-compat: with no sp500_events, the placebo arm must not leak columns.
    p = build_panel(_EVENTS, _HOLDINGS, _MEMBERSHIP)
    assert not any(c.startswith("sp500_") or c == "both_treated" for c in p.columns)


def test_placebo_cohort_is_symmetric_with_esg_arm():
    # The S&P 500 add is built with the identical cohort/event-time/post logic.
    bbb = _panel_placebo().xs("BBB222222")
    assert bbb["sp500_treated"].all()
    assert (bbb["sp500_cohort"] == pd.Timestamp("2022-09-30")).all()   # Aug-15 -> Q3
    assert bbb.loc["2022-09-30", "sp500_event_time"] == 0
    assert bbb.loc["2022-12-31", "sp500_event_time"] == 1
    assert bbb.loc["2022-09-30", "sp500_post"]                         # absorbing
    assert bbb.loc["2022-12-31", "sp500_post"]
    # BBB is S&P-only: the ESG arm stays untouched (clean generic placebo treatment).
    assert not bbb["treated"].any()
    assert not bbb["post"].any()


def test_both_treated_flags_esg_and_sp500_overlap():
    p = _panel_placebo()
    aaa = p.xs("AAA111111")
    assert aaa["treated"].all() and aaa["sp500_treated"].all()
    assert aaa["both_treated"].all()           # in BOTH index events -> contaminated
    bbb = p.xs("BBB222222")
    assert not bbb["both_treated"].any()        # S&P only -> usable clean generic


def test_sp500_member_ever_excludes_from_placebo_control_pool():
    # CCC is an ever-S&P-member but not a dated add: flagged, not placebo-treated —
    # the placebo's analogue of dropping left-censored ESG members from controls.
    ccc = _panel_placebo().xs("CCC333333")
    assert ccc["sp500_member_ever"].all()
    assert not ccc["sp500_treated"].any()
