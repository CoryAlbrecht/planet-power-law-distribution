"""Physical constants and configuration values."""

G = 6.67430e-11
M_JUP_KG = 1.89813e27
R_JUP_M = 7.14920e7
G_EARTH = 9.80665

DM_AB_KG = 5.0e25
DM_BC_KG = 1.0e27

DM_GRAVITY = {
    "A": (2e-10, 0.4282),
    "B": (14937, -0.1219),
    "C": (4e-28, 1.0482),
}

TAP_BASE = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

COLUMNS = [
    "pl_name",
    "hostname",
    "pl_letter",
    "discoverymethod",
    "disc_year",
    "disc_facility",
    "pl_orbper",
    "pl_orbsmax",
    "pl_bmassj",
    "pl_bmassjerr1",
    "pl_bmassjerr2",
    "pl_bmassj_reflink",
    "pl_bmasse",
    "pl_bmasseerr1",
    "pl_bmasseerr2",
    "pl_bmasse_reflink",
    "pl_radj",
    "pl_radjerr1",
    "pl_radjerr2",
    "pl_radj_reflink",
    "pl_rade",
    "pl_radeerr1",
    "pl_radeerr2",
    "pl_rade_reflink",
    "pl_dens",
    "pl_denserr1",
    "pl_denserr2",
    "pl_dens_reflink",
    "pl_eqt",
    "pl_insol",
    "st_teff",
    "st_rad",
    "st_mass",
    "sy_dist",
    "sy_snum",
    "sy_pnum",
]

WHERE = "pl_bmassj IS NOT NULL AND pl_radj IS NOT NULL AND pl_dens IS NOT NULL"

GROUP_COLOURS = {
    "Identity": "D9EAD3",
    "Discovery": "FCE5CD",
    "Orbit": "CFE2F3",
    "MassJ": "EAD1DC",
    "MassE": "FFD6B0",
    "RadiusJ": "D9D2E9",
    "RadiusE": "C9E1F5",
    "Density": "FFF2CC",
    "Stellar": "F4CCCC",
    "Surface Gravity": "B7E1CD",
    "System": "E9E9E9",
    "DM Class": "D0E0FF",
}

COLUMN_GROUPS = {
    "Planet Name": "Identity",
    "Host Star": "Identity",
    "Letter": "Identity",
    "Discovery Method": "Discovery",
    "Discovery Year": "Discovery",
    "Discovery Facility": "Discovery",
    "Orbital Period (days)": "Orbit",
    "Semi-Major Axis (AU)": "Orbit",
    "Mass (M_Jup)": "MassJ",
    "Mass Err+ (M_Jup)": "MassJ",
    "Mass Err- (M_Jup)": "MassJ",
    "Mass Ref (M_Jup)": "MassJ",
    "Mass (M_Earth)": "MassE",
    "Mass Err+ (M_Earth)": "MassE",
    "Mass Err- (M_Earth)": "MassE",
    "Mass Ref (M_Earth)": "MassE",
    "Radius (R_Jup)": "RadiusJ",
    "Radius Err+ (R_Jup)": "RadiusJ",
    "Radius Err- (R_Jup)": "RadiusJ",
    "Radius Ref (R_Jup)": "RadiusJ",
    "Radius (R_Earth)": "RadiusE",
    "Radius Err+ (R_Earth)": "RadiusE",
    "Radius Err- (R_Earth)": "RadiusE",
    "Radius Ref (R_Earth)": "RadiusE",
    "Density (g/cm³)": "Density",
    "Density Err+ (g/cm³)": "Density",
    "Density Err- (g/cm³)": "Density",
    "Density Ref": "Density",
    "Equil. Temp. (K)": "Stellar",
    "Insolation (F_Earth)": "Stellar",
    "Stellar T_eff (K)": "Stellar",
    "Stellar Radius (R_Sun)": "Stellar",
    "Stellar Mass (M_Sun)": "Stellar",
    "Distance (pc)": "System",
    "Stars in System": "System",
    "Planets in System": "System",
    "Mass (kg)": "MassJ",
    "Mass Unc. (kg)": "MassJ",
    "Radius (m)": "RadiusJ",
    "Radius Unc. (m)": "RadiusJ",
    "Surface Gravity (m/s²)": "Surface Gravity",
    "Surface Gravity (g_Earth)": "Surface Gravity",
    "Surf. Grav. Unc. (m/s²)": "Surface Gravity",
    "Surf. Grav. Unc. (g_Earth)": "Surface Gravity",
    "DM Class": "DM Class",
    "DM Predicted g (m/s²)": "DM Class",
    "DM Predicted g (g_Earth)": "DM Class",
    "DM Grav. Residual (g_Earth)": "DM Class",
}
