"""Phase 4 — pre-registered robustness battery.

Re-runs the headline Sun-Abraham windowed post-ATT (e = 0…+4) and the H2
ESG-specific contrast (ATT_ESG − ATT_S&P) under each perturbation named in
PREREGISTRATION.md (§ "Inference & robustness"), holding the others at the
credible baseline (matched CEM controls, full sample, post horizon 0…+4):

  1. alternative matching   : matched_cem (baseline) vs matched_psm; the full
                              clean-control pool is added as a Callaway-Sant'Anna
                              point estimate (see note below).
  2. alternative horizon    : post-ATT averaged over 0…+2 / 0…+4 / 0…+6 quarters
                              (the ±3/±6-quarter windows of the frozen plan),
                              recomputed from the *same* baseline fit's covariance.
  3. winsorise outcome 1/99 : clip the (level) outcome at its 1st/99th pctiles so
                              a few mega-cap firms cannot drive the ATT.
  4. exclude COVID quarters : drop 2020Q1-Q2 (q_idx 8081, 8082).
  5. treatment definition (a): drop the 177/334 ``ever_dropped`` ESG firms (the
                              non-absorbing-treatment robustness).

Pre-registered but NOT runnable here — stated honestly, never faked:
  * Sun-Abraham on the *full* clean-control pool: the saturated cohort×event
    design is a dense ~1.4 GB matrix on 95k controls, and the comparison is
    confounded anyway. The full-pool effect is instead reported via
    Callaway-Sant'Anna point estimates (matching the headline ``cs_post_full`` in
    results/summary.csv), with no aggregated SE/pre-trend for that row.
  * Treatment definition (b) "restrict the post window to before the first exit":
    the assembled panel persists ``ever_dropped`` but not a per-firm first-exit
    quarter, so this variant is recorded as not-estimable rather than approximated.

Headline reading: the H2 ESG-specific contrast stays ≤ 0 (ESG inclusion draws no
more institutional breadth/depth than a generic S&P 500 add) across every runnable
perturbation — the null is not an artefact of the baseline choices.

Run:  python -m src.estimate.robustness
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.estimate.did import (
    PRIMARY_OUTCOMES,
    RESULTS_DIR,
    run_callaway_santanna,
    run_sun_abraham,
)

COVID_QIDX = (8081, 8082)               # 2020Q1, 2020Q2 (q_idx = year*4 + quarter)

_NOT_RUNNABLE = (
    "Pre-registered robustness variants NOT estimable on the assembled data "
    "(recorded, not faked):\n"
    "  * Sun-Abraham on the full clean-control pool — the saturated cohort x event "
    "design is a dense ~1.4 GB matrix on ~95k controls; the full-pool effect is "
    "reported via Callaway-Sant'Anna point estimates instead (see robustness.csv "
    "rows with estimator=callaway_santanna, and cs_post_full in summary.csv).\n"
    "  * Treatment definition (b) 'restrict the post window to before the first "
    "exit' — the panel carries ever_dropped but not a per-firm first-exit quarter, "
    "so the censored-post variant cannot be built without re-deriving exit timing "
    "from the N-PORT membership diffs.\n"
)


def _window_att(res: dict, window: tuple[int, int]) -> tuple[float, float]:
    """Windowed post-ATT and its SE from a Sun-Abraham result, recomputed from the
    stored event-time coefficients and their delta-method covariance. With
    window == POST_WINDOW this reproduces ``res['post_att']`` / ``res['post_se']``
    exactly (verified in tests/test_robustness.py)."""
    events = res["events"]
    att = res["event_study"]["att"].to_numpy()
    cov = np.asarray(res["cov"], dtype=float)
    lo, hi = window
    idx = [i for i, e in enumerate(events) if lo <= e <= hi]
    if not idx:
        return float("nan"), float("nan")
    w = np.zeros(len(events))
    w[idx] = 1.0 / len(idx)
    return float(w @ att), float(np.sqrt(max(w @ cov @ w, 0.0)))


def _contrast(esg_res: dict, sp_res: dict,
              window: tuple[int, int] = (0, 4)) -> dict:
    """H2 ESG-specific contrast (ATT_ESG − ATT_S&P) over ``window``; independent-
    arm SE (the matched control pools are largely disjoint). 'supported' uses the
    pre-registered rule: diff > 0, p < 0.05, AND the ESG pre-trends test passes."""
    from scipy import stats
    a_e, s_e = _window_att(esg_res, window)
    a_s, s_s = _window_att(sp_res, window)
    diff = a_e - a_s
    se = float(np.hypot(s_e, s_s))
    z = diff / se if se > 0 else np.nan
    p = float(2 * stats.norm.sf(abs(z))) if np.isfinite(z) else np.nan
    return {
        "att_esg": a_e, "se_esg": s_e,
        "esg_pretrend_pass": esg_res["pre_trends"]["passes"],
        "att_sp": a_s, "se_sp": s_s,
        "sp_pretrend_pass": sp_res["pre_trends"]["passes"],
        "esg_specific": diff, "se_diff": se, "z": z, "p_value": p,
        "supported": bool(diff > 0 and np.isfinite(p) and p < 0.05
                          and esg_res["pre_trends"]["passes"]),
    }


def _winsorize(panel: pd.DataFrame, outcome: str,
               lo: float = 0.01, hi: float = 0.99) -> pd.DataFrame:
    """Copy of ``panel`` with ``outcome`` clipped to its [lo, hi] quantiles."""
    p = panel.copy()
    s = pd.to_numeric(p[outcome], errors="coerce")
    p[outcome] = s.clip(s.quantile(lo), s.quantile(hi))
    return p


def run_battery(panel: pd.DataFrame) -> pd.DataFrame:
    """The full robustness sweep → one tidy DataFrame (rows = variants)."""
    rows: list[dict] = []

    for outcome in PRIMARY_OUTCOMES:
        esg_b = run_sun_abraham(panel, outcome, arm="esg", control_pool="matched_cem")
        sp_b = run_sun_abraham(panel, outcome, arm="sp500", control_pool="matched_cem")

        def add(check, variant, esg_res, sp_res, *, window=(0, 4),
                estimator="sun_abraham", control_pool="matched_cem"):
            rows.append({
                "check": check, "variant": variant, "estimator": estimator,
                "outcome": outcome, "control_pool": control_pool,
                "post_window": f"{window[0]}..{window[1]}",
                **_contrast(esg_res, sp_res, window),
                "n_treated_esg": esg_res["n_treated"],
                "n_treated_sp": sp_res["n_treated"],
            })

        # 0. baseline + 2. alternative horizons (same fit, different averaging window)
        add("baseline", "matched_cem, post 0..4", esg_b, sp_b, window=(0, 4))
        add("horizon", "post 0..2", esg_b, sp_b, window=(0, 2))
        add("horizon", "post 0..6", esg_b, sp_b, window=(0, 6))

        # 1. alternative matching — PSM
        esg_p = run_sun_abraham(panel, outcome, arm="esg", control_pool="matched_psm")
        sp_p = run_sun_abraham(panel, outcome, arm="sp500", control_pool="matched_psm")
        add("matching", "matched_psm", esg_p, sp_p, control_pool="matched_psm")

        # 3. winsorise the level outcome at 1/99
        pw = _winsorize(panel, outcome)
        esg_w = run_sun_abraham(pw, outcome, arm="esg", control_pool="matched_cem")
        sp_w = run_sun_abraham(pw, outcome, arm="sp500", control_pool="matched_cem")
        add("winsorise", "level outcome 1/99", esg_w, sp_w)

        # 4. exclude the COVID crisis quarters
        pc = panel[~panel["q_idx"].isin(COVID_QIDX)].copy()
        esg_c = run_sun_abraham(pc, outcome, arm="esg", control_pool="matched_cem")
        sp_c = run_sun_abraham(pc, outcome, arm="sp500", control_pool="matched_cem")
        add("exclude_covid", "drop 2020Q1-Q2", esg_c, sp_c)

        # 5. treatment definition (a): drop ever-dropped ESG firms (S&P arm unchanged)
        pe = panel.copy()
        pe.loc[pe["treated"].to_numpy(bool) & pe["ever_dropped"].to_numpy(bool),
               "treated"] = False
        esg_e = run_sun_abraham(pe, outcome, arm="esg", control_pool="matched_cem")
        add("treatment_def", "drop ever_dropped (ESG arm)", esg_e, sp_b)

        # 1b. full clean-control pool via Callaway-Sant'Anna (SA infeasible on full)
        cs_e = run_callaway_santanna(panel, outcome, arm="esg", control_pool="full")
        cs_s = run_callaway_santanna(panel, outcome, arm="sp500", control_pool="full")
        rows.append({
            "check": "matching", "variant": "full pool (CS point est.)",
            "estimator": "callaway_santanna", "outcome": outcome,
            "control_pool": "full", "post_window": "0..4",
            "att_esg": cs_e["post_att"], "se_esg": np.nan, "esg_pretrend_pass": None,
            "att_sp": cs_s["post_att"], "se_sp": np.nan, "sp_pretrend_pass": None,
            "esg_specific": cs_e["post_att"] - cs_s["post_att"], "se_diff": np.nan,
            "z": np.nan, "p_value": np.nan, "supported": None,
            "n_treated_esg": cs_e["n_treated"], "n_treated_sp": cs_s["n_treated"],
        })

    return pd.DataFrame(rows)


def main(panel_path: str = "data/processed/panel.parquet") -> None:
    panel = pd.read_parquet(panel_path)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df = run_battery(panel)
    df.to_csv(RESULTS_DIR / "robustness.csv", index=False)
    (RESULTS_DIR / "robustness_notes.txt").write_text(_NOT_RUNNABLE)

    pd.set_option("display.width", 200, "display.max_columns", 30)
    for outcome in PRIMARY_OUTCOMES:
        d = df[df["outcome"] == outcome]
        print(f"\n=== {outcome} : H2 ESG-specific = ATT(ESG) - ATT(S&P) ===")
        for _, r in d.iterrows():
            es = r["esg_specific"]
            se = r["se_diff"]
            setxt = f"se {se:6.3f}" if np.isfinite(se) else "se   n/a"
            ptxt = f"p={r['p_value']:.3f}" if np.isfinite(r["p_value"]) else "p= n/a "
            print(f"  {r['check']:14s} {r['variant']:26s} "
                  f"ATT_esg={r['att_esg']:+8.3f}  ATT_sp={r['att_sp']:+8.3f}  "
                  f"esg-specific={es:+8.3f} ({setxt}, {ptxt})")
    print(f"\n{_NOT_RUNNABLE}")
    print(f"Robustness written to {RESULTS_DIR}/robustness.csv")


if __name__ == "__main__":
    main()
