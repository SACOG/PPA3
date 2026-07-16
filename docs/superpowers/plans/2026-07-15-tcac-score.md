# TCAC Opportunity Score (Community Design) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Community-Design-only indicator that reports the maximum TCAC composite opportunity index among the TCAC areas a project directly intersects, plus that area's opportunity category, into the `cdp_housingchoice` subreport.

**Architecture:** A new `tcac_score.py` in `cdp_housingchoice` splits the work into a pure decision function (`_select_max_tcac`, unit-tested without arcpy) and a thin arcpy wrapper (`get_max_tcac`, verified against the local test gdb). `cd_housingchoice_rpt()` calls the wrapper and writes two top-level scalars into the result JSON. TCAC_2021 is added to the local-test export manifest.

**Tech Stack:** Python 3.11 (ArcGIS Pro `arcgispro-py3`), `arcpy` 3.7, `unittest`/`pytest`.

## Global Constraints

- **Repo/branch:** `C:\Users\tenoru\Downloads\data_layer_update`, branch `data_layer_update`. Never `main`. Targeted `git add` of only the files each task names — the working tree has unrelated pre-existing changes; leave them.
- **Pro python (verified):** `C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe`. Run anything touching `\\Arcserverppa-svr` via **PowerShell** (the Bash tool can't see that UNC path); pure-Python pytest can run from either.
- **`tcac_score.py` must have NO module-level `arcpy` or `parameters` import** — `arcpy` is imported *inside* `get_max_tcac`. This keeps the no-arcpy suite (`gp-services/regionalprogram/tests/test_no_server_tasks.py`) importable and CI-portable.
- **Field facts (verified in SDE 2026-07-15):** `TCAC_2021` FC; score field `index_` (Double, range −1.167…1.004); category field `oppcat` (String). Bare FC name resolves against `arcpy.env.workspace`.
- **Reported behavior (from spec):** max by `index_`; report that polygon's `oppcat`; blank/whitespace category → `"Not Categorized"`; no intersecting polygon (or all `index_` null) → both values `None` (JSON `null`); index ties → first-encountered wins.
- **Scope = Approach A.** Do NOT wire the CD-family `PPA3_LOCAL_CONFIG` switch, register `cdp_housingchoice` in `run_local.py`, run the full subreport headless, or touch the module's pre-existing `output_dir`/`project_fc` `__main__`-global bugs. Verification targets the new function directly.
- **Read-only against prod:** the only SDE read is the one-time `TCAC_2021` export to the local gdb. `get_max_tcac` performs a selection + search cursor only — no writes to any FC.

---

### Task 1: `_select_max_tcac` pure decision logic + unit tests

**Files:**
- Create: `gp-services/commdesign/cdp_housingchoice/tcac_score.py`
- Test: `gp-services/regionalprogram/tests/test_no_server_tasks.py` (add one `unittest.TestCase` class)

**Interfaces:**
- Produces: `_select_max_tcac(rows)` where `rows` is an iterable of `(index, category)` tuples (`index` is `float|None`, `category` is `str|None`). Returns a 2-tuple `(max_index, category)` = `(float, str)` or `(None, None)`.

- [ ] **Step 1: Write the failing test**

Add to the end of `gp-services/regionalprogram/tests/test_no_server_tasks.py`, immediately **before** the final `if __name__ == '__main__':` block:

```python
# ---------------------------------------------------------------------------
# TCAC opportunity score — test _select_max_tcac (no arcpy)
# ---------------------------------------------------------------------------
import os as _os_tcac
_CDP_HC = _os_tcac.path.abspath(
    _os_tcac.path.join(_os_tcac.path.dirname(__file__), '..', '..', 'commdesign', 'cdp_housingchoice')
)
if _CDP_HC not in sys.path:
    sys.path.insert(0, _CDP_HC)
from tcac_score import _select_max_tcac  # must import WITHOUT pulling arcpy


class TestTcacMaxSelection(unittest.TestCase):
    """TCAC: verify _select_max_tcac picks the max-index row and reports its category."""

    def test_picks_max_index_and_category(self):
        rows = [(0.10, 'Low Resource'), (0.90, 'Highest Resource'), (0.50, 'Moderate Resource')]
        self.assertEqual(_select_max_tcac(rows), (0.90, 'Highest Resource'))

    def test_negative_indices(self):
        rows = [(-0.50, 'Low Resource'), (-1.10, 'High Segregation & Poverty')]
        self.assertEqual(_select_max_tcac(rows), (-0.50, 'Low Resource'))

    def test_skips_none_index(self):
        rows = [(None, 'Highest Resource'), (0.20, 'Low Resource')]
        self.assertEqual(_select_max_tcac(rows), (0.20, 'Low Resource'))

    def test_all_none_index_returns_none_pair(self):
        rows = [(None, 'X'), (None, 'Y')]
        self.assertEqual(_select_max_tcac(rows), (None, None))

    def test_empty_returns_none_pair(self):
        self.assertEqual(_select_max_tcac([]), (None, None))

    def test_blank_category_on_max_becomes_not_categorized(self):
        rows = [(0.90, '   '), (0.10, 'Low Resource')]
        self.assertEqual(_select_max_tcac(rows), (0.90, 'Not Categorized'))

    def test_none_category_on_max_becomes_not_categorized(self):
        rows = [(0.90, None), (0.10, 'Low Resource')]
        self.assertEqual(_select_max_tcac(rows), (0.90, 'Not Categorized'))

    def test_index_tie_first_wins(self):
        rows = [(0.50, 'First'), (0.50, 'Second')]
        self.assertEqual(_select_max_tcac(rows), (0.50, 'First'))
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"C:/Users/tenoru/AppData/Local/Programs/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe" -m pytest gp-services/regionalprogram/tests/test_no_server_tasks.py::TestTcacMaxSelection -q
```
Expected: collection/import error `ModuleNotFoundError: No module named 'tcac_score'` (file doesn't exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `gp-services/commdesign/cdp_housingchoice/tcac_score.py` with ONLY the pure function for now (no arcpy, no imports):

```python
"""
tcac_score.py — TCAC opportunity score indicator for Community Design.

Reports the maximum TCAC composite opportunity index (`index_`) among the TCAC
opportunity areas a project directly intersects, plus that polygon's opportunity
category (`oppcat`).

IMPORTANT: no module-level `arcpy` or `parameters` import — arcpy is imported
inside get_max_tcac so the pure logic stays testable without arcpy.
"""


def _select_max_tcac(rows):
    """Pick the (index, category) with the greatest index.

    rows: iterable of (index, category) tuples; index is float|None, category str|None.
    Returns (max_index, category) or (None, None) if no row has a non-None index.
    A blank/None category on the chosen row is reported as "Not Categorized".
    On an index tie, the first-encountered row wins.
    """
    best_index = None
    best_category = None
    for index, category in rows:
        if index is None:
            continue
        if best_index is None or index > best_index:
            best_index = index
            best_category = category
    if best_index is None:
        return (None, None)
    if best_category is None or str(best_category).strip() == "":
        best_category = "Not Categorized"
    return (best_index, best_category)
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
"C:/Users/tenoru/AppData/Local/Programs/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe" -m pytest gp-services/regionalprogram/tests/test_no_server_tasks.py::TestTcacMaxSelection -q
```
Expected: `8 passed`.

- [ ] **Step 5: Run the full no-arcpy suite to confirm no regression**

Run:
```bash
"C:/Users/tenoru/AppData/Local/Programs/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe" -m pytest gp-services/regionalprogram/tests/test_no_server_tasks.py -q
```
Expected: `36 passed` (28 existing + 8 new).

- [ ] **Step 6: Commit**

```bash
git add gp-services/commdesign/cdp_housingchoice/tcac_score.py gp-services/regionalprogram/tests/test_no_server_tasks.py
git commit -m "feat: add _select_max_tcac pure logic for TCAC opportunity score"
```

---

### Task 2: `get_max_tcac` arcpy wrapper + config + local test data + integration verify

**Files:**
- Modify: `gp-services/commdesign/cdp_housingchoice/tcac_score.py` (add `get_max_tcac`)
- Modify: `gp-services/commdesign/cdp_housingchoice/data_paths.yaml` (add `tcac_fc`)
- Modify: `gp-services/commdesign/cdp_housingchoice/parameters.py` (add 3 constants)
- Modify: `testing/local_env/manifest.py` (add `TCAC_2021` to `SHARED_FCS`)

**Interfaces:**
- Consumes: `_select_max_tcac` from Task 1.
- Produces: `get_max_tcac(fc_project, fc_tcac, col_index="index_", col_category="oppcat")` → `{"tcac_index": float|None, "tcac_category": str|None}`. Config constants `params.tcac_fc = 'TCAC_2021'`, `params.col_tcac_index = 'index_'`, `params.col_tcac_category = 'oppcat'`.

- [ ] **Step 1: Add `get_max_tcac` to `tcac_score.py`**

Append to `gp-services/commdesign/cdp_housingchoice/tcac_score.py`:

```python
def get_max_tcac(fc_project, fc_tcac, col_index="index_", col_category="oppcat"):
    """Return the max TCAC index (and its category) among polygons fc_project intersects.

    fc_tcac resolves against arcpy.env.workspace (the fgdb). Read-only.
    Returns {"tcac_index": float|None, "tcac_category": str|None}.
    """
    import arcpy

    lyr = "tcac_sel_lyr"
    if arcpy.Exists(lyr):
        arcpy.management.Delete(lyr)
    arcpy.management.MakeFeatureLayer(fc_tcac, lyr)
    arcpy.management.SelectLayerByLocation(lyr, "INTERSECT", fc_project)
    rows = [(r[0], r[1]) for r in arcpy.da.SearchCursor(lyr, [col_index, col_category])]
    arcpy.management.Delete(lyr)

    max_index, category = _select_max_tcac(rows)
    return {"tcac_index": max_index, "tcac_category": category}
```

- [ ] **Step 2: Add the FC name to `data_paths.yaml`**

In `gp-services/commdesign/cdp_housingchoice/data_paths.yaml`, add one line to the `sde:` block (after `proj_line_template_fc`):

```yaml
  tcac_fc: TCAC_2021 # HCD/TCAC opportunity areas; fields index_ (score) + oppcat (category)
```

- [ ] **Step 3: Add config constants to `parameters.py`**

In `gp-services/commdesign/cdp_housingchoice/parameters.py`, next to the other `pathconfigs['sde'][...]` input-FC assignments, add:

```python
tcac_fc = pathconfigs['sde']['tcac_fc']  # TCAC opportunity areas FC
col_tcac_index = 'index_'      # TCAC composite opportunity index (Double)
col_tcac_category = 'oppcat'   # TCAC opportunity category label (String)
```

- [ ] **Step 4: Add `TCAC_2021` to the export manifest**

In `testing/local_env/manifest.py`, add `"TCAC_2021"` to the `SHARED_FCS` list (so future full refreshes include it):

```python
    "parcel_data_pts_2035",
    "TCAC_2021",
]
```

- [ ] **Step 5: Export `TCAC_2021` into the local gdb (fast, targeted)**

Run via PowerShell (targeted export avoids re-copying all 472 MB; the manifest edit covers future full refreshes):
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import arcpy; src=r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\owner_PPA.sde\TCAC_2021'; dst=r'C:\PPA3Testing\PPA3Testing.gdb\TCAC_2021'; arcpy.management.Delete(dst) if arcpy.Exists(dst) else None; arcpy.conversion.ExportFeatures(src, dst); print('rows:', arcpy.management.GetCount(dst)[0])"
```
Expected: `rows: 726`.

- [ ] **Step 6: Integration verify `get_max_tcac` against the local gdb + manual cross-check**

Run via PowerShell (uses the `TestTruxelBridge` line and the local `TCAC_2021`; computes the expected answer independently, then compares):
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import arcpy, sys; sys.path.insert(0, r'gp-services\commdesign\cdp_housingchoice'); import tcac_score; arcpy.env.workspace=r'C:\PPA3Testing\PPA3Testing.gdb'; proj='TestTruxelBridge'; func=tcac_score.get_max_tcac(proj,'TCAC_2021'); lyr=arcpy.management.MakeFeatureLayer('TCAC_2021','t')[0]; arcpy.management.SelectLayerByLocation(lyr,'INTERSECT',proj); rows=[(r[0],r[1]) for r in arcpy.da.SearchCursor(lyr,['index_','oppcat'])]; import builtins; mx=max([r for r in rows if r[0] is not None], key=lambda x:x[0]) if any(r[0] is not None for r in rows) else (None,None); print('intersecting polys:', rows); print('manual max:', mx); print('function:', func); assert func['tcac_index']==mx[0], 'MISMATCH'; print('MATCH OK')"
```
Expected: prints the intersecting polygons, a `manual max` tuple, the `function` dict, and `MATCH OK`. If `TestTruxelBridge` doesn't exist or intersects nothing, report the observed output as DONE_WITH_CONCERNS (do not fabricate a match).

- [ ] **Step 7: Commit**

```bash
git add gp-services/commdesign/cdp_housingchoice/tcac_score.py gp-services/commdesign/cdp_housingchoice/data_paths.yaml gp-services/commdesign/cdp_housingchoice/parameters.py testing/local_env/manifest.py
git commit -m "feat: get_max_tcac arcpy wrapper + TCAC config; add TCAC_2021 to local manifest"
```

---

### Task 3: Wire TCAC into `cd_housingchoice_rpt` output

**Files:**
- Modify: `gp-services/commdesign/cdp_housingchoice/run_cd_housingchoice_rpt.py`

**Interfaces:**
- Consumes: `tcac_score.get_max_tcac`, and `params.tcac_fc`/`params.col_tcac_index`/`params.col_tcac_category` from Task 2.
- Produces: result JSON with top-level `tcacIndex` (float|null) and `tcacCategory` (str|null); `data_to_log` gains `tcac_index`/`tcac_category`.

- [ ] **Step 1: Import the module**

In `gp-services/commdesign/cdp_housingchoice/run_cd_housingchoice_rpt.py`, add to the import block (near `import parcel_data` at line 26):

```python
import tcac_score
```

- [ ] **Step 2: Compute and write the TCAC values**

In `cd_housingchoice_rpt()`, after the housing-mix `for` loop ends (after the block that fills `row_data`, i.e. just before the `# log results to data tables` comment), insert:

```python
    # TCAC opportunity score: max composite index among intersected TCAC areas, + its category
    tcac = tcac_score.get_max_tcac(fc_project, params.tcac_fc,
                                   params.col_tcac_index, params.col_tcac_category)
    loaded_json["tcacIndex"] = tcac["tcac_index"]
    loaded_json["tcacCategory"] = tcac["tcac_category"]
```

- [ ] **Step 3: Add the values to the logged row**

In the same function, extend the `data_to_log` dict (currently `data_to_log = {'project_uid': project_uid}` then `data_to_log.update(row_data)`). After the `data_to_log.update(row_data)` line, add:

```python
    data_to_log['tcac_index'] = tcac["tcac_index"]
    data_to_log['tcac_category'] = tcac["tcac_category"]
```

- [ ] **Step 4: Import-smoke check (arcpy available; full subreport run is out of scope per Approach A)**

Run via PowerShell — confirms the edited module imports with no syntax/name error and that `get_max_tcac` is reachable through it:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import sys; sys.path.insert(0, r'gp-services\commdesign\cdp_housingchoice'); import run_cd_housingchoice_rpt as m; assert hasattr(m, 'tcac_score') and hasattr(m.tcac_score, 'get_max_tcac'); import inspect, re; src=inspect.getsource(m.cd_housingchoice_rpt); assert 'tcacIndex' in src and 'tcacCategory' in src and 'get_max_tcac' in src; print('WIRING OK')"
```
Expected: `WIRING OK`. (This checks the module loads and the wiring is present; the end-to-end subreport run is deferred to the CD-family "B" pass per the spec.)

- [ ] **Step 5: Commit**

```bash
git add gp-services/commdesign/cdp_housingchoice/run_cd_housingchoice_rpt.py
git commit -m "feat: report TCAC opportunity score in cd_housingchoice subreport JSON"
```

---

## Self-review notes

- **Spec coverage:** Component 1 (`_select_max_tcac` + `get_max_tcac`) → Tasks 1–2; Component 2 (config) → Task 2 Steps 2–3; Component 3 (wire into subreport) → Task 3; Component 4 (manifest + local data) → Task 2 Steps 4–5; Verification (unit + integration) → Task 1 Steps 2/4/5 and Task 2 Step 6. Out-of-scope items (CD-family switch, run_local registration, global-scope bug fixes, VertiGIS display) are intentionally absent.
- **Type/name consistency:** `_select_max_tcac` returns a `(index, category)` tuple; `get_max_tcac` wraps it into `{"tcac_index","tcac_category"}`; the run script reads those dict keys and writes `tcacIndex`/`tcacCategory` JSON keys + `tcac_index`/`tcac_category` log keys. Field names `index_`/`oppcat` consistent across params, wrapper defaults, and verification. No arcpy at module scope in `tcac_score.py`, satisfying the no-arcpy-suite import in Task 1.
- **Verification honesty:** Task 3's automated check is an import-smoke + wiring-presence check (the full subreport run is deliberately out of scope for Approach A); the indicator's correctness is proven by Task 1 (unit) and Task 2 (integration against real local data).
