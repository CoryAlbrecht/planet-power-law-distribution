"""Scatter plot generation for exoplanet data."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


def save_scatter_png(
    df: pd.DataFrame,
    output_path: str,
    x_col: str,
    x_err_plus_col: str,
    x_err_minus_col: str,
    y_col: str,
    y_err_plus_col: str,
    y_err_minus_col: str,
    x_weight_col: str | None = None,
    y_weight_col: str | None = None,
    point_color: str = "#027BA3",
    x_err_color: str = "#027BA3",
    y_err_color: str = "#027BA3",
    width_px: int = 3840,
    height_px: int = 2160,
    error_cross: bool = True,
) -> None:
    """
    Generate a high-resolution scatter plot with axis-specific reliability colors,
    mean-based point alpha, and inset distribution bar charts.
    """

    if x_weight_col and y_weight_col:
        # Convert weight columns to numeric and clamp to [0, 1]
        wx = np.clip(
            pd.to_numeric(df[x_weight_col], errors="coerce").fillna(0).values, 0, 1
        )
        wy = np.clip(
            pd.to_numeric(df[y_weight_col], errors="coerce").fillna(0).values, 0, 1
        )

        # 1. Horizontal Error Color (X-axis reliability: Red)
        rgba_x_err = np.column_stack([np.ones_like(wx), 1.0 - wx, 1.0 - wx, wx])

        # 2. Vertical Error Color (Y-axis reliability: Blue)
        rgba_y_err = np.column_stack([1.0 - wy, 1.0 - wy, np.ones_like(wy), wy])

        # 3. Scatter Point Color (Additive intersection mix)
        # Alpha is the ARITHMETIC MEAN of both weightings.
        rgba_points = np.column_stack([wx, np.zeros_like(wx), wy, (wx + wy) / 2.0])
    else:
        # Fallback logic
        alphas = np.full(len(df), 0.4)
        rgba_points = [to_rgba(point_color, a) for a in alphas]
        rgba_x_err = [to_rgba(x_err_color, a) for a in alphas]
        rgba_y_err = [to_rgba(y_err_color, a) for a in alphas]
        wx = None
        wy = None

    dpi = 150
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = df[x_col].values
    y = df[y_col].values

    if error_cross:
        x_min = x - np.abs(
            pd.to_numeric(df[x_err_minus_col], errors="coerce").fillna(0).values
        )
        x_max = x + np.abs(
            pd.to_numeric(df[x_err_plus_col], errors="coerce").fillna(0).values
        )
        y_min = y - np.abs(
            pd.to_numeric(df[y_err_minus_col], errors="coerce").fillna(0).values
        )
        y_max = y + np.abs(
            pd.to_numeric(df[y_err_plus_col], errors="coerce").fillna(0).values
        )

        ax.hlines(y, x_min, x_max, colors=rgba_x_err, linewidth=1, alpha=None)
        ax.vlines(x, y_min, y_max, colors=rgba_y_err, linewidth=1, alpha=None)

    ax.scatter(x, y, color=rgba_points, s=10, zorder=3)

    # Inset Bar Graphs for Weight Distributions
    if wx is not None and wy is not None:
        # Decile bins: 0-0.1, 0.1-0.2, ..., 0.9-1.0
        bins = np.linspace(0, 1, 11)

        # Inset for X Weightings (Red)
        ax_ins_x = inset_axes(
            ax,
            width="20%",
            height="15%",
            loc="upper left",
            bbox_to_anchor=(0.02, -0.02, 1, 1),
            bbox_transform=ax.transAxes,
        )
        counts_x, _ = np.histogram(wx, bins=bins)
        ax_ins_x.bar(
            bins[:-1], counts_x, width=0.08, color="red", align="edge", alpha=0.8
        )
        ax_ins_x.set_title("X Weight Dist", fontsize=8, color="red", pad=2)
        ax_ins_x.tick_params(axis="both", which="both", labelsize=6, length=2)
        ax_ins_x.set_xticks([0, 0.5, 1])

        # Inset for Y Weightings (Blue) - Positioned below the first inset
        ax_ins_y = inset_axes(
            ax,
            width="20%",
            height="15%",
            loc="upper left",
            bbox_to_anchor=(0.02, -0.22, 1, 1),
            bbox_transform=ax.transAxes,
        )
        counts_y, _ = np.histogram(wy, bins=bins)
        ax_ins_y.bar(
            bins[:-1], counts_y, width=0.08, color="blue", align="edge", alpha=0.8
        )
        ax_ins_y.set_title("Y Weight Dist", fontsize=8, color="blue", pad=2)
        ax_ins_y.tick_params(axis="both", which="both", labelsize=6, length=2)
        ax_ins_y.set_xticks([0, 0.5, 1])

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)

    # Utilizing the intersection character \u2A40 as you previously suggested
    ax.set_title(f"{x_col} vs {y_col} \u2a40 {len(x)} points (Mean Reliability Alpha)")

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
