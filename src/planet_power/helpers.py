"""Utility functions that don't belong in a more specific module."""

import csv
import glob
import os
import re
from functools import reduce
from pathlib import Path
from typing import Optional

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

from planet_power.constants import (
    ALL_CALCULATED_COLUMNS,
    ALL_PS_COLUMNS,
    ALL_PSCOMPPARS_COLUMNS,
    DATA_DIR,
    RAW_DATA_FILE_TEMPLATE,
)


def get_latest_datafile(table: str = "ps", tag: str = "") -> list[str]:

    data_file_name = os.path.join(
        DATA_DIR,
        RAW_DATA_FILE_TEMPLATE.replace("%t", table).replace(
            "%T", f".{tag}" if tag != "" else "*"
        ),
    )
    print(f"Search for file '{data_file_name}'")
    return sorted(
        glob.glob(data_file_name),
        key=os.path.getmtime,
        reverse=True,
    )


def list_available_columns() -> None:
    """Print a two-column table of PS and PSCompPars column names using rich."""
    console = Console()
    table = Table(
        title="Available NASA Exoplanet Archive Columns",
        title_style="regular",
        header_style="dim",
        box=box.SQUARE,
    )
    table.add_column("Exoplanet Archive Table PS", no_wrap=False)
    table.add_column("Exoplanet Archive Table PSCompPars", no_wrap=False)
    table.add_column("Local Calculated Columns", no_wrap=False)
    ps_list = ", ".join(ALL_PS_COLUMNS)
    pscomppars_list = ", ".join(ALL_PSCOMPPARS_COLUMNS)
    calculated_list = ",".join(ALL_CALCULATED_COLUMNS)
    row = [ps_list, pscomppars_list, calculated_list]
    table.add_row(*row)
    console.print(table)


def get_column_list(patterns: list[str], *extra_lists: list[str]) -> list[str]:
    """Match column names using exact matches or regex patterns across all sources.

    Parameters
    ----------
    patterns : list[str]
        List of patterns, regex (~), or file paths (@).
    *extra_lists : list[str]
        Additional lists of column names to search in. If empty, uses the default
        pool of ALL_PSCOMPPARS_COLUMNS, ALL_PS_COLUMNS, and ALL_COMPUTED_COLUMNS.

    Returns
    -------
    list[str]
        Deduplicated list of matching column names.
    """
    # Create search pool from extra_lists or default columns
    if extra_lists:
        raw_pool: list[str] = []
        for lst in extra_lists:
            raw_pool.extend(lst)
    else:
        raw_pool = ALL_PSCOMPPARS_COLUMNS + ALL_PS_COLUMNS + ALL_CALCULATED_COLUMNS

    ordered_unique_pool = list(dict.fromkeys(raw_pool))
    lookup_set = set(ordered_unique_pool)

    result: list[str] = []
    seen: set[str] = set()

    def process_pattern(
        p: str | list[str] | tuple[str], allow_recursive: bool = True
    ) -> None:
        # Handle nested lists from argparse (fixes the AttributeError)
        if isinstance(p, (list, tuple)):
            for item in p:
                process_pattern(item, allow_recursive)
            return

        p = p.strip()  # type: ignore[union-attr]
        if not p:
            return

        # Handle File Reference (@)
        if p.startswith("@") and allow_recursive:
            filepath = p[1:]
            if not os.path.isfile(filepath):
                raise FileNotFoundError(f"Pattern file not found: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        process_pattern(line, allow_recursive=False)

        # Handle Regex Match (~)
        elif p.startswith("~"):
            regex_str = p[1:]
            try:
                regex = re.compile(regex_str)
                # Use the unique pool for iteration to avoid redundant checks
                for col in ordered_unique_pool:
                    if col not in seen and regex.search(col):
                        result.append(col)
                        seen.add(col)
            except re.error as e:
                raise ValueError(f"Invalid regex '{regex_str}': {e}")

        # Handle Exact Match
        else:
            if p in lookup_set:
                if p not in seen:
                    result.append(p)
                    seen.add(p)
            else:
                # Raise error if a specific column is requested but doesn't exist
                raise ValueError(
                    f"Column '{p}' not found in NASA Archive or computed lists."
                )

    for pattern in patterns:
        process_pattern(pattern)

    return result


def load_csv_to_df(
    csv_file: str, required_cols: list[str] = ["pl_name"], encoding: str = "utf-8"
) -> Optional[pd.DataFrame]:  # sourcery skip: default-mutable-arg
    try:
        # This will raise a ValueError if any item in required_cols is missing
        must_have_cols = required_cols
        df = pd.read_csv(csv_file, encoding=encoding)
        for col in must_have_cols:
            if col not in df.columns:
                print(f"Not loading {csv_file}: Critical column '{col}' is missing.")
                return None
        return df
    except ValueError as e:
        print(f"Could not load {csv_file}: Missing required columns. {e}")
        return None
    except PermissionError as e:
        print(f"Permission denied: {e}")
        return None
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return None
    except OSError as e:
        print(f"OS error: {e}")
        return None
    except Exception as e:
        print(f"Error loading {csv_file}: {e}")
        return None


def save_df_to_csv(df: pd.DataFrame, file_name: str = "file.csv") -> bool:
    try:
        target_path = Path(file_name).resolve()
        folder_path = target_path.parent
        folder_path.mkdir(parents=True, exist_ok=True)
        df.to_csv(
            target_path,
            index=False,
            quoting=csv.QUOTE_NONNUMERIC,
            encoding="utf-8",
        )
        return True
    except PermissionError as e:
        print(f"Permission denied: {e}")
        return False
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False
    except Exception as e:
        print(f"Error saving DataFrame to CSV: {e}")
        return False


def combine_df(*dfs: pd.DataFrame | None) -> Optional[pd.DataFrame]:
    # Filter out None values and empty DataFrames
    valid_dfs: list[pd.DataFrame] = []
    valid_dfs.extend(df for df in dfs if df is not None and not df.empty)
    if not valid_dfs:
        return None

    # Reduce using combine_first
    combined: pd.DataFrame = reduce(
        lambda left, right: left.combine_first(right), valid_dfs
    )

    return combined.reset_index() if combined.index.name else combined


def combine_csv_files(
    index_col: str = "pl_name", required_cols: list[str] = [], *csv_files: str
) -> Optional[pd.DataFrame]:  # sourcery skip: default-mutable-arg
    df_list: list[pd.DataFrame] = []

    for cf in csv_files:
        df = load_csv_to_df(
            cf,
            required_cols=(
                required_cols + [index_col]
                if index_col not in required_cols
                else required_cols
            ),
        )
        if df is not None:
            # We set the index here to guarantee alignment by planet name
            df_list.append(df.set_index(index_col))

    return combine_df(*df_list)


def extract_columns(columns: list[str], df: pd.DataFrame) -> pd.DataFrame:
    return df[columns].copy()


def apply_filter_rules(
    df: pd.DataFrame,
    filter_rules: list[tuple[str, str]] | None = None,
) -> pd.DataFrame:
    """
    Apply a list of (column, regex) exclusion rules to a DataFrame.

    Rows where the column value matches the regex are removed. Rules
    referencing columns not present in the DataFrame are skipped with a
    warning rather than raising an exception, so that the remaining rules
    still execute.

    Parameters
    ----------
    df : DataFrame to filter.
    filter_rules : List of (column_name, regex_pattern) tuples. Rows where
        column_name matches regex_pattern are excluded. Pass None to skip
        filtering entirely.

    Returns
    -------
    Filtered DataFrame (or the original if filter_rules is None or empty).
    """
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
    mask = pd.Series([True] * len(df), index=df.index)
    for col_name, pattern in active_rules:
        matches = df[col_name].astype(str).str.contains(pattern, regex=True, na=False)
        mask = mask & ~matches
    return df[mask]
