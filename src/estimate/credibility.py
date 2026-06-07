"""Phase 6 — credibility of the null.

A null result is only worth anything if the design could have detected an effect.
This module stress-tests the headline null three ways, all pre-specified and all
reported whichever way they land:

  A. Power / minimum detectable effect (MDE) + equivalence.  For every contrast
     (H2, H3, H4) report the smallest true effect the design would catch with 80%
     power, the 95% CI, and whether the CI rules out an *economically meaningful*
     effect — a SESOI set at a quarter of the mechanical index-inclusion effect we
     actually observe. Turns "we found nothing" into "we can rule out effects
     larger than X" (or, honestly, "this arm is underpowered").

  B. Relative-magnitudes sensitivity (Rambachan & Roth 2023, "honest DiD").  The
     headline rests on a matched design whose pre-trends still fail. This asks how
     large a post-treatment parallel-trends violation — measured relative to the
     largest *pre*-period deviation δ — would have to be to overturn each estimate.
     We use the conservative additive worst-case bound: robust CI = point ±
     1.96·se ± M·δ, and report the breakdown M* where the robust set first admits
     zero. (The exact ARP confidence set of Rambachan-Roth is weakly tighter; this
     outer bound is deliberately the pessimistic, against-our-own-result choice.)

  C. Randomization / placebo-in-time inference.  Re-assign each treated name a fake
     inclusion quarter drawn from the observed cohort distribution, re-estimate, and
     locate the real effect in the resulting placebo distribution. Validates the
     analytic clustered SE without leaning on its asymptotics.

Honest bottom line this produces: the ESG-specific *breadth* null is well-powered
(MDE ≈ 104 filers; the 95% CI rules out any positive premium), while *depth* and
the H3 *decay* split are underpowered (stated, not hidden). The significantly
negative breadth point estimate is itself sensitive to the documented differential
pre-trend (low M*) — which is why the conclusion is "no evidence of a positive ESG
premium, in a design powered to find one," never "trust the negative point estimate."
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.estimate.did import (PRE_PERIODS, RESULTS_DIR, run_sun_abraham,
                              _ARMS, _matched_control_cusips)

# ── Pre-registered knobs ──────────────────────────────────────────────────────
POWER = 0.80
ALPHA = 0.05
SESOI_FRAC = 0.25                     # SESOI = 1/4 of the mechanical inclusion effect
M_GRID = (0.0, 0.25, 0.5, 1.0, 1.5, 2.0)
PLACEBO_DRAWS = 300
PLACEBO_SEED = 12345

_Z2 = float(stats.norm.ppf(1 - ALPHA / 2))          # 1.95996 — two-sided 5%
_MDE_FACTOR = _Z2 + float(stats.norm.ppf(POWER))    # 2.80159 — 80% power, 5% size


# ── A. Power / MDE / equivalence (pure) ───────────────────────────────────────
def mde(se: float, *, power: float = POWER, alpha: float = ALPHA) -> float:
    """Minimum detectable effect: smallest true |effect| a two-sided α test catches
    with the given power. MDE = (z_{1-α/2} + z_{power}) · se."""
    factor = float(stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power))
    return factor * float(se)


def conf_int(estimate: float, se: float, *, alpha: float = ALPHA) -> tuple[float, float]:
    z = float(stats.norm.ppf(1 - alpha / 2))
    return estimate - z * se, estimate + z * se


def power_row(family: str, outcome: str, estimate: float, se: float,
              benchmark: float, *, direction: int = 1,
              frac: float = SESOI_FRAC) -> dict:
    """One power/equivalence verdict.

    ``direction`` = +1 if the hypothesis predicts a positive effect (H2/H4 premium),
    −1 if negative (H3 decay). The SESOI is ``frac`` × |benchmark| (the mechanical
    inclusion effect for that outcome). ``rules_out_meaningful`` is True when the
    95% CI excludes effects as large as the SESOI on the hypothesised side — i.e.
    the null is *precise*, not merely non-significant.
    """
    lo, hi = conf_int(estimate, se)
    sesoi = frac * abs(benchmark) if np.isfinite(benchmark) else np.nan
    if not np.isfinite(sesoi):
        rules_out = None
    elif direction > 0:
        rules_out = bool(hi < sesoi)        # upper CI below a meaningful premium
    else:
        rules_out = bool(lo > -sesoi)       # lower CI above a meaningful decay
    return {
        "family": family, "outcome": outcome, "direction": direction,
        "estimate": estimate, "se": se, "ci_lo": lo, "ci_hi": hi,
        "mde80": mde(se), "benchmark": benchmark, "sesoi": sesoi,
        "rules_out_meaningful": rules_out,
    }


# ── B. Relative-magnitudes sensitivity / honest DiD (pure) ────────────────────
def robust_bounds(estimate: float, se: float, delta_pre: float,
                  m_grid=M_GRID, *, alpha: float = ALPHA) -> pd.DataFrame:
    """Conservative relative-magnitudes robust CIs over a grid of M.

    Under a parallel-trends violation bounded by M·δ (δ = largest pre-period
    deviation), the post-ATT bias lies in [−M·δ, +M·δ]; the robust CI is the
    union over that interval: [point − z·se − M·δ, point + z·se + M·δ]."""
    z = float(stats.norm.ppf(1 - alpha / 2))
    rows = [{"M": float(M), "robust_lo": estimate - z * se - M * delta_pre,
             "robust_hi": estimate + z * se + M * delta_pre} for M in m_grid]
    return pd.DataFrame(rows)


def breakdown_m(estimate: float, se: float, delta_pre: float,
                *, alpha: float = ALPHA) -> float:
    """Smallest M at which the robust CI first includes 0 (significance breaks).

    For a negative estimate this is −(point + z·se)/δ; for a positive estimate it
    is (point − z·se)/δ. Returns 0.0 if already non-significant at M=0, and inf if
    there is no pre-period deviation to extrapolate (δ = 0)."""
    z = float(stats.norm.ppf(1 - alpha / 2))
    if delta_pre <= 0:
        return float("inf")
    edge = (estimate + z * se) if estimate < 0 else (estimate - z * se)
    if (estimate < 0 and edge >= 0) or (estimate >= 0 and edge <= 0):
        return 0.0
    return abs(edge) / delta_pre


def _contrast_event_study(es: pd.DataFrame, outcome: str,
                          control_pool: str = "matched_cem") -> pd.DataFrame:
    """ESG-minus-S&P Sun-Abraham event-time point estimates from the saved study."""
    sub = es[(es["estimator"] == "sun_abraham") & (es["outcome"] == outcome)
             & (es["control_pool"] == control_pool)]
    esg = sub[sub["arm"] == "esg"].set_index("event_time")["att"]
    sp = sub[sub["arm"] == "sp500"].set_index("event_time")["att"]
    diff = (esg - sp).rename("att").reset_index().sort_values("event_time")
    return diff


def delta_pre(event_atts: pd.Series | pd.DataFrame, *,
              pre=PRE_PERIODS) -> float:
    """Largest absolute pre-period event-time coefficient (the violation scale δ)."""
    if isinstance(event_atts, pd.DataFrame):
        s = event_atts.set_index("event_time")["att"]
    else:
        s = event_atts
    return float(s.reindex(list(pre)).abs().max())


# ── C. Randomization / placebo-in-time inference (re-estimates) ───────────────
def placebo_in_time(panel: pd.DataFrame, outcome: str = "n_filers",
                    arm: str = "esg", *, control_pool: str = "matched_cem",
                    n_draws: int = PLACEBO_DRAWS, seed: int = PLACEBO_SEED) -> dict:
    """Re-assign treated names fake inclusion quarters (drawn from the observed
    cohort distribution), re-run Sun-Abraham, and place the real post-ATT in the
    resulting placebo distribution. Empirical two-sided p = share of placebo
    |post-ATT| ≥ |real|."""
    cfg = _ARMS[arm]
    cohort_col, treated_col = cfg["cohort"], cfg["treated"]

    # Restrict to the rows the matched fit actually uses, so each refit is cheap.
    treated_cusips = set(panel.loc[panel[treated_col].astype(bool), "cusip"].astype(str))
    if control_pool != "full":
        ctrl = _matched_control_cusips(arm, control_pool.split("_", 1)[1])
    else:
        ctrl = set(panel.loc[cfg["control"](panel), "cusip"].astype(str))
    sub = panel[panel["cusip"].astype(str).isin(treated_cusips | ctrl)].copy()

    real = run_sun_abraham(sub, outcome, arm=arm, control_pool=control_pool)["post_att"]

    tre = sub[treated_col].astype(bool).to_numpy()
    pool = sub.loc[tre, cohort_col].dropna().to_numpy()
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_draws):
        g = pd.to_numeric(sub[cohort_col], errors="coerce").to_numpy(float).copy()
        g[tre] = rng.choice(pool, size=int(tre.sum()), replace=True)
        sub2 = sub.copy()
        sub2[cohort_col] = g
        try:
            draws.append(run_sun_abraham(sub2, outcome, arm=arm,
                                         control_pool=control_pool)["post_att"])
        except Exception:
            continue
    d = np.asarray(draws, dtype=float)
    d = d[np.isfinite(d)]
    emp_p = float((np.abs(d) >= abs(real)).mean()) if len(d) else np.nan
    return {
        "outcome": outcome, "arm": arm, "control_pool": control_pool,
        "real_post_att": float(real), "n_draws": int(len(d)),
        "placebo_mean": float(d.mean()) if len(d) else np.nan,
        "placebo_sd": float(d.std(ddof=1)) if len(d) > 1 else np.nan,
        "emp_p_two_sided": emp_p, "draws": d,
    }


# ── Orchestration ─────────────────────────────────────────────────────────────
def _power_table() -> pd.DataFrame:
    """Assemble the power/MDE/equivalence table from the frozen contrast CSVs."""
    rows = []
    h2 = pd.read_csv(RESULTS_DIR / "h2_esg_specific.csv")
    for _, r in h2.iterrows():
        rows.append(power_row("H2", r["outcome"], r["esg_specific"], r["se"],
                              r["att_sp500"], direction=1))
    h3 = pd.read_csv(RESULTS_DIR / "h3_decay.csv")
    for _, r in h3.iterrows():
        rows.append(power_row("H3", r["outcome"], r["decay"], r["se"],
                              r["att_early"], direction=-1))
    h4_path = RESULTS_DIR / "h4_filer.csv"
    if h4_path.exists():
        h4 = pd.read_csv(h4_path)
        for _, r in h4.iterrows():
            rows.append(power_row("H4", r["outcome"], r["esg_specific"], r["se"],
                                  r["att_sp500"], direction=1))
    return pd.DataFrame(rows)


def _honest_did_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Relative-magnitudes summary (one row per target) + the full M-grid curve."""
    es = pd.read_parquet(RESULTS_DIR / "event_studies.parquet")
    h2 = pd.read_csv(RESULTS_DIR / "h2_esg_specific.csv").set_index("outcome")
    summ = pd.read_csv(RESULTS_DIR / "summary.csv")

    summary_rows, curve_rows = [], []

    def _add(target, outcome, estimate, se, dpre):
        m_star = breakdown_m(estimate, se, dpre)
        summary_rows.append({
            "target": target, "outcome": outcome, "estimate": estimate, "se": se,
            "delta_pre": dpre, "breakdown_M": m_star,
        })
        c = robust_bounds(estimate, se, dpre)
        c.insert(0, "target", target); c.insert(1, "outcome", outcome)
        curve_rows.append(c)

    for outcome in ("n_filers", "log_shares"):
        # the ESG-specific CONTRAST (headline quantity)
        diff = _contrast_event_study(es, outcome)
        _add("esg_specific", outcome,
             float(h2.loc[outcome, "esg_specific"]), float(h2.loc[outcome, "se"]),
             delta_pre(diff))
        # the ESG ARM on its own (the arm whose pre-trends fail)
        arm = summ[(summ["outcome"] == outcome) & (summ["arm"] == "esg")].iloc[0]
        esg_es = es[(es["estimator"] == "sun_abraham") & (es["arm"] == "esg")
                    & (es["outcome"] == outcome) & (es["control_pool"] == "matched_cem")]
        _add("esg_arm", outcome,
             float(arm["sa_post_matched"]), float(arm["sa_post_se_matched"]),
             delta_pre(esg_es[["event_time", "att"]]))

    return pd.DataFrame(summary_rows), pd.concat(curve_rows, ignore_index=True)


def main(panel_path: str = "data/processed/panel.parquet",
         *, n_draws: int = PLACEBO_DRAWS) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # A. power / MDE / equivalence
    power = _power_table()
    power.to_csv(RESULTS_DIR / "credibility_power.csv", index=False)

    # B. relative-magnitudes / honest DiD
    hd_summary, hd_curve = _honest_did_table()
    hd_summary.to_csv(RESULTS_DIR / "credibility_honest_did.csv", index=False)
    hd_curve.to_csv(RESULTS_DIR / "credibility_honest_did_curve.csv", index=False)

    # C. randomization / placebo-in-time (re-estimates; the slow part)
    panel = pd.read_parquet(panel_path)
    plac_rows, draw_frames = [], []
    for outcome in ("n_filers", "log_shares"):
        res = placebo_in_time(panel, outcome, arm="esg", n_draws=n_draws)
        draws = res.pop("draws")
        plac_rows.append(res)
        draw_frames.append(pd.DataFrame({"outcome": outcome, "post_att": draws}))
    pd.DataFrame(plac_rows).to_csv(RESULTS_DIR / "credibility_placebo.csv", index=False)
    pd.concat(draw_frames, ignore_index=True).to_parquet(
        RESULTS_DIR / "credibility_placebo_draws.parquet")

    # ── console summary ───────────────────────────────────────────────────────
    print("\nA. Power / MDE / equivalence (SESOI = 1/4 of the mechanical effect)")
    show = power[["family", "outcome", "estimate", "ci_lo", "ci_hi", "mde80",
                  "sesoi", "rules_out_meaningful"]]
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(show.to_string(index=False, float_format=lambda x: f"{x:.3g}"))

    print("\nB. Relative-magnitudes sensitivity (breakdown M* = violation, "
          "in units of the worst pre-period deviation, that admits 0)")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(hd_summary.to_string(index=False, float_format=lambda x: f"{x:.3g}"))

    print("\nC. Placebo-in-time randomization inference (ESG arm)")
    plac = pd.read_csv(RESULTS_DIR / "credibility_placebo.csv")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(plac.to_string(index=False, float_format=lambda x: f"{x:.3g}"))

    n_powered = int((power["rules_out_meaningful"] == True).sum())  # noqa: E712
    print(f"\n>> Null is well-powered (rules out a meaningful effect) for "
          f"{n_powered}/{len(power)} contrasts; see results/credibility_*.csv.")


if __name__ == "__main__":
    main()
