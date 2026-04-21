"""Utility functions that don't belong in a more specific module."""

import os
import re
import glob

from rich import box
from rich.console import Console
from rich.table import Table

from planet_power.constants import (
    ALL_PS_COLUMNS,
    ALL_PSCOMPPARS_COLUMNS,
    ALL_COMPUTED_COLUMNS,
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
    existing = sorted(
        glob.glob(data_file_name),
        key=os.path.getmtime,
        reverse=True,
    )
    return existing


def list_available_columns() -> None:
    """Print a two-column table of PS and PSCompPars column names using rich."""
    console = Console()
    table = Table(
        title="Available NASA Exoplanet Archive Columns",
        title_style="regular",
        header_style="dim",
        box=box.SQUARE,
    )
    table.add_column("Table PS", no_wrap=False)
    table.add_column("Table PSCompPars", no_wrap=False)
    ps_list = ", ".join(ALL_PS_COLUMNS)
    pscomppars_list = ", ".join(ALL_PSCOMPPARS_COLUMNS)
    row = [ps_list, pscomppars_list]
    table.add_row(*row)
    console.print(table)


def get_column_list(patterns: list[str]) -> list[str]:
    """Match column names using exact matches or regex patterns across all sources.

    Parameters
    ----------
    patterns : list[str]
        List of patterns, regex (~), or file paths (@).

    Returns
    -------
    list[str]
        Deduplicated list of matching column names.
    """
    # 1. Create a deduplicated search pool from all sources
    raw_pool = ALL_PSCOMPPARS_COLUMNS + ALL_PS_COLUMNS + ALL_COMPUTED_COLUMNS
    ordered_unique_pool = list(dict.fromkeys(raw_pool))
    lookup_set = set(ordered_unique_pool)

    result: list[str] = []
    seen: set[str] = set()

    def process_pattern(p, allow_recursive: bool = True) -> None:
        # Handle nested lists from argparse (fixes the AttributeError)
        if isinstance(p, (list, tuple)):
            for item in p:
                process_pattern(item, allow_recursive)
            return

        p = p.strip()
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
