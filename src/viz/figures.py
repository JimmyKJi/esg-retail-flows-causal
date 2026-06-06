"""Figures for the writeup (Phase 3).

Reads the tidy estimation outputs written by ``src.estimate.did`` (results/)
and renders three headline exhibits to paper/figures/:

  * event_study.png    — ESG-inclusion event study for breadth (#filers) and
                         depth (log shares): the headline matched-control CS and
                         Sun-Abraham coefficients with 95% CIs, with the
                         confounded full-control CS line shown faded for contrast;
  * esg_vs_placebo.png — H2: the ESG arm beside the S&P 500 placebo arm, same
                         estimator, with the windowed ESG-specific contrast;
  * decay.png          — H3: early- vs late-cohort (pre/post-2022Q1) windowed
                         post-ATT, the legitimacy-decay test.

A companion ``write_tables()`` emits markdown versions of the summary / H2 / H3
tables to paper/tables/. Everything is reproducible from the saved results, so
the figures never re-fit a model. Matplotlib only (Agg backend; no display).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless; must precede pyplot import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.estimate.did import POST_WINDOW, RESULTS_DIR  # noqa: E402
from src.utils.paths import FIGURES, TABLES  # noqa: E402

OUTCOME_LABEL = {
    "n_filers": "Breadth — number of 13F filers",
    "log_shares": "Depth — log aggregate shares held",
    "log_value": "log aggregate $ value held",
}
_C = {"cs_matched": "#1f77b4", "sa_matched": "#d62728",
      "cs_full": "#9e9e9e", "esg": "#1f77b4", "sp500": "#ff7f0e",
      "early": "#1f77b4", "late": "#d62728"}

try:
    plt.style.use("seaborn-v0_8-whitegrid")
except Exception:  # pragma: no cover - style availability is cosmetic
    pass


# ── helpers ───────────────────────────────────────────────────────────────────
def _load_es() -> pd.DataFrame:
    p = RESULTS_DIR / "event_studies.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} not found — run `make estimate` first.")
    return pd.read_parquet(p)


def _read_csv(name):
    p = RESULTS_DIR / name
    return pd.read_csv(p) if p.exists() else None


def _slice(es: pd.DataFrame, estimator: str, arm: str, outcome: str,
           pool: str) -> pd.DataFrame:
    d = es[(es["estimator"] == estimator) & (es["arm"] == arm)
           & (es["outcome"] == outcome) & (es["control_pool"] == pool)]
    return d.sort_values("event_time")


def _draw(ax, d, *, label, color, band=True, ls="-", marker="o", alpha_band=0.15):
    if d.empty:
        return
    x = d["event_time"].to_numpy(float)
    y = d["att"].to_numpy(float)
    ax.plot(x, y, ls=ls, marker=marker, color=color, label=label,
            lw=1.8, ms=4, zorder=3)
    if band and {"lo", "hi"} <= set(d.columns):
        ax.fill_between(x, d["lo"].to_numpy(float), d["hi"].to_numpy(float),
                        color=color, alpha=alpha_band, lw=0, zorder=1)


def _decorate(ax, d_for_xlim):
    ax.axhline(0, color="k", lw=0.8, zorder=2)
    ax.axvline(-1, color="k", lw=0.6, ls=":", zorder=2)          # reference period
    if not d_for_xlim.empty:
        xlo = float(d_for_xlim["event_time"].min())
        ax.axvspan(xlo - 0.5, -1.5, color="#ffcc80", alpha=0.18, lw=0,
                   zorder=0)                                       # pre-period
    ax.set_xlabel("event time (quarters from inclusion)")


# ── Figure 1: headline event study (ESG arm) ──────────────────────────────────
def event_study_plot(es: pd.DataFrame | None = None,
                     outpath=FIGURES / "event_study.png"):
    es = _load_es() if es is None else es
    outs = ["n_filers", "log_shares"]
    fig, axes = plt.subplots(1, len(outs), figsize=(6.4 * len(outs), 4.7))
    axes = np.atleast_1d(axes)
    for ax, o in zip(axes, outs):
        cs_full = _slice(es, "callaway_santanna", "esg", o, "full")
        cs_m = _slice(es, "callaway_santanna", "esg", o, "matched_cem")
        _draw(ax, cs_full, label="CS — full controls (confounded)",
              color=_C["cs_full"], band=False, ls=":", marker="")
        _draw(ax, cs_m, label="CS — matched (headline)", color=_C["cs_matched"])
        _draw(ax, _slice(es, "sun_abraham", "esg", o, "matched_cem"),
              label="Sun-Abraham — matched", color=_C["sa_matched"],
              band=False, ls="--", marker="s")
        _decorate(ax, cs_m if not cs_m.empty else cs_full)
        ax.set_title(OUTCOME_LABEL.get(o, o))
    axes[0].set_ylabel("ATT relative to e = -1")
    axes[0].legend(fontsize=8, loc="best", framealpha=0.9)
    fig.suptitle("ESG-Leaders inclusion — institutional-ownership event study",
                 fontweight="bold", y=1.02)
    fig.text(0.5, -0.04,
             "Pre-period (shaded) coefficients test parallel trends; matching "
             "balances the level at e=-1 but does not eliminate the pre-trend.",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return outpath


# ── Figure 2: ESG vs S&P 500 placebo (H2) ─────────────────────────────────────
def esg_vs_placebo_plot(es: pd.DataFrame | None = None,
                        outpath=FIGURES / "esg_vs_placebo.png"):
    es = _load_es() if es is None else es
    o = "n_filers"
    h2 = _read_csv("h2_esg_specific.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.7))
    for ax, arm, title in [(axes[0], "esg", "ESG-Leaders adds"),
                           (axes[1], "sp500", "S&P 500 adds (placebo)")]:
        cs = _slice(es, "callaway_santanna", arm, o, "matched_cem")
        _draw(ax, cs, label="CS — matched", color=_C[arm])
        _draw(ax, _slice(es, "sun_abraham", arm, o, "matched_cem"),
              label="Sun-Abraham — matched", color=_C["sa_matched"],
              band=False, ls="--", marker="s")
        _decorate(ax, cs)
        ax.set_title(title)
    axes[0].set_ylabel(f"ATT — {OUTCOME_LABEL[o]}")
    axes[0].legend(fontsize=8, loc="best", framealpha=0.9)
    lo, hi = POST_WINDOW
    sub = "" if h2 is None else _h2_caption(h2, o, lo, hi)
    fig.suptitle("H2 — ESG-specific effect vs mechanical index inclusion",
                 fontweight="bold", y=1.02)
    if sub:
        fig.text(0.5, -0.04, sub, ha="center", fontsize=9, color="#333")
    fig.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return outpath


def _h2_caption(h2, outcome, lo, hi):
    r = h2[h2["outcome"] == outcome]
    if r.empty:
        return ""
    r = r.iloc[0]
    verdict = "supported" if bool(r["supported"]) else "NOT supported"
    return (f"Windowed post-ATT (e={lo}..{hi}): ESG {r['att_esg']:+.1f} vs "
            f"S&P {r['att_sp500']:+.1f}  ->  ESG-specific = {r['esg_specific']:+.1f} "
            f"(se {r['se']:.1f}, p={r['p_value']:.3f}); H2 {verdict}. "
            f"Pre-trends {'pass' if bool(r['esg_pretrend_pass']) else 'FAIL'} (ESG arm).")


# ── Figure 3: legitimacy decay (H3) ───────────────────────────────────────────
def decay_plot(outpath=FIGURES / "decay.png"):
    h3 = _read_csv("h3_decay.csv")
    if h3 is None or h3.empty:
        raise FileNotFoundError("results/h3_decay.csv not found — run estimate.")
    outs = list(h3["outcome"])
    fig, axes = plt.subplots(1, len(outs), figsize=(5.6 * len(outs), 4.6))
    axes = np.atleast_1d(axes)
    for ax, (_, r) in zip(axes, h3.iterrows()):
        ax.errorbar([0], [r["att_early"]], yerr=[1.96 * r["se_early"]], fmt="o",
                    ms=8, capsize=4, color=_C["early"], label="early (<2022Q1)")
        ax.errorbar([1], [r["att_late"]], yerr=[1.96 * r["se_late"]], fmt="s",
                    ms=8, capsize=4, color=_C["late"], label="late (>=2022Q1)")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xlim(-0.5, 1.5)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["early\n(<2022Q1)", "late\n(>=2022Q1)"])
        verdict = "decay" if bool(r["supported"]) else "no sig. decay"
        ax.set_title(f"{OUTCOME_LABEL.get(r['outcome'], r['outcome'])}\n"
                     f"Δ(late-early)={r['decay']:+.2f} "
                     f"(p={r['p_value']:.3f}; {verdict})", fontsize=9)
    axes[0].set_ylabel("windowed post-ATT")
    axes[0].legend(fontsize=8, loc="best")
    fig.suptitle("H3 — ESG-legitimacy decay: inclusion effect by cohort era",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return outpath


# ── Figure 4: H4 filer-type ESG-specific contrast (forest) ────────────────────
_H4_LABEL = {
    "n_filers_esg": "ESG-named managers\n(breadth)",
    "n_filers_passive": "passive complexes\n(breadth)",
    "log_shares_passive": "passive complexes\n(depth, log shares)",
    "log_shares_esg": "ESG-named managers\n(depth, log shares)",
}


def h4_filer_plot(outpath=FIGURES / "h4_filer.png"):
    """H4: ESG-specific contrast (ESG arm − S&P placebo) by filer type, with 95%
    CIs. Faceted into breadth (counts) and depth (log shares) panels because the
    units differ. A positive bar clear of zero would mean ESG inclusion draws that
    filer type *specifically* — the composition shift the flat aggregate might hide.
    """
    h4 = _read_csv("h4_filer.csv")
    if h4 is None or h4.empty:
        raise FileNotFoundError("results/h4_filer.csv not found — run h4_filer.")
    panels = [("breadth — # distinct filers", ["n_filers_esg", "n_filers_passive"]),
              ("depth — log shares held", ["log_shares_passive", "log_shares_esg"])]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.2))
    for ax, (title, outs) in zip(axes, panels):
        d = h4[h4["outcome"].isin(outs)].set_index("outcome").reindex(outs).dropna(how="all")
        ys = np.arange(len(d))[::-1]
        for y, (o, r) in zip(ys, d.iterrows()):
            col = "#2ca02c" if bool(r["supported"]) else "#d62728"
            ax.errorbar(r["esg_specific"], y, xerr=1.96 * r["se"], fmt="o",
                        ms=7, capsize=4, color=col, lw=1.8, zorder=3)
            ax.annotate(f"p={r['p_value']:.2f}", (r["esg_specific"], y),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=8, color="#555")
        ax.axvline(0, color="k", lw=0.9, zorder=2)
        ax.set_yticks(ys)
        ax.set_yticklabels([_H4_LABEL.get(o, o) for o in d.index], fontsize=9)
        ax.set_ylim(-0.6, len(d) - 0.4)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("ESG-specific effect (ESG − S&P placebo)")
    fig.suptitle("H4 — does ESG / passive demand respond specifically to ESG inclusion?",
                 fontweight="bold", y=1.03)
    fig.text(0.5, -0.06,
             "Matched Sun-Abraham, windowed post-ATT (e=0..4). Green = positive & "
             "significant with ESG pre-trend passing; red otherwise. 13F is filed at "
             "the manager level, so ESG-named = ESG-branded firms, not ESG sleeves of "
             "large complexes (those surface as passive depth).",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return outpath


# ── markdown tables for the writeup ───────────────────────────────────────────
def write_tables(outdir=TABLES):
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, title in [("summary.csv", "Event-study summary (per outcome x arm)"),
                        ("h2_esg_specific.csv", "H2 — ESG-specific contrast"),
                        ("h3_decay.csv", "H3 — legitimacy decay"),
                        ("h4_filer.csv", "H4 — filer-type ESG-specific contrast")]:
        df = _read_csv(name)
        if df is None:
            continue
        md = f"### {title}\n\n{df.round(3).to_markdown(index=False)}\n"
        dst = outdir / name.replace(".csv", ".md")
        dst.write_text(md)
        written.append(dst)
    return written


def main():
    es = _load_es()
    paths = [event_study_plot(es), esg_vs_placebo_plot(es), decay_plot()]
    if (RESULTS_DIR / "h4_filer.csv").exists():       # Phase 5, optional
        paths.append(h4_filer_plot())
    paths += write_tables()
    for p in paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
