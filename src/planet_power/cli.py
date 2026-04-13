"""Command-line interface for the exoplanet data fetcher."""

from __future__ import annotations

import argparse
import os
import re
import time
import glob as g
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")

import warnings
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from planet_power.fetch import fetch_data
from planet_power.compute import compute_surface_gravity, assign_dm_class
from planet_power.format import rename_columns, format_workbook

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)


def _make_timestamped_filename() -> str:
    """Generate timestamped filename like exoplanet_data.20260411T180234.xlsx"""
    ts = time.strftime("%Y%m%dT%H%M%S")
    return f"exoplanet_data.{ts}.xlsx"


def _get_latest_datafile() -> list[str]:
    existing = sorted(
        g.glob(os.path.join(DATA_DIR, "exoplanet_data.*.xlsx")),
        key=os.path.getmtime,
        reverse=True,
    )
    return existing


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
    # xerr = [np.abs(df[x_err_minus_col].values), np.abs(df[x_err_plus_col].values)]
    # yerr = [np.abs(df[y_err_minus_col].values), np.abs(df[y_err_plus_col].values)]
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


def _validate_tag(tag: str) -> str:
    if tag and not re.match(r"^[a-zA-Z0-9_\-:]+$", tag):
        raise argparse.ArgumentTypeError(
            f"Invalid tag '{tag}' - only alphanumeric, underscore, hyphen, colon allowed"
        )
    return tag


def _apply_filter_rules(
    df: pd.DataFrame, filter_rules: list[tuple[str, str]] | None = None
) -> pd.DataFrame:
    if filter_rules is None:
        return df
    active_rules: list[tuple[str, str]] = []
    for col_name, pattern in filter_rules:
        if col_name not in df.columns:
            print(
                f"  Warning: filter rule skipped — column '{col_name}' not in DataFrame"
            )
        else:
            active_rules.append((col_name, pattern))
    if not active_rules:
        return df
    mask = pd.Series([True] * len(df))
    for col_name, pattern in active_rules:
        matches = df[col_name].astype(str).str.contains(pattern, regex=True, na=False)
        mask = mask & ~matches
    return df[mask]


def _create_split_files(
    df: pd.DataFrame,
    timestamp: str,
    filter_rules: list[tuple[str, str]] | None = None,
    tag: str = "",
) -> None:
    """Create split files for mass-vs-radius, mass-vs-density, mass-vs-surface-gravity."""
    splits: list[dict[str, Any]] = [
        {
            "stem": "mass-vs-radius",
            "cols": [
                "pl_name",
                "ppld_mass_kg",
                "ppld_mass_kg_err1",
                "ppld_mass_kg_err2",
                "pl_bmassj_reflink",
                "pl_bmasse_reflink",
                "ppld_radius_m",
                "ppld_radius_m_err1",
                "ppld_radius_m_err2",
                "pl_radj_reflink",
                "pl_rade_reflink",
            ],
            "x_col": "ppld_mass_kg",
            "x_err_plus_col": "ppld_mass_kg_err1",
            "x_err_minus_col": "ppld_mass_kg_err2",
            "y_col": "ppld_radius_m",
            "y_err_plus_col": "ppld_radius_m_err1",
            "y_err_minus_col": "ppld_radius_m_err2",
        },
        {
            "stem": "mass-vs-density",
            "cols": [
                "pl_name",
                "ppld_mass_kg",
                "ppld_mass_kg_err1",
                "ppld_mass_kg_err2",
                "pl_bmassj_reflink",
                "pl_bmasse_reflink",
                "pl_dens",
                "pl_denserr1",
                "pl_denserr2",
                "pl_dens_reflink",
            ],
            "x_col": "ppld_mass_kg",
            "x_err_plus_col": "ppld_mass_kg_err1",
            "x_err_minus_col": "ppld_mass_kg_err2",
            "y_col": "pl_dens",
            "y_err_plus_col": "pl_denserr1",
            "y_err_minus_col": "pl_denserr2",
        },
        {
            "stem": "mass-vs-surface-gravity",
            "cols": [
                "pl_name",
                "ppld_mass_kg",
                "ppld_mass_kg_err1",
                "ppld_mass_kg_err2",
                "pl_bmassj_reflink",
                "pl_bmasse_reflink",
                "ppld_surf_grav_ms2",
                "ppld_surf_grav_ms2_err1",
                "ppld_surf_grav_ms2_err2",
                "pl_radj_reflink",
                "pl_rade_reflink",
            ],
            "x_col": "ppld_mass_kg",
            "x_err_plus_col": "ppld_mass_kg_err1",
            "x_err_minus_col": "ppld_mass_kg_err2",
            "y_col": "ppld_surf_grav_ms2",
            "y_err_plus_col": "ppld_surf_grav_ms2_err1",
            "y_err_minus_col": "ppld_surf_grav_ms2_err2",
        },
    ]

    for split in splits:
        print()
        df_split = cast(pd.DataFrame, df[split["cols"]])
        df_filtered = _apply_filter_rules(df=df_split, filter_rules=filter_rules)
        if len(df_filtered) < len(df_split):
            print(
                f"Dataset {split['stem']} filtered from {len(df_split)} down to {len(df_filtered)} lines."
            )
        base_path = os.path.join(
            DATA_DIR,
            f"{split['stem']}.{timestamp}{f'.{tag}' if tag else ''}",
        )
        df_filtered.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")  # type: ignore[reportUnknownMemberType]
        df_filtered.to_csv(f"{base_path}.csv", index=False, quoting=1, encoding="utf-8")  # type: ignore[reportUnknownMemberType]
        format_workbook(f"{base_path}.xlsx", len(df_split))

        _save_scatter_png(
            df=df_filtered,
            output_path=f"{base_path}.png",
            x_col=split["x_col"],
            x_err_plus_col=split["x_err_plus_col"],
            x_err_minus_col=split["x_err_minus_col"],
            y_col=split["y_col"],
            y_err_plus_col=split["y_err_plus_col"],
            y_err_minus_col=split["y_err_minus_col"],
        )

        print(
            f"Created {os.path.basename(base_path)}.xlsx, {os.path.basename(base_path)}.csv, {os.path.basename(base_path)}.png"
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
        "-S",
        "--script",
        type=str,
        metavar="FILE",
        help="Path to a text file containing commands to follow",
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
        nargs="+",
        action="append",
        default=[],
        metavar="COLUMN:REGEX",
        help="Filter rows where COLUMN matches REGEX. Can be used multiple times.",
    )
    parser.add_argument(
        "-t",
        "--tag",
        type=_validate_tag,
        default="",
        metavar="TAG",
        help="Tag to append to split output filenames (alphanumeric, underscore, hyphen, colon)",
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

    # get the filter rules
    filter_rules: list[tuple[str, str]] = []
    flat_args = [item for sublist in args.filter for item in sublist]
    for arg in flat_args:
        if ":" not in arg:
            print(f'String "{arg}" is not a valid filter string.')
            continue
        col, pattern = arg.split(":", 1)
        filter_rules.append((col, pattern))

    if args.clean_up > 0:
        _cleanup_data_files(args.clean_up)
        return

    if args.fetch:
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

    if args.split:
        existing = _get_latest_datafile()
        if not existing:
            parser.error(
                "--split requires --fetch when no existing exoplanet_data file found"
            )
            return
        latest = existing[0]
        timestamp = (
            os.path.basename(latest).replace("exoplanet_data.", "").replace(".xlsx", "")
        )
        print(f"Using existing exoplanet_data.{timestamp}.xlsx")
        df = pd.read_excel(latest, sheet_name="Exoplanets")  # type: ignore[reportUnknownMemberType]
        _create_split_files(df, timestamp, filter_rules=filter_rules, tag=args.tag)
        return

    if not args.fetch and not args.split and not args.script:
        parser.print_help()
        return

    print(f"Done.")
    print(
        f"\nFiles saved: {os.path.basename(base_path)}.xlsx, {os.path.basename(csv_output)}"
    )

    print()
    print("Summary statistics:")
    print(
        f"  Planets with surface gravity computed : {df['ppld_surf_grav_ms2'].notna().sum():,}"
    )
    print(
        f"  Surface gravity range (m/s²)          : "
        f"{df['ppld_surf_grav_ms2'].min():.2f} – {df['ppld_surf_grav_ms2'].max():.2f}"
    )
    print(
        f"  Surface gravity range (g_Earth)       : "
        f"{df['ppld_surf_grav_earth'].min():.3f} – {df['ppld_surf_grav_earth'].max():.3f}"
    )
    print()
    counts = df["dm_class"].value_counts().sort_index()
    print("Durand-Manterola class counts:")
    for cls, n in counts.items():
        print(f"  Class {cls}: {n:,} planets")
    print()


if __name__ == "__main__":
    main()
