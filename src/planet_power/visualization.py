"""Scatter plot generation for exoplanet data."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams
from matplotlib.colors import to_rgba
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# Force font configuration for Noto Sans Math and Noto Sans
# This ensures the \u2A40 intersection character renders correctly.
rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Noto Sans Math", "Noto Sans", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False  # Improve math symbol rendering


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
    width_px: int = 1280,
    height_px: int = 720,
    dpi: int = 100,
    error_cross: bool = False,
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
        # Transition from White (1,1,1) to Red (1,0,0)
        rgba_x_err = np.column_stack([np.ones_like(wx), 1.0 - wx, 1.0 - wx, wx])

        # 2. Vertical Error Color (Y-axis reliability: Blue)
        # Transition from White (1,1,1) to Blue (0,0,1)
        rgba_y_err = np.column_stack([1.0 - wy, 1.0 - wy, np.ones_like(wy), wy])

        # 3. Scatter Point Color (Additive intersection mix)
        # Alpha is the arithmetic mean of the two weights
        rgba_points = np.column_stack([wx, np.zeros_like(wx), wy, (wx + wy) / 2.0])
    else:
        # Fallback if no weights are provided
        alphas = np.full(len(df), 0.4)
        rgba_points = [to_rgba(point_color, a) for a in alphas]
        rgba_x_err = [to_rgba(x_err_color, a) for a in alphas]
        rgba_y_err = [to_rgba(y_err_color, a) for a in alphas]
        wx, wy = None, None

    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)

    # Ensure white background for the 'fade to white' reliability effect
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = df[x_col].values
    y = df[y_col].values

    # Draw error crosses
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

    # Plot scatter points on top of the crosses
    ax.scatter(x, y, color=rgba_points, s=10, zorder=3)

    # Frequency Distribution Insets
    if wx is not None and wy is not None:
        bins = np.linspace(0, 1, 11)

        # X Weighting Distribution (Red)
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
        ax_ins_x.set_title("X Weight Distribution", fontsize=8, color="red", pad=2)
        ax_ins_x.tick_params(axis="both", which="both", labelsize=6, length=2)
        ax_ins_x.set_xticks([0, 0.5, 1])

        # Y Weighting Distribution (Blue)
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
        ax_ins_y.set_title("Y Weight Distribution", fontsize=8, color="blue", pad=2)
        ax_ins_y.tick_params(axis="both", which="both", labelsize=6, length=2)
        ax_ins_y.set_xticks([0, 0.5, 1])

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)

    # Title includes the intersection character \u2A40
    ax.set_title(f"{x_col} \u2a40 {y_col} {len(x)} planets (Reliability Mapping)")

    # Manual margin adjustment to silence tight_layout warnings and prevent clipping
    plt.subplots_adjust(left=0.08, right=0.96, top=0.94, bottom=0.08)

    plt.savefig(output_path)
    plt.close()
