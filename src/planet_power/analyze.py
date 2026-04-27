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
        & (df["ppld_mass_kg_weight"] > 0)
        & (df["ppld_radius_m_weight"] > 0)
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

    return {
        "a": a_coefficient,
        "b": beta_mean,
        "b_std": beta_std,
        "m_lower_limit": m_lower_limit,
        "m_upper_limit": m_upper_limit,
    }


def run_bayesian_slice_weighted(
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
        & (df["ppld_mass_kg_weight"] > 0)
        & (df["ppld_radius_m_weight"] > 0)
    )
    subset: pd.DataFrame = df[mask].copy()

    # Safety check for sufficient data points to run MCMC
    if len(subset) < 5:
        return {
            "a": np.nan,
            "b": np.nan,
            "b_std": np.nan,
            "n": len(subset),
            "m_lower_limit": m_lower_limit,
            "m_upper_limit": m_upper_limit,
        }

    def to_vec(col_name: str) -> np.ndarray:
        return pd.to_numeric(subset[col_name], errors="coerce").fillna(0).values

    # 2. Extract Values and Errors
    m_val: np.ndarray = to_vec("ppld_mass_kg")
    m_err1: np.ndarray = to_vec("ppld_mass_kg_err1")
    m_err2: np.ndarray = to_vec("ppld_mass_kg_err2")
    m_weight = to_vec("ppld_mass_kg_weight")

    r_val: np.ndarray = to_vec("ppld_radius_m")
    r_err1: np.ndarray = to_vec("ppld_radius_m_err1")
    r_err2: np.ndarray = to_vec("ppld_radius_m_err2")
    r_weight = to_vec("ppld_radius_m_weight")

    # 3. Symmetrize Errors (Mean Magnitude)
    # We average the absolute values of the plus and minus errors.
    mass_err_avg: np.ndarray = (np.abs(m_err1) + np.abs(m_err2)) / 2.0
    rad_err_avg: np.ndarray = (np.abs(r_err1) + np.abs(r_err2)) / 2.0
    # 3. APPLY WEIGHTS: Scale the linear errors
    # Lower weight increases the error, making the point less influential.
    # Note: We use np.sqrt because weights apply to variance, not std dev.
    mass_err_weighted = mass_err_avg / np.sqrt(m_weight)
    rad_err_weighted = rad_err_avg / np.sqrt(r_weight)

    # 4. Log-transform (Base 10) and Propagate Errors
    # Error in log10 space: sigma_log = sigma_linear / (val * ln(10))
    ln_10: float = np.log(10)

    x: np.ndarray = np.log10(m_val)
    xsig: np.ndarray = mass_err_weighted / (m_val * ln_10)

    y: np.ndarray = np.log10(r_val)
    ysig: np.ndarray = rad_err_weighted / (r_val * ln_10)

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

    return {
        "a": a_coefficient,
        "b": beta_mean,
        "b_std": beta_std,
        "n": len(subset),
        "m_lower_limit": m_lower_limit,
        "m_upper_limit": m_upper_limit,
    }


def run_numpyro_slice_weighted(
    df: pd.DataFrame, m_lower_limit: float, m_upper_limit: float
) -> Dict[str, float]:
    """
    JAX/NumPyro replacement for the linmix-based Bayesian regression.

    Fits log10(R) = alpha + beta * log10(M) via NUTS (No-U-Turn Sampler).
    Mirrors run_bayesian_slice_weighted() exactly in its data preparation
    (weight-scaled asymmetric errors, log10-propagation) but replaces the
    Gibbs sampler with NUTS for GPU-compatibility and faster convergence.

    Probabilistic model:
    - A K=2 Gaussian mixture prior on the latent true log10(mass), matching
      linmix's treatment of the clumpy exoplanet mass distribution.
    - Per-point heteroscedastic measurement noise on both axes.
    - A HalfNormal prior on intrinsic scatter in log10(radius).

    JAX imports are deferred so the XLA runtime is only initialised in worker
    processes, keeping the main process lightweight and spawn-safe.
    """
    # Deferred imports: JAX must not be imported in the main process before
    # multiprocessing.Pool(context="spawn") forks, or XLA state is corrupted.
    import jax
    import jax.numpy as jnp
    import numpyro
    import numpyro.distributions as dist
    from numpyro.infer import MCMC, NUTS

    # ── 1. Filter ──────────────────────────────────────────────────────────
    mask: pd.Series = (
        (df["ppld_mass_kg"] > m_lower_limit)
        & (df["ppld_mass_kg"] <= m_upper_limit)
        & (df["ppld_mass_kg_weight"] > 0)
        & (df["ppld_radius_m_weight"] > 0)
    )
    subset: pd.DataFrame = df[mask].copy()

    if len(subset) < 5:
        return {
            "a": np.nan,
            "b": np.nan,
            "b_std": np.nan,
            "n": len(subset),
            "m_lower_limit": m_lower_limit,
            "m_upper_limit": m_upper_limit,
        }

    def to_vec(col_name: str) -> np.ndarray:
        return pd.to_numeric(subset[col_name], errors="coerce").fillna(0).values

    # ── 2. Extract values and weight-scaled errors ─────────────────────────
    m_val: np.ndarray = to_vec("ppld_mass_kg")
    m_err1: np.ndarray = to_vec("ppld_mass_kg_err1")
    m_err2: np.ndarray = to_vec("ppld_mass_kg_err2")
    m_weight: np.ndarray = to_vec("ppld_mass_kg_weight")

    r_val: np.ndarray = to_vec("ppld_radius_m")
    r_err1: np.ndarray = to_vec("ppld_radius_m_err1")
    r_err2: np.ndarray = to_vec("ppld_radius_m_err2")
    r_weight: np.ndarray = to_vec("ppld_radius_m_weight")

    mass_err_avg: np.ndarray = (np.abs(m_err1) + np.abs(m_err2)) / 2.0
    rad_err_avg: np.ndarray = (np.abs(r_err1) + np.abs(r_err2)) / 2.0
    mass_err_weighted: np.ndarray = mass_err_avg / np.sqrt(m_weight)
    rad_err_weighted: np.ndarray = rad_err_avg / np.sqrt(r_weight)

    # ── 3. Log-transform and propagate errors ──────────────────────────────
    # sigma_log10 = sigma_linear / (value * ln10)
    # Floor at 1e-6 prevents degenerate zero-error points dominating the fit.
    ln_10: float = np.log(10)
    x_np: np.ndarray = np.log10(m_val)
    xsig_np: np.ndarray = np.maximum(mass_err_weighted / (m_val * ln_10), 1e-6)
    y_np: np.ndarray = np.log10(r_val)
    ysig_np: np.ndarray = np.maximum(rad_err_weighted / (r_val * ln_10), 1e-6)

    # ── 4. Cast to JAX arrays ──────────────────────────────────────────────
    x_obs = jnp.array(x_np, dtype=jnp.float32)
    y_obs = jnp.array(y_np, dtype=jnp.float32)
    x_sig = jnp.array(xsig_np, dtype=jnp.float32)
    y_sig = jnp.array(ysig_np, dtype=jnp.float32)

    K: int = 2

    # ── 5. Probabilistic model ─────────────────────────────────────────────
    def _model(
        x_obs: Any,
        y_obs: Any,
        x_sig: Any,
        y_sig: Any,
    ) -> None:
        # Regression line in log10 space
        alpha = numpyro.sample("alpha", dist.Normal(0.0, 10.0))
        beta = numpyro.sample("beta", dist.Normal(0.0, 10.0))

        # Intrinsic scatter in log10(radius) beyond measurement noise
        sigsqr = numpyro.sample("sigsqr", dist.HalfNormal(1.0))

        # K=2 Gaussian mixture prior on true log10(mass).
        # Mirrors linmix's K=2 GMM; captures the bimodal terrestrial/Jovian
        # population structure without forcing a unimodal prior on x_true.
        pi = numpyro.sample("pi", dist.Dirichlet(jnp.ones(K)))
        mu_k = numpyro.sample(
            "mu_k",
            dist.Normal(jnp.mean(x_obs) * jnp.ones(K), 3.0),
        )
        sig_k = numpyro.sample("sig_k", dist.HalfNormal(jnp.ones(K)))

        mixture = dist.MixtureSameFamily(
            dist.Categorical(probs=pi),
            dist.Normal(mu_k, sig_k),
        )

        N: int = x_obs.shape[0]
        with numpyro.plate("obs", N):
            # Latent true log10(mass) drawn from the GMM
            x_true = numpyro.sample("x_true", mixture)

            # Observed log10(mass): true value + measurement noise
            numpyro.sample("x_like", dist.Normal(x_true, x_sig), obs=x_obs)

            # Observed log10(radius): regression + intrinsic scatter +
            # measurement noise, combined in quadrature
            y_scale = jnp.sqrt(y_sig**2 + sigsqr)
            numpyro.sample(
                "y_like",
                dist.Normal(alpha + beta * x_true, y_scale),
                obs=y_obs,
            )

    # ── 6. NUTS sampling ───────────────────────────────────────────────────
    # Key is derived from slice bounds: reproducible per slice, unique across
    # slices, no global state needed in worker processes.
    rng_seed: int = int(abs(m_lower_limit + m_upper_limit)) % (2**31)
    rng_key = jax.random.PRNGKey(rng_seed)

    mcmc = MCMC(
        NUTS(_model),
        num_warmup=500,
        num_samples=1000,
        num_chains=1,
        progress_bar=False,  # per-slice progress handled by cli_analyze via stderr
    )
    mcmc.run(rng_key, x_obs, y_obs, x_sig, y_sig)

    # ── 7. Posterior summaries ─────────────────────────────────────────────
    samples = mcmc.get_samples()
    beta_arr: np.ndarray = np.array(samples["beta"])
    alpha_arr: np.ndarray = np.array(samples["alpha"])

    beta_mean: float = float(np.mean(beta_arr))
    beta_std: float = float(np.std(beta_arr))
    intercept_mean: float = float(np.mean(alpha_arr))
    a_coefficient: float = float(10**intercept_mean)

    return {
        "a": a_coefficient,
        "b": beta_mean,
        "b_std": beta_std,
        "n": len(subset),
        "m_lower_limit": m_lower_limit,
        "m_upper_limit": m_upper_limit,
    }
