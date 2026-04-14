"""Command-line interface for the exoplanet data fetcher."""

from __future__ import annotations

import argparse
import glob as g
import os
import re
from importlib.metadata import version

import pandas as pd

from planet_power.compute import assign_dm_class, compute_surface_gravity
from planet_power.constants import DATA_DIR
from planet_power.extraction import create_split_files
from planet_power.format import format_workbook
from planet_power.helpers import list_available_columns
from planet_power.retrieve import retrieve_exoplanet_data


def _get_latest_datafile() -> list[str]:
    existing = sorted(
        g.glob(os.path.join(DATA_DIR, "exoplanet_data.xlsx")),
        key=os.path.getmtime,
        reverse=True,
    )
    return existing


def _validate_tag(tag: str) -> str:
    if tag and not re.match(r"^[a-zA-Z0-9_\-:]+$", tag):
        raise argparse.ArgumentTypeError(
            f"Invalid tag '{tag}' - only alphanumeric, underscore, hyphen, colon allowed"
        )
    return tag


def main() -> None:
    """Main entry point for the CLI."""
    print(
        f"planet-power v{version("planet-power-law-distribution")} - Investigating classification of exoplanets"
    )
    print()
    parser = argparse.ArgumentParser(
        description="Fetch exoplanet data from NASA Exoplanet Archive and compute surface gravity."
    )
    parser.add_argument(
        "-r",
        "--retrieve",
        action="store_true",
        help="Retrieve data from NASA Exoplanet Archive",
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
        "-c",
        "--column",
        nargs="+",
        action="append",
        default=[],
        metavar="COLUMN|REGEX",
        help="Exact name of a column ore a regular expression to match multiple. Can be used multiple times.",
    )

    parser.add_argument(
        "--help-columns",
        action="store_true",
        help="List all the available columns",
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
        "-R",
        "--refresh",
        action="store_true",
        help="Force refresh of raw data from NASA Exoplanet Archive",
    )

    parser.add_argument(
        "-p",
        "--pscomppars",
        action="store_true",
        help="Use the 'pscomppars' table from NASA Exoplanet Archive instead of 'ps'",
    )

    args = parser.parse_args()

    df = None

    if args.help_columns:
        print()
        list_available_columns()
        print()
        return

    # get the filter rules
    filter_rules: list[tuple[str, str]] = []
    flat_args = [item for sublist in args.filter for item in sublist]
    for arg in flat_args:
        if ":" not in arg:
            print(f'String "{arg}" is not a valid filter string.')
            continue
        col, pattern = arg.split(":", 1)
        filter_rules.append((col, pattern))

    if not args.retrieve and not args.split and not args.script:
        parser.print_help()
        return

    if args.retrieve:
        df = retrieve_exoplanet_data(
            force_refresh=args.refresh, pscomppars=args.pscomppars
        )
        df = compute_surface_gravity(df)
        df = assign_dm_class(df)
        base_path = os.path.join(DATA_DIR, "exoplanet_data")
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
        print(f"\nFiles saved: exoplanet_data.xlsx, exoplanet_data.csv")

    if args.split:
        existing = _get_latest_datafile()
        if not existing:
            parser.error(
                "--split requires --retrieve when no existing exoplanet_data file found"
            )
            return
        latest = existing[0]
        print(f"Using existing {os.path.basename(latest)}")
        df = pd.read_excel(latest, sheet_name="Exoplanets")  # type: ignore[reportUnknownMemberType]
        create_split_files(df, filter_rules=filter_rules, tag=args.tag)

    if df is not None:
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
