"""Compute weights, surface gravity, and assign Durand-Manterola classes."""

from typing import cast

import numpy as np
import pandas as pd

from planet_power.constants import (
    DM_AB_KG,
    DM_BC_KG,
    DM_GRAVITY,
    G_EARTH,
    M_JUP_KG,
    R_JUP_M,
    G,
)


def calculate_astrophysical_weight(
    value: float,
    err_plus: float | None = None,
    err_minus: float | None = None,
    provenance: str | None = None,
) -> float:
    """
    Calculate a normalized weight [0, 1] based on provenance and relative precision.
    """

    if provenance is not None:
        # 1. Base Provenance Weighting
        # (Using the hierarchy discussed previously)
        prov_matrix = {
            "Mass": 1.0,
            "Msin(i)/sin(i)": 1.0,
            "Msini": 0.2,
            "M-R relationship": 0.0,
        }
        w_base = prov_matrix.get(provenance, 0.1)
    else:
        w_base = 1.0

    # 2. Handle Error Completeness
    e1_exists = pd.notna(err_plus)
    e2_exists = pd.notna(err_minus)

    if not (e1_exists or e2_exists):
        return w_base * 0.1  # Heavy penalty for no errors

    if not (e1_exists and e2_exists):
        w_base *= 0.6  # Penalty for unilateral constraint (one error missing)

    # 3. Calculate Relative Error (Precision Factor)
    # Use the absolute average of available errors
    # sigma = np.nanmean([np.abs(err_plus), np.abs(err_minus)])
    vals = [np.abs(v) for v in [err_plus, err_minus] if v is not None]
    sigma = sum(vals) / len(vals)

    if value < 0 or pd.isna(sigma):
        return 0.0

    rel_error = sigma / value

    # Precision Factor: Higher relative error = lower weight.
    # Exponential decay ensures the weight drops off reasonably but
    # doesn't hit zero too early.
    precision_factor = np.exp(-rel_error)

    return float(np.clip(w_base * precision_factor, 0, 1))


def _row_mass_weight(row: pd.Series) -> float:
    bmassj: float = row["pl_bmassj"]
    bmassjerr1: float | None = (
        row["pl_bmassjerr1"] if pd.notna(row["pl_bmassjerr1"]) else None
    )
    bmassjerr2: float | None = (
        row["pl_bmassjerr2"] if pd.notna(row["pl_bmassjerr2"]) else None
    )
    bmassprov: str | None = (
        row["pl_bmassprov"] if pd.notna(row["pl_bmassprov"]) else None
    )
    return calculate_astrophysical_weight(
        value=bmassj, err_plus=bmassjerr1, err_minus=bmassjerr2, provenance=bmassprov
    )


def _row_radius_weight(row: pd.Series) -> float:
    radius: float = row["pl_radj"]
    err1: float | None = row["pl_radjerr1"] if pd.notna(row["pl_radjerr1"]) else None
    err2: float | None = row["pl_radjerr2"] if pd.notna(row["pl_radjerr2"]) else None
    return calculate_astrophysical_weight(value=radius, err_plus=err1, err_minus=err2)


def _row_density_weight(row: pd.Series) -> float:
    density: float = row["pl_dens"]
    err1: float | None = row["pl_denserr1"] if pd.notna(row["pl_denserr1"]) else None
    err2: float | None = row["pl_denserr2"] if pd.notna(row["pl_denserr2"]) else None
    return calculate_astrophysical_weight(value=density, err_plus=err1, err_minus=err2)


def calculate_extras(df: pd.DataFrame, data_table: str = "ps") -> pd.DataFrame:
    """
    Compute derived columns from raw NASA mass, radius, and density columns
    and return them as a new DataFrame alongside the planet identity columns.

    The output DataFrame is also written to a CSV named
    ``{table}-computed[.{tag}].csv`` in DATA_DIR.

    Parameters
    ----------
    df : DataFrame containing the raw NASA columns (pl_bmassj*, pl_radj*,
        pl_bmassprov, pl_name, pl_letter, hostname).
    table : Source table name used in the output filename (default: "ps").
    tag : Optional tag appended to the output filename.

    Returns
    -------
    DataFrame with identity columns and all ppld_* computed columns.
    """

    print("Computing extra data …")

    mass_weights: pd.Series[float] = df.apply(_row_mass_weight, axis=1)
    radius_weights: pd.Series[float] = df.apply(_row_radius_weight, axis=1)
    density_weights: pd.Series[float] = df.apply(_row_density_weight, axis=1)

    df_extras = pd.DataFrame(
        {
            "hostname": df["hostname"],
            "pl_letter": df["pl_letter"],
            "pl_name": df["pl_name"],
            "ppld_mass_kg": df["pl_bmassj"] * M_JUP_KG,
            "ppld_mass_kg_err1": df["pl_bmassjerr1"] * M_JUP_KG,
            "ppld_mass_kg_err2": df["pl_bmassjerr2"] * M_JUP_KG,
            "ppld_mass_kg_weight": mass_weights,
            "ppld_radius_m": df["pl_radj"] * R_JUP_M,
            "ppld_radius_m_err1": df["pl_radjerr1"] * R_JUP_M,
            "ppld_radius_m_err2": df["pl_radjerr2"] * R_JUP_M,
            "ppld_radius_m_weight": radius_weights,
            "ppld_density_gcm3_weight": density_weights,
        }
    )

    # Compute surface gravity
    df_extras = compute_surface_gravity(df_extras)

    # Assign Durand-Manterola classes
    df_extras = assign_dm_class(df_extras)

    return df_extras


def compute_surface_gravity(df: pd.DataFrame) -> pd.DataFrame:
    """Compute surface gravity g = G·M / R² with propagated uncertainties."""
    print("Compute surface gravity g = G·M / R² with propagated uncertainties.")
    M = df["ppld_mass_kg"].fillna(0)
    R = df["ppld_radius_m"].fillna(0)
    g = G * M / R**2

    df["ppld_surf_grav_ms2"] = g.round(4)
    df["ppld_surf_grav_earth"] = (g / G_EARTH).round(4)

    # --- UPPER BOUND (Maximum Gravity) ---
    # To maximize g, we need the largest Mass and the smallest Radius.
    # Since Radius_err2 is negative, R + R_err2 makes the denominator smaller.
    M_max = (M + df["ppld_mass_kg_err1"]).clip(lower=0)
    R_min = (R + df["ppld_radius_m_err2"]).clip(lower=1e-10)
    g_max = G * M_max / R_min**2

    # --- LOWER BOUND (Minimum Gravity) ---
    # To minimize g, we need the smallest Mass and the largest Radius.
    M_min = (M + df["ppld_mass_kg_err2"]).clip(lower=0)
    R_max = (R + df["ppld_radius_m_err1"]).clip(lower=1e-10)
    g_min = G * M_min / R_max**2

    # --- FINAL ASSIGNMENT ---
    # Positive value (e.g., +0.5)
    df["ppld_surf_grav_ms2_err1"] = (g_max - g).round(4)

    # Negative value (e.g., -0.3)
    df["ppld_surf_grav_ms2_err2"] = (g_min - g).round(4)

    df["ppld_surf_grav_earth_err1"] = (df["ppld_surf_grav_ms2_err1"] / G_EARTH).round(4)
    df["ppld_surf_grav_earth_err2"] = (df["ppld_surf_grav_ms2_err2"] / G_EARTH).round(4)

    return df


def assign_dm_class(df: pd.DataFrame) -> pd.DataFrame:
    """Assign Durand-Manterola (2011) planet class based on mass in kg."""
    print("Assign Durand-Manterola (2011) planet class based on mass in kg.")
    M_kg: pd.Series = df["ppld_mass_kg"]
    M_kg_null: pd.Series = df["ppld_mass_kg"].isna()

    dm_class_arr: pd.Series = pd.cut(
        M_kg,
        bins=[-np.inf, DM_AB_KG, DM_BC_KG, np.inf],
        labels=["A", "B", "C"],
        right=False,
    )
    dm_class_arr = dm_class_arr.astype(object)
    dm_class_arr = dm_class_arr.where(~M_kg_null, None)
    df["dm_class"] = dm_class_arr

    coeff_a, exp_a = DM_GRAVITY["A"]
    coeff_b, exp_b = DM_GRAVITY["B"]
    coeff_c, exp_c = DM_GRAVITY["C"]

    pred_g_a: pd.Series = coeff_a * (M_kg**exp_a)
    pred_g_b: pd.Series = coeff_b * (M_kg**exp_b)
    pred_g_c: pd.Series = coeff_c * (M_kg**exp_c)

    pred_g: np.ndarray = np.select(
        [df["dm_class"] == "A", df["dm_class"] == "B", df["dm_class"] == "C"],
        [pred_g_a, pred_g_b, pred_g_c],
        default=np.nan,
    )
    pred_g = np.where(M_kg_null, np.nan, pred_g)

    pred_g_rounded: np.ndarray = np.round(pred_g, 4)
    df["dm_pred_g_ms2"] = pd.Series(
        data=np.where(np.isnan(pred_g_rounded), None, pred_g_rounded),  # type: ignore[call-overload]
        dtype=object,
    )

    pred_g_earth_rounded: np.ndarray = np.round(pred_g_rounded / G_EARTH, 4)
    df["dm_pred_g_earth"] = pd.Series(
        data=np.where(np.isnan(pred_g_earth_rounded), None, pred_g_earth_rounded),  # type: ignore[call-overload]
        dtype=object,
    )

    surf_grav_earth: np.ndarray = cast(np.ndarray, df["ppld_surf_grav_earth"].values)
    residual: np.ndarray = surf_grav_earth - pred_g_rounded / G_EARTH
    residual_rounded: np.ndarray = np.round(residual, 4)
    df["dm_grav_residual"] = pd.Series(
        data=np.where(np.isnan(residual_rounded), None, residual_rounded),  # type: ignore[call-overload]
        dtype=object,
    )

    return df
