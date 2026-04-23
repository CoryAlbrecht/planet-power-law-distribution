"""Command-line interface for the exoplanet data fetcher."""

from __future__ import annotations

import argparse
import os
import re
from importlib.metadata import version

from planet_power.compute import calculate_extras
from planet_power.constants import (
    DATA_DIR,
    RAW_DATA_FILE_TEMPLATE,
    CALCULATED_DATA_FILE_TEMPLATE,
)
from planet_power.extraction import combine_and_extract_and_graph
from planet_power.helpers import (
    combine_csv_files,
    extract_columns,
    get_column_list,
    list_available_columns,
    load_csv_to_df,
    save_df_to_csv,
)
from planet_power.retrieve import retrieve_exoplanet_data


def _validate_tag(tag: str) -> str:
    if tag and not re.match(r"^[a-zA-Z0-9_\-:]+$", tag):
        raise argparse.ArgumentTypeError(
            f"Invalid tag '{tag}' - only alphanumeric, underscore, hyphen, colon allowed"
        )
    return tag


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
        "-s",
        "--split",
        action="store_true",
        help="Create split files: mass-vs-radius, mass-vs-density, mass-vs-surface-gravity",
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

    # table to use
    data_table = "pscomppars" if args.pscomppars else "ps"
    raw_data_file = os.path.join(
        DATA_DIR, RAW_DATA_FILE_TEMPLATE.replace("%t", data_table)
    )
    calculated_data_file = os.path.join(
        DATA_DIR, CALCULATED_DATA_FILE_TEMPLATE.replace("%t", data_table)
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

    if not args.retrieve and not args.split and not args.extract and not args.compute:
        parser.print_help()
        return

    if args.retrieve:
        df = retrieve_exoplanet_data(
            columns=columns_list,
            force_refresh=args.refresh,
            pscomppars=args.pscomppars,
        )

    if args.calculate:
        if df is None:
            df = load_csv_to_df(csv_file=raw_data_file, encoding="utf-8")
        if df is not None:
            df_extras = calculate_extras(df, data_table=data_table)
            success = save_df_to_csv(df_extras, calculated_data_file)
            if success:
                print(
                    f"Calculated extra data saved to '{os.path.relpath(calculated_data_file)}'."
                )
            else:
                print(
                    f"Error! Could not save calculated extra data to '{os.path.relpath(calculated_data_file)}'."
                )
        else:
            print(f"Unable to load file '{raw_data_file}'.")

    if args.extract:
        if columns_list == []:
            print("No columns to extract were given.")
            return
        df_combined = combine_csv_files(raw_data_file, calculated_data_file)
        if df_combined is None:
            print(f"Unable to combine data files.")
            return
        df_extracted = extract_columns(columns_list, df_combined)
        success = save_df_to_csv(
            df_extracted,
            os.path.join(
                DATA_DIR, f"extracted{'.'+args.tag if args.tag != '' else ''}.csv"
            ),
        )

    if args.split:
        combine_and_extract_and_graph(
            columns=columns_list,
            filter_rules=filter_rules,
            stem="mass-vs-radius",
            table=data_table,
            tag=args.tag,
            x_col="ppld_mass_kg",
            x_err_plus_col="ppld_mass_kg_err1",
            x_err_minus_col="ppld_mass_kg_err2",
            x_weight_col="ppld_mass_weight",
            x_hexcolor="#ff0000",
            x_axis_min=1e21,
            x_axis_max=1e30,
            y_col="ppld_radius_m",
            y_err_plus_col="ppld_radius_m_err1",
            y_err_minus_col="ppld_radius_m_err2",
            y_weight_col="ppld_radius_weight",
            y_hexcolor="#0000ff",
            y_axis_min=1e05,
            y_axis_max=1e09,
            width_px=3840,
            height_px=2160,
            dpi=150,
            error_cross=False,
        )
        combine_and_extract_and_graph(
            columns=columns_list,
            filter_rules=filter_rules,
            stem="mass-vs-density",
            table=data_table,
            tag=args.tag,
            x_col="ppld_mass_kg",
            x_err_plus_col="ppld_mass_kg_err1",
            x_err_minus_col="ppld_mass_kg_err2",
            x_weight_col="ppld_mass_weight",
            x_hexcolor="#ff0000",
            x_axis_min=1e21,
            x_axis_max=1e30,
            y_col="pl_dens",
            y_err_plus_col="pl_denserr1",
            y_err_minus_col="pl_denserr2",
            y_weight_col="ppld_density_weight",
            y_hexcolor="#00ff00",
            y_axis_min=1e-3,
            y_axis_max=2010,
            error_cross=False,
        )


if __name__ == "__main__":
    main()
