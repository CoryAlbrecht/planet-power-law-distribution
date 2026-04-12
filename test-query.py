#!/usr/bin/env python3
"""One-off script to query NASA Exoplanet Archive TAP service."""

import os
import requests
import pandas as pd
from io import StringIO

TAP_BASE = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

query = """SELECT pl_name,hostname,pl_letter,discoverymethod,disc_year,disc_facility,pl_orbper,pl_orbsmax,pl_bmassj,pl_bmassjerr1,pl_bmassjerr2,pl_bmassj_reflink,pl_bmasse,pl_bmasseerr1,pl_bmasseerr2,pl_bmasse_reflink,pl_radj,pl_radjerr1,pl_radjerr2,pl_radj_reflink,pl_rade,pl_radeerr1,pl_radeerr2,pl_rade_reflink,pl_dens,pl_denserr1,pl_denserr2,pl_dens_reflink,pl_eqt,pl_insol,st_teff,st_rad,st_mass,sy_dist,sy_snum,sy_pnum
FROM pscomppars
WHERE (pl_bmassj IS NOT NULL OR pl_bmasse IS NOT NULL) AND (pl_radj IS NOT NULL OR pl_rade IS NOT NULL) AND pl_radj_reflink NOT LIKE '%CALCULATED_VALUE%' AND pl_rade_reflink NOT LIKE '%CALCULATED_VALUE%' AND pl_dens IS NOT NULL AND pl_dens_reflink  NOT LIKE '%CALCULATED_VALUE%'
ORDER BY pl_name ASC"""

params = {"query": query, "format": "csv"}

print("Querying NASA Exoplanet Archive …", flush=True)
resp = requests.get(TAP_BASE, params=params, timeout=120)
resp.raise_for_status()

df = pd.read_csv(StringIO(resp.text), comment="#", encoding="utf-8")
print(f"  → {len(df):,} planets retrieved.")

os.makedirs("./data", exist_ok=True)
df.to_csv("./data/test-query.csv", index=False, quoting=1, encoding="utf-8")
print("  → Saved to ./data/test-query.csv")
