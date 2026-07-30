# PPA3 Phase 2 — Report Renderer — Design Spec

**Date:** 2026-07-30
**Author:** Claude Code (with user, superpowers:brainstorming)
**Status:** Approved design — ready for implementation planning
**Repo under test:** `github.com/SACOG/PPA3`, branch `data_layer_update`
**Builds on:** the Phase-1 test harness (`testing/local_env/`, spec
`docs/superpowers/specs/2026-07-27-ppa3-test-harness-design.md`)

---

## Purpose

Phase 1 produces trustworthy merged GP output (`testing/local_env/out/runs/<stamp>/merged.json`)
but stops there. Phase 2 turns that JSON into an actual **report** — HTML now, PDF as a
fast-follow — that visually matches the real PPA tool's output, without needing VertiGIS, the
portal, or any server access.

## Scope

**In scope (Phase 2 v1):**
- A **full arterial report**: title page + "Using This Report" boilerplate + all 8 arterial
  outcome sections (VMT, Congestion, MultiModal, EconProsp, Freight, Safety, SGR, Equity), in
  dispatch order, rendered as one HTML document per run.
- Charts, KPI numbers, and tables — matched in content/order/labeling to the golden PDFs.
- A fast-follow PDF export of that same HTML via headless-browser print-to-PDF.

**Out of scope (deferred):**
- Map images (title-page location thumbnail, Safety's collision heat map). Both are already
  `null` locally (no staged `.aprx`) — rendered as an empty placeholder box, not solved here.
- Freeway sections (structure unvalidated against a golden — see Phase-1 memory: `fed_run_submit.har`
  captured no result bodies). Revisit once a fresh capture exists.
- Driving the real VertiGIS reporting service — decided against; see "Rejected approaches" below.
- Pixel-exact pagination matching the goldens' exact page breaks — HTML flows continuously; PDF
  page breaks are approximate (CSS `page-break-inside: avoid` per card), not hand-placed to match
  the goldens page-for-page.

---

## Rejected approaches (for the record)

- **Drive the real VertiGIS reporting service** — would require portal.sacog.org credentials and
  reverse-engineering a proprietary report-item format; reintroduces a live-server dependency that
  Phase 1 deliberately avoided. Rejected in favor of a fully local renderer.
- **Export the portal report items** as the layout source — higher fidelity in principle, but
  access/permissions are unconfirmed and could stall the start of Phase 2. Rejected in favor of
  reconstructing layout directly from the golden PDFs (`report.pdf`, `report transportion_test.pdf`),
  which are already in hand and required no new access.
- **WeasyPrint + matplotlib** for rendering — WeasyPrint needs the GTK3 runtime on Windows, a known
  pain point in this environment. Rejected in favor of a headless-browser (Playwright) pipeline,
  which bundles its own Chromium via pip with no system dependency.

---

## Findings from inspecting the golden PDFs (grounds this design)

Extracted via `pypdf` (poppler/pdftoppm unavailable in this environment) against `report.pdf`
(CMCP, "Trell Test", 18 pages, full 8 outcomes) and `report transportion_test.pdf` (ATP,
"Active Transportation Program Report Test", 14 pages, fixed 5 outcomes + ATP intro page):

- **Every chart is a grouped bar chart.** Axis values/labels extract as text (not raster), and each
  page's chart is a vector Form XObject — confirming charts are drawn, not images. This shape maps
  directly onto `merged.json`'s existing `charts: {name: {title, features: [{attributes: {...}}]}}`
  structure: `attributes` keys split cleanly into one categorical field (x-axis: `year`, `type`, …)
  and 1+ numeric fields (series).
- **Only the title page carries a real raster image** (576×384 XObject, `/Subtype /Image`) — a
  location-map thumbnail. Every other page's XObjects are vector Forms. This confirms the "no maps"
  scope decision covers nearly the entire report.
- **Section H1s already exist as data** — `dispatch.py`'s outcome names (e.g.
  `"Multimodal/Transportation Choice (Reduce VMT)"`) are verbatim what's printed as each section
  header in the goldens. No need to re-author these; the renderer sources them from `dispatch.py`.
- **Sub-headers, chart "question" captions, footnotes, and units are NOT present anywhere in the
  JSON** (e.g. "Will the project serve areas with significant growth in jobs and housing?", the
  land-use-diversity-index footnote). These must be hand-transcribed from the goldens into a new
  per-service layout config — this is genuinely new content-authoring work, not something derivable
  from existing code or data.
- Some outcome sections span multiple sub-topics on the goldens (e.g. Economic Prosperity =
  "Increase Job Access" / "Increase School Access" / "Support Ag Economy"; Freight = STAA route
  share + industrial jobs share). These correspond to multiple `charts` entries (or scalar fields)
  within one service's JSON, laid out as a sequence of "cards" within that service's section — not
  separate services.
- Scalar KPI fields exist alongside `charts` (e.g. Safety's `"Total collisions"`,
  `"Collisions per 100 million VMT"`) — the layout config must support a KPI/number card type, not
  just charts.

---

## Data contract (input to the renderer)

Two files from a Phase-1 harness run (`testing/local_env/out/runs/<stamp>/`):

- **`manifest.json`** — supplies the dispatch order (which services fired, in what order) and the
  run inputs (project name, jurisdiction, ADT, PCI, posted speed, funding program) needed for the
  title-page summary table.
- **`merged.json`** — `{ service_short_name: <that service's result JSON> }`. Each service's JSON is
  a mix of:
  - scalar fields (KPIs, e.g. `"Total collisions": 12`)
  - `"<Name> Image Url"` fields (currently always `null` locally — map/heat-map images, out of scope)
  - a `"charts"` dict: `{ chart_name: { "title": str, "features": [ { "attributes": {...} }, ... ] } }`

The renderer does not talk to arcpy, the SDE, or any server — it is pure Python + a static HTML/JS
output, consistent with Phase 1's "no server in the resident process" invariant.

---

## Architecture

```
testing/local_env/out/runs/<stamp>/{manifest.json, merged.json}
        │
        ▼
testing/local_env/reporting/
  layout/<service>.yaml     hand-authored per service: ordered list of "cards"
                             (kpi | table | chart), each with the golden-PDF-only text
                             (subtitle/question, footnote, units, axis labels) + a
                             pointer to the merged.json field/chart name it renders.
  static/report.css         typography/colors matched to the goldens
  static/chart.js            vendored (no CDN — offline-safe), MIT-licensed
  templates/
    report.html.j2          top-level: title page + boilerplate + section loop
    section.html.j2          one outcome section: H1 (from dispatch.py) + its cards
    card_kpi.html.j2 / card_table.html.j2 / card_chart.html.j2
  boilerplate/
    using_this_report.html   verbatim static copy from the goldens
    atp_intro.html           verbatim static copy (ATP-only sections)
  render.py                  CLI: reads a run dir, resolves dispatch order (reuses
                              dispatch.resolve_dispatch, same source of truth as Phase 1),
                              builds the Jinja2 context per section, writes report.html
        │
        ▼
report.html  (open directly in a browser to iterate/compare against the golden PDF)
        │
        ▼ (fast-follow, v1.1)
export_pdf.py   Playwright headless Chromium loads report.html, page.pdf() → report.pdf
```

### Why one generic chart component, not one per metric

Every chart in both goldens is a grouped bar chart over the same `{attributes: {...}}` shape. A
single Chart.js bar-chart component, parameterized by (categorical field, series fields, axis
labels, units) from the layout config, covers 100% of observed charts. This avoids ~15+ bespoke
chart implementations and means adding a new outcome section is authoring data (a layout config
entry), not writing new rendering code.

### Why hand-authored layout configs, not derived from the goldens automatically

The golden-PDF-only text (questions, footnotes, units) has no structured source — it only exists as
prose on the PDF pages. Reconstructing it is inherently manual transcription. The layout config is
the single place this transcription lives, kept small and declarative (YAML) so it's easy to
proofread against the PDF side-by-side and easy to extend per-outcome incrementally.

---

## Layout config format (illustrative — ATP's VMT section, first two cards)

```yaml
service: RPArtExpVMT
section_title_from: dispatch          # H1 sourced from dispatch.py, not repeated here
cards:
  - type: chart
    source: charts["Jobs and Dwelling"]
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
    source: charts["Land Use Diversity"]
    subtitle: "Walk/bike destinations nearby (land use by 2035)*"
    question: "Does the project connect to a mix of land uses that support walking and biking?"
    x_field: type
    series:
      - field: "diversity 2020"
        label: "2020"
      - field: "diversity 2035"
        label: "2035"
    y_label: "Land Use Diversity Index"
    footnote: >
      *The land use diversity index ranges from 0 to 1 and measures an area's ratio of
      households to K-12 student enrollment, park acreage, and employment in the retail,
      service, and food sectors...
```

`render.py` looks up `source` against the service's `merged.json` entry at render time; if the
field/chart is missing, the card renders a "(no data)" placeholder instead of crashing (see Error
handling).

---

## Error handling

Mirrors Phase 1's per-service fault tolerance — one bad section never kills the whole report:

- **Card references a field/chart missing from `merged.json`** (service ran but that particular
  metric came back empty) → render a visible "(no data)" placeholder in that card only.
- **Service in the dispatch order but absent from `merged.json`** (it failed upstream in the
  harness run) → render a "section unavailable" placeholder page in its place, continue with the
  rest of the report.
- **Dispatched service has no layout config yet** (not all 8 outcomes will be authored on day one —
  see build order) → same "section unavailable" fallback + a logged warning, so the renderer never
  hard-crashes as sections are added incrementally.
- **`render.py` itself** fails fast with a clear message if `manifest.json`/`merged.json` are
  missing or malformed — this is a developer-facing CLI, not something that needs to degrade
  gracefully at that level.

---

## Testing / validation

Because the harness's own local run data (e.g. `TestTruxelBridge`) is for a *different project*
than the goldens, section **numbers** can't be diffed directly against a golden PDF from a fresh
local run. Two complementary checks:

1. **Golden fidelity check** — extract the real per-service result JSON for the *same* project as
   each golden (Trell Test/CMCP from `atp_ppa_run_submit.har` — reusing the extraction already done
   in Phase-1 validation, `PPA3_Handoff/atp_ppa_run_submit.har` `job/artifacts` bodies) into a
   `merged.json`-shaped fixture, render it, and manually compare section-by-section (labels, order,
   values, footnotes) against `report.pdf` / `report transportion_test.pdf`.
2. **Generalization check** — render a real local harness `merged.json` (e.g. the ATP
   `TestTruxelBridge` run already on disk, `testing/local_env/out/runs/20260729_172109/`) and
   confirm no crashes and all dispatched sections present, proving the renderer works on the
   harness's actual output shape, not just the golden fixture.
3. **Unit tests (no arcpy)** for the generic chart-spec builder — given a sample `charts["X"]`
   entry + layout config, assert the correct categorical/series fields are extracted — added to the
   existing no-arcpy suite pattern (`gp-services/regionalprogram/tests/test_no_server_tasks.py` or a
   sibling under `testing/local_env/`).

---

## Golden references

- `PPA3_Handoff/report.pdf` — CMCP "Trell Test", 18 pages, full 8 outcomes. Target for the CMCP
  build-order step.
- `PPA3_Handoff/report transportion_test.pdf` — ATP "Active Transportation Program Report Test",
  14 pages, fixed 5 outcomes + ATP intro page. Target for the ATP-first build-order step.
- `PPA3_Handoff/atp_ppa_run_submit.har` — holds the real result JSON for both goldens' projects
  (`job/artifacts` response bodies), the numeric ground truth for the golden fidelity check.
- `testing/local_env/out/runs/20260729_172109/` — real local ATP harness run (6/6 clean:
  Title+VMT+Safety+MultiModal+EconProsp+SGR), the generalization-check fixture.

---

## Build order (for the implementation plan)

1. Vendor Chart.js + base CSS (typography/colors read off the goldens); scaffold
   `testing/local_env/reporting/` module structure + `render.py` skeleton.
2. Author layout configs for the **ATP 6-service set** (Title, VMT, Safety, MultiModal, EconProsp,
   SGR) — clean local data already exists for this set, so this step can validate visually
   immediately.
3. Build the generic chart/table/KPI card templates + section/report templates; wire `render.py` to
   produce `report.html` from a run dir.
4. Golden fidelity check against `report transportion_test.pdf` using the HAR-extracted ATP-project
   JSON; generalization check against the `20260729_172109` local run.
5. Extend layout configs to the remaining CMCP-only outcomes (Congestion, Freight, Equity). Run a
   CMCP Non-Freeway full-8-outcome run through the Phase-1 harness locally to get real test data for
   these (doesn't exist yet — reuses existing Phase-1 code, not new work).
6. Golden fidelity check against `report.pdf` (Trell Test/CMCP) using its HAR-extracted JSON.
7. Fast-follow: `export_pdf.py` (Playwright print-to-PDF of `report.html`).

---

## Open items (non-blocking)

1. **Map placeholders** — title-page thumbnail and Safety's heat map render as empty boxes in v1.
   Staging `PPA3_GIS_SVR.aprx` locally to produce real map images is a separate, unscoped task.
2. **Freeway sections** — not in v1 scope; structure can't be validated against a golden until a
   fresh browser capture of a freeway run with response bodies is taken (per Phase-1 memory).
3. **CMCP full-8 local run doesn't exist yet** — build-order step 5 creates it via the existing
   Phase-1 harness; no new harness code anticipated, but flagging in case dispatch/data gaps surface
   for Congestion/Freight/Equity specifically (these haven't been individually run-validated locally
   before, only Title/VMT/Safety/MultiModal/EconProsp/SGR/Fwy-VMT/Fwy-Cong/etc. per the Phase-1
   memory's clean-run list).
