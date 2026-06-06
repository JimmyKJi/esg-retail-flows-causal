"""FF-adjusted cumulative abnormal return (CAR) — the secondary outcome (Phase 2b).

The primary outcome is institutional *flows* (13F ownership, quarterly). This
module adds the *price* reaction: an event-study CAR around index inclusion,
abnormal relative to a Fama-French five-factor market model estimated on a
pre-event window. It is a triangulating secondary outcome, not the headline.

Scope, stated honestly (this is a CV/admissions piece — limitations are
documented, not hidden):

  * **Runs on the S&P 500 placebo arm, not the ESG arm.** A clean daily event
    study needs (a) a security identifier yfinance can price and (b) a precise
    event date. The S&P 500 additions have both — Wikipedia gives the *effective
    date* to the day, and the changes carry tickers. The ESG-Leaders inclusions
    have neither at the needed resolution: the inclusion is observed only at the
    fund's N-PORT *fiscal quarter-end* (quarterly, not daily), and there is no
    free CUSIP→ticker bridge for the ESG-only firms (13F/N-PORT carry CUSIP, not
    ticker). So the ESG-arm CAR is *not* computed; the generic-inclusion CAR is
    the deliverable here, and the ESG question stays on the fully-covered
    quarterly flow design.
  * The S&P CAR doubles as the placebo's price benchmark: the classic "S&P 500
    index effect" (a positive inclusion CAR) is a known result, so recovering it
    validates the event-study machinery the writeup leans on.

Market model: excess return rₜ−rfₜ regressed on (mkt_rf, smb, hml, rmw, cma)
over an estimation window ending well before the event; abnormal return in the
event window is actual−predicted excess; CAR is their sum. Events that can't be
priced or lack a long-enough estimation window are *kept and flagged* (status
column), so coverage is reported, never silently dropped.

Run:  python -m src.build.car
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.paths import DATA_INTERIM, DATA_PROCESSED

_FACTORS = ("mkt_rf", "smb", "hml", "rmw", "cma")


def _returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Long [date, ticker, close] → add daily simple returns per ticker."""
    p = prices.sort_values(["ticker", "date"]).copy()
    p["date"] = pd.to_datetime(p["date"]).dt.normalize()
    p["ret"] = p.groupby("ticker")["close"].pct_change()
    return p.dropna(subset=["ret"])


def _miss(ev, status: str) -> dict:
    return {"event_id": ev.event_id, "ticker": ev.ticker,
            "event_date": pd.Timestamp(ev.event_date).normalize(), "t0_date": pd.NaT,
            "n_est": 0, "alpha": np.nan, "car": np.nan, "n_event_days": 0,
            "status": status}


def build_event_car(
    events: pd.DataFrame,            # cols: event_id, ticker, event_date
    prices: pd.DataFrame,            # long: date, ticker, close
    ff_factors: pd.DataFrame,        # daily, indexed by date: mkt_rf..cma, rf (decimal)
    *,
    est_window: tuple[int, int] = (-252, -22),   # trading days rel. to t0 (≈1yr, gap)
    event_window: tuple[int, int] = (-5, 5),     # trading days rel. to t0 (incl.)
    min_obs: int = 120,
    factors: tuple[str, ...] = _FACTORS,
) -> pd.DataFrame:
    """Per-event FF-adjusted CAR. Returns event_id, ticker, event_date, t0_date,
    n_est, alpha, car, n_event_days, status ('ok' | reason it was skipped).
    """
    rets = _returns(prices)
    by_ticker = {t: g for t, g in rets.groupby("ticker")}
    ff = ff_factors[list(factors) + ["rf"]].copy()
    ff.index = pd.to_datetime(ff.index).normalize()

    rows: list[dict] = []
    for ev in events.itertuples(index=False):
        ed = pd.Timestamp(ev.event_date).normalize()
        g = by_ticker.get(ev.ticker)
        if g is None or g.empty:
            rows.append(_miss(ev, "no_prices")); continue

        d = (g.set_index("date")[["ret"]].join(ff, how="inner").dropna()
             .sort_index())
        if d.empty:
            rows.append(_miss(ev, "no_factor_overlap")); continue

        idx = d.index
        pos = int(idx.searchsorted(ed))                # first trading day ≥ event date
        if pos >= len(idx):
            rows.append(_miss(ev, "event_after_data")); continue

        a, b = pos + est_window[0], pos + est_window[1]
        ea, eb = pos + event_window[0], pos + event_window[1] + 1
        if a < 0:
            rows.append(_miss(ev, "insufficient_pre")); continue
        if ea < 0 or eb > len(idx):
            rows.append(_miss(ev, "event_window_oob")); continue

        est, evt = d.iloc[a:b], d.iloc[ea:eb]
        if len(est) < min_obs:
            rows.append(_miss(ev, "short_estimation")); continue

        fac = list(factors)
        x = np.column_stack([np.ones(len(est)), est[fac].to_numpy(float)])
        y = (est["ret"] - est["rf"]).to_numpy(float)
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)

        xe = np.column_stack([np.ones(len(evt)), evt[fac].to_numpy(float)])
        ye = (evt["ret"] - evt["rf"]).to_numpy(float)
        ar = ye - xe @ beta
        rows.append({"event_id": ev.event_id, "ticker": ev.ticker, "event_date": ed,
                     "t0_date": idx[pos], "n_est": len(est), "alpha": float(beta[0]),
                     "car": float(ar.sum()), "n_event_days": len(evt), "status": "ok"})
    return pd.DataFrame(rows)


def car_summary(car_df: pd.DataFrame) -> dict:
    """Cross-sectional CAR summary: n, mean, cross-sectional t-stat, %>0."""
    ok = car_df[car_df["status"] == "ok"]
    n = len(ok)
    if n == 0:
        return {"n": 0, "mean_car": np.nan, "t_stat": np.nan, "pct_positive": np.nan}
    m = float(ok["car"].mean())
    sd = float(ok["car"].std(ddof=1)) if n > 1 else np.nan
    t = m / (sd / np.sqrt(n)) if n > 1 and sd > 0 else np.nan
    return {"n": n, "mean_car": m, "t_stat": t, "pct_positive": float((ok["car"] > 0).mean())}


def main() -> None:
    from src.build.placebo import build_sp500_cusip_events
    from src.ingest.prices import load_prices

    ev = build_sp500_cusip_events(since="2019-01-01").rename(columns={"cusip": "event_id"})
    ev = ev.dropna(subset=["ticker", "event_date"])
    ff = pd.read_parquet(DATA_INTERIM / "ff_factors_daily.parquet")

    start = (ev["event_date"].min() - pd.Timedelta(days=420)).strftime("%Y-%m-%d")
    end = (ev["event_date"].max() + pd.Timedelta(days=40)).strftime("%Y-%m-%d")
    tickers = sorted(ev["ticker"].unique())
    print(f"[car] pulling {len(tickers)} S&P-500 tickers {start}..{end}")
    prices = load_prices(tickers, start, end)

    for win in [(-5, 5), (-1, 1), (0, 1)]:
        car = build_event_car(ev, prices, ff, event_window=win)
        s = car_summary(car)
        tag = f"[{win[0]:+d},{win[1]:+d}]"
        t = f"{s['t_stat']:+.2f}" if pd.notna(s["t_stat"]) else "n/a"
        print(f"  CAR {tag}: n={s['n']:3d} | mean={s['mean_car']*100:+.2f}% | "
              f"t={t} | {s['pct_positive']*100:.0f}% positive")
        if win == (-5, 5):
            cov = car["status"].value_counts().to_dict()
            out = DATA_PROCESSED / "car_sp500.parquet"
            car.to_parquet(out, index=False)
            print(f"  coverage: {cov}\n  wrote {out}")


if __name__ == "__main__":
    main()
