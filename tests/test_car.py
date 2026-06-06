"""Unit tests for the FF-adjusted CAR event study (Phase 2b, synthetic inputs).

A deterministic price path (flat, then a one-day +5% jump on the event day) with
zero factors makes the abnormal return exactly the jump, so the CAR is known and
the market-model arithmetic is verified end-to-end.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.build.car import build_event_car, car_summary

_DATES = pd.bdate_range("2020-01-01", periods=320)
_EVENT = _DATES[280]


def _prices() -> pd.DataFrame:
    # flat at 100 until the event day, then a one-off +5% step to 105.
    close = np.where(_DATES >= _EVENT, 105.0, 100.0)
    return pd.DataFrame({"date": _DATES, "ticker": "XYZ", "close": close})


def _ff() -> pd.DataFrame:
    z = np.zeros(len(_DATES))
    return pd.DataFrame({"mkt_rf": z, "smb": z, "hml": z, "rmw": z, "cma": z, "rf": z},
                        index=pd.Index(_DATES, name="date"))


_EVENTS = pd.DataFrame({"event_id": ["XYZ", "GONE"], "ticker": ["XYZ", "GONE"],
                        "event_date": [_EVENT, _EVENT]})


def test_car_recovers_known_jump():
    car = build_event_car(_EVENTS, _prices(), _ff(),
                          est_window=(-150, -10), event_window=(-1, 1), min_obs=50)
    xyz = car[car["ticker"] == "XYZ"].iloc[0]
    assert xyz["status"] == "ok"
    assert xyz["t0_date"] == _EVENT                      # event day located exactly
    assert abs(xyz["alpha"]) < 1e-9                      # flat pre-period -> zero alpha
    assert abs(xyz["car"] - 0.05) < 1e-9                 # the +5% jump, abnormal


def test_unpriceable_event_is_flagged_not_dropped():
    car = build_event_car(_EVENTS, _prices(), _ff(),
                          est_window=(-150, -10), event_window=(-1, 1), min_obs=50)
    assert set(car["event_id"]) == {"XYZ", "GONE"}       # nothing silently dropped
    assert car[car["ticker"] == "GONE"].iloc[0]["status"] == "no_prices"


def test_short_estimation_window_flagged():
    # demand more pre-event history than exists -> flagged, not a crash.
    car = build_event_car(_EVENTS, _prices(), _ff(),
                          est_window=(-150, -10), event_window=(-1, 1), min_obs=10_000)
    assert car[car["ticker"] == "XYZ"].iloc[0]["status"] == "short_estimation"


def test_car_summary_arithmetic():
    car = build_event_car(_EVENTS, _prices(), _ff(),
                          est_window=(-150, -10), event_window=(-1, 1), min_obs=50)
    s = car_summary(car)
    assert s["n"] == 1                                   # only XYZ is 'ok'
    assert abs(s["mean_car"] - 0.05) < 1e-9
    assert s["pct_positive"] == 1.0
