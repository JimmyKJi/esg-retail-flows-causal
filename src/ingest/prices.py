"""Ingest daily prices/returns from Yahoo Finance via yfinance.

Prices feed the *secondary* outcome (FF-adjusted cumulative abnormal return
around inclusion). The primary outcome is institutional flows from 13F; see
edgar_13f.py. Yahoo is reachable from this environment.

Run:  python -m src.ingest.prices  AAPL MSFT
"""

from __future__ import annotations

import sys

import pandas as pd
import yfinance as yf

from src.utils.paths import DATA_RAW

_OUT = DATA_RAW / "prices"


def load_prices(tickers: list[str], start: str, end: str,
                refresh: bool = False) -> pd.DataFrame:
    """Daily adjusted prices in long form: [date, ticker, close, volume].

    Cached per (start, end) span under data/raw/prices/.
    """
    _OUT.mkdir(parents=True, exist_ok=True)
    cache = _OUT / f"prices_{start}_{end}.parquet"
    if cache.exists() and not refresh:
        df = _read(cache)
        if set(tickers).issubset(set(df["ticker"].unique())):
            return df[df["ticker"].isin(tickers)].reset_index(drop=True)

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False, group_by="column")
    if raw.empty:
        raise RuntimeError(f"yfinance returned no data for {tickers} {start}..{end}")

    close = _field(raw, "Close", tickers)
    vol = _field(raw, "Volume", tickers)
    out = (
        close.merge(vol, on=["date", "ticker"], how="left")
        .dropna(subset=["close"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    )
    _write(out, cache)
    return out


def _field(raw: pd.DataFrame, field: str, tickers: list[str]) -> pd.DataFrame:
    """Extract one yfinance field as long-form [date, ticker, <field>]."""
    sub = raw[field]
    if isinstance(sub, pd.Series):  # single-ticker download
        sub = sub.to_frame(tickers[0])
    long = sub.reset_index().melt(id_vars=sub.index.name or "Date",
                                  var_name="ticker", value_name=field.lower())
    return long.rename(columns={(sub.index.name or "Date"): "date"})


def _read(path):
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.read_pickle(path.with_suffix(".pkl"))


def _write(df: pd.DataFrame, path) -> None:
    try:
        df.to_parquet(path)
    except Exception:
        df.to_pickle(path.with_suffix(".pkl"))  # pyarrow not yet installed


def main() -> None:
    tickers = sys.argv[1:] or ["AAPL", "MSFT"]
    df = load_prices(tickers, "2020-01-01", "2024-12-31", refresh=True)
    print(f"prices: {len(df)} rows, {df['ticker'].nunique()} tickers")
    print(f"date coverage: {df['date'].min().date()} -> {df['date'].max().date()}")
    print(df.groupby("ticker").size().to_string())


if __name__ == "__main__":
    main()
