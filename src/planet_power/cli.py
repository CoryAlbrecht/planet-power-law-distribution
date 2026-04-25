"""Command-line interface for the exoplanet data fetcher."""

from __future__ import annotations

import argparse
import os
import re
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from planet_power.compute import calculate_extras
from planet_power.constants import (
    CALCULATED_DATA_FILE_TEMPLATE,
    DATA_DIR,
    EXTRACTED_DATA_FILE_TEMPLATE,
    RAW_DATA_FILE_TEMPLATE,
)
from planet_power.extraction import combine_and_extract_and_graph
from planet_power.helpers import (
    apply_filter_rules,
    combine_df,
    extract_columns,
    get_column_list,
    list_available_columns,
    load_csv_to_df,
    save_df_to_csv,
)
from planet_power.retrieve import retrieve_exoplanet_data
from planet_power.visualization import save_scatter_png


def _validate_tag(tag: str) -> str:
    if tag and not re.match(r"^[a-zA-Z0-9_:-]+$", tag):
        raise argparse.ArgumentTypeError(
            f"Invalid tag '{tag}' - only alphanumeric, underscore, hyphen, colon allowed"
        )
    return tag


def _validate_column_family(column_family: str) -> str:
    cols: list[str] = get_column_list([f"~{column_family}.*"])
    if (
        f"{column_family}_err1" in cols
        and f"{column_family}_err2" in cols
        and f"{column_family}_weight" in cols
    ):
        return column_family
    else:
        raise argparse.ArgumentTypeError(
            f"Invalid column family '{column_family}', no *_err1, *err2, or *_weight accessory columns found"
        )


def cli_calculate(
    df_raw: pd.DataFrame | None,
    raw_data_file: str,
    calculated_data_file: str,
    data_table: str = "ps",
) -> pd.DataFrame | None:
    df_raw_loaded = None
    if df_raw is None:
        df_raw_loaded = load_csv_to_df(csv_file=raw_data_file, encoding="utf-8")
    else:
        df_raw_loaded = df_raw
    if df_raw_loaded is not None:
        df_extras = calculate_extras(df_raw_loaded, data_table=data_table)
        if save_df_to_csv(df_extras, calculated_data_file):
            print(
                f"Calculated extra data saved to '{os.path.relpath(calculated_data_file)}'."
            )
            return df_extras
        else:
            print(
                f"Error! Could not save calculated extra data to '{os.path.relpath(calculated_data_file)}'."
            )
            return None
    else:
        print(f"Unable to load file '{os.path.relpath(raw_data_file)}'.")
        return None


def cli_extract(
    df_raw: pd.DataFrame | None,
    raw_data_file: str,
    df_extras: pd.DataFrame | None,
    calculated_data_file: str,
    columns_list: list[str] = [],
    filter_rules: list[tuple[str, str]] = [],
    tag: str = "",
) -> pd.DataFrame | None:  # sourcery skip: default-mutable-arg
    if not columns_list:
        print("No columns to extract were given.")
        return None

    if df_raw is not None:
        df_one = df_raw
    else:
        df_one = load_csv_to_df(raw_data_file, required_cols=["pl_name"])

    if df_extras is not None:
        df_two = df_extras
    else:
        df_two = load_csv_to_df(calculated_data_file, required_cols=["pl_name"])

    # df_combined = combine_csv_files("pl_name", [], raw_data_file, calculated_data_file)
    df_combined = combine_df(df_one, df_two)

    if df_combined is None:
        print("Unable to combine data files.")
        return
    print(f"Combined dataset has {len(df_combined)} records.")
    df_filtered = apply_filter_rules(df_combined, filter_rules)
    print(f"Filtered dataset has {len(df_filtered)} records.")
    df_extracted = extract_columns(columns_list, df_filtered)
    print(f"Extracted dataset has {len(df_extracted)} records.")
    extract_file = os.path.join(
        DATA_DIR, EXTRACTED_DATA_FILE_TEMPLATE.replace("%T", f"{tag and '.' + tag}")
    )
    if save_df_to_csv(df_extracted, extract_file):
        print(f"Extracted data saved to {os.path.relpath(extract_file)}")
    return df_extracted


def cli_image(
    df_extracted: pd.DataFrame | None,
    extracted_file: str,
    x_col_fam: str | None,
    y_col_fam: str | None,
):
    if not x_col_fam:
        print("You must set an X-axis column family with --x-column-family/-x")
        return

    if not y_col_fam:
        print("You must set an Y-axis column family with --y-column-family/-y")
        return

    x_cols: list[str] = get_column_list([f"~{x_col_fam}.*"])
    y_cols: list[str] = get_column_list([f"~{y_col_fam}.*"])
    all_cols: list[str] = x_cols + y_cols

    df_pull = df_extracted
    if df_pull is None:
        df_pull = load_csv_to_df(extracted_file, required_cols=all_cols)

    if df_pull is None:
        return

    png_path = Path(extracted_file)
    png_file = os.path.join(png_path.parent, png_path.stem + ".png")
    save_scatter_png(
        df=df_pull,
        output_path=png_file,
        x_col=f"{x_col_fam}",
        x_err_plus_col=f"{x_col_fam}_err1",
        x_err_minus_col=f"{x_col_fam}_err2",
        x_weight_col=f"{x_col_fam}_weight",
        y_col=f"{y_col_fam}",
        y_err_plus_col=f"{y_col_fam}_err1",
        y_err_minus_col=f"{y_col_fam}_err2",
        y_weight_col=f"{y_col_fam}_weight",
    )
    return


def main() -> None:
    """Main entry point for the CLI."""
    print(
        f"planet-power v{version('planet-power-law-distribution')} - Investigating classification of exoplanets"
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
        "-c",
        "--calculate",
        action="store_true",
        help="Create extra CSV file with calculated values not in the NASA Exoplanet Archive data",
    )
    parser.add_argument(
        "-e",
        "--extract",
        action="store_true",
        help="Combine data files and extract specific columns to a new data file",
    )
    parser.add_argument(
        "-f",
        "--filter",
        nargs="+",
        action="append",
        default=[],
        metavar="COLUMN:REGEX",
        help="Filter rows where COLUMN matches REGEX. Can be used multiple times.",
    )
    parser.add_argument(
        "-C",
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
        "-i",
        "--image",
        action="store_true",
        help="Creates a scatter plot from a CSV data file",
    )
    parser.add_argument(
        "-x",
        "--x-column-family",
        type=_validate_column_family,
        default=None,
        metavar="COLUMN_FAMILY",
        help="Select a group of columns to use as the X-axis data in a scatter plot",
    )
    parser.add_argument(
        "-y",
        "--y-column-family",
        type=_validate_column_family,
        default=None,
        metavar="COLUMN_FAMILY",
        help="Select a group of columns to use as the Y-axis data in a scatter plot",
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

    df_raw = None
    df_extras = None
    df_extracted = None

    if args.help_columns:
        print()
        list_available_columns()
        print()
        return

    # table to use
    data_table = "pscomppars" if args.pscomppars else "ps"
    raw_data_file = os.path.join(
        DATA_DIR, RAW_DATA_FILE_TEMPLATE.replace("%t", data_table)
    )
    calculated_data_file = os.path.join(
        DATA_DIR, CALCULATED_DATA_FILE_TEMPLATE.replace("%t", data_table)
    )
    extracted_file = os.path.join(
        DATA_DIR,
        EXTRACTED_DATA_FILE_TEMPLATE.replace("%T", f"{args.tag and '.' + args.tag}"),
    )
    # get the columns
    columns_list = get_column_list(args.column)

    # get the filter rules
    filter_rules: list[tuple[str, str]] = []
    flat_args = [item for sublist in args.filter for item in sublist]
    for arg in flat_args:
        if ":" not in arg:
            print(f'String "{arg}" is not a valid filter string.')
            continue
        col, pattern = arg.split(":", 1)
        filter_rules.append((col, pattern))

    if not args.retrieve and not args.extract and not args.calculate and not args.image:
        parser.print_help()
        return

    if args.retrieve:
        df_raw = retrieve_exoplanet_data(
            columns=columns_list,
            force_refresh=args.refresh,
            pscomppars=args.pscomppars,
        )

    if args.calculate:
        df_extras = cli_calculate(
            df_raw, raw_data_file, calculated_data_file, data_table
        )

    if args.extract:
        df_extracted = cli_extract(
            df_raw,
            raw_data_file,
            df_extras,
            calculated_data_file,
            columns_list,
            filter_rules,
            args.tag,
        )
    if args.image:
        cli_image(
            df_extracted,
            extracted_file,
            args.x_column_family,
            args.y_column_family,
        )


if __name__ == "__main__":
    main()
