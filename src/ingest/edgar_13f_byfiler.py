"""Phase 5 — re-ingest 13F at the filer (CIK) grain to enable H4.

The primary outcome (``edgar_13f.aggregate_ownership``) rolls INFOTABLE up to one
row per CUSIP, discarding filer identity — which is exactly why H4 (does
*ESG-badged* or *passive* institutional demand respond specifically to ESG
inclusion?) is "not estimable" from the assembled panel. This module re-parses the
**same cached bundles** (``data/raw/edgar_13f/*.zip`` — no network) but keeps the
filer dimension: it joins every holding to its filer CIK (SUBMISSION) and manager
name (COVERPAGE), classifies the filer (``heterogeneity.classify_esg_filers`` /
``classify_passive``), and rolls up per CUSIP into filer-TYPE breadth + depth
columns, restricted to the analysis universe (treated + matched controls,
~1.5k CUSIPs) so the per-filer parse stays small.

IMPORTANT CAVEAT (measurement). 13F is filed at the *manager* level, not the fund
level. A dedicated ESG/SRI boutique ("Trillium ESG…") trips the ESG name match,
but ESG ETFs *inside* a large complex file under the parent ("BlackRock Inc."), so
``n_filers_esg`` captures ESG-branded *firms* only, not ESG sleeves of giants. The
mechanical ESG-index-tracking channel instead surfaces as **passive depth**: when a
name enters an ESG index, the passive complexes that track it (BlackRock/SSGA/
Vanguard — all name-matched as passive) must buy, lifting ``shares_passive``.
``shares_passive`` is therefore the sharpest single H4 outcome.

Reconciliation: ``n_filers_total`` here equals ``edgar_13f``'s ``n_filers`` for the
same (cusip, period) — the type columns are a partition of the frozen breadth
measure. ``aggregate_by_filer_type`` is pure and unit-tested; the build is a pure
re-parse of cached zips (no SEC access).

Run:  python -m src.ingest.edgar_13f_byfiler
"""

from __future__ import annotations

import zipfile

import pandas as pd

from src.estimate.heterogeneity import classify_esg_filers, classify_passive
from src.utils.paths import DATA_INTERIM, DATA_PROCESSED, DATA_RAW

_RAW = DATA_RAW / "edgar_13f"
_PARTS = DATA_INTERIM / "_13f_byfiler_parts"
_OUT = DATA_INTERIM / "holdings_13f_byfiler.parquet"
_SINCE = pd.Timestamp("2019-01-01")

# Only the columns the rollup needs (INFOTABLE is tens of millions of rows/quarter).
_INFO_COLS = {"ACCESSION_NUMBER", "CUSIP", "SSHPRNAMT"}
_SUB_COLS = {"ACCESSION_NUMBER", "CIK", "FILING_DATE", "PERIODOFREPORT"}
_COV_COLS = {"ACCESSION_NUMBER", "FILINGMANAGER_NAME"}


def analysis_universe() -> set[str]:
    """CUSIPs that estimation actually touches: treated (ESG + S&P placebo) plus
    every matched control across both arms and both matching schemes. Restricting
    the per-filer parse to this set (~1.5k names) keeps it small while covering the
    full matched DiD design."""
    cusips: set[str] = set()
    for arm in ("esg", "sp500"):
        for method in ("cem", "psm"):
            p = DATA_PROCESSED / f"matched_{arm}_{method}.parquet"
            if p.exists():
                cusips |= set(pd.read_parquet(p, columns=["cusip"])["cusip"].astype(str))
    panel_p = DATA_PROCESSED / "panel.parquet"
    if panel_p.exists():
        pn = pd.read_parquet(panel_p, columns=["cusip", "treated", "sp500_treated"])
        tre = pn["treated"].fillna(False).to_numpy(bool) | \
            pn["sp500_treated"].fillna(False).to_numpy(bool)
        cusips |= set(pn.loc[tre, "cusip"].astype(str))
    return cusips


def aggregate_by_filer_type(infotable: pd.DataFrame, submission: pd.DataFrame,
                            coverpage: pd.DataFrame) -> pd.DataFrame:
    """Roll holdings up to one row per CUSIP, split by filer type. Pure.

    Inputs are one quarter's tables already filtered to the kept (amendment-deduped)
    filings. Returns per-CUSIP columns:
      n_filers_total   distinct filer CIKs holding (reconciles to edgar_13f.n_filers)
      n_filers_esg     distinct filers whose manager name matches the ESG pattern
      n_filers_passive distinct filers whose name matches a passive complex
      shares_total     summed SSHPRNAMT (reconciles to edgar_13f.total_shares)
      shares_esg       summed SSHPRNAMT held by ESG-named filers
      shares_passive   summed SSHPRNAMT held by passive filers
    ``n_filers_nonesg``/``n_filers_active`` are derived downstream as the complements.
    """
    info = infotable.copy()
    info["SSHPRNAMT"] = pd.to_numeric(info["SSHPRNAMT"], errors="coerce")

    sub = submission[["ACCESSION_NUMBER", "CIK"]].drop_duplicates()
    cov = coverpage[["ACCESSION_NUMBER", "FILINGMANAGER_NAME"]] \
        .drop_duplicates("ACCESSION_NUMBER")
    meta = sub.merge(cov, on="ACCESSION_NUMBER", how="left")
    # Classification is a property of the filer name → constant within a CIK.
    meta["is_esg"] = classify_esg_filers(meta["FILINGMANAGER_NAME"]).to_numpy()
    meta["is_passive"] = classify_passive(meta["FILINGMANAGER_NAME"]).to_numpy()

    m = info.merge(meta, on="ACCESSION_NUMBER", how="left").dropna(subset=["CIK"])

    # Breadth: dedup to one row per (CUSIP, CIK) so a boolean sum counts distinct
    # filers of each type (is_esg/is_passive are constant within CIK).
    fc = m.drop_duplicates(["CUSIP", "CIK"])
    counts = fc.groupby("CUSIP").agg(
        n_filers_total=("CIK", "nunique"),
        n_filers_esg=("is_esg", "sum"),
        n_filers_passive=("is_passive", "sum"),
    )

    # Depth: sum shares over all holding rows (matches aggregate_ownership), by type.
    shares_total = m.groupby("CUSIP")["SSHPRNAMT"].sum().rename("shares_total")
    shares_esg = m.loc[m["is_esg"]].groupby("CUSIP")["SSHPRNAMT"].sum().rename("shares_esg")
    shares_passive = m.loc[m["is_passive"]].groupby("CUSIP")["SSHPRNAMT"].sum() \
        .rename("shares_passive")

    out = counts.join([shares_total, shares_esg, shares_passive], how="left")
    out[["shares_esg", "shares_passive"]] = out[["shares_esg", "shares_passive"]].fillna(0.0)
    for c in ("n_filers_total", "n_filers_esg", "n_filers_passive"):
        out[c] = out[c].astype(int)
    return out.reset_index().rename(columns={"CUSIP": "cusip"})


def _parse_three(zip_path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the needed INFOTABLE + SUBMISSION + COVERPAGE columns from a bundle.

    Mirrors ``edgar_13f.parse_dataset`` (basename match + header upper-case for the
    dataset's occasional casing/nesting changes), adding COVERPAGE for the filer
    manager name.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = {n.rsplit("/", 1)[-1].upper(): n for n in zf.namelist()}

        def _read(member: str, cols: set[str]) -> pd.DataFrame:
            with zf.open(names[member]) as f:
                return pd.read_csv(f, sep="\t", dtype=str,
                                   usecols=lambda c: c.upper() in cols).rename(columns=str.upper)

        info = _read("INFOTABLE.TSV", _INFO_COLS)
        sub = _read("SUBMISSION.TSV", _SUB_COLS)
        cov = _read("COVERPAGE.TSV", _COV_COLS)
    return info, sub, cov


def parse_bundle_byfiler(zip_path, universe: set[str]) -> pd.DataFrame | None:
    """One bundle zip → per-CUSIP filer-type rollup for one quarter (or None).

    Same quarter resolution as ``edgar_13f._aggregate_bundle``: modal
    PERIODOFREPORT, keep that period's filings, dedup to the latest filing per CIK
    (amendment supersedes original), then restrict to the analysis ``universe`` and
    roll up by filer type. Pure given the file: no network.
    """
    info, sub, cov = _parse_three(zip_path)
    per = pd.to_datetime(sub["PERIODOFREPORT"].str.title(),
                         format="%d-%b-%Y", errors="coerce")
    if per.dropna().empty:
        return None
    period = per.mode().iloc[0]
    keep = sub[per == period].copy()
    keep["_fdate"] = pd.to_datetime(keep["FILING_DATE"].str.title(),
                                    format="%d-%b-%Y", errors="coerce")
    keep = keep.sort_values("_fdate").drop_duplicates("CIK", keep="last")

    acc = set(keep["ACCESSION_NUMBER"])
    info_q = info[info["ACCESSION_NUMBER"].isin(acc)
                  & info["CUSIP"].isin(universe)].copy()
    if info_q.empty:
        return None
    cov_q = cov[cov["ACCESSION_NUMBER"].isin(acc)]
    agg = aggregate_by_filer_type(info_q, keep.drop(columns="_fdate"), cov_q)
    agg["period"] = period.normalize()
    return agg


def build_byfiler_panel(refresh: bool = False) -> pd.DataFrame:
    """Re-parse every cached bundle at the filer grain → long CUSIP×quarter panel
    of filer-type breadth/depth. Checkpoints one parquet per bundle under
    ``_PARTS`` (a killed run resumes instead of re-parsing). No SEC access — reads
    only the zips already in ``data/raw/edgar_13f/``.
    """
    bundles = sorted(_RAW.glob("*.zip"))
    if not bundles:
        raise FileNotFoundError(
            f"No cached bundles in {_RAW} — run `make data-sec` (edgar_13f) first.")
    universe = analysis_universe()
    if not universe:
        raise FileNotFoundError(
            "Empty analysis universe — run `make panel matched` first.")
    _PARTS.mkdir(parents=True, exist_ok=True)
    print(f"[13f-byfiler] {len(bundles)} cached bundles; universe={len(universe)} cusips",
          flush=True)

    for zp in bundles:
        part = _PARTS / f"{zp.name}.parquet"
        if part.exists() and not refresh:
            continue
        agg = parse_bundle_byfiler(zp, universe)
        if agg is None or agg.empty:
            print(f"[13f-byfiler] {zp.name}: nothing in universe, skipped", flush=True)
            continue
        agg.to_parquet(part, index=False)
        print(f"[13f-byfiler] {zp.name} -> {agg['period'].iloc[0].date()} "
              f"({len(agg)} cusips, max esg {int(agg['n_filers_esg'].max())}, "
              f"max passive {int(agg['n_filers_passive'].max())})", flush=True)

    parts = [pd.read_parquet(_PARTS / f"{zp.name}.parquet")
             for zp in bundles if (_PARTS / f"{zp.name}.parquet").exists()]
    panel = pd.concat(parts, ignore_index=True)
    panel = (panel[panel["period"] >= _SINCE]
             .sort_values(["period", "cusip"]).reset_index(drop=True))
    panel.to_parquet(_OUT, index=False)
    return panel


def _reconcile(panel: pd.DataFrame) -> None:
    """Sanity check: per (cusip, period), n_filers_total must equal the frozen
    edgar_13f n_filers (the type split is a partition of the same breadth measure)."""
    froz = DATA_INTERIM / "holdings_13f.parquet"
    if not froz.exists():
        print("[13f-byfiler] holdings_13f.parquet absent — skipping reconciliation")
        return
    h = pd.read_parquet(froz, columns=["cusip", "period", "n_filers"])
    j = panel.merge(h, on=["cusip", "period"], how="inner")
    d = (j["n_filers_total"] - j["n_filers"]).abs()
    print(f"[13f-byfiler] reconcile vs frozen n_filers on {len(j)} rows: "
          f"max|Δ|={int(d.max())}, mismatches={int((d > 0).sum())}")


def main() -> None:
    panel = build_byfiler_panel()
    n = len(panel)
    esg = panel["n_filers_esg"].sum()
    pas = panel["n_filers_passive"].sum()
    tot = panel["n_filers_total"].sum()
    print(f"13F byfiler panel: {n} cusip×quarter rows across "
          f"{panel['period'].nunique()} quarters "
          f"({panel['period'].min().date()}…{panel['period'].max().date()}); "
          f"ESG-named filer-holdings {esg}/{tot} ({esg / tot:.1%}), "
          f"passive {pas}/{tot} ({pas / tot:.1%})")
    _reconcile(panel)


if __name__ == "__main__":
    main()
