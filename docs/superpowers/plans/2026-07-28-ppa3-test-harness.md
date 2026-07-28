# PPA3 Test Harness (Phase 1 — Orchestrator) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a program-aware local orchestrator + Flask UI that reproduces the live PPA tool's GP-service dispatch for a chosen (program, project type, outcomes), runs each service against local Tier-1 data, and shows a per-service status/output dashboard.

**Architecture:** A pure-Python `dispatch.py` encodes the capture-proven dispatch model (projectType→service map, program→outcome-set/mode) and resolves the ordered service list for a run. `orchestrator.py` runs each dispatched service as an **isolated ArcGIS-Pro-python subprocess** (reusing the existing `run_local.py`), captures status/output, and merges results into a per-run folder. A **Flask** app (no arcpy — it shells out) provides the input form and the run dashboard.

**Tech Stack:** Python 3.11 (ArcGIS Pro `arcgispro-py3` env), `arcpy` (only inside the per-service subprocess, never in the web app), `pandas`, `pyyaml`, `flask`, `pytest`/`unittest`, `subprocess`.

## Global Constraints

- **Repo (checked out):** `C:\Users\tenoru\Downloads\data_layer_update`, branch `data_layer_update`. All commits go here — never `main`.
- **ArcGIS Pro python (verified):** `C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe`. Used for every `pytest`/service subprocess.
- **Run anything touching arcpy or `\\Arcserverppa-svr` via PowerShell**, not the Bash tool (Bash can't see that UNC path).
- **Local sandbox:** `C:\PPA3Testing\` (built by `testing/local_env/build_test_gdb.py`); `globalconfig\` there is the local config the switch points at.
- **The config switch:** setting env var `PPA3_LOCAL_CONFIG` → local globalconfig; unset → production (byte-for-byte unchanged). Proven form: `config_dir = os.environ.get('PPA3_LOCAL_CONFIG') or _PROD_CONFIG`.
- **Prod-safety invariant:** local mode never opens the SDE and never writes the production run gdb. The `run_local.py` safety gate runs before every service.
- **Web app needs no arcpy** — it imports only `dispatch.py` (pure) and shells out to the Pro python via `run_local.py`. Isolation per service is via **subprocess**, never in-process import (same-named modules across `rp_*` folders collide in `sys.modules`).
- **Sequential dispatch** — one arcpy subprocess at a time (license/lock safety). No parallelism.
- **`params.user_inputs` keys (verbatim):** `geom="Project_Line"`, `name="Project_Name"`, `jur="Jurisdiction"`, `funding_pgm="Funding_Program"`, `ptype="Project_Type"`, `perf_outcomes="PerfOutcomes"`, `aadt="AADT"`, `posted_spd="Posted_Speed_Limit"`, `pci="PCI"`, `email="userEmail"`.
- **Design spec:** `docs/superpowers/specs/2026-07-27-ppa3-test-harness-design.md`.

---

## File Structure

- `testing/local_env/dispatch.py` — **new.** `SERVICE_REGISTRY`, `OUTCOME_SERVICE_MAP`, `PROGRAM_PRESETS`, `resolve_dispatch()`, `load_workflow_config()`. Pure Python, no arcpy.
- `testing/local_env/orchestrator.py` — **new.** `run_report()`: run folder, incremental manifest, per-service subprocess loop, `merged.json`.
- `testing/local_env/samples/lines.json` — **new.** Pre-staged project-line registry for the form dropdown.
- `testing/local_env/webapp/app.py` — **new.** Flask app: input form + run/history/detail dashboard.
- `testing/local_env/webapp/templates/{form,run,history,detail}.html` — **new.** Pages.
- `testing/local_env/tests/test_dispatch.py` — **new.** Pure-Python dispatch tests (no arcpy).
- `testing/local_env/tests/test_orchestrator.py` — **new.** Orchestrator tests with mocked subprocess (no arcpy).
- `testing/local_env/tests/test_webapp.py` — **new.** Flask test-client tests (no arcpy).
- `testing/local_env/run_local.py` — **modify.** Replace its 2-entry `ENTRYPOINTS` dict with an import of `dispatch.SERVICE_REGISTRY` so all 15 services are runnable.
- 13 × `gp-services/regionalprogram/rp_*/config_links.py` — **modify.** Add the `PPA3_LOCAL_CONFIG` switch.
- `testing/local_env/README.md` — **modify.** Document the harness + optional archive-schema step.

---

### Task 1: `dispatch.py` — service maps & registry

**Files:**
- Create: `testing/local_env/dispatch.py`
- Test: `testing/local_env/tests/test_dispatch.py`

**Interfaces:**
- Produces: `SERVICE_REGISTRY: dict[str, tuple[str,str,str]]` (service short-name → `(folder, entry_module, entry_function)`); `OUTCOME_SERVICE_MAP: dict[str, dict[str, str]]` (projectType → outcome name → service short-name); `TITLE_SERVICE = "RPTitleAndGuide"`.

- [ ] **Step 1: Write the failing test**

Create `testing/local_env/tests/test_dispatch.py`:
```python
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
import dispatch


class TestServiceMaps(unittest.TestCase):
    def test_registry_has_all_15_live_services(self):
        expected = {
            "RPTitleAndGuide", "RPArtExpVMT", "RPArtExpCongestion", "RPArtExpMultiModal",
            "RPArtExpEconProsp", "RPArtExpFreight", "RPArtExpSafety", "RPArtSGRSGR",
            "RPArtExpEquity", "RPFwyExpVMT", "RPFwyExpCongestion", "RPFwyExpMultiModal",
            "RPFwyExpEconProsp", "RPFwyExpFreight", "RPFwyExpSafety",
        }
        self.assertEqual(set(dispatch.SERVICE_REGISTRY), expected)

    def test_registry_entries_point_at_real_files(self):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        for svc, (folder, module, fn) in dispatch.SERVICE_REGISTRY.items():
            path = os.path.join(repo, "gp-services", "regionalprogram", folder, module + ".py")
            self.assertTrue(os.path.isfile(path), f"{svc}: missing {path}")

    def test_nonfreeway_map_matches_capture(self):
        m = dispatch.OUTCOME_SERVICE_MAP["Non-Freeway Investment"]
        self.assertEqual(m["Safety or Security"], "RPArtExpSafety")
        self.assertEqual(m["Maintain State of Good Repair"], "RPArtSGRSGR")
        self.assertEqual(m["Benefits to the Transportation Network and Impacted Communities"],
                         "RPArtExpEquity")

    def test_freeway_map_matches_capture(self):
        m = dispatch.OUTCOME_SERVICE_MAP["Freeway Investment"]
        self.assertEqual(m["Safety or Security"], "RPFwyExpSafety")
        self.assertNotIn("Maintain State of Good Repair", m)  # freeway has no SGR


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run (PowerShell):
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_dispatch.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'dispatch'`.

- [ ] **Step 3: Write minimal implementation**

Create `testing/local_env/dispatch.py`:
```python
"""
dispatch.py — the capture-proven PPA dispatch model, as pure data + resolution.

Given a (program, projectType, selected_outcomes), reproduces the ordered
titleReport + reports[] list the live tool sends to its server workflow. No arcpy.

Data is grounded in real run captures (PPA3_Handoff/live_config_*_run.json) and the
tool documentation. See docs/superpowers/specs/2026-07-27-ppa3-test-harness-design.md.
"""

TITLE_SERVICE = "RPTitleAndGuide"

# service short-name -> (folder, entry_module, entry_function)
SERVICE_REGISTRY = {
    "RPTitleAndGuide":    ("rp_title_guidepg", "run_title_guidepg",         "make_title_guidepg_regpgm"),
    "RPArtExpVMT":        ("rp_artexp_vmt",     "run_vmt_report",            "make_vmt_report_artexp"),
    "RPArtExpCongestion": ("rp_artexp_cong",    "run_congestion_report",     "make_congestion_rpt_artexp"),
    "RPArtExpMultiModal": ("rp_artexp_mm",      "run_artexp_mm_report",      "make_mm_report_artexp"),
    "RPArtExpEconProsp":  ("rp_artexp_econ",    "run_econprosp_report",      "make_econ_report_artexp"),
    "RPArtExpFreight":    ("rp_artexp_frgt",    "run_artexp_freight_report", "make_frgt_report_artexp"),
    "RPArtExpSafety":     ("rp_artexp_saf",     "run_artexp_safety_report",  "make_safety_report_artexp"),
    "RPArtSGRSGR":        ("rp_artsgr_sgr",     "run_artsgr_sgr_report",     "make_sgr_report_artsgr"),
    "RPArtExpEquity":     ("rp_artexp_eq",      "run_equity_report",         "make_equity_rpt_artexp"),
    "RPFwyExpVMT":        ("rp_fwyexp_vmt",     "run_vmt_report",            "make_vmt_report_fwyexp"),
    "RPFwyExpCongestion": ("rp_fwyexp_cong",    "run_congestion_report",     "make_congestion_rpt_fwyexp"),
    "RPFwyExpMultiModal": ("rp_fwyexp_mm",      "run_mm_report",             "make_mm_report_fwyexp"),
    "RPFwyExpEconProsp":  ("rp_fwyexp_econ",    "run_econprosp_report",      "make_econ_report_fwyexp"),
    "RPFwyExpFreight":    ("rp_fwyexp_frgt",    "run_fwy_freight_report",    "make_freight_rept_fwyexp"),
    "RPFwyExpSafety":     ("rp_fwyexp_saf",     "run_fwyexp_safety_report",  "make_safety_report_fwyexp"),
}

# Outcome display-name -> service short-name, per projectType. Program-independent.
_NONFREEWAY = {
    "Multimodal/Transportation Choice (Reduce VMT)":                          "RPArtExpVMT",
    "Multimodal/Transportation Choice (Reduce Congestion)":                   "RPArtExpCongestion",
    "Multimodal/Transportation Choice (Encourage Multimodal Travel)":        "RPArtExpMultiModal",
    "Freight Movement (Economic Prosperity)":                                 "RPArtExpEconProsp",
    "Freight Movement (Freight Mobility)":                                     "RPArtExpFreight",
    "Safety or Security":                                                     "RPArtExpSafety",
    "Maintain State of Good Repair":                                          "RPArtSGRSGR",
    "Benefits to the Transportation Network and Impacted Communities":        "RPArtExpEquity",
}
_FREEWAY = {
    "Multimodal/Transportation Choice (Reduce VMT)":                          "RPFwyExpVMT",
    "Multimodal/Transportation Choice (Reduce Congestion)":                   "RPFwyExpCongestion",
    "Multimodal/Transportation Choice (Encourage Multimodal Travel)":        "RPFwyExpMultiModal",
    "Freight Movement (Economic Prosperity)":                                 "RPFwyExpEconProsp",
    "Freight Movement (Freight Mobility)":                                     "RPFwyExpFreight",
    "Safety or Security":                                                     "RPFwyExpSafety",
}
OUTCOME_SERVICE_MAP = {
    "Non-Freeway Investment": _NONFREEWAY,
    "Freeway Investment":     _FREEWAY,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_dispatch.py -v
```
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/dispatch.py testing/local_env/tests/test_dispatch.py
git commit -m "feat: dispatch.py service maps + registry (15 live services)"
```

---

### Task 2: `dispatch.py` — program presets & `resolve_dispatch`

**Files:**
- Modify: `testing/local_env/dispatch.py` (append)
- Test: `testing/local_env/tests/test_dispatch.py` (append)

**Interfaces:**
- Consumes: `SERVICE_REGISTRY`, `OUTCOME_SERVICE_MAP`, `TITLE_SERVICE` from Task 1.
- Produces: `PROGRAM_PRESETS: dict[str, dict[str, dict]]` (program → projectType → `{"mode": "selectable"|"fixed", "outcomes": [names]}`); `resolve_dispatch(program, project_type, selected_outcomes=None) -> list[dict]` where each dict is `{"outcome": str, "service": str, "folder": str, "module": str, "entry_function": str}`, title first.

- [ ] **Step 1: Write the failing test**

Append to `testing/local_env/tests/test_dispatch.py` (before the `if __name__` block):
```python
class TestResolveDispatch(unittest.TestCase):
    def _services(self, program, ptype, outcomes=None):
        return [d["service"] for d in dispatch.resolve_dispatch(program, ptype, outcomes)]

    def test_cmcp_nonfreeway_all_matches_capture(self):
        # live_config_cmcp_run.json: title + 8, in this order
        got = self._services("CMCP US50", "Non-Freeway Investment")
        self.assertEqual(got, [
            "RPTitleAndGuide", "RPArtExpVMT", "RPArtExpCongestion", "RPArtExpMultiModal",
            "RPArtExpEconProsp", "RPArtExpFreight", "RPArtExpSafety", "RPArtSGRSGR", "RPArtExpEquity",
        ])

    def test_atp_nonfreeway_fixed_matches_capture(self):
        # live_config_atp_run.json: title + 5, in this order; Equity deliberately excluded
        got = self._services("Active Transportation Program", "Non-Freeway Investment")
        self.assertEqual(got, [
            "RPTitleAndGuide", "RPArtExpVMT", "RPArtExpSafety", "RPArtExpMultiModal",
            "RPArtExpEconProsp", "RPArtSGRSGR",
        ])

    def test_federal_matches_capture(self):
        nf = self._services("Regional Federal Funding Program", "Non-Freeway Investment")
        self.assertEqual(len(nf), 9)               # title + full 8
        self.assertIn("RPArtExpEquity", nf)
        fw = self._services("Regional Federal Funding Program", "Freeway Investment")
        self.assertEqual(len(fw), 7)               # title + full 6
        self.assertNotIn("RPArtSGRSGR", fw)

    def test_selectable_program_filters_by_selection(self):
        got = self._services("STIP", "Non-Freeway Investment",
                             ["Safety or Security", "Multimodal/Transportation Choice (Reduce VMT)"])
        # title always first; selected outcomes follow catalog order (VMT before Safety)
        self.assertEqual(got, ["RPTitleAndGuide", "RPArtExpVMT", "RPArtExpSafety"])

    def test_fixed_program_ignores_selection(self):
        got = self._services("Active Transportation Program", "Non-Freeway Investment",
                             ["Safety or Security"])  # selection ignored for fixed mode
        self.assertEqual(len(got), 6)

    def test_resolve_returns_full_registry_fields(self):
        first = dispatch.resolve_dispatch("STIP", "Non-Freeway Investment")[0]
        self.assertEqual(first["service"], "RPTitleAndGuide")
        self.assertEqual(first["folder"], "rp_title_guidepg")
        self.assertEqual(first["entry_function"], "make_title_guidepg_regpgm")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_dispatch.py::TestResolveDispatch -v
```
Expected: FAIL — `AttributeError: module 'dispatch' has no attribute 'resolve_dispatch'`.

- [ ] **Step 3: Write minimal implementation**

Append to `testing/local_env/dispatch.py`:
```python
# --- Full ordered outcome catalogs per projectType (dict preserves insertion order) ---
_NF_CATALOG = list(_NONFREEWAY.keys())   # the full 8, in canonical order
_FW_CATALOG = list(_FREEWAY.keys())      # the full 6, in canonical order

# ATP sends a fixed, curated 5 in this exact order (from live_config_atp_run.json).
_ATP_NF_FIXED = [
    "Multimodal/Transportation Choice (Reduce VMT)",
    "Safety or Security",
    "Multimodal/Transportation Choice (Encourage Multimodal Travel)",
    "Freight Movement (Economic Prosperity)",
    "Maintain State of Good Repair",
]

# program -> projectType -> {mode, outcomes}. "selectable" = user picks (checkboxes);
# "fixed" = program predetermines the set. Capture-backed where noted in the spec.
PROGRAM_PRESETS = {
    "STIP": {
        "Non-Freeway Investment": {"mode": "selectable", "outcomes": _NF_CATALOG},
        "Freeway Investment":     {"mode": "selectable", "outcomes": _FW_CATALOG},
    },
    "CMCP US50": {
        "Non-Freeway Investment": {"mode": "selectable", "outcomes": _NF_CATALOG},   # captured
        "Freeway Investment":     {"mode": "selectable", "outcomes": _FW_CATALOG},   # inferred
    },
    "Active Transportation Program": {
        "Non-Freeway Investment": {"mode": "fixed", "outcomes": _ATP_NF_FIXED},      # captured
        # ATP freeway: confirmed n/a (non-freeway only)
    },
    "Regional Federal Funding Program": {
        "Non-Freeway Investment": {"mode": "fixed", "outcomes": _NF_CATALOG},        # captured
        "Freeway Investment":     {"mode": "fixed", "outcomes": _FW_CATALOG},        # captured
    },
}


def _registry_entry(service):
    folder, module, fn = SERVICE_REGISTRY[service]
    return {"folder": folder, "module": module, "entry_function": fn}


def resolve_dispatch(program, project_type, selected_outcomes=None):
    """Return the ordered dispatch list [{outcome, service, folder, module, entry_function}, ...],
    title first — mirroring the live tool's titleReport + reports[]."""
    if program not in PROGRAM_PRESETS:
        raise ValueError(f"unknown program {program!r}; known: {list(PROGRAM_PRESETS)}")
    if project_type not in PROGRAM_PRESETS[program]:
        raise ValueError(f"program {program!r} does not offer project type {project_type!r}")
    preset = PROGRAM_PRESETS[program][project_type]
    catalog = preset["outcomes"]

    if preset["mode"] == "fixed" or selected_outcomes is None:
        outcomes = list(catalog)
    else:
        chosen = set(selected_outcomes)
        outcomes = [o for o in catalog if o in chosen]   # preserve catalog order

    svc_map = OUTCOME_SERVICE_MAP[project_type]
    result = [dict(outcome="(title)", service=TITLE_SERVICE, **_registry_entry(TITLE_SERVICE))]
    for o in outcomes:
        svc = svc_map[o]
        result.append(dict(outcome=o, service=svc, **_registry_entry(svc)))
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_dispatch.py -v
```
Expected: PASS (all Task 1 + Task 2 tests, 10 total).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/dispatch.py testing/local_env/tests/test_dispatch.py
git commit -m "feat: PROGRAM_PRESETS + resolve_dispatch reproducing CMCP/ATP/Federal captures"
```

---

### Task 3: `dispatch.py` — `load_workflow_config` cross-check

**Files:**
- Modify: `testing/local_env/dispatch.py` (append)
- Test: `testing/local_env/tests/test_dispatch.py` (append)

**Interfaces:**
- Consumes: `OUTCOME_SERVICE_MAP` from Task 1.
- Produces: `load_workflow_config(path) -> dict[str, list[tuple[str,str]]]` (projectType → `[(outcome_name, service_short), ...]`), parsing a workflow-config JSON that may have a leading `={` and either the `stip_config.json` or `wfconfig_regpgm_*.json` shape.

- [ ] **Step 1: Write the failing test**

Append to `testing/local_env/tests/test_dispatch.py` (before `if __name__`):
```python
class TestLoadWorkflowConfig(unittest.TestCase):
    def setUp(self):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        self.stip = os.path.join(repo, "gp-services", "workflow-configs", "stip2025", "stip_config.json")

    def test_parses_stip_config_despite_equals_prefix(self):
        cfg = dispatch.load_workflow_config(self.stip)
        self.assertIn("Non-Freeway Investment", cfg)
        self.assertIn("Freeway Investment", cfg)

    def test_stip_config_agrees_with_hardcoded_map(self):
        # every (outcome -> service) parsed from the live-validated config must match our map
        cfg = dispatch.load_workflow_config(self.stip)
        for ptype, pairs in cfg.items():
            for outcome, service in pairs:
                self.assertEqual(dispatch.OUTCOME_SERVICE_MAP[ptype][outcome], service,
                                 f"{ptype} / {outcome}")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_dispatch.py::TestLoadWorkflowConfig -v
```
Expected: FAIL — `AttributeError: ... 'load_workflow_config'`.

- [ ] **Step 3: Write minimal implementation**

Append to `testing/local_env/dispatch.py` (add `import json`, `import re` at the top of the file first):
```python
import json
import re

# stip_config.json uses projectType name "Non-Freeway Investment"; older wfconfig_regpgm files
# use "Arterial or Transit Expansion" etc. We only need the two names our maps use, so we map
# the config's project "name" through this alias table; unknown names pass through unchanged.
_PTYPE_ALIASES = {
    "Non-Freeway Investment": "Non-Freeway Investment",
    "Freeway Investment": "Freeway Investment",
    "Arterial or Transit Expansion": "Non-Freeway Investment",
    "Freeway Expansion": "Freeway Investment",
}
_SVC_RE = re.compile(r"services/(\w+)/GPServer")


def load_workflow_config(path):
    """Parse a workflow-config JSON (tolerating a leading '=' and either schema shape) into
    {projectType: [(outcome_name, service_short), ...]}. Used to cross-check / regenerate
    OUTCOME_SERVICE_MAP if a live config is ever dropped in."""
    with open(path, "r", encoding="ascii", errors="ignore") as f:
        text = f.read()
    text = text.lstrip().lstrip("=").strip()
    data = json.loads(text)
    out = {}
    for proj in data.get("projects", []):
        ptype = _PTYPE_ALIASES.get(proj.get("name"), proj.get("name"))
        pairs = []
        for rep in proj.get("report", []):
            m = _SVC_RE.search(rep.get("dataUrl", ""))
            if m:
                pairs.append((rep.get("name"), m.group(1)))
        out[ptype] = pairs
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_dispatch.py -v
```
Expected: PASS (all dispatch tests, 12 total).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/dispatch.py testing/local_env/tests/test_dispatch.py
git commit -m "feat: load_workflow_config cross-check vs stip_config.json"
```

---

### Task 4: Roll `PPA3_LOCAL_CONFIG` into the 13 remaining live folders

**Files:**
- Modify (each `config_links.py`): `rp_artexp_mm`, `rp_artexp_econ`, `rp_artexp_frgt`, `rp_artexp_saf`, `rp_artsgr_sgr`, `rp_artexp_eq`, `rp_fwyexp_vmt`, `rp_fwyexp_cong`, `rp_fwyexp_mm`, `rp_fwyexp_econ`, `rp_fwyexp_frgt`, `rp_fwyexp_saf`, `rp_title_guidepg` — all under `gp-services/regionalprogram/`.

**Interfaces:**
- Consumes: nothing.
- Produces: each folder's `params`/`cfg` resolves to the local sandbox when `PPA3_LOCAL_CONFIG` is set, prod when unset. (`rp_artexp_cong` and `rp_artexp_vmt` already done — do not re-edit.)

- [ ] **Step 1: Apply the identical switch edit to each of the 13 files**

In each listed `config_links.py`, find the production config line (it reads exactly):
```python
config_dir = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig'
```
Replace it with:
```python
_PROD_CONFIG = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig'
config_dir = os.environ.get('PPA3_LOCAL_CONFIG') or _PROD_CONFIG
```
And ensure `import os` is present in that file's imports (add it under the existing `import sys` if absent). Do **not** change any other line — the `sys.path.append(config_dir)` / `import parameters as params` / yaml-load block stays as-is.

- [ ] **Step 2: Verify all 15 live folders now carry the switch**

Run (PowerShell):
```powershell
$folders = "rp_title_guidepg","rp_artexp_vmt","rp_artexp_cong","rp_artexp_mm","rp_artexp_econ","rp_artexp_frgt","rp_artexp_saf","rp_artsgr_sgr","rp_artexp_eq","rp_fwyexp_vmt","rp_fwyexp_cong","rp_fwyexp_mm","rp_fwyexp_econ","rp_fwyexp_frgt","rp_fwyexp_saf"
foreach ($f in $folders) {
  $p = "gp-services/regionalprogram/$f/config_links.py"
  $hit = Select-String -Path $p -Pattern "PPA3_LOCAL_CONFIG" -Quiet
  "{0,-20} {1}" -f $f, $(if ($hit) {"OK"} else {"MISSING"})
}
```
Expected: all 15 print `OK`.

- [ ] **Step 3: Verify local resolves local and prod resolves prod (spot-check two new folders)**

Run:
```powershell
$env:PPA3_LOCAL_CONFIG = "C:\PPA3Testing\globalconfig"
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import sys; sys.path.insert(0, r'gp-services/regionalprogram/rp_artexp_saf'); import config_links as c; assert r'PPA3Testing' in c.params.fgdb, c.params.fgdb; print('LOCAL OK', c.params.fgdb)"
Remove-Item Env:\PPA3_LOCAL_CONFIG
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import sys; sys.path.insert(0, r'gp-services/regionalprogram/rp_fwyexp_saf'); import config_links as c; assert r'Arcserverppa-svr' in c.params.fgdb, c.params.fgdb; print('PROD OK', c.params.fgdb)"
```
Expected: `LOCAL OK ...PPA3Testing...` then `PROD OK \\Arcserverppa-svr...`. (Requires VPN for the prod line; if off-VPN, skip the prod line and note it.)

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add gp-services/regionalprogram/rp_*/config_links.py
git commit -m "feat: roll PPA3_LOCAL_CONFIG switch into the 13 remaining live rp_* folders"
```

---

### Task 5: `orchestrator.py` + `run_local.py` registry integration

**Files:**
- Create: `testing/local_env/orchestrator.py`
- Modify: `testing/local_env/run_local.py` (replace `ENTRYPOINTS` with `dispatch.SERVICE_REGISTRY`)
- Test: `testing/local_env/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `dispatch.resolve_dispatch`, `dispatch.SERVICE_REGISTRY`.
- Produces: `run_report(inputs, runs_root=None, _runner=None) -> str` (path to the run folder). `inputs` keys: `program`, `project_type`, `selected_outcomes` (list or None), `project_line` (fc path), `project_name`, `jurisdiction`, `aadt`, `posted_speed`, `pci`, `email`. Writes `manifest.json`, `<service>.json`, `<service>.log`, `merged.json` into the run folder. `_runner` is an injectable callable `(service, sample_path, out_dir) -> (status, result_json_path, log_text)` for testing; default shells out to `run_local.py`.

- [ ] **Step 1: Write the failing test (mocked runner — no arcpy)**

Create `testing/local_env/tests/test_orchestrator.py`:
```python
import os
import sys
import json
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
import orchestrator


class TestRunReport(unittest.TestCase):
    def _inputs(self):
        return dict(
            program="Active Transportation Program", project_type="Non-Freeway Investment",
            selected_outcomes=None, project_line=r"C:\fake\line", project_name="t",
            jurisdiction="Sacramento", aadt=0, posted_speed=0, pci=0, email="x@y.com",
        )

    def _fake_runner(self, service, sample_path, out_dir):
        # emulate a successful service run: write a tiny result json
        p = os.path.join(out_dir, service + ".json")
        with open(p, "w") as f:
            json.dump({"service": service, "ok": True}, f)
        return ("ok", p, f"ran {service}\n")

    def test_creates_run_folder_with_manifest_and_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(self._inputs(), runs_root=tmp, _runner=self._fake_runner)
            self.assertTrue(os.path.isdir(run_dir))
            manifest = json.load(open(os.path.join(run_dir, "manifest.json")))
            # ATP non-freeway dispatches title + 5 = 6 services
            self.assertEqual(len(manifest["services"]), 6)
            self.assertTrue(all(s["status"] == "ok" for s in manifest["services"]))
            merged = json.load(open(os.path.join(run_dir, "merged.json")))
            self.assertEqual(len(merged), 6)
            self.assertIn("RPArtExpSafety", merged)

    def test_failing_service_recorded_and_run_continues(self):
        def flaky(service, sample_path, out_dir):
            if service == "RPArtExpSafety":
                return ("failed", None, "boom\n")
            return self._fake_runner(service, sample_path, out_dir)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(self._inputs(), runs_root=tmp, _runner=flaky)
            manifest = json.load(open(os.path.join(run_dir, "manifest.json")))
            statuses = {s["service"]: s["status"] for s in manifest["services"]}
            self.assertEqual(statuses["RPArtExpSafety"], "failed")
            self.assertEqual(statuses["RPArtExpVMT"], "ok")  # others still ran


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_orchestrator.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'orchestrator'`.

- [ ] **Step 3: Write `orchestrator.py`**

Create `testing/local_env/orchestrator.py`:
```python
"""
orchestrator.py — local stand-in for the PPA server workflow. Resolves the dispatch list for a
run and executes each service as an isolated ArcGIS-Pro-python subprocess (via run_local.py),
capturing status/output into out/runs/<timestamp>/. No arcpy in this process. See the design spec.
"""
import os
import sys
import json
import shutil
import datetime as dt
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dispatch

PRO_PYTHON = r"C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
RUN_LOCAL = os.path.join(HERE, "run_local.py")
DEFAULT_RUNS_ROOT = os.path.join(HERE, "out", "runs")


def _write_sample(inputs, out_dir):
    """Build the run_local sample JSON (keys match run_local's expected raw[...] fields)."""
    sample = {
        "Project_Line": inputs["project_line"],
        "Project_Name": inputs["project_name"],
        "Jurisdiction": inputs["jurisdiction"],
        "Project_Type": inputs["project_type"],
        "PerfOutcomes": "",
        "AADT": inputs["aadt"],
        "Posted_Speed_Limit": inputs["posted_speed"],
        "PCI": inputs["pci"],
        "userEmail": inputs["email"],
    }
    path = os.path.join(out_dir, "_sample.json")
    with open(path, "w") as f:
        json.dump(sample, f)
    return path


def _subprocess_runner(service, sample_path, out_dir):
    """Default runner: run run_local.py <service> <sample> in a fresh Pro-python process.
    Returns (status, result_json_path_or_None, log_text)."""
    proc = subprocess.run([PRO_PYTHON, RUN_LOCAL, service, sample_path],
                          capture_output=True, text=True)
    log = proc.stdout + "\n" + proc.stderr
    result = None
    for line in proc.stdout.splitlines():
        if line.startswith("OK -> "):
            src = line[len("OK -> "):].strip()
            dst = os.path.join(out_dir, service + ".json")
            try:
                shutil.copyfile(src, dst)
                result = dst
            except OSError:
                result = None
    status = "ok" if result else "failed"
    return (status, result, log)


def run_report(inputs, runs_root=None, _runner=None):
    runs_root = runs_root or DEFAULT_RUNS_ROOT
    runner = _runner or _subprocess_runner
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(runs_root, stamp)
    os.makedirs(run_dir, exist_ok=True)

    plan = dispatch.resolve_dispatch(inputs["program"], inputs["project_type"],
                                     inputs.get("selected_outcomes"))
    manifest = {
        "timestamp": stamp,
        "inputs": {k: v for k, v in inputs.items()},
        "services": [{"service": p["service"], "outcome": p["outcome"], "status": "pending"}
                     for p in plan],
    }
    manifest_path = os.path.join(run_dir, "manifest.json")

    def _flush():
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    _flush()

    sample_path = _write_sample(inputs, run_dir)
    merged = {}
    for i, p in enumerate(plan):
        service = p["service"]
        status, result_path, log = runner(service, sample_path, run_dir)
        with open(os.path.join(run_dir, service + ".log"), "w") as f:
            f.write(log or "")
        if result_path and os.path.isfile(result_path):
            try:
                merged[service] = json.load(open(result_path))
            except (OSError, ValueError):
                pass
        manifest["services"][i]["status"] = status
        _flush()

    with open(os.path.join(run_dir, "merged.json"), "w") as f:
        json.dump(merged, f, indent=2)
    return run_dir
```

- [ ] **Step 4: Point `run_local.py` at the shared registry**

In `testing/local_env/run_local.py`, add near the top (after `import datetime as dt`):
```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch
```
Then replace the whole `ENTRYPOINTS = { ... }` dict literal with:
```python
# subreport short-name -> (folder rel to gp-services/regionalprogram, entry module, entry function)
ENTRYPOINTS = {svc: ("regionalprogram/" + folder, module, fn)
               for svc, (folder, module, fn) in dispatch.SERVICE_REGISTRY.items()}
```
(This makes all 15 services runnable by their short-name; the rest of `run_local.py` is unchanged.)

- [ ] **Step 5: Run tests to verify they pass**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_orchestrator.py testing/local_env/tests/test_dispatch.py -v
```
Expected: PASS (orchestrator 2 + dispatch 12).

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/orchestrator.py testing/local_env/run_local.py testing/local_env/tests/test_orchestrator.py
git commit -m "feat: orchestrator.run_report (subprocess-per-service) + run_local uses SERVICE_REGISTRY"
```

---

### Task 6: Sample-line registry + Flask form

**Files:**
- Create: `testing/local_env/samples/lines.json`
- Create: `testing/local_env/webapp/app.py`
- Create: `testing/local_env/webapp/templates/form.html`
- Test: `testing/local_env/tests/test_webapp.py`

**Interfaces:**
- Consumes: `dispatch.PROGRAM_PRESETS`, `dispatch.resolve_dispatch`, `orchestrator.run_report`.
- Produces: a Flask `app` object; `GET /` renders the form; `POST /run` calls `orchestrator.run_report` and redirects to `/run/<stamp>`. `app.config["RUN_REPORT"]` is the injectable orchestrator entry (default `orchestrator.run_report`) so tests can stub it.

- [ ] **Step 1: Install Flask into the Pro env and verify**

Run (PowerShell):
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pip install flask
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import flask; print('flask', flask.__version__)"
```
Expected: prints a flask version. (Flask is pure-Python; it does not touch arcpy.)

- [ ] **Step 2: Write the sample-line registry**

Create `testing/local_env/samples/lines.json`:
```json
{
  "TestTruxelBridge": {
    "fc_path": "I:\\Projects\\Darren\\PPA_V2_GIS\\PPA_V2.gdb\\TestTruxelBridge",
    "valid_project_types": ["Non-Freeway Investment", "Freeway Investment"]
  }
}
```

- [ ] **Step 3: Write the failing test (stubbed orchestrator — no arcpy)**

Create `testing/local_env/tests/test_webapp.py`:
```python
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "webapp"))
sys.path.insert(0, os.path.dirname(HERE))
import app as webapp


class TestForm(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_form_lists_all_four_programs(self):
        html = self.client.get("/").get_data(as_text=True)
        for prog in ["STIP", "CMCP US50", "Active Transportation Program",
                     "Regional Federal Funding Program"]:
            self.assertIn(prog, html)

    def test_form_lists_sample_lines(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("TestTruxelBridge", html)

    def test_post_run_invokes_orchestrator_and_redirects(self):
        captured = {}
        def fake_run_report(inputs):
            captured.update(inputs)
            return r"C:\fake\out\runs\20260101_000000"
        webapp.app.config["RUN_REPORT"] = fake_run_report
        resp = self.client.post("/run", data={
            "program": "Active Transportation Program",
            "project_type": "Non-Freeway Investment",
            "project_line": "TestTruxelBridge",
            "project_name": "t", "jurisdiction": "Sacramento",
            "aadt": "0", "posted_speed": "0", "pci": "0", "email": "x@y.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("20260101_000000", resp.headers["Location"])
        self.assertEqual(captured["program"], "Active Transportation Program")
        self.assertEqual(captured["project_line"],
                         r"I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run test to verify it fails**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_webapp.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 5: Write `app.py` and `form.html`**

Create `testing/local_env/webapp/app.py`:
```python
"""
app.py — Flask UI for the PPA3 test harness. No arcpy: it imports dispatch (pure) and calls
orchestrator.run_report, which shells out to the Pro python per service. Run:
  & "...\arcgispro-py3\python.exe" testing\local_env\webapp\app.py   (then open http://127.0.0.1:5000)
"""
import os
import sys
import json

from flask import Flask, render_template, request, redirect, url_for, abort

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_ENV = os.path.dirname(HERE)
sys.path.insert(0, LOCAL_ENV)
import dispatch
import orchestrator

app = Flask(__name__)
app.config["RUN_REPORT"] = orchestrator.run_report
app.config["RUNS_ROOT"] = os.path.join(LOCAL_ENV, "out", "runs")

with open(os.path.join(LOCAL_ENV, "samples", "lines.json")) as f:
    LINES = json.load(f)


def _programs_json():
    """program -> {projectType -> {mode, outcomes}} for the form's dynamic JS."""
    return dispatch.PROGRAM_PRESETS


@app.route("/")
def form():
    return render_template("form.html", programs=dispatch.PROGRAM_PRESETS,
                           programs_json=json.dumps(dispatch.PROGRAM_PRESETS),
                           lines=LINES)


@app.route("/run", methods=["POST"])
def run():
    f = request.form
    line_key = f["project_line"]
    if line_key not in LINES:
        abort(400, "unknown project line")
    selected = f.getlist("outcomes") or None
    inputs = dict(
        program=f["program"], project_type=f["project_type"],
        selected_outcomes=selected, project_line=LINES[line_key]["fc_path"],
        project_name=f["project_name"], jurisdiction=f["jurisdiction"],
        aadt=int(f.get("aadt") or 0), posted_speed=int(f.get("posted_speed") or 0),
        pci=int(f.get("pci") or 0), email=f["email"],
    )
    run_dir = app.config["RUN_REPORT"](inputs)
    stamp = os.path.basename(run_dir.rstrip("/\\"))
    return redirect(url_for("run_detail", stamp=stamp))


# run_detail/history routes are added in Task 7; a stub keeps url_for happy until then.
@app.route("/run/<stamp>")
def run_detail(stamp):
    return f"run {stamp}"  # replaced in Task 7


if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

Create `testing/local_env/webapp/templates/form.html`:
```html
<!doctype html>
<title>PPA3 Test Harness</title>
<h1>PPA3 Test Harness — Run a report</h1>
<form method="post" action="/run">
  <label>Program:
    <select name="program" id="program"></select></label><br>
  <label>Project type:
    <select name="project_type" id="project_type"></select></label><br>
  <label>Project line:
    <select name="project_line">
      {% for name in lines %}<option value="{{ name }}">{{ name }}</option>{% endfor %}
    </select></label><br>
  <label>Project name: <input name="project_name" required></label><br>
  <label>Jurisdiction: <input name="jurisdiction" value="Sacramento"></label><br>
  <label>AADT: <input name="aadt" type="number" value="0"></label><br>
  <label>Posted speed: <input name="posted_speed" type="number" value="0"></label><br>
  <label>PCI: <input name="pci" type="number" value="0"></label><br>
  <label>Email: <input name="email" type="email" value="test@example.com"></label><br>
  <fieldset><legend>Performance outcomes</legend>
    <div id="outcomes"></div>
    <em id="mode-note"></em>
  </fieldset>
  <button type="submit">Run</button>
</form>
<script>
  const PROGRAMS = {{ programs_json|safe }};
  const progSel = document.getElementById("program");
  const typeSel = document.getElementById("project_type");
  const outDiv = document.getElementById("outcomes");
  const note = document.getElementById("mode-note");
  Object.keys(PROGRAMS).forEach(p => progSel.add(new Option(p, p)));
  function refreshTypes() {
    typeSel.innerHTML = "";
    Object.keys(PROGRAMS[progSel.value]).forEach(t => typeSel.add(new Option(t, t)));
    refreshOutcomes();
  }
  function refreshOutcomes() {
    const preset = PROGRAMS[progSel.value][typeSel.value];
    outDiv.innerHTML = "";
    preset.outcomes.forEach(o => {
      const id = "o_" + o.replace(/\W/g, "");
      outDiv.insertAdjacentHTML("beforeend",
        `<label><input type="checkbox" name="outcomes" value="${o}" checked> ${o}</label><br>`);
    });
    // fixed-mode: pre-checked but the dev may still uncheck (test-tool flexibility)
    note.textContent = preset.mode === "fixed"
      ? "This program's outcomes are fixed in the real tool; pre-selected here, but you may override for testing."
      : "Select the outcomes to include.";
  }
  progSel.addEventListener("change", refreshTypes);
  typeSel.addEventListener("change", refreshOutcomes);
  refreshTypes();
</script>
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_webapp.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/samples/lines.json testing/local_env/webapp/app.py testing/local_env/webapp/templates/form.html testing/local_env/tests/test_webapp.py
git commit -m "feat: Flask input form + sample-line registry, dispatch-driven outcomes"
```

---

### Task 7: Dashboard — run detail & history

**Files:**
- Modify: `testing/local_env/webapp/app.py` (replace the `run_detail` stub; add `/runs` history route)
- Create: `testing/local_env/webapp/templates/detail.html`
- Create: `testing/local_env/webapp/templates/history.html`
- Test: `testing/local_env/tests/test_webapp.py` (append)

**Interfaces:**
- Consumes: run folders written by `orchestrator.run_report` (`manifest.json`, `<service>.json`).
- Produces: `GET /runs` lists past runs; `GET /run/<stamp>` shows the per-service status table, dispatch order, and expandable raw JSON.

- [ ] **Step 1: Write the failing test (fabricated run folder — no arcpy)**

Append to `testing/local_env/tests/test_webapp.py` (before `if __name__`):
```python
import json, tempfile

class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.tmp = tempfile.mkdtemp()
        webapp.app.config["RUNS_ROOT"] = self.tmp
        run_dir = os.path.join(self.tmp, "20260101_000000")
        os.makedirs(run_dir)
        json.dump({"timestamp": "20260101_000000",
                   "inputs": {"program": "STIP", "project_type": "Non-Freeway Investment"},
                   "services": [{"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
                                {"service": "RPArtExpSafety", "outcome": "Safety or Security",
                                 "status": "failed"}]},
                  open(os.path.join(run_dir, "manifest.json"), "w"))
        json.dump({"total": 6}, open(os.path.join(run_dir, "RPTitleAndGuide.json"), "w"))

    def test_detail_shows_services_and_statuses(self):
        html = self.client.get("/run/20260101_000000").get_data(as_text=True)
        self.assertIn("RPArtExpSafety", html)
        self.assertIn("failed", html)
        self.assertIn("Safety or Security", html)

    def test_history_lists_the_run(self):
        html = self.client.get("/runs").get_data(as_text=True)
        self.assertIn("20260101_000000", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_webapp.py::TestDashboard -v
```
Expected: FAIL — detail returns the stub `run <stamp>` text (assertion on "failed" fails) and `/runs` 404s.

- [ ] **Step 3: Replace the stub route and add history in `app.py`**

In `testing/local_env/webapp/app.py`, replace the stub `run_detail` function with:
```python
def _load_run(stamp):
    run_dir = os.path.join(app.config["RUNS_ROOT"], stamp)
    mpath = os.path.join(run_dir, "manifest.json")
    if not os.path.isfile(mpath):
        return None, None
    with open(mpath) as f:
        manifest = json.load(f)
    outputs = {}
    for svc in manifest["services"]:
        jp = os.path.join(run_dir, svc["service"] + ".json")
        if os.path.isfile(jp):
            try:
                outputs[svc["service"]] = json.dumps(json.load(open(jp)), indent=2)
            except (OSError, ValueError):
                outputs[svc["service"]] = None
    return manifest, outputs


@app.route("/run/<stamp>")
def run_detail(stamp):
    manifest, outputs = _load_run(stamp)
    if manifest is None:
        abort(404)
    return render_template("detail.html", stamp=stamp, manifest=manifest, outputs=outputs)


@app.route("/runs")
def history():
    root = app.config["RUNS_ROOT"]
    stamps = sorted([d for d in os.listdir(root)
                     if os.path.isfile(os.path.join(root, d, "manifest.json"))],
                    reverse=True) if os.path.isdir(root) else []
    return render_template("history.html", stamps=stamps)
```

- [ ] **Step 4: Write the dashboard templates**

Create `testing/local_env/webapp/templates/detail.html`:
```html
<!doctype html>
<title>Run {{ stamp }}</title>
<h1>Run {{ stamp }}</h1>
<p><a href="/">&larr; new run</a> | <a href="/runs">run history</a></p>
<p><b>Program:</b> {{ manifest.inputs.program }} &mdash;
   <b>Type:</b> {{ manifest.inputs.project_type }}</p>
<h2>Dispatched services (in order)</h2>
<table border="1" cellpadding="6">
  <tr><th>#</th><th>Service</th><th>Outcome</th><th>Status</th><th>Output</th></tr>
  {% for s in manifest.services %}
  <tr>
    <td>{{ loop.index }}</td>
    <td>{{ s.service }}</td>
    <td>{{ s.outcome }}</td>
    <td>{{ s.status }}</td>
    <td>
      {% if outputs.get(s.service) %}
        <details><summary>JSON</summary><pre>{{ outputs[s.service] }}</pre></details>
      {% else %}&mdash;{% endif %}
    </td>
  </tr>
  {% endfor %}
</table>
```

Create `testing/local_env/webapp/templates/history.html`:
```html
<!doctype html>
<title>PPA3 Test Harness — Run history</title>
<h1>Run history</h1>
<p><a href="/">&larr; new run</a></p>
<ul>
  {% for s in stamps %}<li><a href="/run/{{ s }}">{{ s }}</a></li>{% endfor %}
  {% if not stamps %}<li><em>no runs yet</em></li>{% endif %}
</ul>
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_webapp.py -v
```
Expected: PASS (form 3 + dashboard 2 = 5).

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/webapp/app.py testing/local_env/webapp/templates/detail.html testing/local_env/webapp/templates/history.html testing/local_env/tests/test_webapp.py
git commit -m "feat: run-detail + history dashboard (per-service status, dispatch order, raw JSON)"
```

---

### Task 8 (OPTIONAL): Local archive tables for clean end-to-end runs

**Files:**
- Create: `testing/local_env/build_run_tables.py`

**Interfaces:**
- Consumes (read-only, VPN required): production `\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb`.
- Produces: empty `project_master` + one table per live `rp_*` service in `C:\PPA3Testing\PPA3Testing_run.gdb`, with schemas copied from prod — so the log-write step succeeds locally instead of erroring.

- [ ] **Step 1: Write the schema-copy script**

Create `testing/local_env/build_run_tables.py`:
```python
"""
build_run_tables.py — OPTIONAL. Read (read-only) the real schemas of project_master and the
rp_* archive tables from the production PPA3_run_data.gdb and create EMPTY copies in the local
PPA3Testing_run.gdb, so a full local run completes cleanly through the archive log-write step.
Read-only against prod; writes only to the local sandbox. Run via PowerShell with the Pro python.
"""
import os
import arcpy

PROD_RUN_GDB = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb"
LOCAL_RUN_GDB = r"C:\PPA3Testing\PPA3Testing_run.gdb"

# tables to mirror: project_master + one per live rp_* service (folder names)
TABLES = [
    "project_master",
    "rp_title_guidepg", "rp_artexp_vmt", "rp_artexp_cong", "rp_artexp_mm", "rp_artexp_econ",
    "rp_artexp_frgt", "rp_artexp_saf", "rp_artsgr_sgr", "rp_artexp_eq",
    "rp_fwyexp_vmt", "rp_fwyexp_cong", "rp_fwyexp_mm", "rp_fwyexp_econ", "rp_fwyexp_frgt",
    "rp_fwyexp_saf",
]


def main():
    if not arcpy.Exists(LOCAL_RUN_GDB):
        raise SystemExit(f"local run gdb missing: {LOCAL_RUN_GDB} (run build_test_gdb.py first)")
    for name in TABLES:
        src = os.path.join(PROD_RUN_GDB, name)
        if not arcpy.Exists(src):
            print(f"  !! not in prod, skipped: {name}")
            continue
        dst = os.path.join(LOCAL_RUN_GDB, name)
        if arcpy.Exists(dst):
            arcpy.management.Delete(dst)
        # CreateTable with a template copies the schema WITHOUT copying rows
        arcpy.management.CreateTable(LOCAL_RUN_GDB, name, template=src)
        print(f"  created empty {name} (schema from prod)")
    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it (VPN required) and verify tables exist empty**

Run (PowerShell):
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing/local_env/build_run_tables.py
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -c "import arcpy; arcpy.env.workspace=r'C:\PPA3Testing\PPA3Testing_run.gdb'; print(sorted(arcpy.ListTables())); print('project_master rows:', int(arcpy.management.GetCount('project_master')[0]))"
```
Expected: the table list includes `project_master` and the `rp_*` tables; `project_master rows: 0`.

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/build_run_tables.py
git commit -m "feat: optional build_run_tables.py — mirror prod archive schemas into local run gdb"
```

---

### Task 9: End-to-end validation + README

**Files:**
- Modify: `testing/local_env/README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a documented, verified end-to-end loop.

- [ ] **Step 1: Run the full no-arcpy suite**

Run:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests -v
```
Expected: PASS (dispatch 12 + orchestrator 2 + webapp 5 = 19).

- [ ] **Step 2: Launch the app and run one report end-to-end (VPN + local sandbox)**

Run (PowerShell), then open http://127.0.0.1:5000:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing/local_env/webapp/app.py
```
In the browser: select **CMCP US50** / **Non-Freeway Investment** / **TestTruxelBridge**, leave outcomes all-checked, Run. Then repeat with **Active Transportation Program** (its 5 fixed outcomes). Verify each run's detail page lists the expected dispatch order (CMCP = title+8; ATP = title+5) and that at least the density/land-use services show output JSON. (Congestion/NPMRDS services may show null values for `TestTruxelBridge` — that is incidental, not a failure, as documented in the Tier-1 README §9.)

- [ ] **Step 3: Confirm the run folder contents**

Run:
```powershell
Get-ChildItem "testing\local_env\out\runs" | Sort-Object Name -Descending | Select-Object -First 1 | ForEach-Object { Get-ChildItem $_.FullName | Select-Object Name }
```
Expected: `manifest.json`, `merged.json`, per-service `.json`/`.log` files.

- [ ] **Step 4: Update the README**

Append a "Phase 1 orchestrator" section to `testing/local_env/README.md` documenting: launching the web app (the PowerShell command above), the form fields, that dispatch is driven by `dispatch.resolve_dispatch` (config-validated against `stip_config.json` + the live captures), the four-program preset model, where runs land (`out/runs/<stamp>/`), the optional `build_run_tables.py` step, and that Phase 2 (rendering the report from `merged.json`) is a separate future effort.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/tenoru/Downloads/data_layer_update"
git add testing/local_env/README.md
git commit -m "docs: document Phase-1 orchestrator + web app in local_env README"
```

---

## Self-Review Notes

- **Spec coverage:** dispatch.py (spec §Components 1) → Tasks 1–3; config roll-out (§Component 2) → Task 4; orchestrator (§Component 3) → Task 5; sample lines (§Component 4) → Task 6; Flask form + dashboard (§Component 5) → Tasks 6–7; error handling (§Error handling) → Task 5 tests (failed-service-continues); testing (§Testing) → Tasks 1–7 tests; archive-table option (§Open items 4) → Task 8; golden refs (§Golden references) → recorded in spec, exercised in Task 9. Federal one-reportName/two-preset model → PROGRAM_PRESETS in Task 2.
- **Type consistency:** `resolve_dispatch` returns `list[dict]` with keys `outcome/service/folder/module/entry_function` (Task 2), consumed by `orchestrator.run_report` (Task 5) and the dashboard (Task 7). `run_report(inputs, runs_root=None, _runner=None) -> run_dir` used by `app.py` (Task 6) via `app.config["RUN_REPORT"]`. `SERVICE_REGISTRY` values are `(folder, module, fn)` tuples used identically in Tasks 1/2/5.
- **Deferred deliberately:** Phase 2 (report rendering), `cdp_*` roll-out, the 4 non-live folders, parallel dispatch, CMCP-Freeway run capture.
