"""Command-line interface for the exoplanet data fetcher."""

from __future__ import annotations

import argparse
import csv
import io
import multiprocessing
import os
import re
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import jax
import numpy as np
import pandas as pd
from rich.console import Console
from rich.theme import Theme

from planet_power.analyze import run_bayesian_slice_weighted, run_numpyro_slice_weighted
from planet_power.compute import calculate_extras
from planet_power.constants import (
    CALCULATED_DATA_FILE_TEMPLATE,
    DATA_DIR,
    EXTRACTED_DATA_FILE_TEMPLATE,
    RAW_DATA_FILE_TEMPLATE,
)
from planet_power.helpers import (
    apply_filter_rules,
    combine_csv_files,
    combine_df,
    extract_columns,
    get_column_list,
    list_available_columns,
    load_csv_to_df,
    save_df_to_csv,
)
from planet_power.retrieve import retrieve_exoplanet_data
from planet_power.visualization import save_scatter_png

# -- Pretty Printing
custom_theme = Theme(
    {
        "repr.str": "bold green",  # Change strings to bold green
        "repr.number": "italic blue",  # Change numbers to italic cyan
        "repr.boolean": "underline orange1",
        "repr.none": "bright_magenta",
    }
)
console = Console(theme=custom_theme, stderr=True)


# ── Analysis constants ─────────────────────────────────────────────────────────
# Outer loop: 10^N to 10^(N+M), with M hard-coded to 1 for now.
_ANALYZE_N_MIN: int = 21
_ANALYZE_N_MAX: int = 28
_ANALYZE_M: int = 1  # window width in decades (future: user-supplied)

# Inner loop multipliers: 1.0, 1.5, 2.0, …, 9.5
_ANALYZE_MULTIPLIERS: List[float] = [x / 10 for x in range(10, 100)]  # 1.0,... 9.9

# Parallelism cap (future: user-supplied)
_MAX_WORKERS: int = 8

# Restart each worker after this many slices to flush JAX's XLA compilation
# cache and device-buffer pool.  Lower = more frequent restarts (more overhead
# from re-importing JAX + deserialising the DataFrame) but tighter memory
# ceiling.  At 20 tasks/worker the restart overhead is ~1-2 s per worker.
_TASKS_PER_WORKER: int = 20

# CSV columns written to output
_OUTPUT_FIELDS: List[str] = [
    "slice_lower_limit",
    "slice_upper_limit",
    "n",
    "a",
    "b",
    "b_std",
    "b_std/abs(b)",
    "abs(b)/b_std",
]


def _validate_tag(tag: str) -> str:
    if tag and not re.match(r"^[a-zA-Z0-9_:-]+$", tag):
        raise argparse.ArgumentTypeError(
            f"Invalid tag '{tag}' - only alphanumeric, underscore, hyphen, colon allowed"
        )
    return tag


def _validate_column_family(column_family: str) -> str:
    cols: list[str] = get_column_list([f"~{column_family}.*"])
    if (
        f"{column_family}_err1" in cols
        and f"{column_family}_err2" in cols
        and f"{column_family}_weight" in cols
    ):
        return column_family
    else:
        raise argparse.ArgumentTypeError(
            f"Invalid column family '{column_family}', no *_err1, *err2, or *_weight accessory columns found"
        )


def _validate_file(file_name: str) -> Path:
    file_path = Path(file_name).resolve(strict=False)
    return file_path


# ── Worker initialiser (runs once per spawned process) ─────────────────────────

_worker_df: pd.DataFrame | None = None


def _worker_init(df_bytes: bytes) -> None:
    """Deserialise the shared DataFrame once per worker process.

    Using a module-level global avoids pickling the (potentially large)
    DataFrame on every Pool.apply_async() call.
    """
    jax.config.update("jax_enable_x64", True)
    global _worker_df
    _worker_df = pd.read_parquet(io.BytesIO(df_bytes))


# ── Worker task ────────────────────────────────────────────────────────────────


def _worker_task(lower: float, upper: float) -> Dict[str, float]:
    """Run one slice on the pre-loaded worker DataFrame."""
    import gc

    assert _worker_df is not None, "Worker DataFrame was not initialised"
    result = run_numpyro_slice_weighted(_worker_df, lower, upper)
    # Clear JAX's JIT compilation cache (grows with each unique slice size N)
    # and run Python GC to release any lingering JAX device buffers.
    jax.clear_caches()
    gc.collect()
    return result


def _worker_task_star(args: Tuple[float, float]) -> Dict[str, float]:
    """Unpacking shim so pool.imap can call _worker_task with a single arg."""
    return _worker_task(*args)


# ── cli_analyze ────────────────────────────────────────────────────────────────


def cli_analyze(
    in_files: list[Path],
    out_files: list[Path],
    dex_width: float = 1.0,
    x_col_fam: str | None = None,  # reserved for future generalisation
    y_col_fam: str | None = None,  # reserved for future generalisation
) -> None:
    """
    Run a sliding-window Bayesian power-law regression across mass slices.

    Outer loop  : n ∈ {23, 24, …, 29}  →  window [mult × 10^n, mult × 10^(n+M)]
    Inner loop  : mult ∈ {1.0, 1.5, 2.0, …, 9.5}
    Total slices: 7 × 18 = 126

    Each slice calls run_numpyro_slice_weighted() in a spawned worker process
    (up to _MAX_WORKERS in parallel) so JAX/XLA is isolated from the main
    process and the GIL is never a bottleneck.

    Output CSV columns:
        slice_lower_limit, slice_upper_limit, a, b, b_std,
        b_std/abs(b), abs(b)/b_std

    limit/a columns use scientific notation; b/b_std columns use plain decimal.
    Progress lines go to stderr so stdout remains clean and pipeable.
    """
    # ── Validate input ─────────────────────────────────────────────────────
    if not in_files:
        console.print("Error: -a/--analyze requires -I <input_csv>.")
        return

    input_path = in_files[0]
    if not input_path.exists():
        console.print(f"Error: input file '{input_path}' not found.")
        return

    required_cols = [
        "ppld_mass_kg",
        "ppld_mass_kg_err1",
        "ppld_mass_kg_err2",
        "ppld_mass_kg_weight",
        "ppld_radius_m",
        "ppld_radius_m_err1",
        "ppld_radius_m_err2",
        "ppld_radius_m_weight",
    ]
    df = load_csv_to_df(str(input_path), required_cols=required_cols)
    if df is None:
        console.print(
            f"Error: could not load '{input_path}' or required columns missing.",
        )
        return

    console.print(f"Loaded {len(df):,} rows from '{os.path.relpath(input_path)}'.")

    # ── Build the full slice list ──────────────────────────────────────────
    slices: List[Tuple[float, float]] = []
    for n in range(_ANALYZE_N_MIN, _ANALYZE_N_MAX + 1):
        for mult in _ANALYZE_MULTIPLIERS:
            # lower = mult * 10**n
            lower = 1e-30
            upper = mult * 10 ** (n + dex_width)
            slices.append((lower, upper))

    total = len(slices)
    console.print(
        f"Running {total} slices (n={_ANALYZE_N_MIN}..{_ANALYZE_N_MAX}, "
        f"mult=1.0..9.5, M={dex_width}) "
        f"with up to {_MAX_WORKERS} workers …",
    )

    # ── Serialise DataFrame once for the worker pool ───────────────────────

    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    df_bytes = buf.getvalue()

    # ── Determine output destination ───────────────────────────────────────
    # out_files[0] → CSV file; absent → stdout
    out_path: Path | None = out_files[0] if out_files else None
    out_fh = (
        open(out_path, "w", newline="", encoding="utf-8") if out_path else sys.stdout
    )

    # ── Run pool and stream results ────────────────────────────────────────
    writer = csv.DictWriter(out_fh, fieldnames=_OUTPUT_FIELDS)
    writer.writeheader()

    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["JAX_LOG_COMPILES"] = "0"  # suppresses some XLA noise
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # suppresses the autotuner errors
    os.environ["JAX_PLATFORMS"] = "cpu"  # prevent 4 workers fighting over GPU RAM
    # Switch JAX from the BFC pre-allocator (grabs memory and never returns it
    # to the OS) to the platform allocator (frees memory when arrays are deleted).
    # Must be set before JAX initialises in the worker — env vars are inherited
    # by spawned child processes, so setting it here before Pool() is sufficient.
    os.environ["XLA_PYTHON_CLIENT_ALLOCATOR"] = "platform"

    try:
        ctx = multiprocessing.get_context("spawn")
        completed = 0

        with ctx.Pool(
            processes=_MAX_WORKERS,
            initializer=_worker_init,
            initargs=(df_bytes,),
            # Restart each worker after _TASKS_PER_WORKER slices.
            # This clears any JAX/XLA state that clear_caches() misses and
            # gives a hard upper bound on per-worker memory growth.
            maxtasksperchild=_TASKS_PER_WORKER,
        ) as pool:
            # imap submits tasks lazily (one at a time as workers become free)
            # rather than queuing all N slices up front.  chunksize=1 ensures
            # no extra tasks are sent to a worker until it signals it is ready.
            for (lower, upper), result in zip(
                slices, pool.imap(_worker_task_star, slices, chunksize=1)
            ):
                completed += 1

                n = result.get("n", np.nan)
                b = result.get("b", np.nan)
                b_std = result.get("b_std", np.nan)

                # Derived ratios — guard against division by zero / nan
                if np.isnan(b) or b == 0 or np.isnan(b_std) or b_std == 0:
                    rel_err = np.nan
                    snr = np.nan
                else:
                    rel_err = b_std / abs(b)
                    snr = abs(b) / b_std

                row = {
                    "slice_lower_limit": f"{lower:.3e}",
                    "slice_upper_limit": f"{upper:.3e}",
                    "n": result.get("n", 0),
                    "a": f"{result.get('a', np.nan):.12f}",
                    "b": f"{b:.12f}" if not np.isnan(b) else "nan",
                    "b_std": f"{b_std:.12f}" if not np.isnan(b_std) else "nan",
                    "b_std/abs(b)": (
                        f"{rel_err:.12f}" if not np.isnan(rel_err) else "nan"
                    ),
                    "abs(b)/b_std": f"{snr:.12f}" if not np.isnan(snr) else "nan",
                }
                writer.writerow(row)

                # Flush so the file / stdout updates are visible in real time
                out_fh.flush()

                console.print(
                    f"[{completed:>3}/{total}] data points: {n}; "
                    f"{lower:.3e} – {upper:.3e} "
                    f"b={b:.9f}, b_std={b_std:.12f}, bre={rel_err:.12f}  snr={snr:.12f}",
                )

    finally:
        if out_path is not None:
            out_fh.close()
            console.print(f"\nResults written to '{out_path}'.")
        else:
            console.print("\nDone.")


# ── Existing CLI functions (unchanged) ────────────────────────────────────────


def cli_calculate(
    df_raw: pd.DataFrame | None,
    raw_data_file: str,
    calculated_data_file: str,
    data_table: str = "ps",
) -> pd.DataFrame | None:
    df_raw_loaded = None
    if df_raw is None:
        df_raw_loaded = load_csv_to_df(csv_file=raw_data_file, encoding="utf-8")
    else:
        df_raw_loaded = df_raw
    if df_raw_loaded is not None:
        df_extras = calculate_extras(df_raw_loaded, data_table=data_table)
        if save_df_to_csv(df_extras, calculated_data_file):
            console.print(
                f"Calculated extra data saved to '{os.path.relpath(calculated_data_file)}'."
            )
            return df_extras
        else:
            console.print(
                f"Error! Could not save calculated extra data to '{os.path.relpath(calculated_data_file)}'."
            )
            return None
    else:
        console.print(f"Unable to load file '{os.path.relpath(raw_data_file)}'.")
        return None


def cli_extract(
    in_paths: list[Path],
    out_files: list[Path],
    columns_list: list[str] = [],
    filter_rules: list[tuple[str, str]] = [],
    tag: str = "",
) -> pd.DataFrame | None:  # sourcery skip: default-mutable-arg

    if not len(in_paths):
        console.print("No input CSV data file speicifed.")
        return

    for in_path in in_paths:
        if not in_path.exists():
            console.print(f"File '{os.path.relpath(str(in_path))}' does not exist")
            return

    in_files = [str(p) for p in in_paths]

    if not columns_list:
        console.print("No columns to extract were given.")
        return None

    # df_list: list[pd.DataFrame] = []

    # for in_file in in_files:
    #     df_out = load_csv_to_df(in_file)
    #     if df_out is not None:
    #         df_list.append(df_out.set_index("pl_name"))

    # df_together: pd.DataFrame = reduce(
    #     lambda left, right: left.combine_first(right), df_list
    # )

    # df_combined = df_together.reset_index() if df_together.index.name else df_together

    df_combined = combine_csv_files("pl_name", [], *in_files)

    console.print(f"Combined dataset has {len(df_combined)} records.")
    df_filtered = apply_filter_rules(df_combined, filter_rules)
    console.print(f"Filtered dataset has {len(df_filtered)} records.")
    df_extracted = extract_columns(columns_list, df_filtered)
    console.print(f"Extracted dataset has {len(df_extracted)} records.")

    #
    extract_file = os.path.join(
        DATA_DIR, EXTRACTED_DATA_FILE_TEMPLATE.replace("%T", f"{tag and '.' + tag}")
    )
    if save_df_to_csv(df_extracted, extract_file):
        console.print(f"Extracted data saved to {os.path.relpath(extract_file)}")
    return df_extracted


def cli_image(
    in_files: list[Path],
    out_files: list[Path],
    reg_min: float | None,
    reg_max: float | None,
    df_extracted: pd.DataFrame | None,
    x_col_fam: str | None,
    y_col_fam: str | None,
):
    if not x_col_fam:
        console.print("You must set an X-axis column family with --x-column-family/-x")
        return

    if not y_col_fam:
        console.print("You must set an Y-axis column family with --y-column-family/-y")
        return

    if not len(in_files):
        console.print("No input CSV data file speicifed.")
        return

    if not in_files[0].exists():
        console.print(f"Input CSV file '{str(in_files[0])}' not found.")
        return

    input_csv = str(in_files[0])

    if not len(out_files):
        output_png = f"{in_files[0].parent, in_files[0].stem}.png"
    else:
        output_png = str(out_files[0])

    x_cols: list[str] = get_column_list([f"~{x_col_fam}.*"])
    y_cols: list[str] = get_column_list([f"~{y_col_fam}.*"])
    all_cols: list[str] = x_cols + y_cols

    df_pull = df_extracted
    if df_pull is None:
        df_pull = load_csv_to_df(input_csv, required_cols=all_cols)

    if df_pull is None:
        console.print(f"Unable to read from file '{input_csv}'.")
        return

    console.print(
        f"Starting bayesian regression for masses {reg_min} to {reg_max}...", end=""
    )
    trend = None

    if reg_max is not None and reg_min is not None:
        trend: Optional[Dict[str, float]] = run_bayesian_slice_weighted(
            df_pull,
            reg_min,
            reg_max,
        )
    elif reg_max is not None:
        trend: Optional[Dict[str, float]] = run_bayesian_slice_weighted(
            df_pull,
            1e-30,
            reg_max,
        )
    elif reg_min is not None:
        trend: Optional[Dict[str, float]] = run_bayesian_slice_weighted(
            df_pull,
            reg_min,
            1e30,
        )

    console.print("... done.")

    save_scatter_png(
        df=df_pull,
        output_path=output_png,
        x_col=f"{x_col_fam}",
        x_err_plus_col=f"{x_col_fam}_err1",
        x_err_minus_col=f"{x_col_fam}_err2",
        x_weight_col=f"{x_col_fam}_weight",
        y_col=f"{y_col_fam}",
        y_err_plus_col=f"{y_col_fam}_err1",
        y_err_minus_col=f"{y_col_fam}_err2",
        y_weight_col=f"{y_col_fam}_weight",
        fit_params=trend,
    )
    return


# ── main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """Main entry point for the CLI."""
    console.print(
        f"planet-power v{version('planet-power-law-distribution')} - Investigating classification of exoplanets"
    )
    console.print()
    parser = argparse.ArgumentParser(
        description="Fetch exoplanet data from NASA Exoplanet Archive and compute surface gravity."
    )
    parser.add_argument(
        "-a",
        "--analyze",
        action="store_true",
        help="Run sliding-window Bayesian power-law regression across mass slices",
    )
    parser.add_argument(
        "-c",
        "--calculate",
        action="store_true",
        help="Create extra CSV file with calculated values not in the NASA Exoplanet Archive data",
    )
    parser.add_argument(
        "-C",
        "--column",
        nargs="+",
        action="append",
        default=[],
        metavar="COLUMN|REGEX",
        help="Exact name of a column ore a regular expression to match multiple. Can be used multiple times.",
    )
    parser.add_argument(
        "-d",
        "--dex-width",
        type=float,
        default=None,
        help="Mass slice width for --analyze",
    )
    parser.add_argument(
        "-e",
        "--extract",
        action="store_true",
        help="Join data files and extract specific columns to a new data file",
    )
    parser.add_argument(
        "-f",
        "--filter",
        nargs="+",
        action="append",
        default=[],
        metavar="COLUMN:REGEX",
        help="Filter rows where COLUMN matches REGEX. Can be used multiple times.",
    )
    parser.add_argument(
        "--help-columns",
        action="store_true",
        help="List all the available columns",
    )
    parser.add_argument(
        "-i",
        "--image",
        action="store_true",
        help="Creates a scatter plot from a CSV data file",
    )
    parser.add_argument(
        "-I",
        "--input-file",
        action="append",
        default=[],
        type=_validate_file,
        metavar="CSV_IN",
        help="CSV file to read input data from",
    )
    parser.add_argument(
        "-m",
        "--regression-minimum",
        type=float,
        default=None,
        help="Minimum mass data value for scatter plot regression testing",
    )
    parser.add_argument(
        "-M",
        "--regression-maximum",
        type=float,
        default=None,
        help="Maximum mass data value for scatter plot regression testing",
    )
    parser.add_argument(
        "-O",
        "--output-file",
        action="append",
        default=[],
        type=_validate_file,
        metavar="CSV_OUT",
        help="CSV file to write output data to (omit to print to stdout)",
    )
    parser.add_argument(
        "-p",
        "--pscomppars",
        action="store_true",
        help="Use the 'pscomppars' table from NASA Exoplanet Archive instead of 'ps'",
    )
    parser.add_argument(
        "-r",
        "--retrieve",
        action="store_true",
        help="Retrieve data from NASA Exoplanet Archive",
    )
    parser.add_argument(
        "-R",
        "--refresh",
        action="store_true",
        help="Force refresh of raw data from NASA Exoplanet Archive",
    )
    parser.add_argument(
        "-t",
        "--tag",
        type=_validate_tag,
        default="",
        metavar="TAG",
        help="Tag to append to split output filenames (alphanumeric, underscore, hyphen, colon)",
    )
    parser.add_argument(
        "-x",
        "--x-col-set",
        type=_validate_column_family,
        default=None,
        metavar="COL_SET",
        help="Select a group of columns to use as the X-axis data in a scatter plot",
    )
    parser.add_argument(
        "-y",
        "--y-col-set",
        type=_validate_column_family,
        default=None,
        metavar="COL_SET",
        help="Select a group of columns to use as the Y-axis data in a scatter plot",
    )

    args = parser.parse_args()

    df_raw = None
    df_extras = None
    df_extracted = None

    if args.help_columns:
        console.print()
        list_available_columns()
        console.print()
        return

    # table to use
    data_table = "pscomppars" if args.pscomppars else "ps"
    raw_data_file = os.path.join(
        DATA_DIR, RAW_DATA_FILE_TEMPLATE.replace("%t", data_table)
    )
    calculated_data_file = os.path.join(
        DATA_DIR, CALCULATED_DATA_FILE_TEMPLATE.replace("%t", data_table)
    )
    extracted_file = os.path.join(
        DATA_DIR,
        EXTRACTED_DATA_FILE_TEMPLATE.replace("%T", f"{args.tag and '.' + args.tag}"),
    )
    # get the columns
    columns_list = get_column_list(args.column)

    # get the filter rules
    filter_rules: list[tuple[str, str]] = []
    flat_args = [item for sublist in args.filter for item in sublist]
    for arg in flat_args:
        if ":" not in arg:
            console.print(f'String "{arg}" is not a valid filter string.')
            continue
        col, pattern = arg.split(":", 1)
        filter_rules.append((col, pattern))

    if not any([args.analyze, args.retrieve, args.extract, args.calculate, args.image]):
        parser.print_help()
        return

    if args.retrieve:
        df_raw = retrieve_exoplanet_data(
            columns=columns_list,
            force_refresh=args.refresh,
            pscomppars=args.pscomppars,
        )

    if args.calculate:
        df_extras = cli_calculate(
            df_raw, raw_data_file, calculated_data_file, data_table
        )

    if args.extract:
        cli_extract(
            args.input_file or [],
            args.output_file or [],
            columns_list,
            filter_rules,
            args.tag,
        )

    if args.image:
        cli_image(
            args.input_file or [],
            args.output_file or [],
            args.regression_minimum,
            args.regression_maximum,
            df_extracted,
            args.x_col_set,
            args.y_col_set,
        )

    if args.analyze:
        cli_analyze(
            in_files=args.input_file or [],
            out_files=args.output_file or [],
            dex_width=args.dex_width,
            x_col_fam=args.x_col_set,
            y_col_fam=args.y_col_set,
        )


if __name__ == "__main__":
    main()
