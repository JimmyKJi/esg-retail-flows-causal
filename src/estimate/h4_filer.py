"""Phase 5 — H4: does ESG-badged / passive demand respond *specifically* to ESG
inclusion?

Merges the filer-TYPE breadth/depth columns (``edgar_13f_byfiler``) onto the frozen
panel and runs the SAME matched Sun-Abraham event study + ESG-vs-S&P placebo
contrast (``did.esg_specific_contrast``) on each filer-type outcome. The aggregate
finding is a null/negative ESG-specific effect; H4 asks whether that flat aggregate
hides a *composition* shift — ESG / passive funds piling in while others step back.
If so, the ESG-specific effect should turn positive and significant here, most of
all on ``shares_passive`` (the mechanical index-tracking channel: passive complexes
that track an ESG index must buy a name when it enters).

Outcomes (0 where a name had no filer of that type that quarter):
  n_filers_esg        breadth — dedicated ESG/SRI-named managers
  n_filers_passive    breadth — passive complexes (near-saturated; expect a ceiling)
  log_shares_passive  depth   — log1p shares held by passive complexes  ← sharpest
  log_shares_esg      depth   — log1p shares held by ESG-named managers

The same decision rule applies: an effect is "supported" only if positive, p<.05,
and the ESG arm's pre-trends pass. Honest read of the measurement: 13F is filed at
the manager level, so ``*_esg`` captures ESG-branded firms only (not ESG sleeves of
BlackRock/Vanguard) — see ``edgar_13f_byfiler`` caveat.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.estimate.did import RESULTS_DIR, esg_specific_contrast
from src.utils.paths import DATA_INTERIM, DATA_PROCESSED

H4_OUTCOMES = ("n_filers_esg", "n_filers_passive", "log_shares_passive", "log_shares_esg")

_TYPE_COLS = ["n_filers_total", "n_filers_esg", "n_filers_passive",
              "shares_total", "shares_esg", "shares_passive"]


def load_h4_panel(panel_path: str = "data/processed/panel.parquet",
                  byfiler_path: str | None = None) -> pd.DataFrame:
    """Frozen panel + filer-type columns, merged on (cusip, q_idx).

    Filer-type counts/shares are 0-filled where a (cusip, quarter) carried no filer
    of that type (a genuine zero, not missing — panel rows exist only where the name
    was held). Adds ``log_shares_passive``/``log_shares_esg`` = log1p(shares_*) and
    the ``n_filers_active``/``n_filers_nonesg`` complements.
    """
    byfiler_path = byfiler_path or str(DATA_INTERIM / "holdings_13f_byfiler.parquet")
    panel = pd.read_parquet(panel_path)
    bf = pd.read_parquet(byfiler_path)
    bf = bf.copy()
    bf["q_idx"] = bf["period"].dt.year * 4 + bf["period"].dt.quarter
    bf["cusip"] = bf["cusip"].astype(str)

    merged = panel.merge(bf[["cusip", "q_idx"] + _TYPE_COLS],
                         on=["cusip", "q_idx"], how="left")
    for c in _TYPE_COLS:
        merged[c] = merged[c].fillna(0.0)
    merged["n_filers_active"] = merged["n_filers_total"] - merged["n_filers_passive"]
    merged["n_filers_nonesg"] = merged["n_filers_total"] - merged["n_filers_esg"]
    merged["log_shares_passive"] = np.log1p(merged["shares_passive"])
    merged["log_shares_esg"] = np.log1p(merged["shares_esg"])
    return merged


def run_h4(panel_aug: pd.DataFrame, *, control_pool: str = "matched_cem",
           outcomes=H4_OUTCOMES) -> pd.DataFrame:
    """ESG-vs-S&P placebo contrast (matched Sun-Abraham) for each filer-type
    outcome. One row per outcome; columns are ``esg_specific_contrast`` keys."""
    rows = [esg_specific_contrast(panel_aug, outcome, control_pool=control_pool)
            for outcome in outcomes]
    return pd.DataFrame(rows)


def main(panel_path: str = "data/processed/panel.parquet",
         byfiler_path: str | None = None) -> None:
    panel_aug = load_h4_panel(panel_path, byfiler_path)
    res = run_h4(panel_aug)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "h4_filer.csv"
    res.to_csv(out, index=False)

    print(f"\nH4 — filer-type ESG-specific contrast (matched CEM, post 0..4)  -> {out}")
    show = res[["outcome", "att_esg", "se_esg", "att_sp500", "se_sp500",
                "esg_specific", "se", "p_value", "esg_pretrend_pass", "supported"]]
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(show.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    any_pos = res["supported"].any()
    print(f"\n{'>>' if any_pos else '--'} ESG-specific effect supported for "
          f"{int(res['supported'].sum())}/{len(res)} filer-type outcomes.")


if __name__ == "__main__":
    main()
