"""Physical constants and configuration values."""

G = 6.67430e-11
M_JUP_KG = 1.89813e27
R_JUP_M = 7.14920e7
G_EARTH = 9.80665

DM_AB_KG = 5.0e25
DM_BC_KG = 1.0e27

DM_GRAVITY: dict[str, tuple[float, float]] = {
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

WHERE = "(pl_bmassj IS NOT NULL OR pl_bmasse IS NOT NULL) AND (pl_radj IS NOT NULL OR pl_rade IS NOT NULL) AND pl_dens IS NOT NULL"

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
    "pl_name": "Identity",
    "hostname": "Identity",
    "pl_letter": "Identity",
    "discoverymethod": "Discovery",
    "disc_year": "Discovery",
    "disc_facility": "Discovery",
    "pl_orbper": "Orbit",
    "pl_orbsmax": "Orbit",
    "pl_bmassj": "MassJ",
    "pl_bmassjerr1": "MassJ",
    "pl_bmassjerr2": "MassJ",
    "pl_bmassj_reflink": "MassJ",
    "pl_bmasse": "MassE",
    "pl_bmasseerr1": "MassE",
    "pl_bmasseerr2": "MassE",
    "pl_bmasse_reflink": "MassE",
    "pl_radj": "RadiusJ",
    "pl_radjerr1": "RadiusJ",
    "pl_radjerr2": "RadiusJ",
    "pl_radj_reflink": "RadiusJ",
    "pl_rade": "RadiusE",
    "pl_radeerr1": "RadiusE",
    "pl_radeerr2": "RadiusE",
    "pl_rade_reflink": "RadiusE",
    "pl_dens": "Density",
    "pl_denserr1": "Density",
    "pl_denserr2": "Density",
    "pl_dens_reflink": "Density",
    "pl_eqt": "Stellar",
    "pl_insol": "Stellar",
    "st_teff": "Stellar",
    "st_rad": "Stellar",
    "st_mass": "Stellar",
    "sy_dist": "System",
    "sy_snum": "System",
    "sy_pnum": "System",
    "ppld_mass_kg": "MassJ",
    "ppld_mass_kg_err1": "MassJ",
    "ppld_mass_kg_err2": "MassJ",
    "ppld_rad_m": "RadiusJ",
    "ppld_rad_m_err1": "RadiusJ",
    "ppld_rad_m_err2": "RadiusJ",
    "ppld_surfgrav_ms2": "Surface Gravity",
    "ppld_surfgrav_g": "Surface Gravity",
    "ppld_surfgrav_ms2_err1": "Surface Gravity",
    "ppld_surfgrav_ms2_err2": "Surface Gravity",
    "ppld_surfgrav_g_err1": "Surface Gravity",
    "ppld_surfgrav_g_err2": "Surface Gravity",
    "dm_class": "DM Class",
    "dm_predgrav_ms2": "DM Class",
    "dm_predgrav_g": "DM Class",
    "dm_predgrav_g_res": "DM Class",
}
