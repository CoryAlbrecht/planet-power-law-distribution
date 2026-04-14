"""Utility functions that don't belong in a more specific module."""

import os
import re

from rich import box
from rich.console import Console
from rich.table import Table

from planet_power.constants import ALL_PS_COLUMNS, ALL_PSCOMPPARS_COLUMNS


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
    """Match column names from ALL_COLUMNS using exact matches or regex patterns.

    Parameters
    ----------
    patterns : list[str]
        List of patterns. Each string is either an exact column name from
        ALL_COLUMNS, a regex pattern prefixed with ~ to match against
        ALL_COLUMNS, or a file path prefixed with @ containing regex patterns
        (one per line).

    Returns
    -------
    list[str]
        List of matching column names, in the order they first appear in
        the patterns input.
    """
    result: list[str] = []
    seen: set[str] = set()

    def process_pattern(p: str, allow_recursive: bool = True) -> None:
        p = p.strip()
        if p.startswith("@") and allow_recursive:
            filepath = p[1:]
            if not os.path.isfile(filepath):
                raise FileNotFoundError(f"Pattern file not found: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        process_pattern(line, allow_recursive=False)
        elif p.startswith("~") and allow_recursive:
            regex = p[1:]
            for col in ALL_PSCOMPPARS_COLUMNS:
                if col not in seen and re.match(regex, col):
                    result.append(col)
                    seen.add(col)
        else:
            if p in ALL_PSCOMPPARS_COLUMNS and p not in seen:
                result.append(p)
                seen.add(p)

    for pattern in patterns:
        process_pattern(pattern)

    return result
