"""Scatter plot generation for exoplanet data with reliability-based color mapping."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import os
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams
from matplotlib.colors import to_rgba
from numpy.typing import NDArray

# Force font configuration for Noto Sans Math and Noto Sans
# This ensures the \u2A40 intersection character renders correctly.
rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Noto Sans Math", "Noto Sans"]
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
    x_axis_min: float | None = 1e20,
    x_axis_max: float | None = 1e30,
    y_weight_col: Optional[str] = None,
    y_hexcolor: str = "#00FF00",
    y_axis_min: float | None = 1e5,
    y_axis_max: float | None = 1e9,
    # New parameter for the fit results from run_bayesian_slice()
    fit_params: Optional[Dict[str, float]] = None,
    default_color: str = "#02BEFD",
    width_px: int = 1920,
    height_px: int = 1080,
    dpi: int = 75,
    error_cross: bool = False,
) -> None:
    """
    Generate a high-resolution scatter plot using hex gradients for reliability mapping.
    Includes an optional Bayesian regression line and uncertainty wedge.
    """

    # Prepare color arrays
    if x_weight_col and y_weight_col:
        # Convert weight columns to numeric and clamp to [0, 1]
        wx: Optional[NDArray[np.float64]] = np.clip(
            pd.to_numeric(df[x_weight_col], errors="coerce").fillna(0).values, 0, 1
        )
        wy: Optional[NDArray[np.float64]] = np.clip(
            pd.to_numeric(df[y_weight_col], errors="coerce").fillna(0).values, 0, 1
        )

        # Generate colors using the gradient function
        # Horizontal Errors: White to x_hexcolor
        rgba_x_err: List[Tuple[float, float, float, float]] = [
            to_rgba(get_hex_gradient("#FFFFFF", x_hexcolor, w), alpha=w) for w in wx  # type: ignore[union-attr]
        ]

        # Vertical Errors: White to y_hexcolor
        rgba_y_err: List[Tuple[float, float, float, float]] = [
            to_rgba(get_hex_gradient("#FFFFFF", y_hexcolor, w), alpha=w) for w in wy  # type: ignore[union-attr]
        ]

        # Scatter Points: Gradient between the two primary colors based on Y/X balance
        # Alpha is the arithmetic mean of the weights
        rgba_points: List[Tuple[float, float, float, float]] = []
        for i in range(len(wx)):  # type: ignore[arg-type]
            balance: float = wy[i] / (wx[i] + wy[i]) if (wx[i] + wy[i]) > 0 else 0.5  # type: ignore[index]
            point_hex: str = get_hex_gradient(x_hexcolor, y_hexcolor, balance)
            rgba_points.append(to_rgba(point_hex, alpha=(wx[i] + wy[i]) / 2.0))  # type: ignore[index]
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
        x_min_err: NDArray[np.float64] = x - np.abs(
            pd.to_numeric(df[x_err_minus_col], errors="coerce").fillna(0).values
        )
        x_max_err: NDArray[np.float64] = x + np.abs(
            pd.to_numeric(df[x_err_plus_col], errors="coerce").fillna(0).values
        )
        y_min_err: NDArray[np.float64] = y - np.abs(
            pd.to_numeric(df[y_err_minus_col], errors="coerce").fillna(0).values
        )
        y_max_err: NDArray[np.float64] = y + np.abs(
            pd.to_numeric(df[y_err_plus_col], errors="coerce").fillna(0).values
        )

        ax.hlines(y, x_min_err, x_max_err, colors=rgba_x_err, linewidth=1)
        ax.vlines(x, y_min_err, y_max_err, colors=rgba_y_err, linewidth=1)

    ax.scatter(x, y, color=rgba_points, s=20, zorder=3)

    # --- DRAW THE REGRESSION LINE & BACKGROUND BAND ---
    if fit_params and not np.isnan(fit_params["b"]):
        a_val: float = fit_params["a"]
        b_val: float = fit_params["b"]
        b_std: float = fit_params["b_std"]

        # 1. Extract the mass limits for the slice
        m_min = fit_params.get("m_lower_limit")
        m_max = fit_params.get("m_upper_limit")

        # 2. Draw the vertical background band (The "slice highlight")
        # if m_min is not None and m_max is not None:
        #     # This fills the background between m_lower_limit and m_upper_limit
        #     # zorder=1 places it behind the data points (zorder=3)
        #     ax.axvspan(
        #         m_min,
        #         m_max,
        #         color="#FFFF00",  # Subtle light gray
        #         alpha=0.3,
        #         zorder=1,
        #         label="Analysis Range",
        #     )

        # 3. Best-fit regression line (Full range for context)
        x_draw_min = x_axis_min if x_axis_min else np.nanmin(x)
        x_draw_max = x_axis_max if x_axis_max else np.nanmax(x)
        m_line = np.logspace(np.log10(x_draw_min), np.log10(x_draw_max), 100)
        r_line = a_val * (m_line**b_val)

        ax.plot(
            m_line,
            r_line,
            color="black",
            alpha=0.6,
            linewidth=3,
            linestyle="--",
            label=(
                f"Fit: $b={b_val:.3f} \\pm {b_std:.3f}$ "
                f"(BRE: {b_std/abs(b_val):.3f}, SNR: {abs(b_val)/b_std:.1f})"
            ),
            zorder=5,
        )

        # 4. Uncertainty wedge restricted to the slice
        if m_min is not None and m_max is not None:
            m_wedge = np.logspace(np.log10(m_min), np.log10(m_max), 100)
            r_low = a_val * (m_wedge ** (b_val - b_std))
            r_high = a_val * (m_wedge ** (b_val + b_std))

            ax.fill_between(
                m_wedge, r_low, r_high, color="lightskyblue", alpha=0.1, zorder=4
            )

    # Frequency Distribution Insets
    if wx is not None and wy is not None:
        bins: NDArray[np.float64] = np.linspace(0, 1, 11)

        for weight, color, label, offset in [
            (wx, x_hexcolor, "X Weight", 0.6),
            (wy, y_hexcolor, "Y Weight", 0.8),
        ]:
            ax_ins = ax.inset_axes((0.05, offset, 0.2, 0.15))
            counts, _ = np.histogram(weight, bins=bins)
            ax_ins.bar(
                bins[:-1], counts, width=0.08, color=color, align="edge", alpha=0.8
            )
            ax_ins.set_title(f"{label} Distribution", fontsize=14, pad=10)
            ax_ins.tick_params(axis="both", which="both", labelsize=10, length=4)
            ax_ins.set_xticks([0, 0.5, 1])

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.tick_params(which="major", axis="both", labelsize=16, width=2, length=8, pad=10)
    ax.tick_params(which="minor", axis="both", width=1, length=4)

    if x_axis_min is not None:
        ax.set_xlim(left=x_axis_min)
    if x_axis_max is not None:
        ax.set_xlim(right=x_axis_max)
    if y_axis_min is not None:
        ax.set_ylim(bottom=y_axis_min)
    if y_axis_max is not None:
        ax.set_ylim(top=y_axis_max)

    ax.set_xlabel(x_col, fontsize=24)
    ax.set_ylabel(y_col, fontsize=24)

    # Title includes the intersection character \u2A40
    ax.set_title(
        f"{x_col} \u2a40 {y_col} {len(x)} planets (Reliability Mapping)",
        fontsize=32,
        pad=20,
    )

    if fit_params and not np.isnan(fit_params.get("b", np.nan)):
        ax.legend(loc="lower right", fontsize=16)

    plt.subplots_adjust(left=0.08, right=0.96, top=0.94, bottom=0.08)
    plt.savefig(output_path)
    plt.close()
    print(f"Scatter plot graph written to '{os.path.relpath(output_path)}'")
