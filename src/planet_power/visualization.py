"""Scatter plot generation for exoplanet data."""

from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes


def save_scatter_png(
    df: pd.DataFrame,
    output_path: str,
    x_col: str,
    x_err_plus_col: str,
    x_err_minus_col: str,
    y_col: str,
    y_err_plus_col: str,
    y_err_minus_col: str,
    point_color: str = "#027BA3",
    x_err_color: str = "#027BA3",
    y_err_color: str = "#027BA3",
    width_px: int = 1920,
    height_px: int = 1080,
) -> None:
    """
    Save a log-log scatter plot with error crosses to a PNG file.

    Parameters
    ----------
    df : DataFrame containing the data columns.
    output_path : Full path to the output .png file.
    x_col : Column name for x-axis data points.
    x_err_plus_col : Column name for positive x-axis uncertainties.
    x_err_minus_col : Column name for negative x-axis uncertainties (stored as
        negative numbers; absolute values are used automatically).
    y_col : Column name for y-axis data points.
    y_err_plus_col : Column name for positive y-axis uncertainties.
    y_err_minus_col : Column name for negative y-axis uncertainties (stored as
        negative numbers; absolute values are used automatically).
    point_color : Matplotlib colour for the data point markers (default: #027BA3).
    x_err_color : Matplotlib colour for horizontal error bars (default: #027BA3).
    y_err_color : Matplotlib colour for vertical error bars (default: #027BA3).
    width_px : Output image width in pixels (default: 1920).
    height_px : Output image height in pixels (default: 1080).
    """
    warnings.filterwarnings("ignore", module="matplotlib")

    x_vals = pd.to_numeric(df[x_col], errors="coerce")
    y_vals = pd.to_numeric(df[y_col], errors="coerce")

    valid = (x_vals > 0) & (y_vals > 0) & np.isfinite(x_vals) & np.isfinite(y_vals)
    df = df[valid]
    if len(df) == 0:
        print(f"\tNo valid data to plot for {x_col} vs {y_col}")
        return

    dpi = 100
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)  # type: ignore[reportUnknownMemberType]
    assert isinstance(ax, Axes)

    x = df[x_col].values
    y = df[y_col].values
    xerr = [
        np.abs(pd.to_numeric(df[x_err_minus_col], errors="coerce").fillna(0).values),
        np.abs(pd.to_numeric(df[x_err_plus_col], errors="coerce").fillna(0).values),
    ]
    yerr = [
        np.abs(pd.to_numeric(df[y_err_minus_col], errors="coerce").fillna(0).values),
        np.abs(pd.to_numeric(df[y_err_plus_col], errors="coerce").fillna(0).values),
    ]

    # Plot points and error bars separately so each can carry its own colour.
    ax.errorbar(x, y, xerr=xerr, fmt="none", elinewidth=1.0, ecolor=x_err_color, capsize=2, alpha=0.4)  # type: ignore[reportArgumentType]
    ax.errorbar(x, y, yerr=yerr, fmt="none", elinewidth=1.0, ecolor=y_err_color, capsize=2, alpha=0.4)  # type: ignore[reportArgumentType]
    ax.scatter(x, y, color=point_color, s=5, alpha=0.4, zorder=3)  # type: ignore[reportUnknownMemberType]

    ax.set_xscale("log")  # type: ignore[reportUnknownMemberType]
    ax.set_yscale("log")  # type: ignore[reportUnknownMemberType]
    ax.set_xlabel(x_col)  # type: ignore[reportUnknownMemberType]
    ax.set_ylabel(y_col)  # type: ignore[reportUnknownMemberType]
    ax.set_title(f"{x_col} vs {y_col}, {len(x)} points")  # type: ignore[reportUnknownMemberType]

    plt.tight_layout()
    plt.savefig(output_path)  # type: ignore[reportUnknownMemberType]
    plt.close()
