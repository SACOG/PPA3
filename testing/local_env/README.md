# PPA3 Local Test Environment (Tier 1)

Local, read-only-against-prod sandbox for running individual PPA3 `gp-services`
subreports against a copy of the data, without touching the real SDE, the
production run-archive gdb, or VertiGIS.

## 1. Python interpreter (must use ArcGIS Pro's env, and must use PowerShell)

All commands below use the ArcGIS Pro python (has `arcpy`):

```
C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe
```

Run everything via **PowerShell**, not the Bash tool. A Bash-tool subprocess on
this machine cannot resolve `\\Arcserverppa-svr` UNC paths, which `build_test_gdb.py`
and the default (non-local) `config_links.py` path both reference. Use the call
operator (`&`) since the interpreter path has spaces:

```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\run_local.py rp_artexp_cong samples\rp_artexp_cong.json
```

## 2. Refreshing the local sandbox: `build_test_gdb.py`

`testing/local_env/build_test_gdb.py` does a **read-only** export from the live
SDE (`\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\owner_PPA.sde`) into a
local file gdb at `C:\PPA3Testing`. It is idempotent — re-run any time to
refresh the local copies (it deletes and re-exports each FC named in
`manifest.py`, and overwrites the rasters/CSV/JSON template copies and the
staged `globalconfig`).

```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\build_test_gdb.py
```

Produces:
- `C:\PPA3Testing\PPA3Testing.gdb` — the 14 FCs listed in `manifest.py` (includes
  `parcel_data_pts_2020`, `parcel_data_pts_2035`, `comm_type_jurspec_dissolve`, etc.)
- `C:\PPA3Testing\PPA3Testing_run.gdb` — **empty** file gdb standing in for the
  production run-archive gdb (`log_fgdb`). Nothing pre-populates this — see
  "Known limitation: log-write step" below.
- `C:\PPA3Testing\access_tif\`, `C:\PPA3Testing\CSV\Agg_ppa_vals_latest.csv`,
  `C:\PPA3Testing\json_templates\`
- `C:\PPA3Testing\globalconfig\parameters.py` (verbatim copy of prod logic) +
  `data_paths.yaml` (local paths only)

## 3. Running a subreport: `run_local.py`

```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\run_local.py <subreport> <sample.json>
```

Currently registered subreport: `rp_artexp_cong` (congestion + density). Example:

```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\run_local.py rp_artexp_cong samples\rp_artexp_cong.json
```

`run_local.py` sets `PPA3_LOCAL_CONFIG` (see below), runs a safety gate over the
target subreport folder (fails loudly if it finds `Arcserverppa-svr`,
`owner_PPA.sde`, `TruncateTable`, or `DisconnectUser` outside the expected
`config_links.py` fallback-string exception), builds the `input_dict` from the
sample JSON, calls the subreport's entry function, and copies the result JSON
into `testing/local_env/out/<subreport>_<timestamp>.json`.

`testing/local_env/out/` is gitignored (see `.gitignore:139`) — it's scratch
output, not source. The one exception is the golden file below, which is
force-added.

## 4. The `PPA3_LOCAL_CONFIG` switch

`gp-services/regionalprogram/rp_artexp_cong/config_links.py` reads the env var
`PPA3_LOCAL_CONFIG`. If set, it points `config_dir` (and therefore
`parameters.py` + `data_paths.yaml`) at the local sandbox instead of the
production globalconfig share:

- **Unset (production, unchanged):** `\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig`
- **Set by `run_local.py`:** `C:\PPA3Testing\globalconfig`

In local mode, `params.fgdb` resolves to `C:\PPA3Testing\PPA3Testing.gdb` and
`params.log_fgdb` resolves to `C:\PPA3Testing\PPA3Testing_run.gdb` — so even
the run-archive log write in local mode targets a local, disposable gdb, never
the production run-archive.

## 5. Sample project line — deviation from the original brief

The brief's sample JSON (and several subreports' own `__main__` smoke-test
blocks, e.g. `landuse_buff_calcs.py:127`) reference
`I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Polylines` as the canonical ad hoc
test project line. As of 2026-07-13 **that feature class no longer exists** in
that gdb (confirmed via `arcpy.ListFeatureClasses()` — not present at the root
and no feature dataset contains it either). This is a live, Darren-editable
share, not something this repo controls, so its disappearance is an
environment issue, not a repo bug.

`testing/local_env/samples/rp_artexp_cong.json` was updated to point
`Project_Line` at `I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge`
instead — an existing, valid single-feature polyline (~3,524 ft, NAD 1983
StatePlane CA II feet) in the same gdb that other subreports' commented-out
`__main__` blocks already reference as a known test fixture (e.g.
`parcel_data.py:54`). If `Polylines` is recreated later, swap the path back;
until then, use `TestTruxelBridge`.

## 6. Manual density validation (2026-07-13 run)

Ran `rp_artexp_cong` end-to-end. Density is computed by
`LandUseBuffCalcs.point_sum_density()` in
`gp-services/regionalprogram/rp_artexp_cong/landuse_buff_calcs.py:91-119`.
It defines "net acres" as the sum of the `GISAc` field
(`params.col_area_ac = 'GISAc'`, set in `globalconfig_rp/parameters.py:325`)
across every parcel **point** selected within the buffer — i.e. whole-parcel
area for every parcel whose centroid falls within the buffer distance, not an
area-clipped intersection. `GISAc` itself is a pre-computed acreage field
inherited from the upstream land-use parcel build
(`layer-building/parcel_data/make_ppa_pcl_layer.ipynb`); nothing in
`point_sum_density()` re-derives it from geometry, and it is not re-verified
against raw parcel-polygon area in this test — its "excludes water/ROW/net"
character is inherited as-is from that field.

The buffer distance used for this subreport is `params.ilut_sum_buffdist =
2640` ft (0.5 mi), and parcel selection uses `WITHIN_A_DISTANCE` (equivalent to
buffer-then-intersect against parcel centroids).

Independent manual calc (selected 744 parcels within 2,640 ft of
`TestTruxelBridge`, both `parcel_data_pts_2020` and `parcel_data_pts_2035`):

| Year | sum EMPTOT | sum DU_TOT | sum GISAc | EMPTOT/GISAc (manual) | function's `jobs` | DU_TOT/GISAc (manual) | function's `dwellingUnits` |
|---|---|---|---|---|---|---|---|
| 2020 | 6232.0 | 2353.0 | 763.0699938 | 8.167009646081546 | 8.167009646081565 | 3.0835965496196853 | 3.0835965496196924 |
| 2035 | 10237.0 | 5030.0 | 763.0699938 | 13.415545209713859 | 13.415545209713892 | 6.591793729106253 | 6.59179372910627 |

**Match confirmed** to ~13-14 significant figures in both years for both
metrics; the sub-1e-13 differences are floating-point summation-order noise
(pandas `.sum()` vs. a manual running total), not a logic discrepancy.

## 7. Benchmark bars — actual result differs from the original assumption

The task brief for this environment assumed all four benchmark fields
(`commtype_jobs`, `region_jobs`, `commtype_du`, `region_du`) would come back
`0` because `Agg_ppa_vals_latest.csv` supposedly lacked the
`EMPTOT_NetPclAcre` / `DU_TOT_NetPclAcre` columns. **That assumption did not
hold for year 2020** in the copy of the CSV pulled by `build_test_gdb.py` on
2026-07-13 (`C:\PPA3Testing\Agg_ppa_vals_latest.csv`) — it already has both
columns for `year=2020`:

- 2020: `commtype_jobs=1.704505256`, `region_jobs=0.265858004`,
  `commtype_du=2.440418763`, `region_du=0.247375092` — **all non-zero**.
- 2035: `commtype_jobs=0`, `region_jobs=0`, `commtype_du=0`, `region_du=0` —
  zero, because the CSV has **no row at all** for `year=2035` for those
  metrics (only a `mix_index` row exists for 2035).

Takeaway: the re-aggregation (`reg-ctype-aggregation/PPA3_ctype_region_agg.py`)
appears to have been run for base year 2020 at some point after the CLAUDE.md
wishlist notes were written, but not for the 2035 future year. This is worth
flagging back to whoever owns that re-aggregation step — it is not the "fully
blocked, nothing populated yet" state the wishlist describes.

## 8. Known limitation: log-write step fails on a fresh local run (expected)

`make_congestion_rpt_artexp` (in `run_congestion_report.py`) computes and
writes the result JSON to `arcpy.env.scratchFolder` (density is fully computed
by this point), and only *after* that calls `utils.get_project_uid()` (needs a
`project_master` table in `params.log_fgdb`) and then
`utils.log_row_to_table()` (needs an `rp_artexp_cong` table in the same gdb).
`PPA3Testing_run.gdb` is created empty by `build_test_gdb.py`, so on a fresh
local run this fails with:

```
arcgisscripting.ExecuteError: ... Dataset C:\PPA3Testing\.\PPA3Testing_run.gdb\project_master does not exist or is not supported
```

This is expected and **not** a prod-safety issue — `params.log_fgdb` resolves
to the local `PPA3Testing_run.gdb` in local-config mode (confirmed in Task 2),
never the production run-archive gdb. No prod write was attempted at any
point in this run.

We deliberately did **not** create empty `project_master` / `rp_artexp_cong`
tables in the local run gdb to force the log-write to succeed, since their
exact schemas (field names/types) aren't specified anywhere in the brief and
guessing wrong would silently mask a real integration bug rather than exercise
one honestly. Instead, the golden JSON was recovered from the already-written
result file in `arcpy.env.scratchFolder`
(`C:\Users\tenoru\AppData\Local\Temp\scratch\CongestnRpt*.json`) — which is
exactly the file `run_local.py` would otherwise have copied into
`testing/local_env/out/` had the run completed cleanly. If a fully clean
end-to-end run (through the log write) is needed later, someone with schema
knowledge for `project_master` and `rp_artexp_cong` should add empty tables
with the correct fields to `PPA3Testing_run.gdb` only.

## 9. Golden output

`testing/local_env/out/rp_artexp_cong_GOLDEN.json` — captured 2026-07-13 from
the run described above (project = `TestTruxelBridge`, jobs/DU density
values validated per §6). Diff future runs against this file to catch
regressions in the density/congestion calc path. Note the congestion-related
fields in the golden file are all zero/null — `TestTruxelBridge` did not
conflate to NPMRDS TMC segments in this run; that is incidental to this task
(density was the target), not a defect being asserted here.

## 10. Do NOT run these (out of scope / unsafe / stale)

- `batch_fix_collnrate.ipynb` — one-off batch-fix notebook; not part of the
  local test loop and may target prod paths. (Not present in the current repo
  tree as of 2026-07-13 — flagging per standing instruction in case it
  reappears or exists elsewhere on a dev machine.)
- `.pyHistory` — Jupyter/Spyder console history artifact, not runnable code.
  (Also not found in the repo tree; likely a per-user IDE file outside the
  repo, e.g. under a home/profile directory.)
- `result_db_mgt/` — archived results DB management; present in the repo root.
  Touches the real run-archive DB, not the local sandbox — do not run against
  this test environment.
