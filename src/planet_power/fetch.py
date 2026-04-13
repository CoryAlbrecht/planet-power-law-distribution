"""Query NASA Exoplanet Archive TAP service."""

import os
from datetime import datetime, timedelta

import requests
import pandas as pd
from io import StringIO

from planet_power.constants import TAP_BASE, COLUMNS, WHERE

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
RAW_DATA_FILE = os.path.join(DATA_DIR, "raw-data.csv")
MAX_AGE = timedelta(weeks=1)


def _is_cache_valid(path: str) -> bool:
    """Check if cached file exists and is less than MAX_AGE old."""
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < MAX_AGE


def fetch_data(force_refresh: bool = False) -> pd.DataFrame:
    """Query NASA Exoplanet Archive TAP service.

    Args:
        force_refresh: If True, always download fresh data ignoring cache.

    Returns:
        DataFrame of exoplanet data.
    """
    if not force_refresh and _is_cache_valid(RAW_DATA_FILE):
        print(
            f"Loading cached data from {os.path.basename(RAW_DATA_FILE)} …", flush=True
        )
        df = pd.read_csv(RAW_DATA_FILE, encoding="utf-8")
        print(f"  → {len(df):,} planets loaded from cache.")
        return df

    cols = ",".join(COLUMNS)
    query = f"SELECT {cols} FROM pscomppars WHERE {WHERE} ORDER BY pl_name ASC"
    params = {"query": query, "format": "csv"}

    print("Querying NASA Exoplanet Archive …", flush=True)
    resp = requests.get(TAP_BASE, params=params, timeout=120)
    resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.text), comment="#", encoding="utf-8")
    print(f"  → {len(df):,} planets retrieved.")

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(RAW_DATA_FILE, index=False, quoting=1, encoding="utf-8")
    print(f"  → Saved raw data to {os.path.basename(RAW_DATA_FILE)}")

    return df
