"""Query NASA Exoplanet Archive TAP service."""

import os
from datetime import datetime
from io import StringIO

import pandas as pd
import requests

from planet_power.helpers import load_csv_to_df, save_df_to_csv

from planet_power.constants import (
    DATA_DIR,
    MAX_AGE,
    RAW_DATA_FILE_TEMPLATE,
    EXOPLANET_ARCHIVE_TAP_BASE,
    USUAL_PS_COLUMNS,
    USUAL_PS_WHERE,
    USUAL_PSCOMPPARS_COLUMNS,
    USUAL_PSCOMPPARS_WHERE,
)


def _is_cache_valid(path: str) -> bool:
    """Check if cached file exists and is less than MAX_AGE old."""
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < MAX_AGE


def retrieve_exoplanet_data(
    columns: list[str] = [],
    force_refresh: bool = False,
    pscomppars: bool = False,
) -> pd.DataFrame:
    """Query NASA Exoplanet Archive TAP service.

    Args:
        force_refresh: If True, always download fresh data ignoring cache.

    Returns:
        DataFrame of exoplanet data.
    """
    data_table = "pscomppars" if pscomppars else "ps"

    raw_data_file = os.path.join(
        DATA_DIR, RAW_DATA_FILE_TEMPLATE.replace("%t", data_table)
    )
    if not force_refresh and _is_cache_valid(raw_data_file):
        print(
            f"Loading cached data from {os.path.basename(raw_data_file)} …",
            flush=True,
        )
        df = load_csv_to_df(raw_data_file, encoding="utf-8")
        if df is not None:
            print(f"  → {len(df):,} planets loaded from cache.")
            return df
        else:
            print(
                f"Could not load cached CSV file '{os.path.relpath(raw_data_file)}', so trying to download it again."
            )
    # column selection
    cols: str = "*"
    if not columns:
        if pscomppars:
            cols = ",".join(USUAL_PSCOMPPARS_COLUMNS)
        else:
            cols = ",".join(USUAL_PS_COLUMNS)
    else:
        cols = ",".join(columns)
    # select where ckause
    where = ""
    if pscomppars:
        where = f" WHERE {USUAL_PSCOMPPARS_WHERE}"
    # else:
    #    where = f" WHERE {USUAL_PS_WHERE}"
    query = f"SELECT {cols} FROM {data_table} {where}"
    params = {"query": query, "format": "csv"}

    print(
        f"Querying NASA Exoplanet Archive table '{data_table}' …",
        flush=True,
    )
    resp = requests.get(EXOPLANET_ARCHIVE_TAP_BASE, params=params, timeout=120)
    resp.raise_for_status()

    print("Parsing retrieved data …")
    df = pd.read_csv(StringIO(resp.text), comment="#", encoding="utf-8")
    print(f"  → {len(df):,} planets retrieved.")

    if save_df_to_csv(df, raw_data_file):
        print(f"Saved raw data to {os.path.relpath(raw_data_file)}")
    else:
        print()
        print(
            f"There was a problem saving raw data to {os.path.relpath(raw_data_file)}"
        )

    return df
