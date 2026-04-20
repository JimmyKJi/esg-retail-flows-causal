"""
Visualisation helpers.

Consistent chart styling across the write-up. All figures are saved to
/results/figures at 300 dpi PNG and as vector SVG.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

FIG_DIR = Path(__file__).resolve().parent.parent / "results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def set_default_style() -> None:
    """Apply a consistent, publication-ready matplotlib style."""
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "legend.frameon": False,
    })


def plot_event_study_coefficients(
    coefficients: pd.DataFrame,
    title: str = "Event-study coefficients: institutional flows around ESG rating change",
    save_name: str = "event_study.png",
) -> None:
    """
    Plot event-time coefficients with 95% confidence intervals.

    Expects DataFrame with columns [event_time, coefficient, ci_lower, ci_upper].
    """
    raise NotImplementedError("Implement in notebook 05_results.")


def plot_flow_trajectory(
    trajectories: pd.DataFrame,
    title: str = "Mean institutional ownership: treated vs. control",
    save_name: str = "flow_trajectory.png",
) -> None:
    """Plot mean outcome trajectories for treated and control groups over event time."""
    raise NotImplementedError("Implement in notebook 05_results.")
