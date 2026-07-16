# TCAC Opportunity Score (Community Design) — Design Spec

**Date:** 2026-07-15
**Status:** Approved — ready for implementation planning
**Repo/branch:** `github.com/SACOG/PPA3`, branch `data_layer_update`
**Wishlist item:** "TCAC score in community design only" (Darren/Garett, Med priority, Equity + Community Design)
**Scope:** Approach A — implement the indicator and verify the new logic directly against local data. The full CD-family end-to-end local run is a deliberately separate follow-up.

---

## Purpose

Add a Community-Design-only indicator that reports the **maximum TCAC composite opportunity index** among the TCAC opportunity areas a project directly intersects, together with that area's **opportunity category** label. Extends the existing `cdp_housingchoice` subreport.

## Data source (confirmed in SDE 2026-07-15)

`owner_PPA.sde\TCAC_2021` — 726 polygons (census-tract-scale opportunity areas). Relevant fields:

| Field | Type | Meaning |
|---|---|---|
| `index_` | Double | Composite opportunity index. Range −1.167 … 1.004, mean 0.034. Drives "max". |
| `oppcat` | String | Opportunity category label. Reported alongside the max index. |
| `ecn_dmn`, `env_hl_`, `ed_domn` | Double | Economic / environmental-health / education domain scores (not used in Approach A). |

`oppcat` distinct values (count): Low Resource (184), Moderate Resource (172), Highest Resource (149), High Resource (145), High Segregation & Poverty (43), blank (26), Moderate Resource (Rapidly Changing) (7).

**Design decisions locked during brainstorming:**
- **"TCAC value" = max composite `index_`**, with the `oppcat` category of that same polygon reported as a label. Chosen over category-ordinal-max because the special categories ("High Segregation & Poverty", blanks) don't fit a clean tier ordering; max-by-index is unambiguous.
- **Spatial rule = direct intersect** (TCAC polygons the project geometry crosses/touches), not a buffer — matches the wishlist wording and reports the opportunity area the project truly sits in.
- **Home = `cdp_housingchoice`** (existing CD subreport; opportunity/equity/housing theme), not a new standalone GP service.

## Architecture

`cd_housingchoice_rpt()` already loads a JSON template, buffers parcels, computes a housing-mix indicator, writes results into the loaded JSON, logs a row, and returns the output JSON path. This design adds one more indicator to that flow, computed by a new self-contained module. The calculation is split so the decision logic is testable without arcpy.

```
cd_housingchoice_rpt(input_dict)
  ├─ (existing) housing-mix calc → loaded_json["charts"]["Housing Types"]
  └─ (new) tcac_score.get_max_tcac(fc_project, params.tcac_fc)
             ├─ arcpy: SelectLayerByLocation INTERSECT → cursor over (index_, oppcat)
             └─ _select_max_tcac(rows)  ← pure, unit-tested
        → loaded_json["tcacIndex"], loaded_json["tcacCategory"]  (top-level scalars, like projectAADT)
        → data_to_log["tcac_index"], data_to_log["tcac_category"]
```

## Components

### 1. `gp-services/commdesign/cdp_housingchoice/tcac_score.py` (new)

- `_select_max_tcac(rows)` — **pure, no arcpy.** Input: iterable of `(index, category)` tuples. Behavior:
  - Ignore rows whose `index` is `None`.
  - Return `(max_index, category)` for the row with the greatest `index`.
  - Empty input or all-`None` indices → `(None, None)`.
  - If the chosen row's category is `None`/blank/whitespace → category returned as `"Not Categorized"`.
  - Ties on index: first-encountered wins (deterministic; ties are not meaningful for a single reported value).
- `get_max_tcac(fc_project, fc_tcac)` — **arcpy wrapper.** Makes a feature layer from `fc_tcac`, `SelectLayerByLocation(layer, "INTERSECT", fc_project)`, reads `(params.col_tcac_index, params.col_tcac_category)` for selected features via `arcpy.da.SearchCursor`, passes them to `_select_max_tcac`, and returns `{"tcac_index": float|None, "tcac_category": str|None}`. No intersecting polygons → `{"tcac_index": None, "tcac_category": None}`.

### 2. Config

- `cdp_housingchoice/data_paths.yaml` — add to the `sde:` block: `tcac_fc: TCAC_2021`.
- `cdp_housingchoice/parameters.py` — add:
  - `tcac_fc = pathconfigs['sde']['tcac_fc']`
  - `col_tcac_index = 'index_'`
  - `col_tcac_category = 'oppcat'`

### 3. Wire into `cd_housingchoice_rpt()`

- `import tcac_score` at the top with the other module imports.
- After the housing-mix loop, before `log_row_to_table`:
  ```python
  tcac = tcac_score.get_max_tcac(fc_project, params.tcac_fc)
  loaded_json["tcacIndex"] = tcac["tcac_index"]
  loaded_json["tcacCategory"] = tcac["tcac_category"]
  ```
- Extend `data_to_log` with `'tcac_index': tcac["tcac_index"], 'tcac_category': tcac["tcac_category"]`.
- Uses the already-extracted `fc_project` local (line 32), not a module global.

### 4. Local test data — `testing/local_env/manifest.py`

- Add `"TCAC_2021"` to `SHARED_FCS`, then re-run `build_test_gdb.py` so the local gdb contains it. (Idempotent refresh.)

## Verification (using the local test environment)

- **Unit test (no-arcpy suite, `gp-services/regionalprogram/tests/test_no_server_tasks.py`):** exercise `_select_max_tcac` — normal max pick, tie, empty input, all-`None` indices, and blank-category → `"Not Categorized"`. Runs in the existing fast suite without arcpy or the SDE.
- **Integration check (arcpy, against the local gdb):** run `get_max_tcac(TestTruxelBridge, TCAC_2021)` against `C:\PPA3Testing\PPA3Testing.gdb`; independently dump the `index_`/`oppcat` of every polygon the line intersects and confirm the function returns the true maximum and its category. Same manual cross-check that validated the density indicator.

## Out of scope (deferred — "B" CD-family pass)

- `PPA3_LOCAL_CONFIG` switch for `cdp_*` `parameters.py`, `run_local.py` registration of `cdp_housingchoice`, and a headless full-subreport run. (CD `parameters.py` reads its own sibling `data_paths.yaml` — a different switch point than the `rp_*` `config_links.py` mechanism.)
- The module's pre-existing `output_dir` / `project_fc` `__main__`-global references (the "project-type-as-input" refactor only reached `rp_*`). Left untouched; the new TCAC code uses correct locals.
- VertiGIS chart/template slot to display `tcacIndex`/`tcacCategory` (consultant). The output JSON carries the fields regardless.
- Domain sub-scores (`ecn_dmn`, `env_hl_`, `ed_domn`) — not reported in A.

## Testing / prod-safety notes

- `get_max_tcac` is read-only (a selection + a search cursor); no writes to any FC.
- All verification runs against the local `C:\PPA3Testing` sandbox; the SDE is only read once, by `build_test_gdb.py`, to refresh the local copy of `TCAC_2021`.
