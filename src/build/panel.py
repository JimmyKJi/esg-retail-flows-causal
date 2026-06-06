"""Build the firm × quarter analysis panel (Phase 2 + 2b).

Combines the ingested pieces into one tidy panel keyed on (cusip, quarter).
Both the treatment (N-PORT ESG-index inclusions, dated at the fund's *fiscal*
quarter-end — Feb/May/Aug/Nov) and the outcome (13F holdings, dated at the
*calendar* quarter-end — Mar/Jun/Sep/Dec) are folded onto the **containing
calendar quarter** so they join cleanly: a 2020-02-29 inclusion and the
2020-03-31 13F snapshot both land in 2020Q1.

  treatment   cohort:        first calendar quarter a firm enters the ESG
                             Leaders index (staggered-DiD cohort timing);
              esg_inclusion: 1 from the cohort quarter onward (absorbing);
              event_time:    quarters relative to cohort (negative = pre).
  placebo     sp500_*:       the identical cohort structure for S&P 500
                             additions (the generic-inclusion benchmark), so the
                             ESG-specific effect = ESG ATT − S&P-500 ATT.
  outcomes    n_filers       breadth — count of 13F institutions holding;
              total_shares   depth   — aggregate shares held (unit-immune);
              total_value_usd depth  — aggregate $ held (2023 unit change
                             normalised; see below). Plus 1-quarter changes
                             d_n_filers / dlog_shares / dlog_value across
                             *adjacent* observed quarters only.
  roles       treated / clean_control / esg_excluded (see below).

Two identification subtleties are handled here, not papered over:

  * **2023 VALUE unit change.** SEC switched INFOTABLE.VALUE from $thousands to
    whole-$ for filings on/after 2023-01. Empirically the break is at report
    period 2022-12-31, so values for periods ≤ 2022-09-30 are ×1000'd to whole
    dollars. ``n_filers`` and ``total_shares`` are immune (only VALUE changed).
  * **Left-censored members.** The membership panel starts 2019Q4, so a firm
    already in the index at the window start has no observable inclusion date.
    Such firms (and corp-action-suspect adds) are NOT clean controls — they are
    flagged ``esg_excluded`` and kept out of the never-treated comparison pool.
    The S&P 500 ever-members are excluded from the *placebo's* control pool the
    same way (``sp500_member_ever``).

13F is quarterly, so event time is in QUARTERS, not days — a coarse-timing
caveat carried to the writeup.

DoD (Phase 2): data/processed/panel.parquet exists; no post-treatment leakage
into pre-period columns (lags look strictly backward); event_time supports
balanced pre-trend tests; treated/control counts reported. See
tests/test_panel.py.

Deferred (explicitly): the FF-adjusted CAR secondary outcome (needs the full
price pull) and matched-control selection (src/build/matching.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.paths import DATA_INTERIM, DATA_PROCESSED

# VALUE was reported in $thousands up to and including this period, whole-$ after
# (the empirically-confirmed 2023-01 filing-rule boundary).
_THOUSANDS_THROUGH = pd.Timestamp("2022-09-30")

# 9-char alphanumeric, and not the SEC placeholder family (issuer base 000000,
# e.g. '000000000', '0000000NA', '000000089'). Drops the lone 'N/A' treated CUSIP.
_CUSIP_RE = r"^[0-9A-Z]{9}$"


def _cal_q_end(s) -> pd.Series:
    """Map any date to its containing calendar-quarter-end timestamp."""
    return pd.PeriodIndex(pd.to_datetime(s), freq="Q").to_timestamp(how="end").normalize()


def _q_index(s) -> pd.Series:
    """Integer quarter index (year*4 + quarter) — for differencing & event time."""
    p = pd.PeriodIndex(pd.to_datetime(s), freq="Q")
    return pd.Series(p.year * 4 + p.quarter, index=getattr(s, "index", None))


def _valid_cusip(series: pd.Series) -> pd.Series:
    s = series.astype("string")
    return s.str.fullmatch(_CUSIP_RE).fillna(False) & (s.str.slice(0, 6) != "000000")


def _cohort_from_events(events: pd.DataFrame, date_col: str) -> tuple[pd.Series, pd.Series]:
    """First-event calendar quarter per CUSIP → (cohort timestamp, cohort q_idx)."""
    e = events[_valid_cusip(events["cusip"])].copy()
    q = _cal_q_end(e[date_col])
    e = e.assign(_q=q.to_numpy(), _qi=_q_index(q).to_numpy())
    return e.groupby("cusip")["_q"].min(), e.groupby("cusip")["_qi"].min()


def _apply_cohort(panel: pd.DataFrame, cohort_ts: pd.Series, cohort_qidx: pd.Series,
                  prefix: str) -> pd.DataFrame:
    """Add {prefix}treated/cohort/cohort_q_idx/event_time/post for one treatment arm.

    `post` is absorbing from the cohort quarter. Reused for the ESG arm
    (prefix="") and the S&P 500 placebo arm (prefix="sp500_") so the two designs
    are constructed identically.
    """
    treated = panel["cusip"].isin(set(cohort_qidx.index))
    panel[f"{prefix}treated"] = treated
    panel[f"{prefix}cohort"] = panel["cusip"].map(cohort_ts)
    panel[f"{prefix}cohort_q_idx"] = panel["cusip"].map(cohort_qidx).astype("Int64")
    et = (panel["q_idx"] - panel[f"{prefix}cohort_q_idx"]).astype("Int64")
    panel[f"{prefix}event_time"] = et
    panel[f"{prefix}post"] = (et >= 0).fillna(False) & treated
    return panel


def build_panel(
    inclusion_events: pd.DataFrame,
    holdings_13f: pd.DataFrame,
    membership: pd.DataFrame | None = None,
    *,
    sp500_events: pd.DataFrame | None = None,       # CUSIP-keyed S&P 500 adds (placebo)
    sp500_member_cusips: set[str] | None = None,    # ever-S&P-500 (placebo exclusions)
    prices: pd.DataFrame | None = None,             # reserved: FF-adjusted CAR (follow-on)
    ff_factors: pd.DataFrame | None = None,         # reserved: FF-adjusted CAR (follow-on)
) -> pd.DataFrame:
    """Assemble the firm×quarter panel: 13F outcomes + ESG-inclusion treatment
    (+ the S&P 500 placebo arm when ``sp500_events`` is supplied).
    """
    # ── 1. Outcome panel: clean 13F to valid CUSIPs, normalise the VALUE unit ──
    h = holdings_13f[_valid_cusip(holdings_13f["cusip"])].copy()
    h["period"] = pd.to_datetime(h["period"]).dt.normalize()
    h["q_idx"] = _q_index(h["period"]).to_numpy()

    h["value_unit_normalized"] = h["period"] <= _THOUSANDS_THROUGH
    h["total_value_usd"] = np.where(
        h["value_unit_normalized"], h["total_value"] * 1000.0, h["total_value"].astype(float)
    )
    h["log_shares"] = np.log1p(h["total_shares"].clip(lower=0))
    h["log_value"] = np.log1p(h["total_value_usd"].clip(lower=0))

    panel = (
        h[["cusip", "period", "q_idx", "n_filers", "total_shares", "total_value_usd",
           "value_unit_normalized", "log_shares", "log_value"]]
        .sort_values(["cusip", "q_idx"])
        .reset_index(drop=True)
    )

    # ── 2. ESG treatment: genuine inclusions → cohort (first inclusion quarter) ──
    ev = inclusion_events[_valid_cusip(inclusion_events["cusip"])].copy()
    ev["q_idx"] = _q_index(_cal_q_end(ev["event_date"])).to_numpy()
    genuine = ev[(ev["action"] == "added") & (~ev["corp_action_suspect"])]
    cohort_ts, cohort_qidx = _cohort_from_events(genuine, "event_date")
    treated_cusips = set(cohort_qidx.index)

    panel = _apply_cohort(panel, cohort_ts, cohort_qidx, prefix="")
    panel["esg_inclusion"] = panel["post"]  # documented treatment-indicator alias

    # Treatment reversal: a treated firm later genuinely dropped (non-absorbing).
    removed = ev[(ev["action"] == "removed") & (~ev["corp_action_suspect"])]
    ever_dropped = {
        c for c, g in removed.groupby("cusip")
        if c in treated_cusips and (g["q_idx"] > cohort_qidx.get(c, np.inf)).any()
    }
    panel["ever_dropped"] = panel["cusip"].isin(ever_dropped)

    # ── 3. ESG membership flags (time-varying + ever) for roles & robustness ──
    member_ever: set = set()
    if membership is not None and not membership.empty:
        m = membership[_valid_cusip(membership["cusip"])].copy()
        m["q_idx"] = _q_index(_cal_q_end(m["as_of"])).to_numpy()
        member_ever = set(m["cusip"])
        flag = m[["cusip", "q_idx"]].drop_duplicates().assign(esg_member=True)
        panel = panel.merge(flag, on=["cusip", "q_idx"], how="left")
        panel["esg_member"] = panel["esg_member"].eq(True)  # True where matched, else False
    else:
        panel["esg_member"] = False
    panel["esg_member_ever"] = panel["cusip"].isin(member_ever | treated_cusips)

    # ── 4. Sample role. Left-censored members & suspect adds are NOT controls. ──
    panel["clean_control"] = ~panel["treated"] & ~panel["esg_member_ever"]
    panel["sample_role"] = np.select(
        [panel["treated"], panel["clean_control"]],
        ["treated", "clean_control"],
        default="esg_excluded",
    )

    # ── 5. S&P 500 placebo arm (optional, symmetric with the ESG arm) ──────────
    if sp500_events is not None and not sp500_events.empty:
        sp_ts, sp_qidx = _cohort_from_events(sp500_events, "event_date")
        panel = _apply_cohort(panel, sp_ts, sp_qidx, prefix="sp500_")
        members = set(sp500_member_cusips or set()) | set(sp_qidx.index)
        panel["sp500_member_ever"] = panel["cusip"].isin(members)
        panel["both_treated"] = panel["treated"] & panel["sp500_treated"]

    # ── 6. One-quarter changes across ADJACENT observed quarters only ──────────
    g = panel.groupby("cusip", sort=False)
    panel["gap_q"] = g["q_idx"].diff()
    adj = panel["gap_q"] == 1
    panel["d_n_filers"] = g["n_filers"].diff().where(adj)
    panel["dlog_shares"] = g["log_shares"].diff().where(adj)
    panel["dlog_value"] = g["log_value"].diff().where(adj)

    return panel.sort_values(["cusip", "q_idx"]).reset_index(drop=True)


def summarize(panel: pd.DataFrame) -> str:
    """Human-readable counts for the DoD: treated/control, cohorts, estimability."""
    by_cusip = panel.drop_duplicates("cusip")
    roles = by_cusip["sample_role"].value_counts()
    treated = panel[panel["treated"]]
    et = treated.dropna(subset=["event_time"])
    estimable = set(et.loc[et["event_time"] < 0, "cusip"]) & set(et.loc[et["event_time"] >= 0, "cusip"])

    lines = [
        f"panel: {len(panel):,} rows | {panel['cusip'].nunique():,} cusips | "
        f"{panel['period'].nunique()} quarters "
        f"({panel['period'].min():%Y-%m-%d}→{panel['period'].max():%Y-%m-%d})",
        f"ESG roles (cusips): treated={roles.get('treated', 0):,} | "
        f"clean_control={roles.get('clean_control', 0):,} | "
        f"esg_excluded={roles.get('esg_excluded', 0):,}",
        f"ESG treated firm-quarters: pre={int((treated['event_time'] < 0).sum()):,} | "
        f"post={int((treated['event_time'] >= 0).sum()):,}",
        f"ESG treated cusips with both pre & post observed (estimable): {len(estimable)}",
        f"ESG treated cusips later dropped (reversal): {int(by_cusip['ever_dropped'].sum())}",
    ]
    if "sp500_treated" in panel.columns:
        sp = panel[panel["sp500_treated"]]
        spet = sp.dropna(subset=["sp500_event_time"])
        sp_est = (set(spet.loc[spet["sp500_event_time"] < 0, "cusip"]) &
                  set(spet.loc[spet["sp500_event_time"] >= 0, "cusip"]))
        lines += [
            f"PLACEBO (S&P 500): treated={by_cusip['sp500_treated'].sum():,} | "
            f"ever-member={by_cusip['sp500_member_ever'].sum():,} | "
            f"estimable={len(sp_est)} | also-ESG-treated={int(by_cusip['both_treated'].sum())}",
        ]
    lines.append("ESG cohort sizes (cusips per first-inclusion quarter):")
    coh = by_cusip[by_cusip["treated"]].groupby(by_cusip["cohort"].dt.date).size()
    lines += [f"  {d}: {n}" for d, n in coh.items()]
    return "\n".join(lines)


def load_inputs() -> dict:
    """Read the interim parquets this phase consumes (+ the placebo arm if present)."""
    src = {
        "inclusion_events": pd.read_parquet(DATA_INTERIM / "esg_inclusion_events.parquet"),
        "holdings_13f": pd.read_parquet(DATA_INTERIM / "holdings_13f.parquet"),
        "membership": pd.read_parquet(DATA_INTERIM / "esg_index_holdings.parquet"),
    }
    try:  # placebo arm: requires the crosswalk + persisted S&P 500 events
        from src.build.placebo import build_sp500_cusip_events, sp500_member_cusips
        src["sp500_events"] = build_sp500_cusip_events()
        src["sp500_member_cusips"] = sp500_member_cusips()
    except Exception as exc:  # pragma: no cover — placebo is additive, never fatal
        print(f"[panel] placebo arm skipped ({type(exc).__name__}: {exc})")
        src["sp500_events"] = None
        src["sp500_member_cusips"] = None
    return src


def main() -> None:
    src = load_inputs()
    panel = build_panel(
        src["inclusion_events"], src["holdings_13f"], src["membership"],
        sp500_events=src.get("sp500_events"),
        sp500_member_cusips=src.get("sp500_member_cusips"),
    )
    out = DATA_PROCESSED / "panel.parquet"
    panel.to_parquet(out, index=False)
    print(summarize(panel))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
