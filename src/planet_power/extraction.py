"""Split file generation and row filtering for exoplanet data."""

from __future__ import annotations

import csv
import os

import pandas as pd

from planet_power.constants import (
    CALCULATED_DATA_FILE_TEMPLATE,
    DATA_DIR,
    RAW_DATA_FILE_TEMPLATE,
)
from planet_power.helpers import apply_filter_rules

# from planet_power.format import format_workbook
from planet_power.visualization import save_scatter_png


def combine_and_extract_and_graph(
    x_col: str,
    x_err_plus_col: str,
    x_err_minus_col: str,
    y_col: str,
    y_err_plus_col: str,
    y_err_minus_col: str,
    x_weight_col: str | None = None,
    x_hexcolor: str = "#FF0000",
    x_axis_min: float | None = None,
    x_axis_max: float | None = None,
    y_weight_col: str | None = None,
    y_hexcolor: str = "#00FF00",
    y_axis_min: float | None = None,
    y_axis_max: float | None = None,
    columns: list[str] = [],
    width_px: int = 3840,
    height_px: int = 2160,
    dpi: int = 150,
    error_cross: bool = False,
    filter_rules: list[tuple[str, str]] | None = None,
    stem: str | None = None,
    table: str = "ps",
    tag: str = "",
) -> pd.DataFrame | None:
    if columns is []:
        print("No columns were given to extract from data for scatter plot values.")
        return None
    if stem is None:
        print("No file base name given to save scatter plot values as.")
        return None

    raw_data_file = os.path.join(DATA_DIR, RAW_DATA_FILE_TEMPLATE.replace("%t", table))
    df = pd.read_csv(raw_data_file, encoding="utf-8")
    cols_from_df = [c for c in columns if c in df.columns]
    df_subset = df[["pl_name"] + cols_from_df].copy()

    extras_data_file = os.path.join(
        DATA_DIR, CALCULATED_DATA_FILE_TEMPLATE.replace("%t", table)
    )
    df_extras = pd.read_csv(extras_data_file, encoding="utf-8")
    cols_from_extras = [c for c in columns if c in df_extras.columns]
    df_extras_subset = df_extras[["pl_name"] + cols_from_extras].copy()

    df_combined = pd.merge(df_subset, df_extras_subset, on="pl_name", how="inner")

    out_file = os.path.join(
        DATA_DIR, f"{table}-{stem}{'.'+tag if tag != '' else ''}.csv"
    )
    df_combined.to_csv(
        out_file, index=False, quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8"
    )
    out_png = os.path.join(
        DATA_DIR, f"{table}-{stem}{'.'+tag if tag != '' else ''}.png"
    )
    df_filtered = apply_filter_rules(df_combined, filter_rules)
    print(f" Combined: {len(df_combined)} rows, Filtered: {len(df_filtered)} rows.")
    save_scatter_png(
        df_filtered,
        out_png,
        x_col=x_col,
        x_err_plus_col=x_err_plus_col,
        x_err_minus_col=x_err_minus_col,
        x_weight_col=x_weight_col,
        x_hexcolor=x_hexcolor,
        x_axis_min=x_axis_min,
        x_axis_max=x_axis_max,
        y_col=y_col,
        y_err_plus_col=y_err_plus_col,
        y_err_minus_col=y_err_minus_col,
        y_weight_col=y_weight_col,
        y_hexcolor=y_hexcolor,
        y_axis_min=y_axis_min,
        y_axis_max=y_axis_max,
        error_cross=error_cross,
        width_px=width_px,
        height_px=height_px,
        dpi=dpi,
    )
    print(f"Saved scatter plot to {out_png}")
    return df_combined


# def create_split_files(
#     filter_rules: list[tuple[str, str]] | None = None,
#     table: str = "ps",
#     tag: str = "",
# ) -> None:
#     """
#     Write mass-vs-radius, mass-vs-density, and mass-vs-surface-gravity
#     split files (.xlsx, .csv, .png) to DATA_DIR.

#     Parameters
#     ----------
#     df : Full exoplanet DataFrame (using raw NASA column names plus ppld_*
#         computed columns).
#     filter_rules : Optional list of (column, regex) exclusion rules passed
#         through to apply_filter_rules before writing each split.
#     tag : Optional tag appended to output filenames, e.g. "filtered" produces
#         mass-vs-radius.filtered.xlsx. Empty string produces no tag.
#     """
#     existing = get_latest_datafile(table=table)
#     latest = existing[0]
#     print(f"Using existing {os.path.basename(latest)}")
#     df = pd.read_csv(latest, encoding="utf-8")  # type: ignore[reportUnknownMemberType]

#     splits: list[dict[str, Any]] = [
#         {
#             "stem": "mass-vs-radius",
#             "cols": [
#                 "pl_name",
#                 "pl_massj",
#                 "pl_massjerr1",
#                 "pl_massjerr2",
#                 "pl_radj",
#                 "pl_radjerr1",
#                 "pl_radjerr2",
#             ],
#             "x_col": "pl_massj",
#             "x_err_plus_col": "pl_massjerr1",
#             "x_err_minus_col": "pl_massjerr2",
#             "y_col": "pl_radj",
#             "y_err_plus_col": "pl_radjerr1",
#             "y_err_minus_col": "pl_radjerr2",
#         },
#         {
#             "stem": "mass-vs-density",
#             "cols": [
#                 "pl_name",
#                 "pl_massj",
#                 "pl_massjerr1",
#                 "pl_massjerr2",
#                 "pl_dens",
#                 "pl_denserr1",
#                 "pl_denserr2",
#             ],
#             "x_col": "pl_massj",
#             "x_err_plus_col": "pl_massjerr1",
#             "x_err_minus_col": "pl_massjerr2",
#             "y_col": "pl_dens",
#             "y_err_plus_col": "pl_denserr1",
#             "y_err_minus_col": "pl_denserr2",
#         },
#         # {
#         #     "stem": "mass-vs-surface-gravity",
#         #     "cols": [
#         #         "pl_name",
#         #         "pl_massj",
#         #         "pl_massjerr1",
#         #         "pl_massjerr2",
#         #         "ppld_surf_grav_ms2",
#         #         "ppld_surf_grav_ms2_err1",
#         #         "ppld_surf_grav_ms2_err2",
#         #         "pl_radj_reflink",
#         #         "pl_rade_reflink",
#         #     ],
#         #     "x_col": "pl_massj",
#         #     "x_err_plus_col": "pl_massjerr1",
#         #     "x_err_minus_col": "pl_massjerr2",
#         #     "y_col": "ppld_surf_grav_ms2",
#         #     "y_err_plus_col": "ppld_surf_grav_ms2_err1",
#         #     "y_err_minus_col": "ppld_surf_grav_ms2_err2",
#         # },
#     ]

#     for split in splits:
#         print()
#         df_split = cast(pd.DataFrame, df[split["cols"]])
#         df_filtered = apply_filter_rules(df=df_split, filter_rules=filter_rules)
#         if len(df_filtered) < len(df_split):
#             print(
#                 f"Dataset {split['stem']} filtered from {len(df_split)} down to {len(df_filtered)} lines."
#             )
#         base_path = os.path.join(
#             DATA_DIR,
#             f"{split['stem']}-{table}-{f'.{tag}' if tag else ''}",
#         )
#         # df_filtered.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")  # type: ignore[reportUnknownMemberType]
#         df_filtered.to_csv(f"{base_path}.csv", index=False, quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8")  # type: ignore[reportUnknownMemberType]
#         # format_workbook(f"{base_path}.xlsx", len(df_split))

#         save_scatter_png(
#             df=df_filtered,
#             output_path=f"{base_path}.png",
#             x_col=split["x_col"],
#             x_err_plus_col=split["x_err_plus_col"],
#             x_err_minus_col=split["x_err_minus_col"],
#             y_col=split["y_col"],
#             y_err_plus_col=split["y_err_plus_col"],
#             y_err_minus_col=split["y_err_minus_col"],
#         )

#         print(
#             f"Created {os.path.basename(base_path)}.xlsx, "
#             f"{os.path.basename(base_path)}.csv, "
#             f"{os.path.basename(base_path)}.png"
#         )
