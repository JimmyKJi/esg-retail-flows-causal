"""Phase 3 — heterogeneity-robust staggered-adoption DiD.

Inclusions occur on different dates, so a naive two-way FE estimator is biased
under treatment-effect heterogeneity (Goodman-Bacon 2021). We therefore use
heterogeneity-robust estimators as the headline and keep TWFE only as a labelled
comparison.

Estimators
----------
* Callaway & Sant'Anna (2021) group-time ATT(g,t) via the `differences`
  package, aggregated to a dynamic event study .........................  HEADLINE
* Sun & Abraham (2021) interaction-weighted event study — a saturated
  cohort x event-time regression via `pyfixest`, then cohort-share weighted
  aggregation with a delta-method covariance ...........................  HEADLINE (cross-check)
* Two-way FE event study via `pyfixest` `i(event_time)` ...............  NAIVE BASELINE
  (reported for the Goodman-Bacon contrast; NOT the headline)

Control pools
-------------
* ``full``        : every clean (never-treated) control — the *pre-registered*
                    headline comparison. Treated firms are large; the full pool
                    is dominated by small firms on a steep secular institutional-
                    ownership uptrend, so level comparisons are confounded and the
                    pre-trends test fails. Reported transparently.
* ``matched_cem`` / ``matched_psm`` : size/pre-ownership-matched controls
                    (Phase 2b). The *credible* comparison; pre-trends clean.
The pre-registration anticipated this and named matching as the robustness that
addresses the population mismatch — here it is the load-bearing specification.

Outcomes (frozen pre-registration)
----------------------------------
breadth  : ``n_filers``   (level)      depth : ``log_shares`` (level)
secondary: ``log_value``  (level)
All estimators run on *levels*; each differences the outcome internally relative
to the reference period g-1 (event time -1). Shares/breadth are unit-immune to
the 2023 13F VALUE reporting change; ``log_value`` is secondary for that reason.

Arms
----
esg    : ``treated`` / ``cohort_q_idx``          ; controls = ``clean_control``
sp500  : ``sp500_treated`` & ~``both_treated``   ; controls = ~``sp500_member_ever``
         (primary placebo = 65 S&P-only adds; the 58 ``both_treated`` firms whose
         inclusion conflates the two shocks are excluded — see PREREGISTRATION.md)

Hypotheses
----------
H1 inclusion -> flows : ATT(e) > 0 for e >= 0 on breadth & depth.
H2 ESG-specific       : ATT(ESG) - ATT(S&P) > 0      -> ``esg_specific_contrast``.
H3 decay post-2022    : ATT(late cohorts) < ATT(early cohorts), split at 2022Q1
                        -> ``decay_split``.
H4 heterogeneity      : not estimable from the FROZEN panel directly (it holds
                        cusip x quarter aggregates, so per-filer manager CIK is
                        unavailable). Estimated in Phase 5 by re-ingesting the raw
                        13F INFOTABLE keyed by CIK (``src.ingest.edgar_13f_byfiler``)
                        and re-running the placebo contrast per filer type
                        (``src.estimate.h4_filer``) -> ``make heterogeneity``.

A mandatory pre-trends joint Wald test (event times {-4,-3,-2} == 0) must pass
before any coefficient is trusted; if it fails we prefer the heterogeneity-robust
estimates and say so plainly (PREREGISTRATION.md decision rule).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ── Pre-registered constants ──────────────────────────────────────────────────
PRIMARY_OUTCOMES = ("n_filers", "log_shares")
SECONDARY_OUTCOMES = ("log_value",)
ALL_OUTCOMES = PRIMARY_OUTCOMES + SECONDARY_OUTCOMES
DISPLAY_WINDOW = (-4, 6)           # event-time range shown in tables/figures
POST_WINDOW = (0, 4)               # pre-registered window for the summary ATT
PRE_PERIODS = (-4, -3, -2)         # tested jointly == 0 (reference is -1)
Q_2022Q1 = 2022 * 4 + 1            # = 8089; the post-2022 cohort split for H3
PROC_DIR = Path("data/processed")
RESULTS_DIR = Path("results")

H4_NOTE = (
    "H4 (passive/active and ESG-badged filer heterogeneity) is not estimable from "
    "the frozen panel directly: it holds cusip x quarter aggregates, so per-filer "
    "manager (CIK) identity is unavailable. It is estimated in Phase 5 by "
    "re-ingesting the raw 13F INFOTABLE keyed by filer CIK "
    "(src.ingest.edgar_13f_byfiler) and re-running the placebo contrast per filer "
    "type (src.estimate.h4_filer); run `make heterogeneity` -> results/h4_filer.csv."
)

_ARMS: dict[str, dict] = {
    "esg": {
        "treated": "treated",
        "cohort": "cohort_q_idx",
        "control": lambda d: d["clean_control"].to_numpy(bool),
        "exclude": None,
    },
    "sp500": {
        "treated": "sp500_treated",
        "cohort": "sp500_cohort_q_idx",
        "control": lambda d: ~d["sp500_member_ever"].to_numpy(bool),
        "exclude": "both_treated",   # drop firms that are also ESG-treated
    },
}


# ── Frame construction ────────────────────────────────────────────────────────
def _matched_control_cusips(arm: str, method: str) -> set[str]:
    path = PROC_DIR / f"matched_{arm}_{method}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `make matched` (src.build.matching) first.")
    m = pd.read_parquet(path)
    return set(m.loc[m["role"] == "control", "cusip"].astype(str))


def build_frame(panel: pd.DataFrame, arm: str, outcome: str,
                *, control_pool: str = "full",
                cohort_subset: str | None = None) -> pd.DataFrame:
    """Tidy estimation frame for one arm/outcome/control-pool.

    Columns: cusip, q_idx, <outcome>, g (cohort q_idx; NaN = never treated),
    event_time (NaN for controls), treated_unit (bool). Rows with a missing
    outcome are dropped. ``control_pool`` is ``"full"`` (all clean controls) or
    ``"matched_cem"``/``"matched_psm"`` (restrict to matched controls).
    ``cohort_subset`` (``"early"``/``"late"``) keeps only treated cohorts before /
    on-or-after 2022Q1 (controls always retained) for the H3 decay split.
    """
    if arm not in _ARMS:
        raise ValueError(f"unknown arm {arm!r}; choose from {tuple(_ARMS)}")
    if outcome not in panel.columns:
        raise ValueError(f"outcome {outcome!r} not in panel")
    cfg = _ARMS[arm]
    treated = panel[cfg["treated"]].to_numpy(bool)
    if cfg["exclude"]:
        treated = treated & ~panel[cfg["exclude"]].to_numpy(bool)
    control = cfg["control"](panel)
    if control_pool != "full":
        method = control_pool.split("_", 1)[1]          # matched_cem -> cem
        mc = _matched_control_cusips(arm, method)
        control = control & panel["cusip"].astype(str).isin(mc).to_numpy()

    g_all = pd.to_numeric(panel[cfg["cohort"]], errors="coerce").to_numpy(float)
    if cohort_subset == "early":
        treated = treated & (g_all < Q_2022Q1)
    elif cohort_subset == "late":
        treated = treated & (g_all >= Q_2022Q1)

    keep = treated | control
    f = panel.loc[keep, ["cusip", "q_idx", outcome]].copy()
    tre = treated[keep]
    g = np.where(tre, g_all[keep], np.nan)              # controls -> never (NaN)
    f["g"] = g
    f["treated_unit"] = tre
    f["event_time"] = np.where(np.isfinite(g), f["q_idx"].to_numpy() - g, np.nan)
    return f.dropna(subset=[outcome]).reset_index(drop=True)


def _post_point(ev: pd.DataFrame, window: tuple[int, int] = POST_WINDOW) -> float:
    lo, hi = window
    m = ev[(ev["event_time"] >= lo) & (ev["event_time"] <= hi)]
    return float(m["att"].mean()) if len(m) else np.nan


# ── Callaway & Sant'Anna (HEADLINE dynamics) ──────────────────────────────────
def run_callaway_santanna(panel: pd.DataFrame, outcome: str = "n_filers",
                          arm: str = "esg", *, control_pool: str = "full",
                          est_method: str = "reg",
                          cohort_subset: str | None = None) -> dict:
    """Group-time ATT(g,t) aggregated to a dynamic event study (never-treated
    comparison). Analytic influence-function SEs (clustered by firm)."""
    from differences import ATTgt

    f = build_frame(panel, arm, outcome, control_pool=control_pool,
                    cohort_subset=cohort_subset)
    dd = (f[["cusip", "q_idx", outcome, "g"]]
          .set_index(["cusip", "q_idx"]).sort_index())
    att = ATTgt(data=dd, cohort_column="g")
    att.fit(formula=outcome, control_group="never_treated",
            est_method=est_method, progress_bar=False)

    ev = att.aggregate("event")
    ev.columns = ["att", "se", "lo", "hi", "sig"]
    ev = ev.reset_index()
    ev.columns = ["event_time", "att", "se", "lo", "hi", "sig"]
    ev["event_time"] = ev["event_time"].astype(int)
    lo, hi = DISPLAY_WINDOW
    ev = ev[(ev["event_time"] >= lo) & (ev["event_time"] <= hi)].reset_index(drop=True)

    return {
        "estimator": "callaway_santanna", "arm": arm, "outcome": outcome,
        "control_pool": control_pool, "cohort_subset": cohort_subset,
        "event_study": ev, "post_att": _post_point(ev),
        "n_treated": int(f.loc[f["treated_unit"], "cusip"].nunique()),
        "n_control": int(f.loc[~f["treated_unit"], "cusip"].nunique()),
    }


# ── Sun & Abraham (HEADLINE cross-check; carries windowed inference) ───────────
def _coef_vcov(m):
    b = m.coef()
    names = list(b.index)
    V = getattr(m, "_vcov", None)
    if V is None and hasattr(m, "vcov"):
        vc = m.vcov()
        V = vc.values if hasattr(vc, "values") else vc
    return b, np.asarray(V, dtype=float), names


def _sa_cell(g: int, e: int) -> str:
    """Hyphen-free cohort x event-time dummy name. A literal ``-`` in a column
    name is read as subtraction by the formula parser (formulaic), so negative
    event times are encoded ``m`` (minus) and non-negative ``p`` (plus):
    e=-3 -> ``d_g{g}_em3``; e=2 -> ``d_g{g}_ep2``."""
    return f"d_g{g}_e{'m' if e < 0 else 'p'}{abs(e)}"


def run_sun_abraham(panel: pd.DataFrame, outcome: str = "n_filers",
                    arm: str = "esg", *, control_pool: str = "matched_cem",
                    window: tuple[int, int] = DISPLAY_WINDOW,
                    cohort_subset: str | None = None) -> dict:
    """Interaction-weighted event study (Sun & Abraham 2021): a saturated
    cohort x event-time regression (ref e=-1), firm and quarter FE, SEs clustered
    by firm; cohort-share weighted aggregation to ATT(e) with a delta-method
    covariance (which also drives the windowed ATT and the pre-trends test).

    Defaults to a matched control pool: on the full pool the saturated design
    is a dense ~1.4 GB matrix (and the comparison is confounded anyway)."""
    import pyfixest as pf

    lo, hi = window
    f = build_frame(panel, arm, outcome, control_pool=control_pool,
                    cohort_subset=cohort_subset)
    f["e"] = np.where(np.isfinite(f["event_time"]),
                      np.clip(f["event_time"], lo, hi), np.nan)
    treated = f[f["treated_unit"]]
    cohorts = sorted(int(g) for g in treated["g"].dropna().unique())

    cells, newcols = [], {}
    for g in cohorts:
        for e in range(lo, hi + 1):
            if e == -1:
                continue
            v = ((f["g"] == g) & (f["e"] == e)).astype(float)
            if v.sum() > 0:                      # skip empty cohort x event cells
                col = _sa_cell(g, e)
                newcols[col] = v
                cells.append(col)
    f = pd.concat([f, pd.DataFrame(newcols, index=f.index)], axis=1)  # one block
    m = pf.feols(f"{outcome} ~ {' + '.join(cells)} | cusip + q_idx",
                 data=f, vcov={"CRV1": "cusip"})
    b, V, names = _coef_vcov(m)
    idx = {n: i for i, n in enumerate(names)}

    cnt = (treated.assign(e=np.clip(treated["event_time"], lo, hi))
           .groupby(["e", "g"]).size())
    events = [e for e in range(lo, hi + 1) if e != -1]
    A = np.zeros((len(events), len(names)))
    for r, e in enumerate(events):
        # Weight only over cohort cells that are estimable (survived pyfixest's
        # collinearity drops). Normalising by the full cohort count would put
        # weight on dropped cells and bias att(e) toward 0 — and at least one
        # dropped cell (e.g. d_g8090_ep2) sits in the post-window, so it would
        # contaminate the headline.
        gw = {g: cnt.get((e, g), 0) for g in cohorts if _sa_cell(g, e) in idx}
        tot = sum(gw.values())
        if not tot:
            continue
        for g, wgt in gw.items():
            if wgt:
                A[r, idx[_sa_cell(g, e)]] = wgt / tot

    bb = b.to_numpy()
    att = A @ bb
    cov = A @ V @ A.T
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    ev = pd.DataFrame({"event_time": events, "att": att, "se": se})
    ev["lo"] = att - 1.96 * se
    ev["hi"] = att + 1.96 * se
    ev["sig"] = np.where((ev["lo"] > 0) | (ev["hi"] < 0), "*", "")

    plo, phi = POST_WINDOW
    post = [i for i, e in enumerate(events) if plo <= e <= phi]
    w = np.zeros(len(events)); w[post] = 1.0 / len(post)
    post_att = float(w @ att)
    post_se = float(np.sqrt(w @ cov @ w))

    return {
        "estimator": "sun_abraham", "arm": arm, "outcome": outcome,
        "control_pool": control_pool, "cohort_subset": cohort_subset,
        "event_study": ev, "cov": cov, "events": events,
        "post_att": post_att, "post_se": post_se,
        "pre_trends": pre_trends_test(ev, cov, events),
        "n_treated": int(treated["cusip"].nunique()),
        "n_control": int(f.loc[~f["treated_unit"], "cusip"].nunique()),
    }


# ── Naive TWFE event study (NOT headline) ─────────────────────────────────────
def run_twfe_event_study(panel: pd.DataFrame, outcome: str = "n_filers",
                         arm: str = "esg", *, control_pool: str = "full",
                         window: tuple[int, int] = DISPLAY_WINDOW) -> dict:
    """Two-way FE event study via `i(event_time, ref=-1)`. Biased under
    heterogeneity (Goodman-Bacon) — a comparison, not the headline. Full vcov
    yields a windowed post-ATT and the pre-trends test for this spec."""
    import pyfixest as pf

    lo, hi = window
    f = build_frame(panel, arm, outcome, control_pool=control_pool)
    f["et"] = np.where(np.isfinite(f["event_time"]),
                       np.clip(f["event_time"], lo, hi), -1).astype(int)
    m = pf.feols(f"{outcome} ~ i(et, ref=-1) | cusip + q_idx",
                 data=f, vcov={"CRV1": "cusip"})
    b, V, names = _coef_vcov(m)
    et = np.array([int(n.split("::")[1]) for n in names])
    order = np.argsort(et)
    et, b2, names = et[order], b.to_numpy()[order], [names[i] for i in order]
    V = V[np.ix_(order, order)]
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    ev = pd.DataFrame({"event_time": et, "att": b2, "se": se})
    ev["lo"] = b2 - 1.96 * se
    ev["hi"] = b2 + 1.96 * se
    ev["sig"] = np.where((ev["lo"] > 0) | (ev["hi"] < 0), "*", "")
    events = list(et)
    return {
        "estimator": "twfe", "arm": arm, "outcome": outcome,
        "control_pool": control_pool, "event_study": ev, "cov": V, "events": events,
        "post_att": _post_point(ev),
        "pre_trends": pre_trends_test(ev, V, events),
        "n_treated": int(f.loc[f["treated_unit"], "cusip"].nunique()),
        "n_control": int(f.loc[~f["treated_unit"], "cusip"].nunique()),
    }


# ── Mandatory pre-trends test ─────────────────────────────────────────────────
def pre_trends_test(event_study: pd.DataFrame, cov: np.ndarray,
                    events: list[int], pre: tuple[int, ...] = PRE_PERIODS) -> dict:
    """Joint Wald test that pre-period event-time ATTs == 0. W = b'V^{-1}b ~
    chi2(k). Parallel pre-trends are *not rejected* (test passes) when p >= 0.05."""
    from scipy import stats

    pos = [i for i, e in enumerate(events) if e in pre]
    if not pos:
        return {"stat": np.nan, "df": 0, "p_value": np.nan, "passes": None,
                "pre_periods": list(pre)}
    b = event_study["att"].to_numpy()[pos]
    V = np.asarray(cov)[np.ix_(pos, pos)]
    try:
        W = float(b @ np.linalg.solve(V, b))
    except np.linalg.LinAlgError:
        W = float(b @ np.linalg.pinv(V) @ b)
    df = len(pos)
    p = float(stats.chi2.sf(W, df))
    return {"stat": W, "df": df, "p_value": p, "passes": bool(p >= 0.05),
            "pre_periods": list(pre)}


# ── H2: ESG-specific effect (ESG vs S&P placebo) ──────────────────────────────
def esg_specific_contrast(panel: pd.DataFrame, outcome: str = "n_filers",
                          *, control_pool: str = "matched_cem") -> dict:
    """H2: ATT(ESG) - ATT(S&P), Sun-Abraham windowed post-ATT per arm. The arms
    are separate fits on (largely disjoint) matched control pools, so the contrast
    SE uses the independent-arm approximation. Holds iff the difference > 0."""
    from scipy import stats
    esg = run_sun_abraham(panel, outcome, arm="esg", control_pool=control_pool)
    sp = run_sun_abraham(panel, outcome, arm="sp500", control_pool=control_pool)
    diff = esg["post_att"] - sp["post_att"]
    se = float(np.hypot(esg["post_se"], sp["post_se"]))
    z = diff / se if se > 0 else np.nan
    p = float(2 * stats.norm.sf(abs(z))) if np.isfinite(z) else np.nan
    return {
        "outcome": outcome, "control_pool": control_pool,
        "att_esg": esg["post_att"], "se_esg": esg["post_se"],
        "att_sp500": sp["post_att"], "se_sp500": sp["post_se"],
        "esg_specific": diff, "se": se, "z": z, "p_value": p,
        "esg_pretrend_pass": esg["pre_trends"]["passes"],
        "sp_pretrend_pass": sp["pre_trends"]["passes"],
        "supported": bool(diff > 0 and np.isfinite(p) and p < 0.05
                          and esg["pre_trends"]["passes"]),
    }


# ── H3: legitimacy decay (early vs late cohorts) ──────────────────────────────
def decay_split(panel: pd.DataFrame, outcome: str = "n_filers",
                *, control_pool: str = "matched_cem") -> dict:
    """H3: ESG ATT for cohorts before vs on/after 2022Q1 (Sun-Abraham windowed
    post-ATT). Decay holds iff ATT(late) - ATT(early) < 0. Independent-subset SE
    approximation (the treated cohort sets are disjoint)."""
    from scipy import stats
    early = run_sun_abraham(panel, outcome, arm="esg",
                            control_pool=control_pool, cohort_subset="early")
    late = run_sun_abraham(panel, outcome, arm="esg",
                           control_pool=control_pool, cohort_subset="late")
    diff = late["post_att"] - early["post_att"]
    se = float(np.hypot(early["post_se"], late["post_se"]))
    z = diff / se if se > 0 else np.nan
    p = float(2 * stats.norm.sf(abs(z))) if np.isfinite(z) else np.nan
    return {
        "outcome": outcome, "control_pool": control_pool, "split": "2022Q1",
        "att_early": early["post_att"], "se_early": early["post_se"],
        "att_late": late["post_att"], "se_late": late["post_se"],
        "decay": diff, "se": se, "z": z, "p_value": p,
        "supported": bool(diff < 0 and np.isfinite(p) and p < 0.05),
    }


# ── Orchestration ─────────────────────────────────────────────────────────────
def main(panel_path: str = "data/processed/panel.parquet") -> None:
    """Run the frozen Phase-3 battery and persist tidy results to results/."""
    panel = pd.read_parquet(panel_path)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "figures").mkdir(exist_ok=True)

    es_rows, summary_rows = [], []

    def _stash(res):
        ev = res["event_study"].copy()
        ev.insert(0, "estimator", res["estimator"])
        ev.insert(1, "arm", res["arm"])
        ev.insert(2, "outcome", res["outcome"])
        ev.insert(3, "control_pool", res["control_pool"])
        es_rows.append(ev)

    for outcome in ALL_OUTCOMES:
        for arm in ("esg", "sp500"):
            # full pool (pre-registered headline): CS dynamics + naive TWFE
            cs_f = run_callaway_santanna(panel, outcome, arm=arm, control_pool="full")
            tw_f = run_twfe_event_study(panel, outcome, arm=arm, control_pool="full")
            _stash(cs_f); _stash(tw_f)
            # matched pool (credible): CS + SA + TWFE
            cs_m = run_callaway_santanna(panel, outcome, arm=arm, control_pool="matched_cem")
            sa_m = run_sun_abraham(panel, outcome, arm=arm, control_pool="matched_cem")
            tw_m = run_twfe_event_study(panel, outcome, arm=arm, control_pool="matched_cem")
            _stash(cs_m); _stash(sa_m); _stash(tw_m)
            summary_rows.append({
                "outcome": outcome, "arm": arm,
                "cs_post_full": cs_f["post_att"],
                "twfe_pretrend_p_full": tw_f["pre_trends"]["p_value"],
                "twfe_pretrend_pass_full": tw_f["pre_trends"]["passes"],
                "cs_post_matched": cs_m["post_att"],
                "sa_post_matched": sa_m["post_att"], "sa_post_se_matched": sa_m["post_se"],
                "sa_pretrend_p_matched": sa_m["pre_trends"]["p_value"],
                "sa_pretrend_pass_matched": sa_m["pre_trends"]["passes"],
                "n_treated": cs_m["n_treated"],
                "n_ctrl_full": cs_f["n_control"], "n_ctrl_matched": cs_m["n_control"],
            })
            print(f"[{outcome:10s} {arm:5s}] "
                  f"full CS post={cs_f['post_att']:+8.3f} (pretrend "
                  f"{'PASS' if tw_f['pre_trends']['passes'] else 'FAIL'} "
                  f"p={tw_f['pre_trends']['p_value']:.3f}) | "
                  f"matched SA post={sa_m['post_att']:+7.3f} ({sa_m['post_se']:.3f}) "
                  f"pretrend {'PASS' if sa_m['pre_trends']['passes'] else 'FAIL'} "
                  f"p={sa_m['pre_trends']['p_value']:.3f}")

    h2 = [esg_specific_contrast(panel, o) for o in PRIMARY_OUTCOMES]
    h3 = [decay_split(panel, o) for o in PRIMARY_OUTCOMES]

    pd.concat(es_rows, ignore_index=True).to_parquet(RESULTS_DIR / "event_studies.parquet")
    pd.DataFrame(summary_rows).to_csv(RESULTS_DIR / "summary.csv", index=False)
    pd.DataFrame(h2).to_csv(RESULTS_DIR / "h2_esg_specific.csv", index=False)
    pd.DataFrame(h3).to_csv(RESULTS_DIR / "h3_decay.csv", index=False)
    # H4 is produced by the Phase-5 pipeline (`make heterogeneity` ->
    # results/h4_filer.csv), not here — see H4_NOTE.

    print("\nH2 ESG-specific (ATT_ESG - ATT_S&P, matched, SA):")
    for r in h2:
        print(f"  {r['outcome']:10s}: {r['esg_specific']:+.3f} (se {r['se']:.3f}, "
              f"p={r['p_value']:.3f}) {'SUPPORTED' if r['supported'] else 'not supported'}")
    print("H3 decay (ATT_late - ATT_early, split 2022Q1, matched, SA):")
    for r in h3:
        print(f"  {r['outcome']:10s}: {r['decay']:+.3f} (se {r['se']:.3f}, "
              f"p={r['p_value']:.3f}) {'SUPPORTED' if r['supported'] else 'not supported'}")
    print(f"\nH4: {H4_NOTE}")
    print(f"\nResults written to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
