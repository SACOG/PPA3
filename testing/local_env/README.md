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

## 10. Phase 1 orchestrator — the web app (`testing/local_env/webapp/`)

Beyond running one subreport at a time via `run_local.py`, there is now a
Phase-1 harness that reproduces a whole PPA report run — title service +
however many outcome services a program/projectType dispatches — through a
small local Flask app, driving the same `orchestrator.run_report()` a
scripted/programmatic call would use.

### Launching it

```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\webapp\app.py
```

Then open **http://127.0.0.1:5000**. `app.py` sets `app.config["RUN_REPORT"] =
orchestrator.run_report` (swappable in tests via a `_runner` stub — see
`tests/test_webapp.py`); it does not itself import `arcpy` — only
`orchestrator.run_report` shells out to a fresh Pro-python subprocess per
service (via `run_local.py`), so a real run still needs the Pro python and,
for anything referencing `I:\...` project lines, VPN/network access.

### Form fields (`webapp/templates/form.html`)

- **Program** — populated from `dispatch.PROGRAM_PRESETS` keys (STIP, CMCP
  US50, Active Transportation Program, Regional Federal Funding Program).
- **Project type** — populated from the chosen program's presets
  (`Non-Freeway Investment` / `Freeway Investment`, whichever the program
  offers — ATP offers non-freeway only).
- **Project line** — a dropdown of the named lines in
  `testing/local_env/samples/lines.json` (currently `TestTruxelBridge`); the
  form posts the friendly name, `app.py` resolves it to the real `fc_path`.
- **Project name, Jurisdiction, AADT, Posted speed, PCI, Email** — plain
  inputs, defaulted (`Jurisdiction=Sacramento`, `Email=test@example.com`,
  numeric fields default `0`), passed straight through to the sample JSON
  `orchestrator._write_sample()` builds for `run_local.py`.
- **Performance outcomes** — checkboxes populated client-side from the
  selected program+projectType's outcome catalog. In `"selectable"` mode
  (STIP, CMCP) the checkboxes are real filters; in `"fixed"` mode (ATP,
  Regional Federal Funding Program) they are pre-checked and informational —
  the dev may still uncheck for test flexibility, but the real tool always
  sends its fixed set. `POST /run` reads them via
  `request.form.getlist("outcomes")`, defaulting to `None` (which
  `resolve_dispatch` treats as "use the full/fixed catalog").

### Dispatch resolution

Submitting the form calls `dispatch.resolve_dispatch(program, project_type,
selected_outcomes)`, which returns the ordered `[{outcome, service, folder,
module, entry_function}, ...]` list — title service first, then one entry per
outcome, each outcome mapped to its service short-name via
`OUTCOME_SERVICE_MAP[project_type]`. This mapping is grounded in real capture
data (`PPA3_Handoff/live_config_*_run.json`) and cross-checked against
`stip_config.json`-shaped workflow configs via `load_workflow_config()` (which
tolerates the leading `=` prefix and both project/report schema shapes seen in
the wild) — see `tests/test_dispatch.py::TestLoadWorkflowConfig` and
`TestServiceMaps` for the agreement checks.

### The four-program preset model (`dispatch.PROGRAM_PRESETS`)

| Program | Non-Freeway | Freeway |
|---|---|---|
| STIP | selectable, full 8-outcome catalog | selectable, full 6-outcome catalog |
| CMCP US50 | selectable, full 8 (captured) | selectable, full 6 (inferred) |
| Active Transportation Program | **fixed**, curated 5 (captured) | n/a — confirmed non-freeway only |
| Regional Federal Funding Program | **fixed**, full 8 (captured) | **fixed**, full 6 (captured) |

"Selectable" programs let the user pick a subset via checkboxes (filtered,
catalog order preserved); "fixed" programs ignore `selected_outcomes` and
always dispatch their full/curated set regardless of what's checked in the
UI. ATP's fixed 5, in dispatch order, are VMT, Safety, MultiModal,
EconProsp, SGR (`RPArtExpVMT`, `RPArtExpSafety`, `RPArtExpMultiModal`,
`RPArtExpEconProsp`, `RPArtSGRSGR`), preceded by the title service
(`RPTitleAndGuide`) — i.e. 6 services total, matching the "title + 5" shorthand
used elsewhere in this repo's docs.

### Where runs land

Each submitted run creates `testing/local_env/out/runs/<YYYYmmdd_HHMMSS>/`
containing:
- `manifest.json` — inputs + ordered `services: [{service, outcome, status}]`,
  flushed to disk after each service so a killed/hung run still leaves partial
  progress visible.
- `_sample.json` — the `run_local.py`-shaped input dict built from the form.
- `<Service>.json` — that service's result JSON (only written on success —
  copied from wherever the subreport wrote its output).
- `<Service>.log` — combined stdout+stderr from that service's subprocess
  (present whether it succeeded or failed — this is where to look first for a
  failed service's traceback).
- `merged.json` — all successful services' JSON merged under their service
  key (`{}` if every service in the run failed).

`/run/<stamp>` (the detail page) renders the manifest's per-service status and
pretty-prints any `<Service>.json` that exists; `/runs` (history) lists every
stamp under `out/runs/` that has a `manifest.json`. `out/runs/` is scratch
output under the existing `testing/local_env/out/` gitignore — nothing here
is meant to be committed.

### Optional: `build_run_tables.py`

Every service's `run_*.py` writes its result JSON *before* attempting the
archive log-write step (`utils.get_project_uid()` +
`utils.log_row_to_table()`, which need a `project_master` table and a
per-service `rp_*` table in `params.log_fgdb`). `build_test_gdb.py` creates
`PPA3Testing_run.gdb` **empty**, so on a fresh sandbox every service's
log-write step fails locally — expected, and not prod-unsafe, since
`params.log_fgdb` in local-config mode always resolves to the local
disposable gdb.

`testing/local_env/build_run_tables.py` is an **optional** follow-on step
that read-only-copies the real *schemas* (via `arcpy.management.CreateTable`
with a prod template — no rows) of `project_master` + the arterial `rp_*`
tables into `PPA3Testing_run.gdb`, so those services' log-write step can
succeed locally too:

```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\build_run_tables.py
```

As of this task, `project_master` and the 8 ARTERIAL `rp_*` tables exist
locally (created in Task 8). **`rp_title_guidepg` and the `rp_fwyexp_*`
tables are not present in prod under those folder-name spellings**, so
`build_run_tables.py` skips them — the title service and any freeway service
will still fail their local log-write step even after running this script.
That is incidental to the local sandbox, not a defect in the real tool.

Separately: `CreateTable` always creates a non-spatial attribute Table, even
when the prod source is a spatial FeatureClass. During this task's live run,
`RPArtSGRSGR`'s log-write step failed with `MakeFeatureLayer` reporting
`project_master ... does not exist or is not supported` even though
`arcpy.Exists()` confirms the table is present — consistent with
`MakeFeatureLayer` requiring a spatial feature class and finding a
`CreateTable`-produced plain Table instead. Flagging this as a known gap in
`build_run_tables.py` (worth fixing later if a fully clean archive log-write
is ever needed locally); it is not a defect in the production tool.

### Phase 2: report rendering

This harness (Phase 1) proves the dispatch model and exercises each service's
*computation* against local data, producing per-service JSON and a merged
JSON. A Phase 2 renderer now exists at `testing/local_env/reporting/`: it
turns a Phase-1 run's `manifest.json` + `merged.json` into a single-file,
browser-viewable `report.html` (`python3 testing/local_env/reporting/render.py
<run_dir>`), with per-service card layouts defined in
`testing/local_env/reporting/layout/`. As of this plan it covers the ATP path
only (the 5 outcome sections VertiGIS dispatches for an Active Transportation
Program project) — it does not yet cover Freeway/non-ATP report paths, and it
does not produce map images or a PDF/VertiGIS-rendered layout (those still
need the server + VertiGIS).

### Task 9 validation results (2026-07-28)

- **Step 1 (no-arcpy suite):** `pytest testing/local_env/tests -v` → **19
  passed** (dispatch 12, orchestrator 2, webapp 5) in 0.34s.
- **Step 2 (real end-to-end run):** ran `orchestrator.run_report()` directly
  (same code path `POST /run` uses) for `program="Active Transportation
  Program"`, `project_type="Non-Freeway Investment"`,
  `project_line=TestTruxelBridge`, with `PPA3_LOCAL_CONFIG` set. The
  orchestrator completed and produced a full run folder
  (`out/runs/20260728_171524/`) with `manifest.json`, `merged.json`
  (`{}`), 6 `.log` files, and `_sample.json`. Dispatch order matched the
  expected ATP sequence exactly: `RPTitleAndGuide, RPArtExpVMT,
  RPArtExpSafety, RPArtExpMultiModal, RPArtExpEconProsp, RPArtSGRSGR`. All 6
  services reported `status: "failed"` in the manifest — acceptable per the
  task's pass criterion, and each for a distinct, legible reason recorded in
  its `.log`: `RPTitleAndGuide`/`RPArtExpSafety` — `commtype.get_proj_ctype`'s
  intersect+`GetCount` step ("not a Table View"/"not a Raster Layer");
  `RPArtExpVMT`/`RPArtExpEconProsp` — `ModuleNotFoundError: geopandas` (not
  installed in the arcgispro-py3 env); `RPArtExpMultiModal` — a `NameError:
  project_fc` (an undefined-variable bug in `run_artexp_mm_report.py`, likely
  a leftover from the Task-2 global-scope-leakage refactor — worth a follow-up
  look); `RPArtSGRSGR` — got the furthest (successfully computed and printed
  land-use/complete-street-score/transit-density output) before failing at
  the `project_master` log-write step per the `CreateTable`-schema gap noted
  above. No individual failure blocked the run as a whole; the orchestrator's
  continue-on-service-failure behavior worked as designed.

## 11. Do NOT run these (out of scope / unsafe / stale)

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
