# Exoplanet Mass–Radius–Density–Gravity Dataset

A Python script that queries the [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/) for all confirmed exoplanets with known mass, radius, and density, computes surface gravity with propagated uncertainties, classifies each planet using the Durand-Manterola (2011) three-class scheme, and exports the result as a formatted Excel workbook.

---

## Contents

- [Quickstart](#quickstart)
- [Output](#output)
- [Methodology](#methodology)
  - [Data source](#data-source)
  - [Surface gravity](#surface-gravity)
  - [Durand-Manterola classification](#durand-manterola-classification)
- [Caveats and known limitations](#caveats-and-known-limitations)
- [Future directions](#future-directions)
- [Citation](#citation)

---

## Quickstart

**Requirements:** Python 3.8+, git

### Automated install (Linux/macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/CoryAlbrecht/planet-power-law-distribution/main/install.sh | bash
```

### Automated install (Windows)

```powershell
irm https://raw.githubusercontent.com/CoryAlbrecht/planet-power-law-distribution/main/install.ps1 | iex
```

### Manual install

```bash
# Clone repository
git clone https://github.com/CoryAlbrecht/planet-power-law-distribution.git
cd planet-power-law-distribution

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\venv\Scripts\Activate.ps1  # Windows

# Install package
pip install -e .

# Fetch data and generate output files
planet-power -f

# Optional: Create split files for plotting
planet-power -f -s

# Clean up old files, keep only 1 most recent set
planet-power -C 1
```

Output files: `exoplanet_data.xlsx`, `exoplanet_data.csv`

With `-s` also creates:

- `mass-vs-radius.xlsx/.csv/.png` - Planet Name, Mass (kg), Mass Err± (kg), Radius (m), Radius Err± (m)
- `mass-vs-density.xlsx/.csv/.png` - Planet Name, Mass (kg), Mass Err± (kg), Density (g/cm³), Density Err±
- `mass-vs-surface-gravity.xlsx/.csv/.png` - Planet Name, Mass (kg), Mass Err± (kg), Surface Gravity (m/s²), Err±

No API key is required. The script queries NASA's public TAP service directly.

---

## Output

The workbook contains two sheets.

### Exoplanets sheet

One row per confirmed exoplanet. Columns are colour-coded by parameter group:

| Group            | Columns                                                             |
|------------------|---------------------------------------------------------------------|
| Identity         | Planet name, host star, planet letter                               |
| Discovery        | Method, year, facility                                              |
| Orbit            | Period, semi-major axis                                             |
| Mass (Jupiter)   | M_Jup with ±errors                                                  |
| Mass (Earth)     | M_Earth with ±errors                                                |
| Mass (kg)        | Mass in kg with ±errors                                             |
| Radius (Jupiter) | R_Jup with ±errors                                                  |
| Radius (Earth)   | R_Earth with ±errors                                                |
| Radius (m)       | Radius in m with ±errors                                            |
| Density          | g/cm³ with ±errors                                                  |
| Surface Gravity  | Computed g in m/s² and g_Earth, with ±errors                        |
| DM Class         | Durand-Manterola class (A/B/C), predicted g, and residual           |
| Stellar          | T_eff, stellar radius and mass, insolation, equilibrium temperature |
| System           | Distance, number of stars and planets in system                     |

### Notes sheet

Documents the TAP query used, physical constants, all computed column formulae, the Durand-Manterola classification scheme, and citation information.

---

## Methodology

### Data source

Data are pulled from the NASA Exoplanet Archive **PSCompPars** (Planetary Systems Composite Parameters) table via the [TAP service](https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html). This table provides one row per confirmed planet, drawing parameters from the best available published reference for each quantity. Parameters for a given planet may therefore come from different papers and are not guaranteed to be internally self-consistent.

The query filters for rows where all three of `pl_bmassj`, `pl_radj`, and `pl_dens` are non-null. Note that the archive calculates density from mass and radius (assuming a spherical planet) when no directly measured density is available; such rows are flagged as "Calculated Value" in the `pl_dens_reflink` column, which is not included in this dataset but can be retrieved separately if needed.

**Radius columns:** `pl_radj` and `pl_rade` represent the transit radius — the planet radius inferred from the fractional dimming of the host star during transit. For non-transiting planets, this is derived from a mass-radius relation (Chen & Kipping 2017). The reference unit for Jupiter radii is the equatorial radius at the 1-bar pressure level; the exact value used varies by source paper and is not standardised across the archive.

### Surface gravity

Surface gravity is computed from first principles:

```math
g = G · M / R²
```

where:

- `M = pl_bmassj × M_Jup` (kg)
- `R = pl_radj × R_Jup` (m)
- `G = 6.67430 × 10⁻¹¹ m³ kg⁻¹ s⁻²`
- `M_Jup = 1.89813 × 10²⁷ kg`
- `R_Jup = 7.14920 × 10⁷ m`

Uncertainty is propagated assuming independent mass and radius errors, using symmetric (averaged) uncertainties:

```math
σ_g / g = sqrt( (σ_M/M)² + (2·σ_R/R)² )
```

Results are reported in both m/s² and Earth gravities (g_Earth = 9.80665 m/s²).

### Durand-Manterola classification

Planets are assigned to one of three classes based on the empirical classification of Durand-Manterola (2011), who fitted power laws to radius, mean density, and surface gravity as functions of mass across 118 Solar System and transiting exoplanet bodies.

| Class | Mass range           | Approximate equivalent               | Representative members       |
|-------|----------------------|--------------------------------------|------------------------------|
| A     | M < 5×10²⁵ kg        | < ~0.026 M_Jup / ~8.3 M_Earth        | Earth, rocky super-Earths    |
| B     | 5×10²⁵ ≤ M < 10²⁷ kg | ~0.026–0.53 M_Jup / ~8.3–167 M_Earth | Neptune, Saturn, sub-Jovians |
| C     | M ≥ 10²⁷ kg          | > ~0.53 M_Jup                        | Jupiter, hot Jupiters        |

Class A planets have increasing radius, density, and surface gravity with mass. Class B planets have increasing radius but *decreasing* density and surface gravity — a consequence of volatile (H/He) accretion dominating mass gain once escape velocity is sufficient. Class C planets have nearly constant radius despite increasing mass, due to internal compression into denser phases.

For each planet, the script also computes the **predicted surface gravity** from the class-specific power laws (equations 4a–4c of Durand-Manterola 2011):

| Class | Power law              |
|-------|------------------------|
| A     | g = 2×10⁻¹⁰ × M^0.4282 |
| B     | g = 14937 × M^−0.1219  |
| C     | g = 4×10⁻²⁸ × M^1.0482 |

where M is in kg and g is in m/s². The **DM Grav. Residual** column gives the difference between the computed and predicted surface gravity in g_Earth units; large residuals flag planets that deviate significantly from the 2011 population trends, which may reflect updated measurements, unusual compositions, or boundary classification ambiguity.

---

## Caveats and known limitations

**PSCompPars is not self-consistent.** Parameters for a single planet may be drawn from different publications. This is appropriate for demographic studies but should be treated with caution for any individual planet.

**Density may be calculated, not measured.** Many densities in the archive are derived from mass and radius rather than independently measured. If your analysis requires only directly measured densities, filter on `pl_dens_reflink NOT LIKE '%alculated%'` (retrievable by adding `pl_dens_reflink` to the query).

**Radius is a transit radius.** It is not a volumetric mean or equatorial radius in the Solar System sense. For gas giants, it is pressure-level and wavelength-dependent. The Jupiter and Earth reference radii used for unit conversion are equatorial values, introducing a small systematic inconsistency.

**DM class boundaries were chosen by eye.** The paper gives no formal method for determining the A/B and B/C boundaries. The text states that planets in different mass ranges "seem to follow" different power laws — the cuts were placed where the slope of the point cloud appeared to change on the log-log plot, with no statistical breakpoint test and no uncertainty on the boundary locations themselves. The correlation coefficients in Table 1 validate the fits *given* the chosen boundaries, but do not independently justify where the boundaries sit. With a modern dataset of thousands of planets, a more rigorous approach would be to treat the boundary locations as free parameters — for example using piecewise regression breakpoint detection (`pwlf`) or a hierarchical Bayesian model — rather than inheriting the 2011 visual judgement. Planets near the boundaries (especially in the B/C transition region around 10²⁷ kg) may be ambiguously classified under the current hard cuts.

**DM power laws were fitted with OLS in log space.** This minimises relative errors and weights all planets equally regardless of measurement quality. It is not equivalent to fitting in linear space, and the resulting coefficients can be sensitive to outliers. Several of the correlation coefficients in the original paper — particularly for surface gravity in Class B (R = 0.248) and radius in Class C (R = 0.120) — fall below or near the paper's own critical significance threshold, so those specific power laws should be interpreted cautiously.

**The 2011 dataset was small.** The paper used 92 transiting exoplanets; the current NASA archive contains several thousand confirmed planets with measured radii. The class structure and power law exponents may shift with the larger, more diverse modern sample.

---

## My Observations

Three distinct groups of planets that can be seen in the unfiltered data

- A <= 1.2×10^25
- 1.2×10^25 <= B <= 8.1×10^26
- C >= 8.1×10^26

But the inflection points between te segments are oddly sharp. When a planet has a measured mass but no observed transit radius, the archive calculates the radius using the Chen & Kipping piecewise power law. That relation has hard breakpoints built into it — the archive's own documentation lists the exact boundaries at 2.04, 132, and 26,600 M_Earth, or 1.22×10^25 kg, 7.90×10^26 kg, and 1.589×10^29 kg.

The data that has the string `CALCULATED_VALUE` in the `*_reflink` can now be filtered out when creating the split files for each comaprison vs mass.

---

## Future directions

**Refit the power laws on the modern dataset.** With thousands of planets now available, the Durand-Manterola exponents could be refitted and compared to the 2011 values. This would test whether the classification scheme holds at scale.

**Use better fitting methods.** Ordinary least squares in log space assumes symmetric, equal-weight Gaussian errors on logged quantities — a poor match to real exoplanet data. More appropriate methods include:

- *Weighted least squares* — weights each point by 1/σ², respecting measurement quality
- *Orthogonal distance regression (ODR)* — accounts for uncertainties on both axes (`scipy.odr`)
- *Bayesian regression with intrinsic scatter* — the standard modern approach; the `linmix` package (Kelly 2007) is designed for exactly this use case

**Treat class boundaries as uncertain.** The hard mass cuts could be replaced with a mixture model or a hierarchical Bayesian model that allows planets near the boundaries to have probabilistic class membership.

**Separate calculated from measured densities.** Rerunning the analysis on the subset with directly measured densities would test whether the power law structure is robust to the archive's density imputation.

**Add escape velocity.** Durand-Manterola's toy model (Figure 5) uses escape velocity to explain volatile retention in Class B. This is straightforward to compute from the same mass and radius data and would add physical context to the dataset.

---

## Citation

If you use this dataset or script in your work, please cite the NASA Exoplanet Archive:

> NASA Exoplanet Archive. Planetary Systems Composite Parameters Table.
> DOI: [10.26133/NEA12](https://doi.org/10.26133/NEA12)

For the Durand-Manterola classification:

> Durand-Manterola, H.J. (2011). Planets: Power Laws and Classification.
> DOI [arXiv:1111.3986](https://arxiv.org/abs/1111.3986)

For the mass-radius relation used by the archive to fill missing radii/masses:

> Chen, J., & Kipping, D. (2017). Probabilistic Forecasting of the Masses and Radii of Other Worlds. *ApJ*, 834, 17.
> DOI: [10.3847/1538-4357/834/1/17](https://doi.org/10.3847/1538-4357/834/1/17)

For statistical methods

> Kelly, Brandon C. (2007) Some Aspects of Measurement Error in Linear Regression of Astronomical Data
> DOI: [10.1086/519947](https://iopscience.iop.org/article/10.1086/519947)

Data assumptions

> Chen, Jingjing; Kipping, David (2017) Probabilistic Forecasting of the Masses and Radii of Other Worlds
> DOI: [10.3847/1538-4357/834/1/17](https://iopscience.iop.org/article/10.3847/1538-4357/834/1/17)
