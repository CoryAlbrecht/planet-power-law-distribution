#!/usr/bin/env python3
"""Create scatter plot of Mass vs Radius from the most recent mass-vs-radius Excel file."""

import glob
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def get_latest_mass_vs_radius_file() -> str:
    """Find the most recent mass-vs-radius Excel file."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    files = sorted(glob.glob(os.path.join(data_dir, "mass-vs-radius.*.xlsx")), reverse=True)
    return files[0]


def main() -> None:
    """Create the scatter plot."""
    xlsx_path = get_latest_mass_vs_radius_file()
    timestamp = os.path.basename(xlsx_path).replace("mass-vs-radius.", "").replace(".xlsx", "")

    print(f"Reading {xlsx_path} …")
    df = pd.read_excel(xlsx_path, sheet_name="Exoplanets")

    print(f"Loaded {len(df)} rows")

    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)

    mass = df["Mass (kg)"].values
    radius = df["Radius (m)"].values
    mass_err_plus = df["Mass Err+ (kg)"].values
    mass_err_minus = df["Mass Err- (kg)"].values
    radius_err_plus = df["Radius Err+ (m)"].values
    radius_err_minus = df["Radius Err- (m)"].values

    mass_err_minus_abs = -mass_err_minus
    radius_err_minus_abs = -radius_err_minus

    xerr = [mass_err_minus_abs, mass_err_plus]
    yerr = [radius_err_minus_abs, radius_err_plus]

    ax.errorbar(
        mass,
        radius,
        xerr=xerr,
        yerr=yerr,
        fmt='o',
        linestyle='none',
        capsize=2,
        alpha=0.4,
    )

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Mass (kg)')
    ax.set_ylabel('Radius (m)')
    ax.set_title('Mass vs Radius')

    plt.tight_layout()

    output_path = xlsx_path.replace(".xlsx", ".png")
    plt.savefig(output_path)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()