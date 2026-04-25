"""Scatter plot generation for exoplanet data with reliability-based color mapping."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional, List, Tuple, Any
from numpy.typing import NDArray
from matplotlib import rcParams
from matplotlib.colors import to_rgba

# from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# Force font configuration for Noto Sans Math and Noto Sans
# This ensures the \u2A40 intersection character renders correctly. [cite: 2026-01-25]
rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Noto Sans Math", "Noto Sans", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False  # Improve math symbol rendering


def get_hex_gradient(low_hex: str, high_hex: str, value: float) -> str:
    """
    Interpolates between two #RRGGBB colors.

    :param low_hex: String starting with '#' (e.g., "#FF0000")
    :param high_hex: String starting with '#' (e.g., "#0000FF")
    :param value: Float between 0.0 and 1.0
    :return: Hex string of the interpolated color
    """
    # Clamp the value between 0 and 1
    value = max(0.0, min(1.0, value))

    # Convert hex strings to (R, G, B) tuples
    low_rgb: Tuple[int, ...] = tuple(
        int(low_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
    )
    high_rgb: Tuple[int, ...] = tuple(
        int(high_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
    )

    # Calculate the interpolated RGB values
    res_rgb: List[int] = [
        int(low_rgb[i] + (high_rgb[i] - low_rgb[i]) * value) for i in range(3)
    ]

    # Convert back to #RRGGBB format
    return "#{:02x}{:02x}{:02x}".format(*res_rgb)


def save_scatter_png(
    df: pd.DataFrame,
    output_path: str,
    x_col: str,
    x_err_plus_col: str,
    x_err_minus_col: str,
    y_col: str,
    y_err_plus_col: str,
    y_err_minus_col: str,
    x_weight_col: Optional[str] = None,
    x_hexcolor: str = "#FF0000",
    x_axis_min: float | None = None,
    x_axis_max: float | None = None,
    y_weight_col: Optional[str] = None,
    y_hexcolor: str = "#00FF00",
    y_axis_min: float | None = None,
    y_axis_max: float | None = None,
    default_color: str = "#02BEFD",
    width_px: int = 3840,
    height_px: int = 2160,
    dpi: int = 150,
    error_cross: bool = False,
) -> None:
    """
    Generate a high-resolution scatter plot using hex gradients for reliability mapping.
    """

    # Prepare color arrays
    if x_weight_col and y_weight_col:
        # Convert weight columns to numeric and clamp to [0, 1]
        wx: NDArray[np.float64] = np.clip(
            pd.to_numeric(df[x_weight_col], errors="coerce").fillna(0).values, 0, 1
        )
        wy: NDArray[np.float64] = np.clip(
            pd.to_numeric(df[y_weight_col], errors="coerce").fillna(0).values, 0, 1
        )

        # Generate colors using the gradient function
        # Horizontal Errors: White to x_hexcolor (Red)
        rgba_x_err: List[Tuple[float, float, float, float]] = [
            to_rgba(get_hex_gradient("#FFFFFF", x_hexcolor, w), alpha=w) for w in wx
        ]

        # Vertical Errors: White to y_hexcolor (Blue)
        rgba_y_err: List[Tuple[float, float, float, float]] = [
            to_rgba(get_hex_gradient("#FFFFFF", y_hexcolor, w), alpha=w) for w in wy
        ]

        # Scatter Points: Gradient between the two primary colors based on Y/X balance
        # Alpha is the arithmetic mean of the weights
        rgba_points: List[Tuple[float, float, float, float]] = []
        for i in range(len(wx)):
            # Determine color bias based on which axis is more reliable
            balance: float = wy[i] / (wx[i] + wy[i]) if (wx[i] + wy[i]) > 0 else 0.5
            point_hex: str = get_hex_gradient(x_hexcolor, y_hexcolor, balance)
            rgba_points.append(to_rgba(point_hex, alpha=(wx[i] + wy[i]) / 2.0))
    else:
        # Fallback if no weights are provided
        fallback_rgba: Tuple[float, float, float, float] = to_rgba(default_color, 0.4)
        rgba_points = [fallback_rgba] * len(df)
        rgba_x_err = [fallback_rgba] * len(df)
        rgba_y_err = [fallback_rgba] * len(df)
        wx, wy = None, None

    fig: plt.Figure
    ax: plt.Axes
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x: NDArray[Any] = df[x_col].values
    y: NDArray[Any] = df[y_col].values

    if error_cross:
        x_min: NDArray[np.float64] = x - np.abs(
            pd.to_numeric(df[x_err_minus_col], errors="coerce").fillna(0).values
        )
        x_max: NDArray[np.float64] = x + np.abs(
            pd.to_numeric(df[x_err_plus_col], errors="coerce").fillna(0).values
        )
        y_min: NDArray[np.float64] = y - np.abs(
            pd.to_numeric(df[y_err_minus_col], errors="coerce").fillna(0).values
        )
        y_max: NDArray[np.float64] = y + np.abs(
            pd.to_numeric(df[y_err_plus_col], errors="coerce").fillna(0).values
        )

        ax.hlines(y, x_min, x_max, colors=rgba_x_err, linewidth=1)
        ax.vlines(x, y_min, y_max, colors=rgba_y_err, linewidth=1)

    ax.scatter(x, y, color=rgba_points, s=10, zorder=3)

    # Frequency Distribution Insets
    if wx is not None and wy is not None:
        bins: NDArray[np.float64] = np.linspace(0, 1, 11)

        for weight, color, label, offset in [
            (wx, x_hexcolor, "X Weight", -0.02),
            (wy, y_hexcolor, "Y Weight", -0.22),
        ]:
            # ax_ins = inset_axes(
            #     ax,
            #     width="20%",
            #     height="15%",
            #     loc="upper left",
            #     bbox_to_anchor=(0.02, offset, 1, 1),
            #     bbox_transform=ax.transAxes,
            # )
            ax_ins = ax.inset_axes([0.02, offset, 0.2, 0.15])
            counts, _ = np.histogram(weight, bins=bins)
            ax_ins.bar(
                bins[:-1], counts, width=0.08, color=color, align="edge", alpha=0.8
            )
            ax_ins.set_title(f"{label} Distribution", fontsize=8, color=color, pad=2)
            ax_ins.tick_params(axis="both", which="both", labelsize=6, length=2)
            ax_ins.set_xticks([0, 0.5, 1])

    ax.set_xscale("log")
    ax.set_yscale("log")

    if x_axis_min is not None:
        ax.set_xlim(left=x_axis_min)
    if x_axis_max is not None:
        ax.set_xlim(right=x_axis_max)
    if y_axis_min is not None:
        ax.set_ylim(bottom=y_axis_min)
    if y_axis_max is not None:
        ax.set_ylim(top=y_axis_max)

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)

    # Title includes the intersection character \u2A40
    ax.set_title(f"{x_col} \u2a40 {y_col} {len(x)} planets (Reliability Mapping)")

    plt.subplots_adjust(left=0.08, right=0.96, top=0.94, bottom=0.08)
    plt.savefig(output_path)
    plt.close()
