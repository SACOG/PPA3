# Congestion Layer Update (NPMRDS)

How to rebuild the PPA NPMRDS feature class for a new data year. This layer
provides per-TMC congestion metrics (LOTTR, free-flow speeds, worst-hour
analysis, etc.) and is one of the inputs registered with ArcServer for the
PPA tool. See Darren's main handoff guide for the broader context of how
input layers feed into the tool.

## TL;DR for the next person

1. Download fresh RITIS data + NHS shapefile for the new year (see "Inputs").
2. Stage them in a local folder; update the `CONFIG` block in `test.py`.
3. Run `python test.py` from the `arcpro_env` conda environment.
4. Output lands in a local file geodatabase as `NPMRDS_<year>data_<timestamp>`.
5. Inspect the output, manually correct the ~12% of TMCs flagged `tru_shp_yr=0`.
6. Hand off to whoever publishes it to the registered ArcServer location.

## What this produces

A single ESRI feature class with one row per TMC, containing:

- **Identity fields** from RITIS: `tmc`, `road`, `route_numb`, `direction_signd`,
  `f_system`, `nhs`, `miles`.
- **Congestion metrics** (see "Metrics computed" below).
- **Geometry** assembled from up to three sources, with a `tru_shp_yr` flag
  indicating which:
  - `<data_year>` — true shape from this year's NHS shapefile, OR a stick
    line that was auto-accepted because its length matched the RITIS-reported
    miles within 0.17%.
  - `2023`, `2021`, etc. — reused from a previous vintage because the TMC's
    start/end points haven't moved more than 1 ft.
  - `0` — stick line that doesn't match the spec'd mileage; needs manual
    geometry correction in ArcGIS Pro.

Typical breakdown for a fresh run (2025 numbers, for reference):

| Source | Count | Share |
|---|---|---|
| 2025 NHS true shapes | 3,162 | 41% |
| 2023 reused | 3,115 | 41% |
| 2021 reused | 519 | 7% |
| Needs manual correction | 890 | 12% |
| **Total** | **7,686** | |

## Inputs

All inputs go in a single working folder; the `CONFIG` block in `test.py`
points at them. For 2025 the folder was
`C:\Users\tenoru\Downloads\Layer_update\Congestion\` (local copy to avoid
network slowness — see "Performance notes").

### 1. RITIS travel-time CSV

Per-TMC speed/travel-time observations for the whole region.

- **Source**: RITIS Massive Data Downloader — https://ritis.org/
- **How to pull**: Submit a download request for the SACOG region, all TMCs,
  passenger + truck combined, full calendar year, 1-hour or 15-minute epochs.
  RITIS emails a download link when ready (usually < 1 day).
- **Required columns**: `tmc_code`, `measurement_tstamp`, `speed`,
  `travel_time_seconds`.
- **2025 file**: `npmrds_2025_alltmc_paxtruck_comb.csv`.

### 2. RITIS TMC identification CSV

One row per TMC with metadata and lat-long endpoints. RITIS bundles this
with every download.

- **File**: `TMC_Identification.csv` (filename is fixed by RITIS).
- **Required columns**: `tmc`, `road`, `route_numb`, `direction`, `f_system`,
  `nhs`, `miles`, `start_latitude`, `start_longitude`, `end_latitude`,
  `end_longitude`.

### 3. NHS true-shape shapefile (region-clipped)

The National Highway System shapes from NPMRDS, clipped to the SACOG region.
Provides true geometry (with curves) for NHS roads. Non-NHS roads have to be
filled in via vintage reuse or stick lines.

- **Source**: https://npmrds.ritis.org/analytics/shapefiles — pulls
  California-wide, then clip to SACOG.
- **How to make it**: Use `utils.ipynb` in this folder. It reads
  `California.shp`, clips to the SACOG planning area
  (`I:\Projects\Josh\Geospatial Data\GISOWNER\PlanningArea\PlanningArea.shp`),
  and writes the result. For 2025 the output was `NPMRDS_2025_NHS_SACOG.shp`.

### 4. Old true-shape feature classes (for geometry reuse)

Prior-vintage NPMRDS feature classes, used to fill in non-NHS TMCs whose
endpoints haven't moved. Configured as a priority-ordered list in `CONFIG`;
each is tried in turn and only fills gaps left by earlier sources.

Currently (2025 run):

1. `I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\NPMRDS_2023ppadata_final`
   (dissolve field: `tmc`)
2. `I:\Projects\Darren\PPA3_GIS\PPA3.0_archive.gdb\INRIX_SHP_2020_2021_SACOG`
   (dissolve field: `Tmc`)

The dissolve field name varies between vintages, so each entry specifies its
own — `(path, vintage_year, dissolve_field)`.

For future updates, prepend the most recent prior year (e.g., 2025) to the
front of this list, so it's tried first.

## Running the script

### Environment

The script runs in the ArcGIS Pro default conda environment (`arcpro_env`)
plus a few extra dependencies (`duckdb`, `geopandas`, `shapely`). Activate it:

```
conda activate C:\Users\tenoru\AppData\Local\ESRI\conda\envs\arcpro_env
```

### Updating CONFIG for a new year

In `test.py`, edit the `CONFIG` block at the top:

- `tt_csv_path` → new RITIS travel-time CSV
- `tmc_id_csv_path` → new TMC_Identification.csv
- `nhs_shp` → newly clipped NHS shapefile
- `old_shp_sources` → prepend the just-prior vintage
- `data_year` → the new year (e.g., 2026)
- `metrics_cache_csv` → update filename to match the year (or delete to force
  recompute)

### Run

```
python test.py
```

End-to-end takes ~5-6 minutes on first run (the DuckDB stage dominates).
Subsequent runs use the cached metrics and finish in ~15 seconds — useful
when iterating on the geometry stages.

To force recomputing metrics (after a new RITIS download), either delete the
cache CSV or set `"use_metrics_cache": False` in `CONFIG`.

### Output

```
<out_gdb>\NPMRDS_<data_year>data_<YYYYMMDD_HHMM>
```

Each run is timestamped, so re-running doesn't overwrite earlier outputs.
The output FGDB is auto-created if it doesn't exist.

## Metrics computed

All metrics are computed per-TMC by the DuckDB stage. Weekday = Mon-Fri.

**Time windows** (configurable in `CONFIG`):
- AM peak: 6:00-10:00
- Midday: 10:00-16:00
- PM peak: 16:00-20:00
- Weekend: 6:00-20:00 Sat/Sun
- Free-flow: 20:00-6:00 (overnight, wraps midnight)

**Travel-time percentiles**: 50th and 80th percentile travel time (seconds)
for each of AM peak, midday, PM peak, weekend.

**Level of travel time reliability (LOTTR)**: 80th-percentile travel time
divided by 50th, for each time window. Standard FHWA reliability measure.

**Free-flow speed**: Computed from the overnight window. 85th percentile for
freeways (`f_system` 1 or 2); 70th and 60th percentile alternates for
arterials.

**Worst-4-hours metrics**: Harmonic mean speed across the 4 most congested
weekday hours per TMC, plus the congestion ratio (worst-4 speed / free-flow
speed), capped at 1.0.

**Slowest hour**: The single worst weekday hour of day per TMC, its average
speed, and its congestion ratio.

**Epoch counts**: Number of observations contributing to each period
(AM/midday/PM/weekend/worst-4/slowest-hour/overnight). Data-quality flag.

Missing values are represented as `-1` (numeric sentinel), matching the
convention in Darren's original SQL.

## How the script is organized

`test.py` has four stages, each a top-level function called from `main()`:

1. **`compute_metrics_duckdb`** — reads RITIS CSVs via DuckDB, computes all
   the metrics above, returns a pandas DataFrame. Replaces the original
   SQL-Server-based `PPA3_NPMRDS_metrics_test.sql`.
2. **`attach_nhs_geometry`** — joins the metrics to the NHS shapefile,
   marking matched TMCs with `tru_shp_yr = data_year`.
3. **`reuse_old_geometry`** — for unmatched TMCs, tries each older vintage
   in turn. Reuses old geometry where endpoints have shifted < 1 ft; falls
   back to stick lines (auto-accepted when length matches spec'd miles
   within 0.17%).
4. **`export_feature_class`** — writes the assembled GeoDataFrame to an
   ESRI feature class. Creates the output FGDB if needed.

Tolerances (endpoint match, stick-length match), time windows, and the
output CRS are all exposed in `CONFIG`.

## Performance notes

- **Run the CSVs from a local disk, not `I:\`.** The DuckDB query scans the
  travel-time CSV multiple times; over SMB this is dramatically slower than
  on a local SSD. For 2025 the source files were copied from `I:\` to
  `C:\Users\tenoru\Downloads\Layer_update\Congestion\` before running.
- **The metrics cache is the iteration speedup.** Once Stage 1 has run for
  a given year, you can re-run the whole pipeline in seconds by leaving
  `use_metrics_cache: True`. Only Stages 2-4 re-execute.

## Known environment gotchas

These caused trouble during the 2025 build; if anything breaks the same
way again, the fix is at the top of `test.py`:

- **PROJ database**: `arcpro_env` doesn't expose `proj.db` to `pyproj` by
  default, so EPSG codes fail to resolve. The script sets both `PROJ_LIB`
  and `PROJ_DATA` env vars and calls `pyproj.datadir.set_data_dir()`
  programmatically, then smoke-tests `CRS.from_epsg(4326)`.
- **ESRI WKID vs EPSG**: `.gdb` feature classes report ESRI WKIDs (102xxx
  range) which `pyproj` doesn't recognize under the `EPSG:` authority.
  `load_geom_layer` prefers `latestWkid` (modern EPSG) and falls back to
  `ESRI:<wkid>` syntax when needed.
- **MultiLineString geometries** appear in dissolved old-vintage layers and
  break `.coords[0]` access. `reuse_old_geometry` explodes them and keeps
  the longest single part per TMC.

## Next steps (not yet done as of this writing)

### 1. Manually correct the `tru_shp_yr = 0` geometries

The 890 TMCs flagged for manual correction are stick lines (straight
endpoint-to-endpoint) where the spec'd miles disagrees with the stick
length by more than 0.17%, indicating the road actually has curvature. They
need real geometry added in ArcGIS Pro.

Approach (per Darren's process):
- Open the output feature class in Pro.
- Filter to `tru_shp_yr = 0`.
- For each TMC, use a roadway centerline reference layer (e.g., a regional
  street centerline file) to digitize the actual road shape between the
  TMC's start and end points.
- Update `tru_shp_yr` for each corrected feature to the current data year.

This is the most time-consuming part of the layer update and has no good
automation path — it depends on visual inspection against a reference.

### 2. QA against the prior year

Before promoting to production, sanity-check that the metrics look right:
- Symbolize by `tru_shp_yr` to confirm 2025 NHS shapes are on freeways/major
  arterials, older vintages fill in non-NHS roads, and `tru_shp_yr = 0`
  TMCs are scattered local streets (not freeways).
- For a sample of well-known TMCs (a congested freeway segment, a quiet
  collector), compare LOTTR / free-flow speed / slowest hour against the
  2023 layer. Year-over-year drift should be small.
- Check the `epochs_*` columns for TMCs with suspiciously round-number
  metrics — low epoch counts can indicate sparse data and unreliable
  metrics.

### 3. Hand off to production

Once corrected and QA'd, the layer needs to be:
- Copied to the registered ArcServer data store (see Darren's handoff doc
  for the current location — as of November 2025, `ARCSERVERPPA-SVR`).
- Made the active NPMRDS layer the PPA GP services point at (this involves
  updating either YAML configs or replacing the layer at its registered
  path — check with whoever is doing publishing).
- Optionally cleared from any local working folders to avoid confusion
  about which version is "live."

## File inventory

| File | Purpose |
|---|---|
| `test.py` | Main build script (run this) |
| `utils.ipynb` | Clip California NHS shapefile to SACOG region |
| `cache/npmrds_metrics_<year>.csv` | DuckDB metrics output, used to skip Stage 1 on retry |

## Reference

- Darren's main handoff: `Darren PPA Handoff Guide.docx`
- Original SQL this replaces: `PPA3_NPMRDS_metrics_test.sql` (in the
  PPA3 repo, kept for reference but no longer the source of truth)
- Original notebook this replaces: `build_ppa_npmrds.ipynb`
