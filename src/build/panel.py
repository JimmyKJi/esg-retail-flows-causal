"""Build the firm × quarter analysis panel (Phase 2).

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
    Amendment dedup can leave a 2023-filed amendment of a ≤2022-09-30 position
    already in dollars inside an otherwise-thousands period — minor, documented,
    and why the share/breadth outcomes are primary.
  * **Left-censored members.** The membership panel starts 2019Q4, so a firm
    already in the index at the window start has no observable inclusion date.
    Such firms (and corp-action-suspect adds) are NOT clean controls — they are
    flagged ``esg_excluded`` and kept out of the never-treated comparison pool.

13F is quarterly, so event time is in QUARTERS, not days — a coarse-timing
caveat carried to the writeup.

DoD (Phase 2): data/processed/panel.parquet exists; no post-treatment leakage
into pre-period columns (lags look strictly backward); event_time supports
balanced pre-trend tests; treated/control counts reported. See
tests/test_panel.py.

Deferred to follow-on commits (explicitly, not silently): the S&P 500 *placebo*
arm (sp500_events isn't persisted yet), the FF-adjusted CAR secondary outcome
(needs the full price pull), and matched-control selection (src/build/matching.py).
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


def build_panel(
    inclusion_events: pd.DataFrame,
    holdings_13f: pd.DataFrame,
    membership: pd.DataFrame | None = None,
    *,
    prices: pd.DataFrame | None = None,       # reserved: FF-adjusted CAR (follow-on)
    ff_factors: pd.DataFrame | None = None,   # reserved: FF-adjusted CAR (follow-on)
    sp500_constituents: pd.DataFrame | None = None,  # reserved: placebo arm (follow-on)
) -> pd.DataFrame:
    """Assemble the firm×quarter panel: 13F outcomes + ESG-inclusion treatment.

    Returns one row per (cusip, calendar-quarter) for every valid-CUSIP security
    in the 13F panel, tagged with treatment cohort/event-time and a sample role.
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

    # ── 2. Treatment: genuine inclusions → cohort (first inclusion quarter) ──
    ev = inclusion_events[_valid_cusip(inclusion_events["cusip"])].copy()
    ev["q"] = _cal_q_end(ev["event_date"]).to_numpy()
    ev["q_idx"] = _q_index(ev["q"]).to_numpy()

    genuine = ev[(ev["action"] == "added") & (~ev["corp_action_suspect"])]
    cohort = genuine.groupby("cusip")["q"].min()
    cohort_qidx = genuine.groupby("cusip")["q_idx"].min()
    treated_cusips = set(cohort.index)

    # Treatment reversal: a treated firm later genuinely dropped (membership is
    # non-absorbing). Flagged for a robustness check; cohort still = first entry.
    removed = ev[(ev["action"] == "removed") & (~ev["corp_action_suspect"])]
    drop_after = {
        c: (g["q_idx"] > cohort_qidx.get(c, np.inf)).any()
        for c, g in removed.groupby("cusip") if c in treated_cusips
    }
    ever_dropped = {c for c, v in drop_after.items() if v}

    panel["treated"] = panel["cusip"].isin(treated_cusips)
    panel["cohort"] = panel["cusip"].map(cohort)
    panel["cohort_q_idx"] = panel["cusip"].map(cohort_qidx).astype("Int64")
    panel["event_time"] = (panel["q_idx"] - panel["cohort_q_idx"]).astype("Int64")
    panel["post"] = (panel["event_time"] >= 0).fillna(False) & panel["treated"]
    panel["esg_inclusion"] = panel["post"]  # documented treatment-indicator alias
    panel["ever_dropped"] = panel["cusip"].isin(ever_dropped)

    # ── 3. ESG membership flags (time-varying + ever) for roles & robustness ──
    member_ever: set = set()
    if membership is not None and not membership.empty:
        m = membership[_valid_cusip(membership["cusip"])].copy()
        m["q_idx"] = _q_index(_cal_q_end(m["as_of"])).to_numpy()
        member_ever = set(m["cusip"])
        flag = (m[["cusip", "q_idx"]].drop_duplicates().assign(esg_member=True))
        panel = panel.merge(flag, on=["cusip", "q_idx"], how="left")
        panel["esg_member"] = panel["esg_member"].fillna(False)
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

    # ── 5. One-quarter changes across ADJACENT observed quarters only ──
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
    # firms with at least one pre (event_time<0) AND one post (>=0) observed quarter
    et = treated.dropna(subset=["event_time"])
    has_pre = set(et.loc[et["event_time"] < 0, "cusip"])
    has_post = set(et.loc[et["event_time"] >= 0, "cusip"])
    estimable = has_pre & has_post

    lines = [
        f"panel: {len(panel):,} rows | {panel['cusip'].nunique():,} cusips | "
        f"{panel['period'].nunique()} quarters "
        f"({panel['period'].min():%Y-%m-%d}→{panel['period'].max():%Y-%m-%d})",
        f"roles (cusips): treated={roles.get('treated', 0):,} | "
        f"clean_control={roles.get('clean_control', 0):,} | "
        f"esg_excluded={roles.get('esg_excluded', 0):,}",
        f"treated firm-quarters: pre={int((treated['event_time'] < 0).sum()):,} | "
        f"post={int((treated['event_time'] >= 0).sum()):,}",
        f"treated cusips with both pre & post observed (estimable): {len(estimable)}",
        f"treated cusips later dropped (treatment reversal): {int(by_cusip['ever_dropped'].sum())}",
        "cohort sizes (cusips per first-inclusion quarter):",
    ]
    coh = (by_cusip[by_cusip["treated"]].groupby(by_cusip["cohort"].dt.date).size())
    lines += [f"  {d}: {n}" for d, n in coh.items()]
    return "\n".join(lines)


def load_inputs() -> dict:
    """Read the interim parquets this phase consumes."""
    return {
        "inclusion_events": pd.read_parquet(DATA_INTERIM / "esg_inclusion_events.parquet"),
        "holdings_13f": pd.read_parquet(DATA_INTERIM / "holdings_13f.parquet"),
        "membership": pd.read_parquet(DATA_INTERIM / "esg_index_holdings.parquet"),
    }


def main() -> None:
    src = load_inputs()
    panel = build_panel(src["inclusion_events"], src["holdings_13f"], src["membership"])
    out = DATA_PROCESSED / "panel.parquet"
    panel.to_parquet(out, index=False)
    print(summarize(panel))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
