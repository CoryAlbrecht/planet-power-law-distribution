"""Split file generation and row filtering for exoplanet data."""

from __future__ import annotations

import os
from typing import Any, cast

import pandas as pd

from planet_power.constants import DATA_DIR
from planet_power.format import format_workbook
from planet_power.visualization import save_scatter_png


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


def create_split_files(
    df: pd.DataFrame,
    filter_rules: list[tuple[str, str]] | None = None,
    tag: str = "",
) -> None:
    """
    Write mass-vs-radius, mass-vs-density, and mass-vs-surface-gravity
    split files (.xlsx, .csv, .png) to DATA_DIR.

    Parameters
    ----------
    df : Full exoplanet DataFrame (using raw NASA column names plus ppld_*
        computed columns).
    filter_rules : Optional list of (column, regex) exclusion rules passed
        through to apply_filter_rules before writing each split.
    tag : Optional tag appended to output filenames, e.g. "filtered" produces
        mass-vs-radius.filtered.xlsx. Empty string produces no tag.
    """
    splits: list[dict[str, Any]] = [
        {
            "stem": "mass-vs-radius",
            "cols": [
                "pl_name",
                "ppld_mass_kg",
                "ppld_mass_kg_err1",
                "ppld_mass_kg_err2",
                "pl_bmassj_reflink",
                "pl_bmasse_reflink",
                "ppld_radius_m",
                "ppld_radius_m_err1",
                "ppld_radius_m_err2",
                "pl_radj_reflink",
                "pl_rade_reflink",
            ],
            "x_col": "ppld_mass_kg",
            "x_err_plus_col": "ppld_mass_kg_err1",
            "x_err_minus_col": "ppld_mass_kg_err2",
            "y_col": "ppld_radius_m",
            "y_err_plus_col": "ppld_radius_m_err1",
            "y_err_minus_col": "ppld_radius_m_err2",
        },
        {
            "stem": "mass-vs-density",
            "cols": [
                "pl_name",
                "ppld_mass_kg",
                "ppld_mass_kg_err1",
                "ppld_mass_kg_err2",
                "pl_bmassj_reflink",
                "pl_bmasse_reflink",
                "pl_dens",
                "pl_denserr1",
                "pl_denserr2",
                "pl_dens_reflink",
            ],
            "x_col": "ppld_mass_kg",
            "x_err_plus_col": "ppld_mass_kg_err1",
            "x_err_minus_col": "ppld_mass_kg_err2",
            "y_col": "pl_dens",
            "y_err_plus_col": "pl_denserr1",
            "y_err_minus_col": "pl_denserr2",
        },
        {
            "stem": "mass-vs-surface-gravity",
            "cols": [
                "pl_name",
                "ppld_mass_kg",
                "ppld_mass_kg_err1",
                "ppld_mass_kg_err2",
                "pl_bmassj_reflink",
                "pl_bmasse_reflink",
                "ppld_surf_grav_ms2",
                "ppld_surf_grav_ms2_err1",
                "ppld_surf_grav_ms2_err2",
                "pl_radj_reflink",
                "pl_rade_reflink",
            ],
            "x_col": "ppld_mass_kg",
            "x_err_plus_col": "ppld_mass_kg_err1",
            "x_err_minus_col": "ppld_mass_kg_err2",
            "y_col": "ppld_surf_grav_ms2",
            "y_err_plus_col": "ppld_surf_grav_ms2_err1",
            "y_err_minus_col": "ppld_surf_grav_ms2_err2",
        },
    ]

    for split in splits:
        print()
        df_split = cast(pd.DataFrame, df[split["cols"]])
        df_filtered = apply_filter_rules(df=df_split, filter_rules=filter_rules)
        if len(df_filtered) < len(df_split):
            print(
                f"Dataset {split['stem']} filtered from {len(df_split)} down to {len(df_filtered)} lines."
            )
        base_path = os.path.join(
            DATA_DIR,
            f"{split['stem']}{f'.{tag}' if tag else ''}",
        )
        df_filtered.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")  # type: ignore[reportUnknownMemberType]
        df_filtered.to_csv(f"{base_path}.csv", index=False, quoting=1, encoding="utf-8")  # type: ignore[reportUnknownMemberType]
        format_workbook(f"{base_path}.xlsx", len(df_split))

        save_scatter_png(
            df=df_filtered,
            output_path=f"{base_path}.png",
            x_col=split["x_col"],
            x_err_plus_col=split["x_err_plus_col"],
            x_err_minus_col=split["x_err_minus_col"],
            y_col=split["y_col"],
            y_err_plus_col=split["y_err_plus_col"],
            y_err_minus_col=split["y_err_minus_col"],
        )

        print(
            f"Created {os.path.basename(base_path)}.xlsx, "
            f"{os.path.basename(base_path)}.csv, "
            f"{os.path.basename(base_path)}.png"
        )
