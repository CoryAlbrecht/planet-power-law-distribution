"""Query NASA Exoplanet Archive TAP service."""

import os
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests

from planet_power.constants import (
    USUAL_PSCOMPPARS_COLUMNS,
    USUAL_PS_COLUMNS,
    DATA_DIR,
    TAP_BASE,
    WHERE,
)

PS_RAW_DATA_FILE = os.path.join(DATA_DIR, "ps-raw-data.csv")
PSCOMPPARS_RAW_DATA_FILE = os.path.join(DATA_DIR, "pscomppars-raw-data.csv")
MAX_AGE = timedelta(weeks=1)


def _is_cache_valid(path: str) -> bool:
    """Check if cached file exists and is less than MAX_AGE old."""
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < MAX_AGE


def retrieve_exoplanet_data(
    columns: list[str] | None = None,
    force_refresh: bool = False,
    pscomppars: bool = False,
) -> pd.DataFrame:
    """Query NASA Exoplanet Archive TAP service.

    Args:
        force_refresh: If True, always download fresh data ignoring cache.

    Returns:
        DataFrame of exoplanet data.
    """
    if not force_refresh and _is_cache_valid(PS_RAW_DATA_FILE):
        print(
            f"Loading cached data from {os.path.basename(PS_RAW_DATA_FILE)} …",
            flush=True,
        )
        df = pd.read_csv(PS_RAW_DATA_FILE, encoding="utf-8")
        print(f"  → {len(df):,} planets loaded from cache.")
        return df
    cols = None
    if columns is None:
        if pscomppars:
            cols = ",".join(USUAL_PSCOMPPARS_COLUMNS)
        else:
            cols = ",".join(USUAL_PS_COLUMNS)
    else:
        cols = ",".join(columns)
    query = f"SELECT {cols} FROM {'pscomppars' if pscomppars else 'ps'} WHERE {WHERE} ORDER BY pl_bmassj ASC, pl_radj"
    params = {"query": query, "format": "csv"}

    print(
        f"Querying NASA Exoplanet Archive table '{'pscomppars' if pscomppars else 'ps'}' …",
        flush=True,
    )
    resp = requests.get(TAP_BASE, params=params, timeout=120)
    resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.text), comment="#", encoding="utf-8")
    print(f"  → {len(df):,} planets retrieved.")

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(PS_RAW_DATA_FILE, index=False, quoting=1, encoding="utf-8")
    print(f"  → Saved raw data to {os.path.basename(PS_RAW_DATA_FILE)}")

    return df
