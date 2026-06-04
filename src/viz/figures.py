"""Figures for the writeup (Phase 3-6).

Three headline exhibits, all saved to paper/figures/:
  * event_study_plot   — inclusion event-study coefficients with 95% CIs;
  * esg_vs_placebo_plot — ESG inclusion effect vs S&P 500 placebo, side by side;
  * decay_plot         — inclusion effect by period, showing the post-2022 fall.

Matplotlib + seaborn; reproducible from the saved estimation outputs.
"""

from __future__ import annotations

from src.utils.paths import FIGURES


def event_study_plot(estimates: dict, outpath=FIGURES / "event_study.png"):
    raise NotImplementedError("Phase 3.")


def esg_vs_placebo_plot(contrast: dict, outpath=FIGURES / "esg_vs_placebo.png"):
    raise NotImplementedError("Phase 4.")


def decay_plot(decay: dict, outpath=FIGURES / "decay.png"):
    raise NotImplementedError("Phase 5.")
