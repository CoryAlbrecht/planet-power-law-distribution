from __future__ import annotations
import linmix  # type: ignore
import numpy as np
import pandas as pd
from typing import Any, Dict


def run_bayesian_slice(
    df: pd.DataFrame, m_lower_limit: float, m_upper_limit: float
) -> Dict[str, float]:
    """
    Performs a Bayesian linear regression on a subset of data up to a mass limit.
    Fits log10(R) = alpha + beta * log10(M), which corresponds to R = a * M^b.

    This version incorporates asymmetric errors and reliability weight filtering.
    """
    # 1. Intersection Filtering
    # Filter for the mass boundary AND ensure both weights > 0.
    # A weight of 0 (e.g., "Calculated Value") is excluded to prevent circular logic.
    mask: pd.Series = (
        (df["ppld_mass_kg"] > m_lower_limit)
        & (df["ppld_mass_kg"] <= m_upper_limit)
        & (df["ppld_mass_weight"] > 0)
        & (df["ppld_radius_weight"] > 0)
    )
    subset: pd.DataFrame = df[mask].copy()

    # Safety check for sufficient data points to run MCMC
    if len(subset) < 5:
        return {"a": np.nan, "b": np.nan, "b_std": np.nan}

    def to_vec(col_name: str) -> np.ndarray:
        return pd.to_numeric(subset[col_name], errors="coerce").fillna(0).values

    # 2. Extract Values and Errors
    m_val: np.ndarray = to_vec("ppld_mass_kg")
    m_err1: np.ndarray = to_vec("ppld_mass_kg_err1")
    m_err2: np.ndarray = to_vec("ppld_mass_kg_err2")

    r_val: np.ndarray = to_vec("ppld_radius_m")
    r_err1: np.ndarray = to_vec("ppld_radius_m_err1")
    r_err2: np.ndarray = to_vec("ppld_radius_m_err2")

    # 3. Symmetrize Errors (Mean Magnitude)
    # We average the absolute values of the plus and minus errors.
    mass_err_avg: np.ndarray = (np.abs(m_err1) + np.abs(m_err2)) / 2.0
    rad_err_avg: np.ndarray = (np.abs(r_err1) + np.abs(r_err2)) / 2.0

    # 4. Log-transform (Base 10) and Propagate Errors
    # Error in log10 space: sigma_log = sigma_linear / (val * ln(10))
    ln_10: float = np.log(10)

    x: np.ndarray = np.log10(m_val)
    xsig: np.ndarray = mass_err_avg / (m_val * ln_10)

    y: np.ndarray = np.log10(r_val)
    ysig: np.ndarray = rad_err_avg / (r_val * ln_10)

    # 5. Bayesian Regression
    # K=2 uses a Gaussian Mixture Model to account for the 'clumpy'
    # distribution of exoplanets in the archive.
    lm: Any = linmix.LinMix(x, y, xsig, ysig, K=2)
    lm.run_mcmc(silent=True)

    # 6. Parameter Extraction
    # b = exponent, log10(a) = intercept
    beta_mean: float = float(np.mean(lm.chain["beta"]))
    beta_std: float = float(np.std(lm.chain["beta"]))
    intercept_mean: float = float(np.mean(lm.chain["alpha"]))

    # Convert intercept back to the power-law coefficient 'a'
    a_coefficient: float = 10**intercept_mean

    return {"a": a_coefficient, "b": beta_mean, "b_std": beta_std}
