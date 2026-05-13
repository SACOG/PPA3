"""
build_ppa_npmrds.py

Build the PPA NPMRDS feature class from RITIS CSV exports.

Replaces the original notebook (build_ppa_npmrds.ipynb) and the separate
PPA3_NPMRDS_metrics_test.sql file. All logic is self-contained here:

  - Congestion metrics computed via DuckDB on RITIS CSVs directly
    (no SQL Server, no separate .sql file)
  - Geometry attached from NHS shapefile where available
  - Old true-shape SHP reused where TMC start/end points are unchanged
  - Stick geometries built as fallback for the rest
  - Both reuse-tolerance and stick-length-tolerance exposed as parameters

Input data (provide via CONFIG block below):
  - RITIS travel-time CSV(s): one row per TMC per measurement_tstamp,
    with columns tmc_code, measurement_tstamp, speed, travel_time_seconds
  - RITIS TMC_Identification.csv: one row per TMC with road, route_numb,
    direction, f_system, nhs, miles, start/end lat-longs
  - NHS true-shape shapefile (or feature class)
  - Old true-shape feature class for geometry reuse

Output:
  - ESRI feature class with congestion metrics + geometry + tru_shp_yr flag

Author: Terrell, originally based on Darren Conly's notebook
"""
from __future__ import annotations

# ---------------------------------------------------------------------
# PROJ database setup — must come before any geo imports
# ---------------------------------------------------------------------
import os
os.environ["PROJ_LIB"] = r"C:\Users\tenoru\AppData\Local\ESRI\conda\envs\arcpro_env\Library\share\proj"
os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"]  # newer pyproj uses this name

# Belt-and-suspenders: also set programmatically in case env vars are too late
import pyproj
pyproj.datadir.set_data_dir(os.environ["PROJ_LIB"])
print(f"pyproj data dir: {pyproj.datadir.get_data_dir()}")
from pyproj import CRS
_ = CRS.from_epsg(4326)  # fail fast if PROJ db is broken
print("EPSG:4326 resolves OK")

import datetime as dt
import logging
import sys
from pathlib import Path
from time import perf_counter

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString


# Optional arcpy imports — only needed for feature-class export and CRS lookup.
# Code is structured so that upstream stages run without arcpy if needed.
try:
    import arcpy
    from arcgis.features import GeoAccessor, GeoSeriesAccessor  # noqa: F401
    HAS_ARCPY = True
except ImportError:
    HAS_ARCPY = False


# =====================================================================
# CONFIG — edit for each annual update
# =====================================================================
congestion_update_path=Path(r"I:\Projects\Josh\PPA\Layer_update\Congestion")
local_congestion_path= Path(r"C:\Users\tenoru\Downloads\Layer_update\Congestion")  # for testing on local machine
CONFIG = {
    # --- Input CSVs from RITIS Massive Data Downloader ---
    # Path to the travel-time CSV(s). Can be a single file or a glob pattern
    # for multiple files (e.g. monthly exports). DuckDB handles both.
    # Expected columns: tmc_code, measurement_tstamp, speed, travel_time_seconds
    "tt_csv_path": local_congestion_path /"npmrds_2025_alltmc_paxtruck_comb.csv",

    # Path to TMC_Identification.csv from RITIS download
    # Expected columns include: tmc, road, route_numb, direction, f_system,
    # nhs, miles, start_latitude, start_longitude, end_latitude, end_longitude
    "tmc_id_csv_path": local_congestion_path / "TMC_Identification.csv",

    # --- Geometry inputs ---
    # NHS true-shape shapefile/feature class for the new vintage
    "nhs_shp": local_congestion_path  / "NPMRDS_2025_NHS_SACOG.shp",
    # List of older true-shape sources to try, in priority order.
    # First entry is tried first; geometries from later entries fill gaps.
    # Each entry: (path, vintage_year, dissolve_field)
    "old_shp_sources": [
        (r"I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\NPMRDS_2023ppadata_final", 2023, "tmc"),
        (r"I:\Projects\Darren\PPA3_GIS\PPA3.0_archive.gdb\INRIX_SHP_2020_2021_SACOG", 2021, "Tmc"),
    ],

    # --- Output ---
    # Sample output location for now.
    "out_gdb": local_congestion_path  / "PPA3_GIS.gdb",
    "data_year": 2025,

    # Optional: cache the metrics DataFrame to CSV so you don't have to
    # recompute on subsequent runs. Set to None to disable.
    "metrics_cache_csv": local_congestion_path  / "cache" / "npmrds_metrics_2025.csv",

    # If True, load metrics from `metrics_cache_csv` if it exists, skipping
    # the ~5min DuckDB stage. Useful when iterating on Stages 2-4 and the
    # underlying RITIS CSVs haven't changed. Set False to force recompute.
    "use_metrics_cache": True,

    # --- Tolerances (both previously hardcoded — now exposed) ---
    # Max distance in feet between old and new TMC start/end points to
    # accept reusing the old geometry. Darren had this hardcoded to 1.0.
    # Worth tuning empirically based on observed coordinate drift between
    # vintages.
    "reuse_endpoint_tolerance_ft": 1.0,

    # Max acceptable percent difference between stick-line length and the
    # spec'd `miles` value for a TMC to be considered "straight enough" that
    # a stick line is good enough (no manual correction needed).
    # Darren's default was 0.0017 (= 0.17%).
    "stick_length_tolerance_pct": 0.0017,

    # --- CRS ---
    # SACOG region projected CRS, units of feet. Used for all distance math.
    "sacog_crs_epsg": 2226,

    # --- Time period definitions for congestion metrics ---
    # All times are 24-hour. Window is [start, end), i.e. start inclusive,
    # end exclusive (matches Darren's SQL).
    "am_peak":   (6, 10),
    "midday":    (10, 16),
    "pm_peak":   (16, 20),
    "weekend":   (6, 20),    # weekend metrics use this window across Sat/Sun

    # Free-flow window — overnight, wraps midnight (>= start OR < end)
    "ff_start_hr": 20,
    "ff_end_hr":   6,

    # Congestion percentile (the "bad" travel-time percentile used for LOTTR)
    "pctl_congested": 0.80,

    # Min number of epochs required for an hour to count in per-hour metrics
    "min_epochs_per_hour": 100,
}


# =====================================================================
# Logging
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("build_ppa_npmrds")

def find_tmc_field(gdf):
    """Find the TMC ID column regardless of casing convention."""
    candidates = ["Tmc", "TMC", "tmc", "tmc_code", "Tmc_code", "TMC_CODE"]
    for c in candidates:
        if c in gdf.columns:
            return c
    raise ValueError(
        f"No TMC field found in shapefile. Columns: {gdf.columns.tolist()}"
    )


# =====================================================================
# Stage 1 — congestion metrics via DuckDB
# =====================================================================

def compute_metrics_duckdb(tt_csv_path: str, tmc_id_csv_path: str,
                            cfg: dict) -> pd.DataFrame:
    """
    Run the PPA NPMRDS congestion-metrics SQL against the RITIS CSVs
    using DuckDB. Returns a pandas DataFrame with one row per TMC.

    Reproduces the logic of PPA3_NPMRDS_metrics_test.sql:
      - 50th/80th percentile travel times for AM peak, midday, PM peak, weekend
      - LOTTRs (80th/50th) for each period
      - Free-flow speeds (85th pctl for fwy; 70th and 60th pctl for arterials)
        computed from overnight (8pm-6am) window
      - Harmonic mean speed of worst-4 weekday hours per TMC
      - Slowest hour of day per TMC
      - Epoch counts per period (data quality)
    """
    log.info("Computing congestion metrics with DuckDB")
    log.info(f"  travel-time CSV: {tt_csv_path}")
    log.info(f"  TMC ID CSV:      {tmc_id_csv_path}")

    t0 = perf_counter()
    con = duckdb.connect()

    # Register the CSVs as virtual tables. read_csv_auto streams from disk —
    # no need to load into memory. Pattern globs (e.g. "...*.csv") work too.
    con.execute(f"""
        CREATE VIEW tt AS
        SELECT * FROM read_csv_auto('{tt_csv_path}', header=True);
    """)
    con.execute(f"""
        CREATE VIEW tmc AS
        SELECT * FROM read_csv_auto('{tmc_id_csv_path}', header=True);
    """)

    # Sanity check on travel-time table columns
    tt_cols = {row[0].lower() for row in con.execute("DESCRIBE tt").fetchall()}
    required_tt = {"tmc_code", "measurement_tstamp", "speed", "travel_time_seconds"}
    missing = required_tt - tt_cols
    if missing:
        raise ValueError(f"Travel-time CSV missing required columns: {missing}")

    # Time-period bounds and config values, threaded into SQL as parameters
    p = {
        "am_s": cfg["am_peak"][0],   "am_e": cfg["am_peak"][1],
        "md_s": cfg["midday"][0],    "md_e": cfg["midday"][1],
        "pm_s": cfg["pm_peak"][0],   "pm_e": cfg["pm_peak"][1],
        "we_s": cfg["weekend"][0],   "we_e": cfg["weekend"][1],
        "ff_s": cfg["ff_start_hr"],  "ff_e": cfg["ff_end_hr"],
        "pctl": cfg["pctl_congested"],
        "min_epochs": cfg["min_epochs_per_hour"],
    }

    # The big SQL — directly mirrors the structure of the original SQL file.
    # NOTE: DuckDB uses `quantile_cont(col, p)` rather than SQL Server's
    # `PERCENTILE_CONT(p) WITHIN GROUP (ORDER BY col)` — same result, different
    # syntax. `dayofweek(ts)` in DuckDB returns 0=Sunday..6=Saturday;
    # weekdays are 1-5.
    sql = f"""
    -- Travel-time percentiles per TMC per period
    WITH tt_ampk AS (
        SELECT DISTINCT
            tmc_code,
            quantile_cont(travel_time_seconds, {p['pctl']}) OVER (PARTITION BY tmc_code) AS tt_p80_ampk,
            quantile_cont(travel_time_seconds, 0.5) OVER (PARTITION BY tmc_code) AS tt_p50_ampk
        FROM tt
        WHERE dayofweek(measurement_tstamp) BETWEEN 1 AND 5
          AND extract(hour FROM measurement_tstamp) >= {p['am_s']}
          AND extract(hour FROM measurement_tstamp) <  {p['am_e']}
    ),
    tt_midday AS (
        SELECT DISTINCT
            tmc_code,
            quantile_cont(travel_time_seconds, {p['pctl']}) OVER (PARTITION BY tmc_code) AS tt_p80_midday,
            quantile_cont(travel_time_seconds, 0.5) OVER (PARTITION BY tmc_code) AS tt_p50_midday
        FROM tt
        WHERE dayofweek(measurement_tstamp) BETWEEN 1 AND 5
          AND extract(hour FROM measurement_tstamp) >= {p['md_s']}
          AND extract(hour FROM measurement_tstamp) <  {p['md_e']}
    ),
    tt_pmpk AS (
        SELECT DISTINCT
            tmc_code,
            quantile_cont(travel_time_seconds, {p['pctl']}) OVER (PARTITION BY tmc_code) AS tt_p80_pmpk,
            quantile_cont(travel_time_seconds, 0.5) OVER (PARTITION BY tmc_code) AS tt_p50_pmpk
        FROM tt
        WHERE dayofweek(measurement_tstamp) BETWEEN 1 AND 5
          AND extract(hour FROM measurement_tstamp) >= {p['pm_s']}
          AND extract(hour FROM measurement_tstamp) <  {p['pm_e']}
    ),
    tt_weekend AS (
        -- Original SQL uses weekday filter here too — preserved for fidelity
        SELECT DISTINCT
            tmc_code,
            quantile_cont(travel_time_seconds, {p['pctl']}) OVER (PARTITION BY tmc_code) AS tt_p80_weekend,
            quantile_cont(travel_time_seconds, 0.5) OVER (PARTITION BY tmc_code) AS tt_p50_weekend
        FROM tt
        WHERE dayofweek(measurement_tstamp) BETWEEN 1 AND 5
          AND extract(hour FROM measurement_tstamp) >= {p['we_s']}
          AND extract(hour FROM measurement_tstamp) <  {p['we_e']}
    ),
    -- Epoch counts per period (data quality)
    epochs_per_prd AS (
        SELECT
            tmc_code,
            SUM(CASE WHEN dayofweek(measurement_tstamp) BETWEEN 1 AND 5
                AND extract(hour FROM measurement_tstamp) >= {p['am_s']}
                AND extract(hour FROM measurement_tstamp) <  {p['am_e']}
                THEN 1 ELSE 0 END) AS epochs_ampk,
            SUM(CASE WHEN dayofweek(measurement_tstamp) BETWEEN 1 AND 5
                AND extract(hour FROM measurement_tstamp) >= {p['md_s']}
                AND extract(hour FROM measurement_tstamp) <  {p['md_e']}
                THEN 1 ELSE 0 END) AS epochs_midday,
            SUM(CASE WHEN dayofweek(measurement_tstamp) BETWEEN 1 AND 5
                AND extract(hour FROM measurement_tstamp) >= {p['pm_s']}
                AND extract(hour FROM measurement_tstamp) <  {p['pm_e']}
                THEN 1 ELSE 0 END) AS epochs_pmpk,
            SUM(CASE WHEN dayofweek(measurement_tstamp) IN (0, 6)
                AND extract(hour FROM measurement_tstamp) >= {p['we_s']}
                AND extract(hour FROM measurement_tstamp) <  {p['we_e']}
                THEN 1 ELSE 0 END) AS epochs_weekend
        FROM tt
        GROUP BY tmc_code
    ),
    -- Free-flow speeds: 85th pctl for freeways (f_system 1,2),
    -- 70th and 60th pctl alternates for arterials.
    -- Free-flow window wraps midnight: hour >= ff_s OR hour < ff_e
    ff_spd AS (
        SELECT DISTINCT
            tmc.tmc,
            tmc.f_system,
            CASE WHEN tmc.f_system IN (1, 2)
                THEN quantile_cont(tt.speed, 0.85) OVER (PARTITION BY tt.tmc_code)
                ELSE quantile_cont(tt.speed, 0.70) OVER (PARTITION BY tt.tmc_code)
            END AS ff_speed_art70thp,
            CASE WHEN tmc.f_system IN (1, 2)
                THEN quantile_cont(tt.speed, 0.85) OVER (PARTITION BY tt.tmc_code)
                ELSE quantile_cont(tt.speed, 0.60) OVER (PARTITION BY tt.tmc_code)
            END AS ff_speed_art60thp
        FROM tmc
        LEFT JOIN tt ON tmc.tmc = tt.tmc_code
        WHERE extract(hour FROM tt.measurement_tstamp) >= {p['ff_s']}
           OR extract(hour FROM tt.measurement_tstamp) <  {p['ff_e']}
    ),
    -- Count of overnight epochs (data quality for FF speed)
    epochs_night AS (
        SELECT tmc_code, COUNT(*) AS epochs_night
        FROM tt
        WHERE extract(hour FROM measurement_tstamp) >= {p['ff_s']}
           OR extract(hour FROM measurement_tstamp) <  {p['ff_e']}
        GROUP BY tmc_code
    ),
    -- Per-hour weekday metrics (harmonic mean speed, congestion ratio, rank)
    -- Filter: only keep hours with at least min_epochs_per_hour observations
    avspd_x_hour AS (
        SELECT
            tt.tmc_code,
            extract(hour FROM tt.measurement_tstamp) AS hour_of_day,
            COUNT(*) AS total_epochs_hr,
            ff.ff_speed_art60thp,
            -- Harmonic mean: count / sum(1/speed). Required for averaging speeds.
            COUNT(*) / SUM(1.0 / tt.speed) AS havg_spd_weekdy,
            AVG(tt.travel_time_seconds) AS avg_tt_sec_weekdy,
            (COUNT(*) / SUM(1.0 / tt.speed)) / ff.ff_speed_art60thp
                AS cong_ratio_hr_weekdy,
            RANK() OVER (
                PARTITION BY tt.tmc_code
                ORDER BY (COUNT(*) / SUM(1.0 / tt.speed)) / ff.ff_speed_art60thp ASC
            ) AS hour_cong_rank
        FROM tt
        JOIN ff_spd ff ON tt.tmc_code = ff.tmc
        WHERE dayofweek(tt.measurement_tstamp) BETWEEN 1 AND 5
        GROUP BY tt.tmc_code, extract(hour FROM tt.measurement_tstamp),
                 ff.ff_speed_art60thp
        HAVING COUNT(tt.measurement_tstamp) >= {p['min_epochs']}
    ),
    -- Worst-4-hours: harmonic mean speed across the 4 most congested
    -- weekday hours per TMC
    worst4 AS (
        SELECT
            tt.tmc_code,
            COUNT(*) AS epochs_worst4hrs,
            ff.ff_speed_art60thp,
            COUNT(*) / SUM(1.0 / tt.speed) AS havg_spd_worst4hrs
        FROM tt
        JOIN ff_spd ff ON tt.tmc_code = ff.tmc
        JOIN avspd_x_hour avs
          ON tt.tmc_code = avs.tmc_code
         AND extract(hour FROM tt.measurement_tstamp) = avs.hour_of_day
        WHERE dayofweek(tt.measurement_tstamp) BETWEEN 1 AND 5
          AND avs.hour_cong_rank < 5
        GROUP BY tt.tmc_code, ff.ff_speed_art60thp
    ),
    -- Slowest hour: the single most congested weekday hour per TMC
    slowest_hr AS (
        SELECT DISTINCT
            tt.tmc_code,
            COUNT(tt.measurement_tstamp) AS epochs_slowest_hr,
            avs.hour_of_day AS slowest_hr,
            avs.havg_spd_weekdy AS slowest_hr_speed
        FROM tt
        JOIN avspd_x_hour avs
          ON tt.tmc_code = avs.tmc_code
         AND extract(hour FROM tt.measurement_tstamp) = avs.hour_of_day
        WHERE avs.hour_cong_rank = 1
          AND dayofweek(tt.measurement_tstamp) BETWEEN 1 AND 5
        GROUP BY tt.tmc_code, avs.hour_of_day, avs.havg_spd_weekdy
    )
    -- Final assembly with NULL → -1 sentinel substitution and dedup
    -- (some TMCs duplicate when there's a tie for slowest hour)
    SELECT * FROM (
        SELECT
            tmc.tmc,
            tmc.road,
            tmc.route_numb,
            tmc.direction AS direction_signd,
            tmc.f_system,
            tmc.nhs,
            tmc.miles,
            tmc.start_latitude,
            tmc.start_longitude,
            tmc.end_latitude,
            tmc.end_longitude,
            COALESCE(tt_ampk.tt_p80_ampk, -1.0) AS tt_p80_ampk,
            COALESCE(tt_ampk.tt_p50_ampk, -1.0) AS tt_p50_ampk,
            COALESCE(tt_midday.tt_p80_midday, -1.0) AS tt_p80_midday,
            COALESCE(tt_midday.tt_p50_midday, -1.0) AS tt_p50_midday,
            COALESCE(tt_pmpk.tt_p80_pmpk, -1.0) AS tt_p80_pmpk,
            COALESCE(tt_pmpk.tt_p50_pmpk, -1.0) AS tt_p50_pmpk,
            COALESCE(tt_weekend.tt_p80_weekend, -1.0) AS tt_p80_weekend,
            COALESCE(tt_weekend.tt_p50_weekend, -1.0) AS tt_p50_weekend,
            COALESCE(tt_ampk.tt_p80_ampk / NULLIF(tt_ampk.tt_p50_ampk, 0), -1.0) AS lottr_ampk,
            COALESCE(tt_midday.tt_p80_midday / NULLIF(tt_midday.tt_p50_midday, 0), -1.0) AS lottr_midday,
            COALESCE(tt_pmpk.tt_p80_pmpk / NULLIF(tt_pmpk.tt_p50_pmpk, 0), -1.0) AS lottr_pmpk,
            COALESCE(tt_weekend.tt_p80_weekend / NULLIF(tt_weekend.tt_p50_weekend, 0), -1.0) AS lottr_wknd,
            COALESCE(ff.ff_speed_art70thp, -1.0) AS ff_speed_art70thp,
            COALESCE(ff.ff_speed_art60thp, -1.0) AS ff_speed_art60thp,
            COALESCE(worst4.havg_spd_worst4hrs, -1.0) AS havg_spd_worst4hrs,
            -- Cap at 1.0 because overnight may not be the fastest period when
            -- data are sparse (see comment in original SQL)
            CASE
                WHEN worst4.havg_spd_worst4hrs / NULLIF(ff.ff_speed_art60thp, 0) IS NULL THEN -1.0
                WHEN worst4.havg_spd_worst4hrs / NULLIF(ff.ff_speed_art60thp, 0) > 1 THEN 1.0
                ELSE worst4.havg_spd_worst4hrs / NULLIF(ff.ff_speed_art60thp, 0)
            END AS congratio_worst4hrs,
            COALESCE(slowest_hr.slowest_hr, -1) AS slowest_hr,
            COALESCE(slowest_hr.slowest_hr_speed, -1.0) AS slowest_hr_speed,
            COALESCE(slowest_hr.slowest_hr_speed / NULLIF(ff.ff_speed_art60thp, 0), -1.0)
                AS congratio_worsthr,
            COALESCE(epochs_per_prd.epochs_ampk, -1) AS epochs_ampk,
            COALESCE(epochs_per_prd.epochs_midday, -1) AS epochs_midday,
            COALESCE(epochs_per_prd.epochs_pmpk, -1) AS epochs_pmpk,
            COALESCE(epochs_per_prd.epochs_weekend, -1) AS epochs_weekend,
            COALESCE(worst4.epochs_worst4hrs, -1) AS epochs_worst4hrs,
            COALESCE(slowest_hr.epochs_slowest_hr, -1) AS epochs_slowest_hr,
            COALESCE(epochs_night.epochs_night, -1) AS epochs_night,
            -- Tie-breaker: when a TMC has multiple hours with rank=1, keep
            -- the row with the slowest speed (matches original SQL behavior)
            ROW_NUMBER() OVER (
                PARTITION BY tmc.tmc
                ORDER BY slowest_hr.slowest_hr_speed
            ) AS tmc_appearance_n
        FROM tmc
        LEFT JOIN ff_spd ff       ON tmc.tmc = ff.tmc
        LEFT JOIN tt_ampk         ON tmc.tmc = tt_ampk.tmc_code
        LEFT JOIN tt_midday       ON tmc.tmc = tt_midday.tmc_code
        LEFT JOIN tt_pmpk         ON tmc.tmc = tt_pmpk.tmc_code
        LEFT JOIN tt_weekend      ON tmc.tmc = tt_weekend.tmc_code
        LEFT JOIN worst4          ON tmc.tmc = worst4.tmc_code
        LEFT JOIN slowest_hr      ON tmc.tmc = slowest_hr.tmc_code
        LEFT JOIN epochs_per_prd  ON tmc.tmc = epochs_per_prd.tmc_code
        LEFT JOIN epochs_night    ON tmc.tmc = epochs_night.tmc_code
    ) sub
    WHERE tmc_appearance_n = 1
    """

    df = con.execute(sql).fetchdf()
    con.close()

    elapsed = round((perf_counter() - t0) / 60, 2)
    log.info(f"  metrics computed in {elapsed} min — {len(df):,} TMCs")
    return df


# =====================================================================
# Stage 2 — attach NHS true-shape geometry
# =====================================================================

def load_geom_layer(path, fields, target_epsg):
    path = str(path)  # arcpy hates Path objects

    # Shapefiles: just use geopandas, skip arcpy entirely
    is_shp = path.lower().endswith(".shp")

    if is_shp or not HAS_ARCPY:
        gdf = gpd.read_file(path)
        if fields is not None:
            gdf = gdf[fields + ["geometry"]]
    else:
        # .gdb feature class — needs arcpy
        if fields is None:
            sedf = pd.DataFrame.spatial.from_featureclass(path)
        else:
            sedf = pd.DataFrame.spatial.from_featureclass(path, fields=fields)

        # arcgis SpatialReference: prefer latestWkid (modern EPSG) over wkid
        # (often legacy ESRI codes in 102xxx/103xxx range). EPSG codes don't
        # exceed ~33000, so anything >= 100000 is an ESRI authority code.
        sr = sedf.spatial.sr
        wkid = sr.get("wkid") if hasattr(sr, "get") else getattr(sr, "wkid", None)
        latest = sr.get("latestWkid") if hasattr(sr, "get") else getattr(sr, "latestWkid", None)

        crs = None
        if latest and latest < 100000:
            crs = f"EPSG:{latest}"
        elif wkid and wkid < 100000:
            crs = f"EPSG:{wkid}"
        elif wkid:
            crs = f"ESRI:{wkid}"  # fall back to ESRI authority

        gdf = gpd.GeoDataFrame(sedf, geometry=sedf.spatial.name, crs=crs)

    if gdf.crs is None or gdf.crs.to_epsg() != target_epsg:
        gdf = gdf.to_crs(f"EPSG:{target_epsg}")
    return gdf


def attach_nhs_geometry(metrics_df, nhs_path, cfg):
    log.info("Attaching NHS true-shape geometry")
    crs = cfg["sacog_crs_epsg"]

    # Load without specifying fields, then find the TMC column
    nhs_gdf = load_geom_layer(nhs_path, fields=None, target_epsg=crs)
    tmc_field = find_tmc_field(nhs_gdf)
    log.info(f"  using NHS TMC field: '{tmc_field}'")

    nhs_gdf = nhs_gdf[[tmc_field, "geometry"]].rename(columns={tmc_field: "tmc_nhs"})
    log.info(f"  loaded {len(nhs_gdf):,} NHS shapes")

    merged = metrics_df.merge(
        nhs_gdf, how="left", left_on="tmc", right_on="tmc_nhs",
    )
    merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=f"EPSG:{crs}")
    merged["tru_shp_yr"] = 0
    merged.loc[~merged["geometry"].isna(), "tru_shp_yr"] = cfg["data_year"]
    merged.drop(columns=["tmc_nhs"], inplace=True, errors="ignore")

    n_matched = (merged["tru_shp_yr"] == cfg["data_year"]).sum()
    log.info(f"  {n_matched:,} of {len(merged):,} TMCs matched NHS geometry")
    return merged


# =====================================================================
# Stage 3 — reuse old SHP geometry where TMC endpoints are unchanged
# =====================================================================

def reuse_old_geometry(in_gdf: gpd.GeoDataFrame, old_shp_path: str,
                       old_year: int, dissolve_field: str,
                       cfg: dict) -> gpd.GeoDataFrame:
    """
    For TMCs without true-shape geometry, attempt to reuse geometry from an
    older vintage if the TMC's start/end points haven't moved more than
    `reuse_endpoint_tolerance_ft` feet.

    Generalized version of Darren's `insert_links` function:
      - takes any old SHP path and vintage year
      - exposes the endpoint tolerance (was hardcoded to 1.0 ft)
      - exposes the stick-length tolerance (was the only existing param)
      - can be called multiple times in sequence with different old SHPs
        for layered fallback
    """
    log.info(f"Reusing geometry from {old_year} ({Path(old_shp_path).name})")
    crs = cfg["sacog_crs_epsg"]
    endpoint_tol = cfg["reuse_endpoint_tolerance_ft"]
    length_tol = cfg["stick_length_tolerance_pct"]
    data_year = cfg["data_year"]

    # Load old shapes, dissolve to handle multipart geometries
    old_gdf = load_geom_layer(old_shp_path, fields=[dissolve_field], target_epsg=crs)
    old_gdf = old_gdf.dissolve(by=dissolve_field).reset_index()

    # Dissolve can produce MultiLineStrings; .explode() guarantees single-part
    # geometries, then we keep the longest piece per TMC (downstream endpoint
    # check will reject any TMC where this heuristic chose the wrong piece).
    n_multi = (old_gdf.geometry.geom_type == "MultiLineString").sum()
    if n_multi:
        log.info(f"  exploding {n_multi} multi-part geometries")
        old_gdf = old_gdf.explode(index_parts=False).reset_index(drop=True)
        old_gdf["_len"] = old_gdf.geometry.length
        old_gdf = (old_gdf.sort_values("_len", ascending=False)
                          .drop_duplicates(subset=[dissolve_field], keep="first")
                          .drop(columns=["_len"])
                          .reset_index(drop=True))

    # Hard sanity check — anything other than LineString here means a bug
    bad = (old_gdf.geometry.geom_type != "LineString").sum()
    if bad:
        raise RuntimeError(
            f"After cleanup, {bad} geometries are not LineStrings — "
            f"types: {old_gdf.geometry.geom_type.value_counts().to_dict()}"
        )

    # Extract start/end points of old geometries.
    # Build a plain pd.DataFrame for the merge — renaming the active geometry
    # column on a GeoDataFrame via .rename() is unreliable (geopandas tracks
    # the geometry column name internally), so we sidestep it.
    geom_col = f"geometry_{old_year}"
    old_attrs = pd.DataFrame({
        dissolve_field: old_gdf[dissolve_field].values,
        geom_col: old_gdf.geometry.values,
        "startpt_old": old_gdf.geometry.apply(lambda g: g.coords[0]).values,
        "endpt_old": old_gdf.geometry.apply(lambda g: g.coords[-1]).values,
    })

    # Merge onto input
    merged = in_gdf.merge(
        old_attrs,
        how="left", left_on="tmc", right_on=dissolve_field,
        suffixes=("", f"_{old_year}"),
    )

    # Compute new TMC start/end points in projected CRS from the lat-longs
    new_start = gpd.points_from_xy(merged["start_longitude"], merged["start_latitude"],
                                    crs="EPSG:4326").to_crs(f"EPSG:{crs}")
    new_end = gpd.points_from_xy(merged["end_longitude"], merged["end_latitude"],
                                  crs="EPSG:4326").to_crs(f"EPSG:{crs}")

    # Stick distance for new vs. old (endpoint-to-endpoint)
    has_old = merged["startpt_old"].notna()

    def _euclid(p1, p2):
        return np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    new_stick_len = np.array([_euclid((s.x, s.y), (e.x, e.y))
                               for s, e in zip(new_start, new_end)])

    old_stick_len = np.full(len(merged), np.nan)
    for i in merged.index[has_old]:
        old_stick_len[i] = _euclid(merged.at[i, "startpt_old"], merged.at[i, "endpt_old"])

    abs_dist_dif = np.abs(new_stick_len - old_stick_len)

    # Eligibility: not already true-shape, has old geometry, endpoint diff < tolerance
    eligible = (
        (merged["tru_shp_yr"] == 0)
        & has_old
        & (abs_dist_dif < endpoint_tol)
    )
    n_reused = eligible.sum()
    log.info(f"  reused {n_reused:,} geometries from {old_year}")

    # Apply the substitution
    for idx in merged.index[eligible]:
        merged.at[idx, "geometry"] = merged.at[idx, f"geometry_{old_year}"]
    merged.loc[eligible, "tru_shp_yr"] = old_year

    # For TMCs still without geometry, build stick lines
    still_stick = merged["tru_shp_yr"] == 0
    for idx in merged.index[still_stick]:
        s, e = new_start[idx], new_end[idx]
        merged.at[idx, "geometry"] = LineString([(s.x, s.y), (e.x, e.y)])

    # Mark sticks where stick length is close enough to spec'd miles that
    # no manual correction is needed (= the "true" shape really is a line)
    pct_diff = np.where(
        still_stick & (merged["miles"] > 0),
        np.abs(merged["miles"] - merged.geometry.length / 5280) / merged["miles"],
        np.nan,
    )
    auto_resolved = still_stick & (pct_diff <= length_tol)
    merged.loc[auto_resolved, "tru_shp_yr"] = data_year
    log.info(f"  {auto_resolved.sum():,} sticks auto-resolved (length within {length_tol*100:.2f}% of spec)")

    # Clean up working columns. Only drop dissolve_field if it's distinct from
    # the main "tmc" join key — when they share a name, the merge collapses
    # them into one column, and dropping it would kill the next iteration.
    drop_cols = [f"geometry_{old_year}", "startpt_old", "endpt_old"]
    if dissolve_field != "tmc":
        drop_cols.append(dissolve_field)
    merged.drop(columns=[c for c in drop_cols if c in merged.columns], inplace=True)

    return merged


# =====================================================================
# Stage 4 — export to feature class
# =====================================================================

def export_feature_class(gdf: gpd.GeoDataFrame, out_gdb: str,
                          data_year: int) -> str:
    """Write the final GeoDataFrame to an ESRI feature class."""
    if not HAS_ARCPY:
        log.warning("arcpy not available — skipping feature-class export")
        log.warning("  (run on a machine with ArcGIS Pro to export)")
        return ""

    log.info("Exporting to feature class")
    sufx = dt.datetime.now().strftime("%Y%m%d_%H%M")
    outname = f"NPMRDS_{data_year}data_{sufx}"
    out_gdb = str(out_gdb)

    # Auto-create the output FGDB if it doesn't exist yet
    out_gdb_path = Path(out_gdb)
    if not out_gdb_path.exists():
        log.info(f"  output FGDB doesn't exist — creating {out_gdb_path}")
        out_gdb_path.parent.mkdir(parents=True, exist_ok=True)
        arcpy.management.CreateFileGDB(
            out_folder_path=str(out_gdb_path.parent),
            out_name=out_gdb_path.name,
        )

    out_path = str(out_gdb_path / outname)

    # Drop intermediate columns that shouldn't be in the published feature class
    drop_cols = ["tmc_appearance_n", "start_latitude", "start_longitude",
                 "end_latitude", "end_longitude"]
    keep = [c for c in gdf.columns if c not in drop_cols]

    sedf = pd.DataFrame.spatial.from_geodataframe(gdf[keep])
    result = sedf.spatial.to_featureclass(out_path, sanitize_columns=False)
    log.info(f"  written: {result}")
    return result


# =====================================================================
# Main
# =====================================================================

def main(cfg: dict = CONFIG) -> None:
    log.info("=" * 60)
    log.info(f"PPA NPMRDS build — data year {cfg['data_year']}")
    log.info("=" * 60)

    # Stage 1: metrics (load from cache if available and enabled)
    cache_path = Path(cfg["metrics_cache_csv"]) if cfg.get("metrics_cache_csv") else None
    if cfg.get("use_metrics_cache") and cache_path and cache_path.exists():
        log.info(f"Loading cached metrics from {cache_path}")
        metrics_df = pd.read_csv(cache_path)
        log.info(f"  loaded {len(metrics_df):,} TMCs from cache")
    else:
        metrics_df = compute_metrics_duckdb(
            cfg["tt_csv_path"], cfg["tmc_id_csv_path"], cfg
        )
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            metrics_df.to_csv(cache_path, index=False)
            log.info(f"  metrics cached to {cache_path}")

    # Stage 2: NHS geometry
    gdf = attach_nhs_geometry(metrics_df, cfg["nhs_shp"], cfg)

    # Stage 3: reuse old vintages, then build sticks for the rest
    for old_path, old_year, dissolve_fld in cfg["old_shp_sources"]:
        gdf = reuse_old_geometry(gdf, old_path, old_year, dissolve_fld, cfg)

    # Final breakdown
    breakdown = gdf["tru_shp_yr"].value_counts().sort_index()
    log.info("Final geometry source breakdown:")
    for yr, count in breakdown.items():
        label = "needs manual correction" if yr == 0 else f"from {yr}"
        log.info(f"  tru_shp_yr={yr} ({label}): {count:,}")

    # Stage 4: export
    export_feature_class(gdf, cfg["out_gdb"], cfg["data_year"])

    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Build failed")
        sys.exit(1)