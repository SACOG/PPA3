# PPA3 Phase 2 Report Renderer (ATP v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render a full ATP-path PPA report (title page + boilerplate + all 5 ATP outcome
sections) as a browser-viewable HTML file, driven by a Phase-1 harness run's `merged.json`,
visually matched to the golden `report transportion_test.pdf`.

**Architecture:** A new `testing/local_env/reporting/` module: hand-authored per-service YAML
layout configs (subtitles/questions/footnotes transcribed from the golden PDF) drive a generic
Jinja2 template + a single reusable Chart.js grouped-bar-chart component. `render.py` reads a
harness run's `manifest.json` + `merged.json`, resolves dispatch order via the existing
`dispatch.py`, and writes one `report.html`.

**Tech Stack:** Python (Jinja2, PyYAML — both already present in `arcgispro-py3`; this module
itself needs neither arcpy nor a network connection, so it runs under plain `python3`, same as
the existing no-arcpy test suite). Chart.js v4 (vendored UMD build, MIT license) for charts.

**Scope note (read before starting):** This plan implements build-order steps 1–4 of
`docs/superpowers/specs/2026-07-30-ppa3-phase2-report-renderer-design.md` — the **ATP path only**
(Title, VMT, Safety, MultiModal, EconProsp, SGR), through a real end-to-end HTML render and two
forms of validation. Steps 5–7 (CMCP-only outcomes — Congestion/Freight/Equity — and the
Playwright PDF export) depend on artifacts that don't exist yet (a CMCP full-8-outcome local
harness run; golden-PDF text for those 3 sections hasn't been transcribed) and are a **separate,
follow-on plan** written after this one ships and is reviewed. This mirrors the design's own
"ATP-first then CMCP" build order — it is a sequencing decision, not a scope cut.

**Correction to the design spec, discovered while planning (flag to the user):** the design's
"golden fidelity check" step assumed `atp_ppa_run_submit.har` contains a captured result body for
the *same project* as each golden PDF. Direct inspection (Task 11) shows the HAR contains exactly
one fully-captured run — CMCP US50, project "random proj", 8 outcomes — which matches **neither**
golden PDF's project ("Trell Test" / "Active Transportation Program Report Test"). Project-level
**numbers** in that capture cannot be checked against a golden PDF's printed numbers. What it
*can* validate: **structure** (every field/chart name a layout config references exists in a real
prod-captured payload, not just our local harness output) — since GP-service output shape doesn't
depend on which project ran. Task 11 implements this corrected, structural version of the check.
Numeric/visual fidelity to the goldens is instead confirmed by a manual side-by-side read (Task 12).

## Global Constraints

- Repo: `C:\Users\tenoru\Downloads\data_layer_update`, branch `data_layer_update` — never `main`.
- The `reporting/` module has **zero arcpy dependency** and must never import arcpy, touch the
  SDE, or require the ArcGIS Pro python env. Tests run via `pytest testing/local_env/tests -v`
  under plain `python3`, matching the existing no-arcpy suite.
- Chart.js is **vendored** (a local file in `static/`), not loaded from a CDN — the rendered
  report must open and render fully offline.
- Card copy (subtitles, questions, footnotes, notes) must be **transcribed verbatim** from the
  golden PDFs, not paraphrased — these strings have no other source of truth.
- One missing/failed section or card must never crash the whole render — always degrade to a
  visible "(no data)" / "section unavailable" placeholder (mirrors Phase 1's per-service fault
  tolerance).
- `RPArtExpSafety`'s `charts["Collision Types"]` / `charts["Primary Collision Factors"]` are
  **intentionally excluded** from the v1 layout — confirmed (Task 11) to be Task-5 branch-only
  additions absent from the real prod-captured payload and from the golden PDF.
- Map/heat-map image fields (`*Image Url`) render as a placeholder box in v1 — never block
  rendering when `null` (always the case locally; per Phase-1 memory, no `.aprx` is staged).

---

## File Structure

```
testing/local_env/reporting/
  __init__.py
  cards.py                    # pure functions: layout-config card spec + service data -> template context
  layout_loader.py            # load_layout(service) -> dict | None, parses layout/<service>.yaml
  render.py                   # load_run, build_project_context, build_sections, render_report, CLI
  extract_har_fixture.py      # provenance script: HAR -> a real prod-shape manifest/merged fixture
  layout/
    RPArtExpVMT.yaml
    RPArtExpSafety.yaml
    RPArtExpMultiModal.yaml
    RPArtExpEconProsp.yaml
    RPArtSGRSGR.yaml
  templates/
    report.html.j2
    title_page.html.j2
    section.html.j2
    card_kpi.html.j2
    card_table.html.j2
    card_chart.html.j2
    card_image.html.j2
    boilerplate/
      using_this_report.html
      atp_intro.html
  static/
    report.css
    chart.umd.min.js           # vendored, not committed by hand-typing — downloaded in Task 1
testing/local_env/tests/
  test_reporting_cards.py      # Task 2
  test_reporting_render.py     # Task 3, 4, 10
  test_reporting_layouts.py    # Task 5-9
  test_reporting_har_fixture.py  # Task 11
  fixtures/
    reporting/
      har_prod_capture/
        manifest.json           # committed output of extract_har_fixture.py (Task 11)
        merged.json
```

---

### Task 1: Scaffold the reporting module + vendor Chart.js + base CSS

**Files:**
- Create: `testing/local_env/reporting/__init__.py` (empty)
- Create: `testing/local_env/reporting/static/report.css`
- Create: `testing/local_env/reporting/static/chart.umd.min.js` (downloaded, not hand-typed)
- Test: `testing/local_env/tests/test_reporting_cards.py` (placeholder import-only test; real
  card tests land in Task 2)

**Interfaces:**
- Produces: the `testing/local_env/reporting/` package exists and is importable; `static/`
  contains a working Chart.js build and the base stylesheet every later template links to.

- [ ] **Step 1: Confirm jinja2 and pyyaml are available to plain `python3`**

Run: `python3 -c "import jinja2, yaml; print(jinja2.__version__, yaml.__version__)"`

If this fails with `ModuleNotFoundError`, install them (additive, matches the precedent of
pip-installing geopandas/rasterio into `arcgispro-py3` for Phase 1):

```bash
python3 -m pip install jinja2 pyyaml
```

Expected after install: prints two version strings, e.g. `3.1.6 6.0.2`.

- [ ] **Step 2: Create the package skeleton**

```bash
mkdir -p testing/local_env/reporting/static testing/local_env/reporting/layout testing/local_env/reporting/templates/boilerplate testing/local_env/tests/fixtures/reporting/har_prod_capture
touch testing/local_env/reporting/__init__.py
```

- [ ] **Step 3: Vendor Chart.js v4.4.4 (UMD build, MIT license)**

```powershell
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js" -OutFile "testing\local_env\reporting\static\chart.umd.min.js"
```

Verify it downloaded correctly:

```powershell
(Get-Item "testing\local_env\reporting\static\chart.umd.min.js").Length
Select-String -Path "testing\local_env\reporting\static\chart.umd.min.js" -Pattern "Chart" -SimpleMatch -Quiet
```

Expected: file size > 150000 (bytes); the `Select-String` check prints `True`.

If this machine has no internet access at implementation time, download
`chart.umd.min.js` from `https://www.jsdelivr.com/package/npm/chart.js?version=4.4.4` (Files tab
→ `dist/chart.umd.min.js`) on any machine with access and copy it into
`testing/local_env/reporting/static/chart.umd.min.js` — this is a one-time, version-pinned asset,
not something that needs to be re-fetched per run.

- [ ] **Step 4: Write the base stylesheet**

Create `testing/local_env/reporting/static/report.css`:

```css
:root {
  --ppa-navy: #1b3a5c;
  --ppa-accent: #2e75b6;
  --ppa-border: #d0d7de;
  --ppa-text: #1f2328;
  --ppa-muted: #57606a;
}
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", Arial, sans-serif;
  color: var(--ppa-text);
  margin: 0;
  padding: 0 2rem 4rem;
  max-width: 860px;
}
h1.report-title, .title-page h1 {
  color: var(--ppa-navy);
  border-bottom: 3px solid var(--ppa-accent);
  padding-bottom: 0.5rem;
}
.outcome-section {
  page-break-before: always;
  padding-top: 1rem;
}
.outcome-section h1 {
  color: var(--ppa-navy);
  font-size: 1.4rem;
  border-bottom: 2px solid var(--ppa-border);
  padding-bottom: 0.3rem;
}
.card {
  border: 1px solid var(--ppa-border);
  border-radius: 6px;
  padding: 1rem 1.25rem;
  margin: 1rem 0;
  page-break-inside: avoid;
}
.card h2 { font-size: 1.05rem; margin: 0 0 0.25rem; }
.card .sub-outcome {
  font-weight: 600; color: var(--ppa-accent); margin: 0 0 0.25rem;
  text-transform: uppercase; font-size: 0.8rem;
}
.card .question { font-style: italic; color: var(--ppa-muted); margin: 0 0 0.75rem; }
.card .note {
  font-size: 0.85rem; background: #f6f8fa; border-left: 3px solid var(--ppa-accent);
  padding: 0.5rem 0.75rem; margin: 0.5rem 0; white-space: pre-line;
}
.card .footnote { font-size: 0.75rem; color: var(--ppa-muted); margin-top: 0.75rem; white-space: pre-line; }
.card .no-data, .section-unavailable { color: #b42318; font-style: italic; }
.card .kpi-value { font-size: 2rem; font-weight: 700; color: var(--ppa-navy); margin: 0.25rem 0; }
.card table { border-collapse: collapse; width: 100%; margin-top: 0.5rem; }
.card table th, .card table td { text-align: left; padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--ppa-border); }
.card .chart-canvas { max-height: 320px; }
.card .axis-label { font-size: 0.8rem; color: var(--ppa-muted); text-align: center; margin-top: 0.25rem; }
.card .table-label { font-weight: 600; margin: 0 0 0.25rem; }
.map-placeholder {
  border: 1px dashed var(--ppa-border); color: var(--ppa-muted); text-align: center;
  padding: 2rem; margin: 1rem 0; font-size: 0.85rem;
}
.card img { max-width: 100%; border: 1px solid var(--ppa-border); border-radius: 4px; }
.summary-table th { text-align: left; padding-right: 1rem; color: var(--ppa-muted); font-weight: 600; }
.summary-table td { padding: 0.2rem 0; }
.report-generated { font-size: 0.85rem; color: var(--ppa-muted); margin-top: 1rem; }
.boilerplate h2 { color: var(--ppa-navy); font-size: 1.1rem; margin-top: 1.5rem; }
.atp-intro table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
.atp-intro th, .atp-intro td {
  border: 1px solid var(--ppa-border); padding: 0.5rem; vertical-align: top; font-size: 0.85rem;
}
.atp-intro th { background: #f6f8fa; }
```

- [ ] **Step 5: Placeholder test file so pytest collects the new suite cleanly**

Create `testing/local_env/tests/test_reporting_cards.py`:

```python
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards  # noqa: E402  (import-only smoke check; real tests in Task 2)


def test_cards_module_imports():
    assert hasattr(cards, "__name__")
```

This will fail until Task 2 creates `cards.py` — that's expected; it's a marker for Task 2 to
complete, not a real test yet.

- [ ] **Step 6: Run to confirm the scaffold + vendored asset are correct so far**

Run: `python3 -c "import os; p='testing/local_env/reporting/static/chart.umd.min.js'; print(os.path.getsize(p))"`
Expected: a number > 150000, no traceback.

- [ ] **Step 7: Commit**

```bash
git add testing/local_env/reporting/__init__.py testing/local_env/reporting/static/report.css testing/local_env/reporting/static/chart.umd.min.js testing/local_env/tests/test_reporting_cards.py
git commit -m "reporting: scaffold module, vendor Chart.js, base CSS"
```

---

### Task 2: `cards.py` — generic kpi/table/chart/image card builders

**Files:**
- Create: `testing/local_env/reporting/cards.py`
- Modify: `testing/local_env/tests/test_reporting_cards.py` (replace the Task-1 placeholder)

**Interfaces:**
- Consumes: nothing outside stdlib (pure functions over plain dicts).
- Produces (used by Task 3's templates and Task 5-9's layout configs):
  - `build_kpi_card(card_cfg: dict, service_data: dict) -> dict` — keys: `type="kpi"`,
    `sub_outcome`, `subtitle`, `question`, `note`, `footnote`, `missing: bool`, `value_display: str`
  - `build_table_card(card_cfg: dict, service_data: dict) -> dict` — keys: `type="table"`,
    `subtitle`, `question`, `label`, `footnote`, `missing: bool`,
    `rows: list[{"label": str, "value_display": str}]`
  - `build_chart_card(card_cfg: dict, service_data: dict) -> dict` — keys: `type="chart"`,
    `sub_outcome`, `subtitle`, `question`, `note`, `y_label`, `footnote`, `missing: bool`,
    `chart_json: str` (JSON-encoded `{"categories": [...], "series": [{"label", "data"}]}`)
  - `build_image_card(card_cfg: dict, service_data: dict) -> dict` — keys: `type="image"`,
    `caption`, `url` (may be `None` — that's expected locally, not an error), `missing: bool`
    (true only if the field is structurally absent from `service_data`, not merely null)
  - `build_card(card_cfg: dict, service_data: dict) -> dict` — dispatches on `card_cfg["type"]`
  - `build_section(layout_cfg: dict, service_data: dict) -> dict` — keys: `service`,
    `section_title`, `unavailable=False`, `cards: list[dict]`

- [ ] **Step 1: Write the failing tests**

Replace `testing/local_env/tests/test_reporting_cards.py`:

```python
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards


class TestFormatValue(unittest.TestCase):
    def test_percent_formats_fraction(self):
        self.assertEqual(cards._format_value(0.3333, "percent"), "33.3%")

    def test_number_formats_float_two_decimals(self):
        self.assertEqual(cards._format_value(74.91748017650224, "number"), "74.92")

    def test_number_formats_int_with_commas(self):
        self.assertEqual(cards._format_value(15000, "number"), "15,000")

    def test_string_value_passes_through(self):
        self.assertEqual(cards._format_value("0", "number"), "0")

    def test_none_is_no_data(self):
        self.assertEqual(cards._format_value(None, "number"), "(no data)")


class TestBuildKpiCard(unittest.TestCase):
    def test_present_value(self):
        cfg = {"source": "Total collisions", "subtitle": "Total Collisions", "question": "Q?"}
        data = {"Total collisions": 12}
        card = cards.build_kpi_card(cfg, data)
        self.assertEqual(card["type"], "kpi")
        self.assertFalse(card["missing"])
        self.assertEqual(card["value_display"], "12")
        self.assertEqual(card["subtitle"], "Total Collisions")
        self.assertEqual(card["question"], "Q?")

    def test_missing_value_flagged(self):
        cfg = {"source": "Not There"}
        card = cards.build_kpi_card(cfg, {})
        self.assertTrue(card["missing"])
        self.assertEqual(card["value_display"], "(no data)")


class TestBuildTableCard(unittest.TestCase):
    def test_rows_built_in_row_labels_order(self):
        cfg = {
            "source": "Collisions per 100 million VMT",
            "row_labels": {
                "Project": "On project segment*",
                "Community Type": "Within community type",
                "Region": "Within region",
            },
        }
        data = {"Collisions per 100 million VMT": {"Project": -1.0, "Community Type": 140.4, "Region": 95.4}}
        card = cards.build_table_card(cfg, data)
        self.assertFalse(card["missing"])
        self.assertEqual(
            [r["label"] for r in card["rows"]],
            ["On project segment*", "Within community type", "Within region"],
        )
        self.assertEqual(card["rows"][0]["value_display"], "-1.00")

    def test_missing_source_flagged_no_rows(self):
        cfg = {"source": "Nope", "row_labels": {"Project": "Project"}}
        card = cards.build_table_card(cfg, {})
        self.assertTrue(card["missing"])
        self.assertEqual(card["rows"], [])

    def test_percent_format(self):
        cfg = {
            "source": "Bike lanes and paths as share of total road miles",
            "row_labels": {"Within 0.25mi": "Within 0.25mi of project"},
            "value_format": "percent",
        }
        data = {"Bike lanes and paths as share of total road miles": {"Within 0.25mi": 0.44}}
        card = cards.build_table_card(cfg, data)
        self.assertEqual(card["rows"][0]["value_display"], "44.0%")


class TestBuildChartCard(unittest.TestCase):
    def test_categories_and_series_extracted_in_feature_order(self):
        cfg = {
            "source_chart": "Jobs and Dwelling",
            "x_field": "year",
            "series": [{"field": "jobs", "label": "Jobs"}, {"field": "dwellingUnits", "label": "Dwelling Units"}],
        }
        data = {
            "charts": {
                "Jobs and Dwelling": {
                    "title": "t",
                    "features": [
                        {"attributes": {"year": "2020", "jobs": 1612, "dwellingUnits": 3147}},
                        {"attributes": {"year": "2035", "jobs": 2303, "dwellingUnits": 4516}},
                    ],
                }
            }
        }
        card = cards.build_chart_card(cfg, data)
        self.assertFalse(card["missing"])
        spec = json.loads(card["chart_json"])
        self.assertEqual(spec["categories"], ["2020", "2035"])
        self.assertEqual(spec["series"][0], {"label": "Jobs", "data": [1612, 2303]})
        self.assertEqual(spec["series"][1], {"label": "Dwelling Units", "data": [3147, 4516]})

    def test_missing_chart_flagged(self):
        cfg = {"source_chart": "Nope", "x_field": "year", "series": [{"field": "jobs", "label": "Jobs"}]}
        card = cards.build_chart_card(cfg, {"charts": {}})
        self.assertTrue(card["missing"])
        spec = json.loads(card["chart_json"])
        self.assertEqual(spec["categories"], [])


class TestBuildImageCard(unittest.TestCase):
    def test_null_url_is_not_missing(self):
        # A present-but-null Image Url (the normal local case, no .aprx staged) must NOT be
        # flagged "missing" -- that would falsely fail every image card in every local run.
        card = cards.build_image_card({"source": "Bikeway Image Url", "caption": "Bikeway Map"}, {"Bikeway Image Url": None})
        self.assertIsNone(card["url"])
        self.assertFalse(card["missing"])
        self.assertEqual(card["caption"], "Bikeway Map")

    def test_real_url_passthrough(self):
        card = cards.build_image_card({"source": "Bikeway Image Url"}, {"Bikeway Image Url": "https://example/x.png"})
        self.assertEqual(card["url"], "https://example/x.png")
        self.assertFalse(card["missing"])

    def test_structurally_absent_field_is_missing(self):
        card = cards.build_image_card({"source": "Bikeway Image Url"}, {})
        self.assertTrue(card["missing"])


class TestBuildCardDispatch(unittest.TestCase):
    def test_dispatches_by_type(self):
        card = cards.build_card({"type": "kpi", "source": "ADT"}, {"ADT": 15000})
        self.assertEqual(card["type"], "kpi")


class TestBuildSection(unittest.TestCase):
    def test_builds_section_with_cards_in_order(self):
        layout = {
            "service": "RPArtSGRSGR",
            "section_title": "Maintain State of Good Repair",
            "cards": [
                {"type": "kpi", "source": "Pavement Condition Index", "subtitle": "PCI"},
                {"type": "kpi", "source": "ADT", "subtitle": "ADT"},
            ],
        }
        data = {"Pavement Condition Index": 70, "ADT": 15000}
        section = cards.build_section(layout, data)
        self.assertEqual(section["service"], "RPArtSGRSGR")
        self.assertFalse(section["unavailable"])
        self.assertEqual([c["subtitle"] for c in section["cards"]], ["PCI", "ADT"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_cards.py -v`
Expected: `ModuleNotFoundError` or `AttributeError` — `cards.py` doesn't exist yet.

- [ ] **Step 3: Write `cards.py`**

Create `testing/local_env/reporting/cards.py`:

```python
"""cards.py — pure functions that turn a layout-config "card" spec plus a service's
merged.json data into the context dict each card_*.html.j2 template renders. No I/O, no
arcpy — every function here is testable with synthetic dicts alone.
"""

import json


def _format_value(value, fmt="number"):
    if value is None:
        return "(no data)"
    if fmt == "percent" and isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    if fmt == "number" and isinstance(value, float):
        return f"{value:,.2f}"
    if fmt == "number" and isinstance(value, int):
        return f"{value:,}"
    return str(value)


def build_kpi_card(card_cfg, service_data):
    raw_value = service_data.get(card_cfg["source"])
    return {
        "type": "kpi",
        "sub_outcome": card_cfg.get("sub_outcome"),
        "subtitle": card_cfg.get("subtitle"),
        "question": card_cfg.get("question"),
        "note": card_cfg.get("note"),
        "footnote": card_cfg.get("footnote"),
        "missing": raw_value is None,
        "value_display": _format_value(raw_value, card_cfg.get("value_format", "number")),
    }


def build_table_card(card_cfg, service_data):
    raw = service_data.get(card_cfg["source"])
    missing = raw is None
    fmt = card_cfg.get("value_format", "number")
    rows = []
    if not missing:
        for key, label in card_cfg["row_labels"].items():
            rows.append({"label": label, "value_display": _format_value(raw.get(key), fmt)})
    return {
        "type": "table",
        "subtitle": card_cfg.get("subtitle"),
        "question": card_cfg.get("question"),
        "label": card_cfg.get("label"),
        "footnote": card_cfg.get("footnote"),
        "missing": missing,
        "rows": rows,
    }


def build_chart_card(card_cfg, service_data):
    charts = service_data.get("charts", {})
    raw = charts.get(card_cfg["source_chart"])
    missing = raw is None
    categories = []
    series_data = {s["field"]: [] for s in card_cfg["series"]}
    if not missing:
        for feature in raw["features"]:
            attrs = feature["attributes"]
            categories.append(str(attrs.get(card_cfg["x_field"])))
            for s in card_cfg["series"]:
                series_data[s["field"]].append(attrs.get(s["field"]))
    chart_spec = {
        "categories": categories,
        "series": [
            {"label": s["label"], "data": series_data[s["field"]]}
            for s in card_cfg["series"]
        ],
    }
    return {
        "type": "chart",
        "sub_outcome": card_cfg.get("sub_outcome"),
        "subtitle": card_cfg.get("subtitle"),
        "question": card_cfg.get("question"),
        "note": card_cfg.get("note"),
        "y_label": card_cfg.get("y_label"),
        "footnote": card_cfg.get("footnote"),
        "missing": missing,
        "chart_json": json.dumps(chart_spec),
    }


def build_image_card(card_cfg, service_data):
    # "missing" means the field is structurally absent (a layout-config wiring bug), not that
    # its value happens to be null -- Image Url fields are legitimately null locally (no .aprx
    # staged) without that being an error, so a plain None-check would misclassify every image
    # card in every local run as "missing".
    return {
        "type": "image",
        "caption": card_cfg.get("caption"),
        "url": service_data.get(card_cfg["source"]),
        "missing": card_cfg["source"] not in service_data,
    }


_BUILDERS = {
    "kpi": build_kpi_card,
    "table": build_table_card,
    "chart": build_chart_card,
    "image": build_image_card,
}


def build_card(card_cfg, service_data):
    return _BUILDERS[card_cfg["type"]](card_cfg, service_data)


def build_section(layout_cfg, service_data):
    return {
        "service": layout_cfg["service"],
        "section_title": layout_cfg["section_title"],
        "unavailable": False,
        "cards": [build_card(c, service_data) for c in layout_cfg["cards"]],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_cards.py -v`
Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add testing/local_env/reporting/cards.py testing/local_env/tests/test_reporting_cards.py
git commit -m "reporting: add generic kpi/table/chart/image card builders"
```

---

### Task 3: Templates + `render.py` skeleton — generic section rendering end-to-end

**Files:**
- Create: `testing/local_env/reporting/templates/report.html.j2`
- Create: `testing/local_env/reporting/templates/section.html.j2`
- Create: `testing/local_env/reporting/templates/card_kpi.html.j2`
- Create: `testing/local_env/reporting/templates/card_table.html.j2`
- Create: `testing/local_env/reporting/templates/card_chart.html.j2`
- Create: `testing/local_env/reporting/templates/card_image.html.j2`
- Create: `testing/local_env/reporting/render.py`
- Create: `testing/local_env/tests/test_reporting_render.py`

**Interfaces:**
- Consumes: `cards.build_section` (Task 2).
- Produces (used by Task 4 and Task 10):
  - `render.py: render_html(sections: list[dict], project_title: str) -> str` — renders the full
    HTML document from an already-built `sections` list (no file I/O; pure string in, string out).
    Task 4 will add `build_project_context`/`build_sections`/`render_report` around this.

- [ ] **Step 1: Write the failing test**

Create `testing/local_env/tests/test_reporting_render.py`:

```python
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, render


class TestRenderHtmlSkeleton(unittest.TestCase):
    def test_renders_section_titles_and_chart_canvas(self):
        layout = {
            "service": "RPArtSGRSGR",
            "section_title": "Maintain State of Good Repair",
            "cards": [
                {"type": "kpi", "source": "ADT", "subtitle": "Average Daily Traffic (ADT)"},
                {
                    "type": "chart",
                    "source_chart": "Jobs and Dwelling",
                    "x_field": "year",
                    "series": [{"field": "jobs", "label": "Jobs"}],
                },
            ],
        }
        data = {"ADT": 15000, "charts": {"Jobs and Dwelling": {"features": [
            {"attributes": {"year": "2020", "jobs": 100}},
        ]}}}
        section = cards.build_section(layout, data)
        html = render.render_html([section], project_title="Test Project")

        self.assertIn("Test Project", html)
        self.assertIn("Maintain State of Good Repair", html)
        self.assertIn("Average Daily Traffic (ADT)", html)
        self.assertIn("15,000", html)
        self.assertIn('class="chart-canvas"', html)
        self.assertIn("chart.umd.min.js", html)

    def test_unavailable_section_renders_placeholder(self):
        section = {"service": "RPArtExpEquity", "section_title": "Equity", "unavailable": True, "cards": []}
        html = render.render_html([section], project_title="Test Project")
        self.assertIn("section-unavailable", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py -v`
Expected: `ModuleNotFoundError: No module named 'reporting.render'` (or `ImportError`).

- [ ] **Step 3: Write the card partial templates**

Create `testing/local_env/reporting/templates/card_kpi.html.j2`:

```jinja
<div class="card card-kpi">
  {% if card.sub_outcome %}<p class="sub-outcome">{{ card.sub_outcome }}</p>{% endif %}
  {% if card.subtitle %}<h2>{{ card.subtitle }}</h2>{% endif %}
  {% if card.question %}<p class="question">{{ card.question }}</p>{% endif %}
  {% if card.note %}<p class="note">{{ card.note }}</p>{% endif %}
  {% if card.missing %}
    <p class="no-data">(no data)</p>
  {% else %}
    <p class="kpi-value">{{ card.value_display }}</p>
  {% endif %}
  {% if card.footnote %}<p class="footnote">{{ card.footnote }}</p>{% endif %}
</div>
```

Create `testing/local_env/reporting/templates/card_table.html.j2`:

```jinja
<div class="card card-table">
  {% if card.subtitle %}<h2>{{ card.subtitle }}</h2>{% endif %}
  {% if card.question %}<p class="question">{{ card.question }}</p>{% endif %}
  {% if card.label %}<p class="table-label">{{ card.label }}</p>{% endif %}
  {% if card.missing %}
    <p class="no-data">(no data)</p>
  {% else %}
  <table>
    {% for row in card.rows %}
    <tr><th>{{ row.label }}</th><td>{{ row.value_display }}</td></tr>
    {% endfor %}
  </table>
  {% endif %}
  {% if card.footnote %}<p class="footnote">{{ card.footnote }}</p>{% endif %}
</div>
```

Create `testing/local_env/reporting/templates/card_chart.html.j2`:

```jinja
<div class="card card-chart">
  {% if card.sub_outcome %}<p class="sub-outcome">{{ card.sub_outcome }}</p>{% endif %}
  {% if card.subtitle %}<h2>{{ card.subtitle }}</h2>{% endif %}
  {% if card.question %}<p class="question">{{ card.question }}</p>{% endif %}
  {% if card.note %}<p class="note">{{ card.note }}</p>{% endif %}
  {% if card.missing %}
    <p class="no-data">(no data)</p>
  {% else %}
    <canvas class="chart-canvas" data-chart='{{ card.chart_json }}'></canvas>
  {% endif %}
  {% if card.y_label %}<p class="axis-label">{{ card.y_label }}</p>{% endif %}
  {% if card.footnote %}<p class="footnote">{{ card.footnote }}</p>{% endif %}
</div>
```

Create `testing/local_env/reporting/templates/card_image.html.j2`:

```jinja
<div class="card card-image">
  {% if card.caption %}<p class="table-label">{{ card.caption }}</p>{% endif %}
  {% if card.url %}
    <img src="{{ card.url }}" alt="{{ card.caption or '' }}">
  {% else %}
    <div class="map-placeholder">Map not available in local render</div>
  {% endif %}
</div>
```

- [ ] **Step 4: Write the section template**

Create `testing/local_env/reporting/templates/section.html.j2`:

```jinja
<section class="outcome-section" id="{{ section.service }}">
  <h1>{{ section.section_title }}</h1>
  {% if section.unavailable %}
    <p class="section-unavailable">Section unavailable (service failed or no local layout config yet)</p>
  {% else %}
    {% for card in section.cards %}
      {% if card.type == "kpi" %}
        {% include "card_kpi.html.j2" %}
      {% elif card.type == "table" %}
        {% include "card_table.html.j2" %}
      {% elif card.type == "chart" %}
        {% include "card_chart.html.j2" %}
      {% elif card.type == "image" %}
        {% include "card_image.html.j2" %}
      {% endif %}
    {% endfor %}
  {% endif %}
</section>
```

- [ ] **Step 5: Write the top-level report template (Task-3 version — minimal header)**

Create `testing/local_env/reporting/templates/report.html.j2`:

```jinja
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PPA Report: {{ project_title }}</title>
<link rel="stylesheet" href="static/report.css">
<script src="static/chart.umd.min.js"></script>
</head>
<body>
<h1 class="report-title">Project Performance Assessment Report: {{ project_title }}</h1>
{% for section in sections %}
{% include "section.html.j2" %}
{% endfor %}
<script>
document.querySelectorAll('.chart-canvas').forEach(function (canvas) {
  var spec = JSON.parse(canvas.dataset.chart);
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: spec.categories,
      datasets: spec.series.map(function (s) { return {label: s.label, data: s.data}; })
    },
    options: {responsive: true, plugins: {legend: {display: spec.series.length > 1}}}
  });
});
</script>
</body>
</html>
```

- [ ] **Step 6: Write `render.py` (skeleton: `render_html` only)**

Create `testing/local_env/reporting/render.py`:

```python
"""render.py — turns a Phase-1 harness run into report.html.

Task 3 introduces render_html(sections, project_title) — pure templating, no file I/O.
Task 4 adds build_project_context/build_sections/render_report/CLI around it.
"""

import os

import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")


def _env():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(sections, project_title):
    template = _env().get_template("report.html.j2")
    return template.render(sections=sections, project_title=project_title)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py -v`
Expected: both tests `PASSED`.

- [ ] **Step 8: Commit**

```bash
git add testing/local_env/reporting/templates testing/local_env/reporting/render.py testing/local_env/tests/test_reporting_render.py
git commit -m "reporting: generic section/card templates + render_html skeleton"
```

---

### Task 4: Title page + boilerplate + `render_report()` full pipeline

**Files:**
- Create: `testing/local_env/reporting/templates/title_page.html.j2`
- Create: `testing/local_env/reporting/templates/boilerplate/using_this_report.html`
- Create: `testing/local_env/reporting/templates/boilerplate/atp_intro.html`
- Create: `testing/local_env/reporting/layout_loader.py`
- Modify: `testing/local_env/reporting/templates/report.html.j2`
- Modify: `testing/local_env/reporting/render.py`
- Modify: `testing/local_env/tests/test_reporting_render.py`

**Interfaces:**
- Consumes: `dispatch.resolve_dispatch` is NOT used here — `manifest.json`'s own
  `services: [{service, outcome, status}]` list already carries the dispatch order (see Task 10),
  so `render.py` reads that directly rather than recomputing dispatch.
- Produces (used by Task 5-10):
  - `layout_loader.load_layout(service: str) -> dict | None`
  - `render.load_run(run_dir: str) -> tuple[dict, dict]` (manifest, merged)
  - `render.build_project_context(manifest: dict, merged: dict, report_generated: str) -> dict`
  - `render.build_sections(manifest: dict, merged: dict) -> list[dict]`
  - `render.render_report(run_dir: str, output_path: str | None = None) -> str` (path written)

- [ ] **Step 1: Write the failing test**

Add to `testing/local_env/tests/test_reporting_render.py` (keep the Task-3 tests above it):

```python
import json
import tempfile


class TestBuildProjectContext(unittest.TestCase):
    def test_pulls_from_manifest_inputs_and_title_service(self):
        manifest = {
            "timestamp": "20260729_172109",
            "inputs": {
                "program": "Active Transportation Program",
                "project_type": "Non-Freeway Investment",
                "project_name": "verify_run",
                "jurisdiction": "Sacramento",
                "aadt": 15000,
                "posted_speed": 35,
                "pci": 70,
            },
        }
        merged = {"RPTitleAndGuide": {
            "Project Length Centerline Miles": 0.6674009841521,
            "Project Community Type": "Established Communities",
            "Project Unique ID": "fb86f0b5-9b1d-4774-bbcd-889ec7306d69",
        }}
        ctx = render.build_project_context(manifest, merged, report_generated="Wednesday, July 29, 2026")
        self.assertEqual(ctx["name"], "verify_run")
        self.assertEqual(ctx["jurisdiction"], "Sacramento")
        self.assertEqual(ctx["funding_program"], "Active Transportation Program")
        self.assertEqual(ctx["length_miles"], 0.67)
        self.assertEqual(ctx["community_type"], "Established Communities")
        self.assertEqual(ctx["uid"], "fb86f0b5-9b1d-4774-bbcd-889ec7306d69")
        self.assertEqual(ctx["report_generated"], "Wednesday, July 29, 2026")


class TestBuildSections(unittest.TestCase):
    def test_skips_title_includes_ok_services_flags_missing(self):
        manifest = {"services": [
            {"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
            {"service": "RPArtSGRSGR", "outcome": "Maintain State of Good Repair", "status": "ok"},
            {"service": "RPArtExpVMT", "outcome": "Multimodal/Transportation Choice (Reduce VMT)", "status": "failed(x)"},
        ]}
        merged = {"RPArtSGRSGR": {"Pavement Condition Index": 70, "ADT": 15000, "Complete Streets Index": 3.8}}
        sections = render.build_sections(manifest, merged)
        # RPArtSGRSGR has a real layout config (authored in Task 9) -> should render normally
        sgr = next(s for s in sections if s["service"] == "RPArtSGRSGR")
        self.assertFalse(sgr["unavailable"])
        # RPArtExpVMT failed upstream -> unavailable, no crash
        vmt = next(s for s in sections if s["service"] == "RPArtExpVMT")
        self.assertTrue(vmt["unavailable"])
        # Title is never treated as an outcome section
        self.assertNotIn("RPTitleAndGuide", [s["service"] for s in sections])


class TestRenderReport(unittest.TestCase):
    def test_writes_report_html_from_a_run_dir(self):
        with tempfile.TemporaryDirectory() as run_dir:
            manifest = {
                "timestamp": "20260729_172109",
                "inputs": {
                    "program": "Active Transportation Program", "project_type": "Non-Freeway Investment",
                    "project_name": "verify_run", "jurisdiction": "Sacramento",
                    "aadt": 15000, "posted_speed": 35, "pci": 70,
                },
                "services": [
                    {"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
                    {"service": "RPArtSGRSGR", "outcome": "Maintain State of Good Repair", "status": "ok"},
                ],
            }
            merged = {
                "RPTitleAndGuide": {
                    "Project Length Centerline Miles": 0.6674, "Project Community Type": "Established Communities",
                    "Project Unique ID": "abc-123",
                },
                "RPArtSGRSGR": {"Pavement Condition Index": 70, "ADT": 15000, "Complete Streets Index": 3.8},
            }
            with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            with open(os.path.join(run_dir, "merged.json"), "w", encoding="utf-8") as f:
                json.dump(merged, f)

            out_path = render.render_report(run_dir)

            self.assertTrue(os.path.isfile(out_path))
            with open(out_path, encoding="utf-8") as f:
                html = f.read()
            self.assertIn("verify_run", html)
            self.assertIn("Maintain State of Good Repair", html)
            self.assertIn("Using This Report", html)
            self.assertIn("Active Transportation Program", html)  # ATP intro included
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py -v`
Expected: `AttributeError: module 'reporting.render' has no attribute 'build_project_context'`.

- [ ] **Step 3: Write `layout_loader.py`**

Create `testing/local_env/reporting/layout_loader.py`:

```python
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_DIR = os.path.join(HERE, "layout")


def load_layout(service):
    path = os.path.join(LAYOUT_DIR, f"{service}.yaml")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
```

- [ ] **Step 4: Write the title page template**

Create `testing/local_env/reporting/templates/title_page.html.j2`:

```jinja
<section class="title-page">
  <h1>Project Performance Assessment Report: {{ project.name }}</h1>
  <h2>Project Summary</h2>
  <div class="map-placeholder">Map not available in local render</div>
  <table class="summary-table">
    <tr><th>Project name</th><td>{{ project.name }}</td></tr>
    <tr><th>Jurisdiction</th><td>{{ project.jurisdiction }}</td></tr>
    <tr><th>Project type</th><td>{{ project.project_type }}</td></tr>
    <tr><th>Funding Program</th><td>{{ project.funding_program }}</td></tr>
    <tr><th>Project AADT</th><td>{{ project.aadt }}</td></tr>
    <tr><th>Project Pavement Condition Index (PCI)</th><td>{{ project.pci }}</td></tr>
    <tr><th>Posted Speed Limit</th><td>{{ project.posted_speed }}</td></tr>
    <tr><th>Project Length (Centerline Miles)</th><td>{{ project.length_miles }}</td></tr>
    <tr><th>Project Community Type</th><td>{{ project.community_type }}</td></tr>
    <tr><th>Project UID</th><td>{{ project.uid }}</td></tr>
  </table>
  <p class="report-generated">Report Generated: {{ project.report_generated }}</p>
</section>
```

- [ ] **Step 5: Write the boilerplate partials**

Create `testing/local_env/reporting/templates/boilerplate/using_this_report.html`
(verbatim transcription from both golden PDFs — identical text in `report.pdf` p.2 and
`report transportion_test.pdf` p.3):

```html
<section class="boilerplate">
  <h1>Using This Report</h1>
  <h2>What this report does</h2>
  <p>This report provides the most recently available observed data and, where observed data are
  not available, uses base-year modeled data. It aims to provide rich, quantitative contextual
  information about each project to aid reviewers in deciding which projects most align with
  program goals.</p>
  <p>For example, if a sponsor states that a project's goal is to reduce congestion, the report
  provides data on how congested the project corridor is under current conditions along with
  expected job and housing growth in the corridor. Such data, along with any supplemental
  application narrative provided by the sponsor, are provided to help reviewers decide if the
  project has potential to be an effective congestion reduction tool.</p>
  <h2>What this report does NOT do</h2>
  <p>This report does not in any way model the effects that the proposed project would have if it
  were built. Any future-year data shown is based on SACOG's travel demand model and MTP-SCS land
  use forecast and does not necessarily factor in the effects of the proposed project.</p>
  <p>Future-year data are included to show how well the project aligns with the MTP's vision of
  the project area, but not to show the effects that the project itself will have. For example,
  the future-year population and job growth around a road capacity project answers the question
  "how many people is this road expected to serve in the future?", not "how much growth will this
  road project cause?".</p>
  <p>Similarly, for performance outcomes like safety or congestion reduction, the report tells the
  reviewer if there currently is a problem with congestion or safety (e.g., high collision rate),
  but it does not say whether the proposed project will improve the issue, e.g., it won't say
  whether widening a congested segment will reduce its congestion, nor will it say whether a
  proposed safety project will address the root cause of the safety issue.</p>
</section>
```

Create `testing/local_env/reporting/templates/boilerplate/atp_intro.html`
(transcribed from `report transportion_test.pdf` p.2, the ATP-only intro page):

```html
<section class="boilerplate atp-intro">
  <h1>Active Transportation Program</h1>
  <p><strong>Program objectives and how they integrate with the PPA Report</strong></p>
  <p><strong>Focus Area:</strong> The Active Transportation Program (ATP) is a statewide funding
  program meant to increase walking and bicycling by funding projects that provide safe and
  connected infrastructure.</p>
  <p><strong>Key Performance Objectives:</strong> Providing bicycle and pedestrian infrastructure,
  education, plans, and trails to improve connections and increase riding, walking, and rolling.</p>
  <table>
    <tr>
      <th>Program Objectives</th><th>PPA Metric Group</th><th>Relevant PPA Metrics</th><th>Typical Project Elements</th>
    </tr>
    <tr>
      <td>Potential for Increased Walking and Bicycling</td>
      <td>Multimodal/Transportation Choice (Reduce VMT); Multimodal/Transportation Choice (Encourage Multimodal Travel)</td>
      <td>&bull; Walk/bike destinations nearby (mode share)<br>&bull; Street Connectivity (3&amp;4-way intersection/acre)<br>&bull; Bike Network Coverage (% of centerline miles)</td>
      <td>Bike lanes; Trails; Pedestrian crossings</td>
    </tr>
    <tr>
      <td>Potential for Reducing the Number and/or Rate of Pedestrian and Bicyclist Fatalities and Injuries</td>
      <td>Safety</td>
      <td>&bull; Bike &amp; Ped Collisions per Centerline Mile (for active transportation projects)<br>&bull; Collision Rate per 100M VMT</td>
      <td>Bike lanes; Trails; Pedestrian crossings</td>
    </tr>
    <tr>
      <td>Advancing active transportation efforts to achieve greenhouse gas reduction goals</td>
      <td>Multimodal/Transportation Choice (Reduce VMT); Multimodal/Transportation Choice (Encourage Multimodal Travel)</td>
      <td>&bull; Walk/bike destinations nearby (land use by 2035)<br>&bull; Residential Mode Split</td>
      <td>Bike lanes; Trails; Pedestrian crossings</td>
    </tr>
    <tr>
      <td>Supporting economic prosperity goals and strategies</td>
      <td>Economic Prosperity</td>
      <td>&bull; Jobs accessible by mode<br>&bull; Educational facilities accessible by mode</td>
      <td>Bike lanes; Trails; Pedestrian crossings; Mobility hubs; Access improvements; Job center connections</td>
    </tr>
    <tr>
      <td>Disadvantaged Communities</td>
      <td>Benefits to the Transportation Network and Impacted Communities</td>
      <td colspan="2">Notice: The Environmental Justice Analysis shown in the Project Performance
      Assessment (PPA) tool is based on an outdated methodology that is currently not being
      updated. Regional ATP applicants should reference the 2025 Blueprint Appendix E - Plan
      Performance Measures and associated equity-related metrics.</td>
    </tr>
  </table>
</section>
```

- [ ] **Step 6: Update `report.html.j2` to include the title page + boilerplate**

Edit `testing/local_env/reporting/templates/report.html.j2` — replace the line
`<h1 class="report-title">Project Performance Assessment Report: {{ project_title }}</h1>` with:

```jinja
{% include "title_page.html.j2" %}
{% if show_atp_intro %}
{% include "boilerplate/atp_intro.html" %}
{% endif %}
{% include "boilerplate/using_this_report.html" %}
```

and change the `<title>` tag from `{{ project_title }}` to `{{ project.name }}`.

- [ ] **Step 7: Rewrite `render.py`**

Replace `testing/local_env/reporting/render.py`:

```python
"""render.py — turns a Phase-1 harness run into report.html. No arcpy dependency; runs
under plain python3.
"""

import json
import os
import sys
from datetime import datetime

import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")
sys.path.insert(0, HERE)
import cards  # noqa: E402
import layout_loader  # noqa: E402


def _env():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(sections, project_title):
    template = _env().get_template("report.html.j2")
    return template.render(
        sections=sections,
        project_title=project_title,
        project={"name": project_title},
        show_atp_intro=False,
    )


def load_run(run_dir):
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    with open(os.path.join(run_dir, "merged.json"), encoding="utf-8") as f:
        merged = json.load(f)
    return manifest, merged


def _format_stamp(stamp):
    dt = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
    return dt.strftime("%A, %B %d, %Y %I:%M %p")


def build_project_context(manifest, merged, report_generated):
    inputs = manifest["inputs"]
    title = merged.get("RPTitleAndGuide", {})
    length = title.get("Project Length Centerline Miles")
    return {
        "name": inputs.get("project_name"),
        "jurisdiction": inputs.get("jurisdiction"),
        "project_type": inputs.get("project_type"),
        "funding_program": inputs.get("program"),
        "aadt": inputs.get("aadt"),
        "pci": inputs.get("pci"),
        "posted_speed": inputs.get("posted_speed"),
        "length_miles": round(length, 2) if length is not None else None,
        "community_type": title.get("Project Community Type"),
        "uid": title.get("Project Unique ID"),
        "report_generated": report_generated,
    }


def build_sections(manifest, merged):
    sections = []
    for entry in manifest.get("services", []):
        service = entry["service"]
        if service == "RPTitleAndGuide":
            continue
        ok = entry.get("status") == "ok" and service in merged
        layout_cfg = layout_loader.load_layout(service) if ok else None
        if ok and layout_cfg is not None:
            section = cards.build_section(layout_cfg, merged[service])
            section["unavailable"] = False
        else:
            section = {
                "service": service,
                "section_title": entry.get("outcome", service),
                "unavailable": True,
                "cards": [],
            }
        sections.append(section)
    return sections


def render_report(run_dir, output_path=None):
    manifest, merged = load_run(run_dir)
    report_generated = _format_stamp(manifest["timestamp"])
    project = build_project_context(manifest, merged, report_generated)
    sections = build_sections(manifest, merged)
    show_atp_intro = manifest["inputs"].get("program") == "Active Transportation Program"

    template = _env().get_template("report.html.j2")
    html = template.render(
        sections=sections,
        project_title=project["name"],
        project=project,
        show_atp_intro=show_atp_intro,
    )

    if output_path is None:
        output_path = os.path.join(run_dir, "report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


if __name__ == "__main__":
    out = render_report(sys.argv[1])
    print(f"wrote {out}")
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py -v`
Expected: all tests `PASSED` (the `RPArtSGRSGR` layout config referenced by
`TestBuildSections`/`TestRenderReport` doesn't exist yet — Task 9 authors it — but those tests
only assert on `unavailable`/presence, which the "no layout config yet" fallback already
satisfies correctly as `unavailable: True`. Re-run after Task 9 and confirm it flips to
`unavailable: False` with real card content, per Task 9's own test.)

Note: if a test above expects `sgr["unavailable"]` to be `False` before Task 9 exists, it will
fail — that specific assertion is intentionally revisited in Task 9's test file, not here. If it
fails now, that's expected; don't "fix" it by editing render.py — Task 9 supplies the missing file.

- [ ] **Step 9: Commit**

```bash
git add testing/local_env/reporting/templates testing/local_env/reporting/render.py testing/local_env/reporting/layout_loader.py testing/local_env/tests/test_reporting_render.py
git commit -m "reporting: title page, boilerplate, full render_report pipeline"
```

---

### Task 5: Layout config — `RPArtExpVMT` (Multimodal/Transportation Choice, Reduce VMT)

**Files:**
- Create: `testing/local_env/reporting/layout/RPArtExpVMT.yaml`
- Create: `testing/local_env/tests/test_reporting_layouts.py`

**Interfaces:**
- Consumes: `layout_loader.load_layout`, `cards.build_section` (Task 2, 4).
- Produces: a real layout config other tasks' end-to-end tests rely on.

- [ ] **Step 1: Write the failing test**

Create `testing/local_env/tests/test_reporting_layouts.py`:

```python
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, layout_loader

LOCAL_ATP_RUN = os.path.join(
    os.path.dirname(HERE), "out", "runs", "20260729_172109", "merged.json"
)


def _load_local_merged():
    with open(LOCAL_ATP_RUN, encoding="utf-8") as f:
        return json.load(f)


@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestVmtLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpVMT")
        self.data = _load_local_merged()["RPArtExpVMT"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)
        self.assertEqual(self.layout["service"], "RPArtExpVMT")

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [], f"cards with no data: {missing}")

    def test_three_charts_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        subtitles = [c["subtitle"] for c in section["cards"]]
        self.assertEqual(subtitles, [
            "Jobs and Houses nearby by 2035",
            "Walk/bike destinations nearby (land use by 2035)*",
            "Walk/bike destinations nearby (mode share)*",
        ])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py -v`
Expected: `TestVmtLayout::test_layout_loads` FAILS (`layout is None`) — or the whole class is
skipped if `testing/local_env/out/runs/20260729_172109/merged.json` isn't present on this
machine (that's fine; it exists on the machine this plan was written on, and Task 10 doesn't
depend on this specific test passing everywhere — only that it doesn't crash pytest collection).

- [ ] **Step 3: Author the layout config**

Create `testing/local_env/reporting/layout/RPArtExpVMT.yaml`:

```yaml
service: RPArtExpVMT
section_title: "Multimodal/Transportation Choice (Reduce VMT)"
cards:
  - type: chart
    source_chart: "Jobs and Dwelling"
    subtitle: "Jobs and Houses nearby by 2035"
    question: "Will the project serve areas with significant growth in jobs and housing?"
    x_field: year
    series:
      - field: jobs
        label: Jobs
      - field: dwellingUnits
        label: Dwelling Units
    y_label: "Total Jobs and Dwelling Units within 0.5mi of project"

  - type: chart
    source_chart: "Land Use Diversity"
    subtitle: "Walk/bike destinations nearby (land use by 2035)*"
    question: "Does the project connect to a mix of land uses that support walking and biking?"
    x_field: type
    series:
      - field: "diversity 2020"
        label: "2020"
      - field: "diversity 2035"
        label: "2035"
    y_label: "Land Use Mix Index"
    footnote: >
      *The land use diversity index ranges from 0 to 1 and measures an area's ratio of
      households to K-12 student enrollment, park acreage, and employment in the retail,
      service, and food sectors. A score of 1 indicates an "ideal" ratio of households to
      amenities that people use on a daily basis like shopping, restaurants, schools, etc.
      that in turn increases the likelihood that people living in those households will
      either walk or bike to these destinations, or drive a shorter distance.

  - type: chart
    source_chart: "Base Year Service Accessibility"
    subtitle: "Walk/bike destinations nearby (mode share)*"
    question: "Are key destinations accessible by walking, biking, or transit?"
    x_field: type
    series:
      - field: Project
        label: Project
      - field: "Community Type"
        label: "Community Type"
      - field: Region
        label: Region
    y_label: "Total Services Accessible"
    footnote: >
      *"Services" include parks, K-12 schools, higher education facilities, libraries,
      hospitals, other medical service facilities, grocery stores, pharmacies, clothing
      stores, and banks. Similar to the land use diversity index, if a project has more of
      these types of services within a feasible biking, walking, or transit trip, then
      people who live or work near the project segment will on average generate less VMT
      in order to access these services. And in contrast to the diversity index, which
      shows services as a ratio of households to services, this indicator gives a better
      sense of the total amount of services available.
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py -v`
Expected: `TestVmtLayout` tests `PASSED` (or skipped if the local run fixture is absent).

- [ ] **Step 5: Commit**

```bash
git add testing/local_env/reporting/layout/RPArtExpVMT.yaml testing/local_env/tests/test_reporting_layouts.py
git commit -m "reporting: author RPArtExpVMT layout config"
```

---

### Task 6: Layout config — `RPArtExpSafety`

**Files:**
- Create: `testing/local_env/reporting/layout/RPArtExpSafety.yaml`
- Modify: `testing/local_env/tests/test_reporting_layouts.py`

**Interfaces:** same as Task 5, for service `RPArtExpSafety`.

- [ ] **Step 1: Write the failing test**

Add to `testing/local_env/tests/test_reporting_layouts.py`:

```python
@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestSafetyLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpSafety")
        self.data = _load_local_merged()["RPArtExpSafety"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [])

    def test_task5_only_charts_excluded(self):
        # Collision Types / Primary Collision Factors are Task-5 branch-only additions,
        # confirmed absent from the real prod capture (Task 11) and the golden PDF.
        chart_sources = [c.get("source_chart") for c in self.layout["cards"] if c["type"] == "chart"]
        self.assertNotIn("Collision Types", chart_sources)
        self.assertNotIn("Primary Collision Factors", chart_sources)

    def test_five_cards_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual([c["type"] for c in section["cards"]], ["kpi", "image", "table", "chart", "table"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestSafetyLayout -v`
Expected: `test_layout_loads` FAILS (`layout is None`).

- [ ] **Step 3: Author the layout config**

Create `testing/local_env/reporting/layout/RPArtExpSafety.yaml`:

```yaml
service: RPArtExpSafety
# Printed golden header is "Safety" -- shorter than dispatch.py's outcome checkbox label
# "Safety or Security". Confirmed by extracting report.pdf/report transportion_test.pdf text.
section_title: "Safety"
cards:
  - type: kpi
    source: "Total collisions"
    subtitle: "Total Collisions (2019-2023)"
    question: "Is the corridor experiencing a high number of crashes?"
    note: >
      Note: Collision data only include collisions involving an injury or fatality and are
      from UC Berkeley's Transportation Injury Mapping System (TIMS)

  - type: image
    source: "Collision heat map Image Url"
    caption: "Collision heat map of corridor"

  - type: table
    source: "Collisions per 100 million VMT"
    subtitle: "Collision Rate per 100M VMT"
    question: "Is the corridor's crash rate high relative to traffic volume?"
    row_labels:
      Project: "On project segment*"
      "Community Type": "Within community type"
      Region: "Within region"
    footnote: >
      *The on-project collision rate will be -1.0 if the user did not provide an average
      daily traffic value.

  # Golden shows this chart's y-axis in percent; v1 keeps raw fractions (0-1) in the chart
  # data to avoid a custom Chart.js tick-format callback -- see plan Task 6 open item.
  - type: chart
    source_chart: "Fatal and BikePed Collisions"
    subtitle: "Fatal & Bike/Ped Collision Share (%)"
    question: "Are vulnerable users disproportionately involved in severe crashes?"
    x_field: type
    series:
      - field: Project
        label: Project
      - field: "Community Type"
        label: "Community Type"
      - field: Region
        label: Region
    y_label: "Fatal and Bike/Ped Collisions Share %"

  - type: table
    source: "Bike and Ped Collisions per Project Centerline"
    subtitle: "Bike & Ped Collisions per CL Mile"
    question: "Does the corridor have frequent bike/ped crashes?"
    row_labels:
      Project: "Project"
      "Community Type": "Community Type"
      Region: "Region"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestSafetyLayout -v`
Expected: all `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add testing/local_env/reporting/layout/RPArtExpSafety.yaml testing/local_env/tests/test_reporting_layouts.py
git commit -m "reporting: author RPArtExpSafety layout config"
```

---

### Task 7: Layout config — `RPArtExpMultiModal`

**Files:**
- Create: `testing/local_env/reporting/layout/RPArtExpMultiModal.yaml`
- Modify: `testing/local_env/tests/test_reporting_layouts.py`

- [ ] **Step 1: Write the failing test**

Add to `testing/local_env/tests/test_reporting_layouts.py`:

```python
@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestMultiModalLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpMultiModal")
        self.data = _load_local_merged()["RPArtExpMultiModal"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [])

    def test_six_cards_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual(
            [c["type"] for c in section["cards"]],
            ["table", "table", "image", "table", "image", "chart"],
        )
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestMultiModalLayout -v`
Expected: FAILS (`layout is None`).

- [ ] **Step 3: Author the layout config**

Create `testing/local_env/reporting/layout/RPArtExpMultiModal.yaml`:

```yaml
service: RPArtExpMultiModal
section_title: "Multimodal/Transportation Choice (Encourage Multimodal Travel)"
cards:
  - type: table
    source: "Intersections per acre"
    subtitle: "Street Connectivity (3- & 4-way intersections/acre)"
    question: "Does the project improve connectivity for walking and biking?"
    label: "Intersections per acre"
    row_labels:
      "Within 0.25mi": "Within 0.25mi of project"
      "Community Type": "Within community type"
      Region: "Within region"

  - type: table
    source: "Bike lanes and paths as share of total road miles"
    subtitle: "Bike Network Coverage (% of centerline miles)"
    question: "Does the project close gaps in the bike network?"
    label: "Bike lanes and paths as share of total road miles"
    value_format: percent
    row_labels:
      "Within 0.25mi": "Within 0.25mi of project"
      "Community Type": "Within community type"
      Region: "Within region"

  - type: image
    source: "Bikeway Image Url"
    caption: "Project Area Bikeway Map"

  - type: table
    source: "Transit vehicle stops per acre"
    subtitle: "Transit Activity (stops/acre/day)"
    question: "Is transit service frequent enough to support multimodal goals?"
    label: "Transit vehicle stops per acre"
    row_labels:
      "Within 0.25mi": "Within 0.25mi of project"
      "Community Type": "Within community type"
      Region: "Within region"

  - type: image
    source: "Transit Service Density Image Url"
    caption: "Project Area Transit Service Map"

  # Golden shows this chart's y-axis in percent; v1 keeps raw fractions -- same simplification
  # noted in RPArtExpSafety.yaml.
  - type: chart
    source_chart: "Residential Mode Split"
    subtitle: "Residential Mode Split (2020, 2035)"
    question: "Do residents near the project use non-auto modes?"
    note: >
      NOTE - The future-year mode split shown below is based on modeled values estimated
      for SACOG's latest regional plan. As with all other future-year values in this
      report, they do NOT factor in the potential effects of the project for which this
      report was generated.
    x_field: type
    series:
      - field: "year 2020"
        label: "2020"
      - field: "year 2035"
        label: "2035"
    y_label: "Residential Mode Split within 0.5mi of Project Location"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestMultiModalLayout -v`
Expected: all `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add testing/local_env/reporting/layout/RPArtExpMultiModal.yaml testing/local_env/tests/test_reporting_layouts.py
git commit -m "reporting: author RPArtExpMultiModal layout config"
```

---

### Task 8: Layout config — `RPArtExpEconProsp`

**Files:**
- Create: `testing/local_env/reporting/layout/RPArtExpEconProsp.yaml`
- Modify: `testing/local_env/tests/test_reporting_layouts.py`

- [ ] **Step 1: Write the failing test**

Add to `testing/local_env/tests/test_reporting_layouts.py`:

```python
@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestEconProspLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpEconProsp")
        self.data = _load_local_merged()["RPArtExpEconProsp"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [])

    def test_sub_outcomes_present_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        sub_outcomes = [c["sub_outcome"] for c in section["cards"] if c.get("sub_outcome")]
        self.assertEqual(sub_outcomes, [
            "Sub outcome: Increase Job Access",
            "Sub outcome: Increase School Access",
            "Sub outcome: Support Ag Economy",
        ])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestEconProspLayout -v`
Expected: FAILS (`layout is None`).

- [ ] **Step 3: Author the layout config**

Create `testing/local_env/reporting/layout/RPArtExpEconProsp.yaml`:

```yaml
service: RPArtExpEconProsp
# Printed golden header is "Economic Prosperity" -- dispatch.py's outcome checkbox label is the
# longer "Freight Movement (Economic Prosperity)".
section_title: "Economic Prosperity"
cards:
  - type: chart
    source_chart: "Access to jobs"
    sub_outcome: "Sub outcome: Increase Job Access"
    subtitle: "Jobs accessible by mode"
    question: "Are jobs accessible by walking, biking, or transit?"
    x_field: type
    series:
      - field: Project
        label: Project
      - field: "Community Type"
        label: "Community Type"
      - field: Region
        label: Region
    y_label: "Total Jobs Accessible"

  - type: kpi
    source: "Total new jobs added"
    subtitle: "Job growth (2020 to 2035)"
    question: "Will the project serve areas with significant growth in jobs?"

  - type: kpi
    source: "K12 Enrollment"
    sub_outcome: "Sub outcome: Increase School Access"
    subtitle: "K-12 Enrollment"
    question: "Are their significant numbers of students within 0.5mi from the project?"

  - type: chart
    source_chart: "Education Facility"
    subtitle: "Educational facilities accessible by mode"
    question: "Are schools accessible by walking, biking, or transit within 0.5mi from the project?"
    x_field: type
    series:
      - field: Project
        label: Project
      - field: "Community Type"
        label: "Community Type"
      - field: Region
        label: Region
    y_label: "Total Services Accessible"

  - type: chart
    source_chart: "Change in Ag acreage"
    sub_outcome: "Sub outcome: Support Ag Economy"
    subtitle: "Acres of Agricultural Use change, 2020 to 2035"
    question: "Will the project be serving areas with high existing agricultural uses that are preserved by 2035?"
    x_field: year
    series:
      - field: value
        label: "Change in Ag acreage within 0.5mi of project location"
    y_label: "Acres"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestEconProspLayout -v`
Expected: all `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add testing/local_env/reporting/layout/RPArtExpEconProsp.yaml testing/local_env/tests/test_reporting_layouts.py
git commit -m "reporting: author RPArtExpEconProsp layout config"
```

---

### Task 9: Layout config — `RPArtSGRSGR`

**Files:**
- Create: `testing/local_env/reporting/layout/RPArtSGRSGR.yaml`
- Modify: `testing/local_env/tests/test_reporting_layouts.py`

- [ ] **Step 1: Write the failing test**

Add to `testing/local_env/tests/test_reporting_layouts.py`:

```python
@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestSgrLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtSGRSGR")
        self.data = _load_local_merged()["RPArtSGRSGR"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [])

    def test_three_kpi_cards(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual([c["type"] for c in section["cards"]], ["kpi", "kpi", "kpi"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestSgrLayout -v`
Expected: FAILS (`layout is None`).

- [ ] **Step 3: Author the layout config**

Create `testing/local_env/reporting/layout/RPArtSGRSGR.yaml`:

```yaml
service: RPArtSGRSGR
section_title: "Maintain State of Good Repair"
cards:
  - type: kpi
    source: "Pavement Condition Index"
    subtitle: "Pavement Condition Index (PCI)"
    question: "Is the pavement in poor condition?"

  - type: kpi
    source: "ADT"
    subtitle: "Average Daily Traffic (ADT)"
    question: "Does the corridor carry high traffic volumes?"

  - type: kpi
    source: "Complete Streets Index"
    subtitle: "Complete Streets Index (0-100)"
    question: "Does the corridor support multimodal travel and safety?"
    footnote: >
      The complete streets index (CSI) is a 0-100 score based on the densities of
      students, transit service, jobs, and dwelling units within a half mile of the
      project location and the project location's posted speed limit. A higher CSI means
      the street is more likely to support many users of all modes (bike, walk, transit,
      drive) and thus derive greater benefit from complete streets treatments that make
      the project location better serve all types of road users. As posted speed limit
      increases beyond 40mph, the CSI will fall with all else being equal since fast
      vehicle speeds are less conducive to the street serving all users. (The golden PDF
      also shows a per-community-type CSI benchmark table here; that benchmark isn't
      present in merged.json's RPArtSGRSGR output, so it's omitted in v1 -- see this
      plan's Task 9 open item.)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_layouts.py::TestSgrLayout -v`
Expected: all `PASSED`.

- [ ] **Step 5: Re-run the full render suite now that a real `RPArtSGRSGR` layout exists**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py testing/local_env/tests/test_reporting_layouts.py -v`
Expected: all `PASSED`, including the Task-4 `TestBuildSections`/`TestRenderReport` cases that
were noted as depending on this file.

- [ ] **Step 6: Commit**

```bash
git add testing/local_env/reporting/layout/RPArtSGRSGR.yaml testing/local_env/tests/test_reporting_layouts.py
git commit -m "reporting: author RPArtSGRSGR layout config"
```

**Open item (documented, not blocking):** the golden PDF's Complete Streets Index page also
shows a "table below lists the average CSI score for each PPA community type" — that benchmark
table has no corresponding field in `merged.json`'s `RPArtSGRSGR` output today (confirmed absent
in both the local harness output and the real prod HAR capture — see Task 11). Adding it would
require a GP-service change outside this plan's scope; flagged for a future wishlist item, not
implemented here.

---

### Task 10: End-to-end render against the real local ATP harness run (generalization check)

**Files:**
- Modify: `testing/local_env/tests/test_reporting_render.py`

**Interfaces:**
- Consumes: `render.render_report` (Task 4) + all 5 real layout configs (Tasks 5-9) +
  `testing/local_env/out/runs/20260729_172109/` (the real local ATP harness run already on disk,
  per the design spec's golden references).

- [ ] **Step 1: Write the test**

Add to `testing/local_env/tests/test_reporting_render.py`:

```python
LOCAL_ATP_RUN_DIR = os.path.join(os.path.dirname(HERE), "out", "runs", "20260729_172109")


@unittest.skipUnless(os.path.isdir(LOCAL_ATP_RUN_DIR), "local ATP harness run not present")
class TestRenderRealLocalRun(unittest.TestCase):
    def test_renders_all_five_atp_sections_with_no_placeholders(self):
        out_path = render.render_report(
            LOCAL_ATP_RUN_DIR,
            output_path=os.path.join(tempfile.mkdtemp(), "report.html"),
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()

        # All 5 ATP outcome section headers present
        for title in [
            "Multimodal/Transportation Choice (Reduce VMT)",
            "Safety",
            "Multimodal/Transportation Choice (Encourage Multimodal Travel)",
            "Economic Prosperity",
            "Maintain State of Good Repair",
        ]:
            self.assertIn(title, html, f"missing section: {title}")

        # No section fell back to "unavailable" and no card silently reported "(no data)"
        self.assertNotIn("section-unavailable", html)
        self.assertNotIn("(no data)", html)

        # Title-page fields sourced from this specific run's manifest.json
        self.assertIn("verify_run", html)
        self.assertIn("Sacramento", html)
```

- [ ] **Step 2: Run to verify it fails first (TDD sanity check on this specific run)**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py::TestRenderRealLocalRun -v`
If Tasks 4-9 are already complete and committed, this should already `PASS` — in that case, skip
straight to Step 3 and just confirm the pass. If it fails, the failure message (which section
title is missing, or which `(no data)` card fired) tells you which layout config's `source`/
`source_chart` field name doesn't match this run's actual `merged.json` keys — fix the mismatched
YAML field name, not the test.

- [ ] **Step 3: Run to confirm it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_render.py -v`
Expected: every test in the file `PASSED`.

- [ ] **Step 4: Generate a real report.html to look at**

```bash
python3 testing/local_env/reporting/render.py testing/local_env/out/runs/20260729_172109
```

Expected output: `wrote testing/local_env/out/runs/20260729_172109/report.html`. Open that file
in a browser and confirm charts render (bars visible, not blank canvases) and no section says
"unavailable."

- [ ] **Step 5: Commit**

```bash
git add testing/local_env/tests/test_reporting_render.py
git commit -m "reporting: generalization check against the real local ATP harness run"
```

---

### Task 11: HAR extraction fixture + structural fidelity check (corrected golden-fidelity step)

**Files:**
- Create: `testing/local_env/reporting/extract_har_fixture.py`
- Create: `testing/local_env/tests/fixtures/reporting/har_prod_capture/manifest.json` (generated,
  then committed)
- Create: `testing/local_env/tests/fixtures/reporting/har_prod_capture/merged.json` (generated,
  then committed)
- Create: `testing/local_env/tests/test_reporting_har_fixture.py`

**Why this replaces the design's original "compare to golden PDF numbers" plan:** verified while
writing this plan (see the "Correction to the design spec" note at the top) — `atp_ppa_run_submit.har`
contains exactly one fully-captured run (CMCP, project "random proj", 8 outcomes), and it matches
neither golden PDF's project. This task extracts that one real capture into a committed fixture and
uses it to prove the renderer works against **real prod-shaped output**, not just our own local
harness's shape — a meaningfully different, still-valuable check, just not a numeric-match-to-golden
check.

**Interfaces:**
- Produces: `extract_har_fixture.py: build_fixture(har_path: str) -> tuple[dict, dict]`
  (manifest, merged) — a reusable, reproducible provenance script + a committed static fixture the
  test suite reads (hermetic — no dependency on `PPA3_Handoff/` existing at test time).

- [ ] **Step 1: Write `extract_har_fixture.py`**

Create `testing/local_env/reporting/extract_har_fixture.py`:

```python
"""extract_har_fixture.py -- pulls the one fully-captured GP-service result payload out of a
PPA3_Handoff/*.har file into a manifest.json + merged.json pair shaped like a Phase-1 harness
run, for use as a real prod-shape fixture in reporting tests.

The captured run is CMCP US50, project "random proj" (Non-Freeway, all 8 outcomes) -- a
different project than either golden PDF ("Trell Test" / "Active Transportation Program Report
Test"), confirmed by inspecting every entry in the HAR: only one response body contains a
completed run with reports[] data. So this fixture validates STRUCTURE (every field/chart name
a layout config references exists in real prod output), not project-level NUMBERS against a
golden PDF.
"""

import json
import os
import sys


def _find_completed_run(har_path):
    with open(har_path, encoding="utf-8") as f:
        har = json.load(f)
    for entry in har["log"]["entries"]:
        text = entry["response"]["content"].get("text", "")
        if not text:
            continue
        try:
            body = json.loads(text)
        except ValueError:
            continue
        results = body.get("results")
        if not results:
            continue
        output = results[0].get("outputs", {}).get("output")
        if isinstance(output, dict) and output.get("reports"):
            return output
    raise ValueError(f"no completed run with reports[] found in {har_path}")


def build_fixture(har_path):
    output = _find_completed_run(har_path)
    merged = {"RPTitleAndGuide": output["titleReport"]["data"]}
    services_manifest = [{"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"}]
    for report in output["reports"]:
        service = report["dataUrl"].rsplit("/", 1)[-1]
        merged[service] = report["data"]
        services_manifest.append({"service": service, "outcome": report["name"], "status": "ok"})
    manifest = {
        "timestamp": "20260727_000000",
        "inputs": {
            "program": output["fundingProgram"],
            "project_type": output["projectType"],
            "selected_outcomes": None,
            "project_line": None,
            "project_name": output["projectName"],
            "jurisdiction": output["jurisdiction"],
            "aadt": output["ADT"],
            "posted_speed": output["postedSpeedLimit"],
            "pci": output["PCI"],
            "email": output["email"],
        },
        "services": services_manifest,
    }
    return manifest, merged


if __name__ == "__main__":
    har_path = sys.argv[1]
    out_dir = sys.argv[2]
    manifest, merged = build_fixture(har_path)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    with open(os.path.join(out_dir, "merged.json"), "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"wrote fixture to {out_dir}")
```

- [ ] **Step 2: Run it against the real HAR to generate the committed fixture**

```bash
python3 testing/local_env/reporting/extract_har_fixture.py "C:\Users\tenoru\Downloads\PPA3_Handoff\atp_ppa_run_submit.har" testing/local_env/tests/fixtures/reporting/har_prod_capture
```

Expected output: `wrote fixture to testing/local_env/tests/fixtures/reporting/har_prod_capture`,
and the two JSON files now exist. Sanity-check the fixture's service list:

```bash
python3 -c "import json; d=json.load(open('testing/local_env/tests/fixtures/reporting/har_prod_capture/manifest.json')); print([s['service'] for s in d['services']])"
```

Expected: `['RPTitleAndGuide', 'RPArtExpVMT', 'RPArtExpCongestion', 'RPArtExpMultiModal', 'RPArtExpEconProsp', 'RPArtExpFreight', 'RPArtExpSafety', 'RPArtSGRSGR', 'RPArtExpEquity']`.

- [ ] **Step 3: Write the structural fidelity test**

Create `testing/local_env/tests/test_reporting_har_fixture.py`:

```python
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, layout_loader

FIXTURE_DIR = os.path.join(HERE, "fixtures", "reporting", "har_prod_capture")

# The 5 services the ATP path dispatches -- the only ones with a layout config as of this plan.
ATP_SERVICES = [
    "RPArtExpVMT",
    "RPArtExpSafety",
    "RPArtExpMultiModal",
    "RPArtExpEconProsp",
    "RPArtSGRSGR",
]


def _load_merged():
    with open(os.path.join(FIXTURE_DIR, "merged.json"), encoding="utf-8") as f:
        return json.load(f)


class TestHarFixtureExists(unittest.TestCase):
    def test_fixture_files_present(self):
        self.assertTrue(os.path.isfile(os.path.join(FIXTURE_DIR, "manifest.json")))
        self.assertTrue(os.path.isfile(os.path.join(FIXTURE_DIR, "merged.json")))

    def test_fixture_is_a_different_project_than_either_golden(self):
        with open(os.path.join(FIXTURE_DIR, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        name = manifest["inputs"]["project_name"]
        self.assertNotIn(name, ("Trell Test", "Active Transportation Program Report Test"))


class TestLayoutConfigsAgainstRealProdCapture(unittest.TestCase):
    """Every card in every ATP layout config must resolve against this REAL prod-captured
    payload -- not just our own local harness's merged.json. This is the structural check
    that replaces the design's original (infeasible) numeric golden-value comparison."""

    def setUp(self):
        self.merged = _load_merged()

    def test_no_missing_fields_in_any_atp_service(self):
        problems = []
        for service in ATP_SERVICES:
            layout = layout_loader.load_layout(service)
            self.assertIsNotNone(layout, f"{service}: no layout config")
            section = cards.build_section(layout, self.merged[service])
            for card in section["cards"]:
                if card["missing"]:
                    problems.append((service, card.get("subtitle")))
        self.assertEqual(problems, [], f"cards with no data against the real prod capture: {problems}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest testing/local_env/tests/test_reporting_har_fixture.py -v`
Expected: all `PASSED`. If `test_no_missing_fields_in_any_atp_service` fails, the failure message
names which service/card — that means a layout config's `source`/`source_chart` field name
doesn't match the real prod capture's key (even though it matched the local harness output) —
fix the YAML, don't relax the test.

- [ ] **Step 5: Run the full reporting suite together**

Run: `python3 -m pytest testing/local_env/tests/ -v -k reporting`
Expected: every `test_reporting_*` test `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add testing/local_env/reporting/extract_har_fixture.py testing/local_env/tests/fixtures/reporting/har_prod_capture testing/local_env/tests/test_reporting_har_fixture.py
git commit -m "reporting: HAR-derived prod-shape fixture + structural fidelity test"
```

---

### Task 12: Manual visual QA against the golden PDF (closes out design build-order step 4)

**Files:** none (manual verification step — no code changes).

**Interfaces:** none.

- [ ] **Step 1: Render the real local ATP run again for a fresh look**

```bash
python3 testing/local_env/reporting/render.py testing/local_env/out/runs/20260729_172109
```

- [ ] **Step 2: Open side by side**

Open `testing/local_env/out/runs/20260729_172109/report.html` in a browser, and
`PPA3_Handoff\report transportion_test.pdf` in a PDF viewer, side by side.

- [ ] **Step 3: Manually confirm, section by section (checklist)**

- [ ] Title page has the same field set (Project name, Jurisdiction, Project type, Funding
      Program, AADT, PCI, Posted Speed Limit, Length, Community Type, UID, Report Generated).
- [ ] "Using This Report" text matches (same 5 paragraphs, same headers).
- [ ] ATP intro page's 5-row objectives table is present and readable (numbers will differ from
      the golden since this is `verify_run`/TestTruxelBridge data, not "ATP Test" — that's
      expected, see the "Correction to the design spec" note; only layout/structure/copy need to
      match).
- [ ] Each of the 5 outcome sections appears in the same order as the golden, with the same
      subtitles/questions/footnotes and the same number of charts/tables/KPIs per section.
- [ ] No section shows "unavailable" and no card shows "(no data)" (Task 10 already asserts this
      automatically, but eyeball it too).

- [ ] **Step 4: Record the result**

If everything in Step 3 checks out, this plan's ATP v1 scope is done — proceed to the
`superpowers:requesting-code-review` workflow per the `writing-plans` skill's normal completion
path (no code change from this task, so nothing to commit). If something looks wrong, open a
follow-up task against the specific layout config file responsible — do not silently accept a
mismatch.

---

## What's next (not part of this plan)

Once Task 12 passes review: build-order steps 5-7 from the design spec (CMCP-only outcome
layout configs for Congestion/Freight/Equity, a CMCP full-8-outcome local harness run for real
test data, a golden-fidelity pass against `report.pdf`, and the Playwright `export_pdf.py`
fast-follow) become their own follow-on plan, written after this one ships.
