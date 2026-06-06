"""Matched control construction (Phase 2b).

For each treated firm we pick non-included controls matched on *pre-treatment*
characteristics, then hand the matched sample to the staggered-DiD estimator as
a robustness arm alongside the full clean-control design. The identical routine
serves the ESG-Leaders inclusions and the S&P 500 *placebo* inclusions (select
the arm with ``arm="esg"`` / ``arm="sp500"``), so the two designs are matched
symmetrically and their ATTs are comparable.

Design choices that matter for identification:

  * **Baseline = the quarter before the cohort (g−1).** Covariates for a treated
    firm and its candidate controls are read at the *same calendar quarter*
    g−1, so any common calendar/level confounding is differenced away by the
    match itself — we never compare a treated firm's 2020 snapshot to a
    control's 2023 snapshot. (A treated firm with no g−1 observation is dropped;
    these are the 2/334 firms with no pre-period.)

  * **Match on pre-period institutional ownership, the first-order confound.**
    The documented pre-trend (treated firms' breadth was already rising before
    inclusion) means the comparison group must look like the treated firms on
    *ownership level and size* at baseline. We use what the CUSIP-keyed panel
    carries directly: log aggregate institutional dollars held (``log_value``,
    a market-cap proxy), log shares held (``log_shares``), and the count of
    institutional holders (``n_filers``, breadth). Sector and a price-based
    liquidity measure are NOT in the panel (GICS is only free for current S&P
    members; liquidity needs a price/volume pull with a name→ticker bridge) —
    they are accepted as optional covariates when a caller joins them in, and
    their absence is a documented limitation, not a silent omission.

  * **Controls are never-treated for the arm.** ESG controls are the
    ``clean_control`` pool (never in the ESG index, excluding left-censored
    members and corp-action-suspect adds); placebo controls are firms never in
    the S&P 500 (``~sp500_member_ever``). Symmetric exclusion of ever-members.

Two methods: ``psm`` (a single pooled propensity model with baseline-quarter
fixed effects, then nearest-neighbour on the propensity logit within cohort)
and ``cem`` (coarsened exact matching on covariate quantile bins within cohort).
Matching is with replacement; control weights are 1/k so each treated firm's
matches sum to one. Match quality is reported as standardized mean differences
before/after — see ``match_balance`` — not assumed.

Run:  python -m src.build.matching
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.paths import DATA_PROCESSED

# Per-arm column wiring so the ESG and placebo designs run through one routine.
_ARMS = {
    "esg":   {"treated": "treated",       "cohort_qidx": "cohort_q_idx",
              "member_ever": "esg_member_ever"},
    "sp500": {"treated": "sp500_treated", "cohort_qidx": "sp500_cohort_q_idx",
              "member_ever": "sp500_member_ever"},
}
_DEFAULT_COVS = ("log_value", "log_shares", "n_filers")


def _baseline_panel(panel: pd.DataFrame, cfg: dict, covs: list[str]
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cross-sections at each cohort's baseline quarter (g−1).

    Returns (treated, pool): treated firms with their baseline covariates, and
    the eligible never-treated control pool observed at the same baseline
    quarters. Rows missing any covariate are dropped (can't match on a NaN).
    """
    tcol, qcol, mcol = cfg["treated"], cfg["cohort_qidx"], cfg["member_ever"]
    if tcol not in panel.columns:
        raise KeyError(f"panel has no '{tcol}' column — arm not built into this panel")

    cohort = (panel.loc[panel[tcol]].groupby("cusip")[qcol].first()
              .dropna().astype(int))
    if cohort.empty:
        raise ValueError(f"no treated firms for arm column '{tcol}'")
    base_q = cohort - 1

    snap_cols = ["cusip", "q_idx", *covs]
    snap = (panel.loc[panel["q_idx"].isin(base_q.unique()), snap_cols]
            .dropna(subset=covs))

    treated = (pd.DataFrame({"cusip": cohort.index,
                             "cohort_qidx": cohort.to_numpy(),
                             "baseline_qidx": base_q.to_numpy()})
               .merge(snap.rename(columns={"q_idx": "baseline_qidx"}),
                      on=["cusip", "baseline_qidx"]))
    treated["role"] = "treated"

    ctrl_cusips = panel.loc[(~panel[tcol]) & (~panel[mcol]), "cusip"].unique()
    pool = (snap[snap["cusip"].isin(ctrl_cusips)]
            .rename(columns={"q_idx": "baseline_qidx"}).copy())
    pool["role"] = "control"
    return treated, pool


def _fit_propensity(treated: pd.DataFrame, pool: pd.DataFrame, covs: list[str]
                    ) -> pd.DataFrame:
    """Pooled propensity (treated vs pool) with baseline-quarter fixed effects.

    One stable model across all cohorts beats a separate logit per small cohort;
    quarter dummies keep the score within-quarter comparable. Returns the stacked
    frame with a ``lps`` (propensity logit) column for nearest-neighbour matching.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    df = pd.concat([treated.assign(_t=1), pool.assign(_t=0)], ignore_index=True)
    x = StandardScaler().fit_transform(df[covs].to_numpy(dtype=float))
    q = pd.get_dummies(df["baseline_qidx"], prefix="q", drop_first=True).to_numpy(float)
    feat = np.hstack([x, q]) if q.size else x

    lr = LogisticRegression(max_iter=2000, C=1.0)
    lr.fit(feat, df["_t"].to_numpy())
    ps = np.clip(lr.predict_proba(feat)[:, 1], 1e-6, 1 - 1e-6)
    df["ps"] = ps
    df["lps"] = np.log(ps / (1 - ps))
    return df


def _match_psm(t: pd.DataFrame, c: pd.DataFrame, n_controls: int,
               caliper: float | None) -> list[dict]:
    """Nearest-neighbour on the propensity logit within one cohort (with replacement)."""
    out: list[dict] = []
    cl = c["lps"].to_numpy()
    for _, tr in t.iterrows():
        d = np.abs(cl - tr["lps"])
        order = np.argsort(d, kind="stable")
        if caliper is not None:
            order = order[d[order] <= caliper]
        order = order[:n_controls]
        k = len(order)
        out.append({**_row(tr, "treated", 0.0, 1.0)})
        for j in order:
            cc = c.iloc[j]
            out.append(_row(cc, "control", float(d[j]), 1.0 / k,
                            event_id=tr["cusip"], cohort_qidx=tr["cohort_qidx"]))
    return out


def _match_cem(t: pd.DataFrame, c: pd.DataFrame, covs: list[str],
               n_controls: int, n_bins: int) -> list[dict]:
    """Coarsened exact matching: same covariate quantile-bin stratum within cohort."""
    both = pd.concat([t[covs], c[covs]], ignore_index=True)
    edges = {v: np.unique(np.quantile(both[v], np.linspace(0, 1, n_bins + 1)))
             for v in covs}

    def strat(row) -> tuple:
        return tuple(int(np.clip(np.digitize(row[v], edges[v][1:-1]), 0, n_bins))
                     for v in covs)

    c = c.assign(_s=[strat(r) for _, r in c.iterrows()])
    out: list[dict] = []
    for _, tr in t.iterrows():
        s = strat(tr)
        cand = c[c["_s"].apply(lambda x: x == s)]
        if cand.empty:
            out.append(_row(tr, "treated", 0.0, 1.0, unmatched=True))
            continue
        # within stratum, take the n_controls closest on standardized covariates
        sd = both[covs].std(ddof=0).to_numpy(float) + 1e-9
        z = (cand[covs].to_numpy(float) - tr[covs].to_numpy(float)) / sd
        dist = np.sqrt((z ** 2).sum(axis=1))
        order = np.argsort(dist, kind="stable")[:n_controls]
        k = len(order)
        out.append(_row(tr, "treated", 0.0, 1.0))
        for rank, j in enumerate(order):
            cc = cand.iloc[j]
            out.append(_row(cc, "control", float(dist[j]), 1.0 / k,
                            event_id=tr["cusip"], cohort_qidx=tr["cohort_qidx"]))
    return out


def _row(r, role: str, distance: float, weight: float, *, event_id=None,
         cohort_qidx=None, unmatched: bool = False) -> dict:
    return {
        "event_id": event_id if event_id is not None else r["cusip"],
        "cohort_qidx": int(cohort_qidx if cohort_qidx is not None else r["cohort_qidx"]),
        "baseline_qidx": int(r["baseline_qidx"]),
        "role": role,
        "cusip": r["cusip"],
        "distance": distance,
        "weight": weight,
        "ps": float(r.get("ps", np.nan)) if hasattr(r, "get") else np.nan,
        "unmatched": unmatched,
    }


def build_matched_controls(
    panel: pd.DataFrame,
    events: pd.DataFrame | None = None,   # kept for signature compat; cohorts come from panel
    n_controls: int = 5,
    method: str = "psm",                  # "psm" | "cem"
    *,
    arm: str = "esg",                     # "esg" | "sp500"
    covariates: tuple[str, ...] = _DEFAULT_COVS,
    caliper: float | None = None,         # psm: max |Δ propensity-logit|
    n_bins: int = 4,                      # cem: quantile bins per covariate
) -> pd.DataFrame:
    """Return treated+matched-control rows tagged by ``event_id`` and ``role``.

    Columns: event_id (the treated CUSIP), cohort_qidx, baseline_qidx, role
    ('treated'|'control'), cusip, distance, weight (treated=1, controls 1/k),
    ps, unmatched, arm, method. Matching is per-cohort at the baseline quarter
    g−1 and symmetric across arms.
    """
    if arm not in _ARMS:
        raise ValueError(f"arm must be one of {sorted(_ARMS)}")
    if method not in {"psm", "cem"}:
        raise ValueError("method must be 'psm' or 'cem'")
    covs = list(covariates)

    treated, pool = _baseline_panel(panel, _ARMS[arm], covs)
    if method == "psm":
        stacked = _fit_propensity(treated, pool, covs)
        treated = stacked[stacked["_t"] == 1]
        pool = stacked[stacked["_t"] == 0]

    rows: list[dict] = []
    for bq, t in treated.groupby("baseline_qidx"):
        c = pool[pool["baseline_qidx"] == bq]
        if c.empty:
            rows += [_row(tr, "treated", 0.0, 1.0, unmatched=True) for _, tr in t.iterrows()]
            continue
        rows += (_match_psm(t, c, n_controls, caliper) if method == "psm"
                 else _match_cem(t, c, covs, n_controls, n_bins))

    out = pd.DataFrame(rows)
    out["arm"] = arm
    out["method"] = method
    return out.reset_index(drop=True)


def match_balance(panel: pd.DataFrame, matched: pd.DataFrame,
                  covariates: tuple[str, ...] = _DEFAULT_COVS,
                  arm: str = "esg") -> pd.DataFrame:
    """Standardized mean differences (treated − control) before vs after matching.

    |SMD| < 0.1 is the conventional "balanced" threshold. 'before' uses the full
    eligible pool; 'after' uses the weighted matched controls.
    """
    covs = list(covariates)
    treated, pool = _baseline_panel(panel, _ARMS[arm], covs)
    base = matched.merge(
        pd.concat([treated[["cusip", "baseline_qidx", *covs]],
                   pool[["cusip", "baseline_qidx", *covs]]]).drop_duplicates(),
        on=["cusip", "baseline_qidx"], how="left")

    t_all = treated[covs]
    c_all = pool[covs]
    mt = base[base["role"] == "treated"]
    mc = base[base["role"] == "control"]

    def smd(a_mean, b_mean, a, b):
        sd = np.sqrt((a.var(ddof=0) + b.var(ddof=0)) / 2) + 1e-12
        return (a_mean - b_mean) / sd

    rows = []
    for v in covs:
        before = smd(t_all[v].mean(), c_all[v].mean(), t_all[v], c_all[v])
        wc = np.average(mc[v], weights=mc["weight"]) if len(mc) else np.nan
        after = smd(mt[v].mean(), wc, t_all[v], c_all[v])
        rows.append({"covariate": v, "smd_before": before, "smd_after": after})
    return pd.DataFrame(rows)


def main() -> None:
    panel = pd.read_parquet(DATA_PROCESSED / "panel.parquet")
    for arm in ("esg", "sp500"):
        if _ARMS[arm]["treated"] not in panel.columns:
            print(f"[matching] arm '{arm}' not in panel — skipped")
            continue
        for method in ("psm", "cem"):
            m = build_matched_controls(panel, n_controls=5, method=method, arm=arm)
            n_ev = m.loc[m["role"] == "treated", "event_id"].nunique()
            n_unmatched = int(m.loc[m["role"] == "treated", "unmatched"].sum())
            n_ctrl = int((m["role"] == "control").sum())
            out = DATA_PROCESSED / f"matched_{arm}_{method}.parquet"
            m.to_parquet(out, index=False)
            bal = match_balance(panel, m, arm=arm)
            print(f"[{arm}/{method}] {n_ev} treated ({n_unmatched} unmatched) | "
                  f"{n_ctrl} control rows -> {out.name}")
            print(bal.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))


if __name__ == "__main__":
    main()
