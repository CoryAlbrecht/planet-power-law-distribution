"""Compute surface gravity and assign Durand-Manterola classes."""

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
    M_kg: pd.Series = df["pl_bmassj"] * M_JUP_KG
    M_kg_null: pd.Series = df["pl_bmassj"].isna()

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
