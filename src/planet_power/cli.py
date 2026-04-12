"""Command-line interface for the exoplanet data fetcher."""

from __future__ import annotations

import argparse
import os
import time
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")

import warnings
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from .fetch import fetch_data
from .compute import compute_surface_gravity, assign_dm_class
from .format import rename_columns, format_workbook

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)


def _make_timestamped_filename() -> str:
    """Generate timestamped filename like exoplanet_data.20260411T180234.xlsx"""
    ts = time.strftime("%Y%m%dT%H%M%S")
    return f"exoplanet_data.{ts}.xlsx"


DEFAULT_OUTPUT = _make_timestamped_filename()


def _save_scatter_png(
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
    point_color : Matplotlib colour for the data point markers (default: light blue).
    x_err_color : Matplotlib colour for horizontal error bars (default: light blue).
    y_err_color : Matplotlib colour for vertical error bars (default: light blue).
    width_px : Output image width in pixels (default: 1920).
    height_px : Output image height in pixels (default: 1080).
    """
    warnings.filterwarnings("ignore", module="matplotlib")

    # Convert to numeric and filter out invalid data (zeros, negative, inf, NaN)
    x_vals = pd.to_numeric(df[x_col], errors="coerce")
    y_vals = pd.to_numeric(df[y_col], errors="coerce")
    xep = pd.to_numeric(df[x_err_plus_col], errors="coerce")
    xem = pd.to_numeric(df[x_err_minus_col], errors="coerce")
    yep = pd.to_numeric(df[y_err_plus_col], errors="coerce")
    yem = pd.to_numeric(df[y_err_minus_col], errors="coerce")

    valid = (
        (x_vals > 0)
        & (y_vals > 0)
        & np.isfinite(x_vals)
        & np.isfinite(y_vals)
        & np.isfinite(xep)
        & np.isfinite(xem)
        & np.isfinite(yep)
        & np.isfinite(yem)
    )
    df = df[valid]
    if len(df) == 0:
        print(f"\tNo valid data to plot for {x_col} vs {y_col}")
        return

    dpi = 100
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)  # type: ignore[reportUnknownMemberType]
    assert isinstance(ax, Axes)

    x = df[x_col].values
    y = df[y_col].values
    xerr = [np.abs(df[x_err_minus_col].values), np.abs(df[x_err_plus_col].values)]
    yerr = [np.abs(df[y_err_minus_col].values), np.abs(df[y_err_plus_col].values)]

    # Plot points and error bars separately so each can carry its own colour.
    ax.errorbar(x, y, xerr=xerr, fmt="none", ecolor=x_err_color, capsize=2, alpha=0.4)  # type: ignore[reportArgumentType]
    ax.errorbar(x, y, yerr=yerr, fmt="none", ecolor=y_err_color, capsize=2, alpha=0.4)  # type: ignore[reportArgumentType]
    ax.scatter(x, y, color=point_color, s=5, alpha=0.4, zorder=3)  # type: ignore[reportUnknownMemberType]

    ax.set_xscale("log")  # type: ignore[reportUnknownMemberType]
    ax.set_yscale("log")  # type: ignore[reportUnknownMemberType]
    ax.set_xlabel(x_col)  # type: ignore[reportUnknownMemberType]
    ax.set_ylabel(y_col)  # type: ignore[reportUnknownMemberType]
    ax.set_title(f"{x_col} vs {y_col}")  # type: ignore[reportUnknownMemberType]

    plt.tight_layout()
    plt.savefig(output_path)  # type: ignore[reportUnknownMemberType]
    plt.close()


def _create_split_files(
    df: pd.DataFrame, timestamp: str, filter_rows: bool = False
) -> None:
    """Create split files for mass-vs-radius, mass-vs-density, mass-vs-surface-gravity."""
    if filter_rows:
        timestamp_filtered = f"{timestamp}.filter"
        mask = (
            ~df.astype(str)
            .apply(lambda col: col.str.contains("CALCULATED_VALUE", na=False))  # type: ignore[reportUnknownArgumentType]
            .any(axis=1)
        )
        df = df[mask]
        print(f"\tFiltered to {len(df):,} rows (removed CALCULATED_VALUE)")
    else:
        timestamp_filtered = timestamp
    splits: list[dict[str, Any]] = [
        {
            "stem": "mass-vs-radius",
            "cols": [
                "Planet Name",
                "Mass (kg)",
                "Mass Err+ (kg)",
                "Mass Err- (kg)",
                "Mass Ref (M_Jup)",
                "Radius (m)",
                "Radius Err+ (m)",
                "Radius Err- (m)",
                "Radius Ref (R_Jup)",
            ],
            "x_col": "Mass (kg)",
            "x_err_plus_col": "Mass Err+ (kg)",
            "x_err_minus_col": "Mass Err- (kg)",
            "y_col": "Radius (m)",
            "y_err_plus_col": "Radius Err+ (m)",
            "y_err_minus_col": "Radius Err- (m)",
        },
        {
            "stem": "mass-vs-density",
            "cols": [
                "Planet Name",
                "Mass (kg)",
                "Mass Err+ (kg)",
                "Mass Err- (kg)",
                "Mass Ref (M_Jup)",
                "Density (g/cm³)",
                "Density Err+ (g/cm³)",
                "Density Err- (g/cm³)",
                "Density Ref",
            ],
            "x_col": "Mass (kg)",
            "x_err_plus_col": "Mass Err+ (kg)",
            "x_err_minus_col": "Mass Err- (kg)",
            "y_col": "Density (g/cm³)",
            "y_err_plus_col": "Density Err+ (g/cm³)",
            "y_err_minus_col": "Density Err- (g/cm³)",
        },
        {
            "stem": "mass-vs-surface-gravity",
            "cols": [
                "Planet Name",
                "Mass (kg)",
                "Mass Err+ (kg)",
                "Mass Err- (kg)",
                "Mass Ref (M_Jup)",
                "Surface Gravity (m/s²)",
                "Surf. Grav. Err+ (m/s²)",
                "Surf. Grav. Err- (m/s²)",
            ],
            "x_col": "Mass (kg)",
            "x_err_plus_col": "Mass Err+ (kg)",
            "x_err_minus_col": "Mass Err- (kg)",
            "y_col": "Surface Gravity (m/s²)",
            "y_err_plus_col": "Surf. Grav. Err+ (m/s²)",
            "y_err_minus_col": "Surf. Grav. Err- (m/s²)",
        },
    ]

    for split in splits:
        base_path = os.path.join(DATA_DIR, f"{split['stem']}.{timestamp_filtered}")
        df_split = cast(pd.DataFrame, df[split["cols"]])

        df_split.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")  # type: ignore[reportUnknownMemberType]
        df_split.to_csv(f"{base_path}.csv", index=False, quoting=1, encoding="utf-8")  # type: ignore[reportUnknownMemberType]
        format_workbook(f"{base_path}.xlsx", len(df_split))

        _save_scatter_png(
            df=df_split,
            output_path=f"{base_path}.png",
            x_col=split["x_col"],
            x_err_plus_col=split["x_err_plus_col"],
            x_err_minus_col=split["x_err_minus_col"],
            y_col=split["y_col"],
            y_err_plus_col=split["y_err_plus_col"],
            y_err_minus_col=split["y_err_minus_col"],
        )

        print(
            f"\nCreated {os.path.basename(base_path)}.xlsx, {os.path.basename(base_path)}.csv, {os.path.basename(base_path)}.png"
        )


def _cleanup_data_files(keep: int) -> None:
    """Delete old data files, keeping only the N most recent timestamped sets."""
    import glob
    import re

    base_names = [
        "exoplanet_data",
        "mass-vs-radius",
        "mass-vs-density",
        "mass-vs-surface-gravity",
    ]
    extensions = [".xlsx", ".csv", ".png"]

    all_files: list[str] = []
    for base in base_names:
        for ext in extensions:
            all_files.extend(glob.glob(os.path.join(DATA_DIR, f"{base}.*{ext}")))  # type: ignore[reportUnknownMemberType]
            all_files.extend(glob.glob(os.path.join(DATA_DIR, f"{base}.*.filter{ext}")))  # type: ignore[reportUnknownMemberType]

    timestamp_pattern = re.compile(r"\.([0-9]{8}T[0-9]{6})(?:\.filter)?\.?")

    timestamp_set: set[str] = set()
    for f in all_files:
        match = timestamp_pattern.search(os.path.basename(f))
        if match:
            timestamp_set.add(match.group(1))

    sorted_timestamps: list[str] = sorted(timestamp_set, reverse=True)
    to_delete: set[str] = set(sorted_timestamps[keep:])

    deleted_count = 0
    for ts in to_delete:
        for base in base_names:
            for ext in extensions:
                path = os.path.join(DATA_DIR, f"{base}.{ts}{ext}")
                if os.path.exists(path):
                    os.remove(path)
                    deleted_count += 1
                path_filtered = os.path.join(DATA_DIR, f"{base}.{ts}.filter{ext}")
                if os.path.exists(path_filtered):
                    os.remove(path_filtered)
                    deleted_count += 1

    print(f"\nCleaned up {deleted_count} files, kept {keep} most recent set(s)")


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Fetch exoplanet data from NASA Exoplanet Archive and compute surface gravity."
    )
    parser.add_argument(
        "-f",
        "--fetch",
        action="store_true",
        help="Fetch data from NASA Exoplanet Archive and generate output files",
    )
    parser.add_argument(
        "-s",
        "--split",
        action="store_true",
        help="Create split files: mass-vs-radius, mass-vs-density, mass-vs-surface-gravity",
    )
    parser.add_argument(
        "-F",
        "--filter",
        action="store_true",
        help="Filter out rows with 'CALCULATED_VALUE' (use with --split only)",
    )
    parser.add_argument(
        "-C",
        "--clean-up",
        type=int,
        nargs="?",
        const=1,
        default=0,
        help="Keep only N most recent file sets (default: 1)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output Excel file (default: auto-generated timestamped name)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh of raw data from NASA Exoplanet Archive",
    )
    args = parser.parse_args()

    if args.clean_up > 0:
        _cleanup_data_files(args.clean_up)
        return

    if args.filter and not args.split:
        parser.error("--filter / -F requires --split")

    if args.split and not args.fetch:
        import glob as g

        existing = sorted(
            g.glob(os.path.join(DATA_DIR, "exoplanet_data.*.xlsx")),
            key=os.path.getmtime,
            reverse=True,
        )
        if not existing:
            parser.error(
                "--split requires --fetch when no existing exoplanet_data file found"
            )
        latest = existing[0]
        timestamp = (
            os.path.basename(latest).replace("exoplanet_data.", "").replace(".xlsx", "")
        )
        print(f"Using existing exoplanet_data.{timestamp}.xlsx")
        df = pd.read_excel(latest, sheet_name="Exoplanets")  # type: ignore[reportUnknownMemberType]
        _create_split_files(df, timestamp, filter_rows=args.filter)
        return

    if not args.fetch and not args.split:
        parser.print_help()
        return

    df = fetch_data(force_refresh=args.force_refresh)
    df = compute_surface_gravity(df)
    df = assign_dm_class(df)
    df = rename_columns(df)

    timestamp = args.output.replace("exoplanet_data.", "").replace(".xlsx", "")
    base_path = os.path.join(DATA_DIR, f"exoplanet_data.{timestamp}")

    csv_output = f"{base_path}.csv"
    print(
        f"Writing {len(df):,} rows to {os.path.basename(base_path)}.xlsx and {os.path.basename(csv_output)} …",
        flush=True,
        end="",
    )
    df.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")  # type: ignore[reportUnknownMemberType]
    df.to_csv(csv_output, index=False, quoting=1, encoding="utf-8")

    format_workbook(f"{base_path}.xlsx", len(df))

    print(f"Done.")
    print(
        f"\nFiles saved: {os.path.basename(base_path)}.xlsx, {os.path.basename(csv_output)}"
    )

    if args.split:
        _create_split_files(df, timestamp, filter_rows=args.filter)

    print()
    print("Summary statistics:")
    print(
        f"  Planets with surface gravity computed : {df['Surface Gravity (m/s²)'].notna().sum():,}"
    )
    print(
        f"  Surface gravity range (m/s²)          : "
        f"{df['Surface Gravity (m/s²)'].min():.2f} – {df['Surface Gravity (m/s²)'].max():.2f}"
    )
    print(
        f"  Surface gravity range (g_Earth)       : "
        f"{df['Surface Gravity (g_Earth)'].min():.3f} – {df['Surface Gravity (g_Earth)'].max():.3f}"
    )
    print()
    counts = df["DM Class"].value_counts().sort_index()
    print("Durand-Manterola class counts:")
    for cls, n in counts.items():
        print(f"  Class {cls}: {n:,} planets")
    print()


if __name__ == "__main__":
    main()
