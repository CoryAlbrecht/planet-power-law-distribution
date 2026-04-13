"""Compute surface gravity and assign Durand-Manterola classes."""

import pandas as pd

from planet_power.constants import (
    G,
    M_JUP_KG,
    R_JUP_M,
    G_EARTH,
    DM_AB_KG,
    DM_BC_KG,
    DM_GRAVITY,
)


def compute_surface_gravity(df: pd.DataFrame) -> pd.DataFrame:
    """Compute surface gravity g = G·M / R² with propagated uncertainties."""
    M = df["pl_bmassj"].fillna(0) * M_JUP_KG
    R = df["pl_radj"].fillna(0) * R_JUP_M
    g = G * M / R**2

    df["ppld_mass_kg"] = M
    df["ppld_mass_kg_err1"] = df["pl_bmassjerr1"].fillna(0) * M_JUP_KG
    df["ppld_mass_kg_err2"] = df["pl_bmassjerr2"].fillna(0) * M_JUP_KG

    df["ppld_radius_m"] = R
    df["ppld_radius_m_err1"] = df["pl_radjerr1"].fillna(0) * R_JUP_M
    df["ppld_radius_m_err2"] = df["pl_radjerr2"].fillna(0) * R_JUP_M

    df["ppld_surf_grav_ms2"] = g.round(4)
    df["ppld_surf_grav_earth"] = (g / G_EARTH).round(4)

    M_err1 = df["ppld_mass_kg_err1"]
    M_err2 = df["ppld_mass_kg_err2"]
    R_err1 = df["ppld_radius_m_err1"]
    R_err2 = df["ppld_radius_m_err2"]

    M_large = (M + M_err1).clip(lower=0)
    R_large = (R + R_err1).clip(lower=1e-10)
    g_large = G * M_large / R_large**2

    M_small = (M - M_err2).clip(lower=0)
    R_small = (R - R_err2).clip(lower=1e-10)
    g_small = G * M_small / R_small**2

    df["ppld_surf_grav_ms2_err1"] = (g_large - g).round(4)
    df["ppld_surf_grav_ms2_err2"] = (g - g_small).round(4)
    df["ppld_surf_grav_earth_err1"] = (df["ppld_surf_grav_ms2_err1"] / G_EARTH).round(4)
    df["ppld_surf_grav_earth_err2"] = (df["ppld_surf_grav_ms2_err2"] / G_EARTH).round(4)

    return df


def assign_dm_class(df: pd.DataFrame) -> pd.DataFrame:
    """Assign Durand-Manterola (2011) planet class based on mass in kg."""
    M_kg = df["pl_bmassj"] * M_JUP_KG

    def classify(m: float) -> str | None:
        if pd.isna(m):
            return None
        if m < DM_AB_KG:
            return "A"
        if m < DM_BC_KG:
            return "B"
        return "C"

    df["dm_class"] = M_kg.apply(classify)

    def predicted_g(row: pd.Series) -> float | None:
        cls = row["dm_class"]
        m = row["pl_bmassj"] * M_JUP_KG
        if cls is None or pd.isna(m):
            return None
        coeff, exp = DM_GRAVITY[cls]
        return round(coeff * (m**exp), 4)

    df["dm_pred_g_ms2"] = df.apply(predicted_g, axis=1)
    df["dm_pred_g_earth"] = (df["dm_pred_g_ms2"] / G_EARTH).round(4)
    df["dm_grav_residual"] = (df["ppld_surf_grav_earth"] - df["dm_pred_g_earth"]).round(
        4
    )

    return df
