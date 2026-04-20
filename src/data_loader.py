"""
Data retrieval module for ESG + retail flows study.

Wraps the external data sources (Yahoo Finance, SEC EDGAR, Fama-French data
library) behind a consistent interface so notebooks can call single-function
retrievals without handling API quirks inline.

Every pull is cached under /data/raw; subsequent calls read from cache unless
`refresh=True` is passed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_RAW.mkdir(parents=True, exist_ok=True)


def load_prices(tickers: Iterable[str], start: str, end: str, refresh: bool = False) -> pd.DataFrame:
    """
    Pull daily adjusted-close prices from Yahoo Finance for the given tickers
    and date range. Returns a long-form DataFrame with columns
    [date, ticker, close, volume].

    Cached to /data/raw/prices_{start}_{end}.parquet.
    """
    raise NotImplementedError("Implement in notebook 01_data_ingestion.")


def load_sustainability_scores(tickers: Iterable[str], refresh: bool = False) -> pd.DataFrame:
    """
    Pull Yahoo Finance sustainability scores per ticker. Note: Yahoo provides
    a point-in-time snapshot; for historical panels use MSCI ESG archives or
    academic replica datasets and load from /data/raw/msci_esg_archive.csv.

    Returns DataFrame with columns [ticker, as_of, total_esg, environment,
    social, governance, controversy_level].
    """
    raise NotImplementedError("Implement in notebook 01_data_ingestion.")


def load_13f_filings(quarters: Iterable[str], refresh: bool = False) -> pd.DataFrame:
    """
    Pull SEC 13F institutional holdings for specified quarters (e.g.
    ["2023Q1", "2023Q2"]).

    Returns long DataFrame with columns [cusip, ticker, institution_cik,
    institution_name, quarter, shares, value_usd].

    Implementation: iterates sec-edgar-downloader across ~5k institutional
    filers per quarter; expect ~6 minutes per quarter.
    """
    raise NotImplementedError("Implement in notebook 01_data_ingestion.")


def load_index_membership(index_name: str, refresh: bool = False) -> pd.DataFrame:
    """
    Load historical membership of an ESG index (e.g. MSCI ESG Leaders, S&P 500
    ESG) with monthly add/drop dates. Source: historical index fact sheets or
    academic replica files, held locally under /data/raw/index_membership/.

    Returns DataFrame with columns [ticker, index_name, date_added, date_removed].
    """
    raise NotImplementedError("Implement in notebook 01_data_ingestion.")


def load_ff_factors(start: str, end: str) -> pd.DataFrame:
    """
    Load Fama-French 5-factor + momentum daily returns from Kenneth French's
    data library. Cached locally after first download.

    Returns DataFrame indexed by date with columns [mkt_rf, smb, hml, rmw,
    cma, mom, rf].
    """
    raise NotImplementedError("Implement in notebook 01_data_ingestion.")
