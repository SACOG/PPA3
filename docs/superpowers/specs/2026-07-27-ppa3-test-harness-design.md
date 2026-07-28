# PPA3 Test Harness (Phase 1 — Orchestrator) — Design Spec

**Date:** 2026-07-27
**Author:** GIS Solutions Architect (with Claude Code, superpowers:brainstorming)
**Status:** Approved design — ready for implementation planning
**Repo under test:** `github.com/SACOG/PPA3`, branch `data_layer_update`
**Builds on:** the Tier-1 local test environment (`testing/local_env/`, designed 2026-07-12/13)

---

## Purpose

Give a SACOG developer a **local, self-serve way to enter project inputs like the real PPA tool,
run the geoprocessing (GP) services that a given program + project type dispatches, and see what
each service did with the data** — without VertiGIS, without touching production, and without
hand-editing JSON per run.

Today's Tier-1 harness (`run_local.py`) runs **one** subreport at a time, from the command line,
against a hand-authored input JSON, for only 2 of the ~15 live subreports. This phase turns that
into a **program-aware orchestrator with a browser UI**: pick a program and project type, pick (or
inherit) performance outcomes, pick a pre-staged project line, hit Run, and get a per-service
status dashboard plus the raw output JSON of every service that fired.

This is **Phase 1 of 2**. Phase 2 (a separate spec) will reverse-engineer the VertiGIS report
templates to render an actual report from the merged output. Phase 1 deliberately stops at
producing and displaying the correct **merged GP output**, which is the input Phase 2 needs.

## Scope

**In scope (Phase 1):**
- A config-driven **dispatch** layer that reproduces, for a chosen (program, project type), the
  exact ordered list of GP services the live tool fires, filtered by selected performance outcomes.
- An **orchestrator** that runs each dispatched service locally (Tier-1 local data) as an isolated
  subprocess, captures status/timing/output, and merges results.
- A local **Flask web app**: input form (with a pre-staged project-line dropdown and outcome
  checkboxes) + a run-history/run-detail dashboard.
- Rolling the `PPA3_LOCAL_CONFIG` switch out to the **15 live** Regional Program (`rp_*`) folders.

**Out of scope (deferred):**
- **Phase 2** — rendering the DevExpress/VertiGIS report templates into a PDF/HTML report.
- **Community Design** (`cdp_*`) subreports — different config mechanism; add later.
- Replicating VertiGIS UI exactly (interactive map draw, program-specific styling).
- Publishing/serving anything beyond localhost.

---

## Architecture (validated against the live tool)

This design is grounded in a live capture of the production tool (browser DevTools HAR of real
CMCP and ATP runs on 2026-07-27), not inference. Verified facts:

- **The browser never calls the GP services directly.** On Run, the browser POSTs a single JSON
  body to a **server-side VertiGIS workflow** (`.../vertigisstudio/workflow/service/job/run`), and
  that workflow — server-side — dispatches to each `.../GPServer/<service>` and polls results back.
- **The POST `/job/run` body carries the full dispatch list** as `inputs.titleReport` +
  `inputs.reports[]`, each entry naming a `dataUrl` (the GP service) and a `dataSourceName` (its
  result-JSON template). The server workflow simply iterates `reports[]`.
- The two captured bodies are saved as reference fixtures:
  `PPA3_Handoff/live_config_cmcp_run.json`, `PPA3_Handoff/live_config_atp_run.json`.

Our Phase-1 orchestrator mirrors this exactly — it **is** a local stand-in for the server workflow:

```
Flask UI (form)
  program + projectType + [outcomes] + project-line choice + name/juris/ADT/PCI/speed/email
        │
        ▼
dispatch.py   reads a workflow-config source; for (program, projectType) returns the ordered
              titleReport + reports[] catalog, filtered to the selected/fixed outcomes.
              Output shape mirrors the live POST /job/run "inputs".
        │
        ▼
orchestrator.py   for each service in order:
                    build input_dict (keys = params.user_inputs.*), set PPA3_LOCAL_CONFIG,
                    run run_local.py <service> as its OWN ArcGIS-Pro-python subprocess
                    (sequential), capture stdout/stderr/exit/timing + the result JSON.
                  writes manifest.json incrementally; builds merged.json at the end.
        │
        ▼
testing/local_env/out/runs/<timestamp>/
   ├── manifest.json         (inputs used, dispatch order, per-service status/timing)
   ├── <service>.json        (raw GP output, one per service that produced output)
   ├── <service>.log         (stdout/stderr/timing for that service)
   └── merged.json           (all services keyed by service name — Phase-2 input)
        │
        ▼
Flask dashboard: run history  →  run detail (per-service status table, dispatch order,
                                  expandable raw JSON, links to logs)
```

### Why subprocess-per-service, sequential

- **Isolation:** every `rp_*` folder ships self-contained copies of same-named modules
  (`run_congestion_report.py`, `config_links.py`, `utils.py`, …). Importing two of them into one
  Python process collides in `sys.modules`. A fresh subprocess per service — which is exactly how
  `run_local.py` already invokes a single subreport — sidesteps this entirely.
- **License/lock safety:** running one arcpy process at a time avoids ArcGIS Pro license-checkout
  contention and local-GDB write locks. A test harness inspected one run at a time does not need
  parallelism; simplicity and safety win. (Parallelism is a possible later optimization, explicitly
  not built now — YAGNI.)

---

## The dispatch model (three layers, proven from live data)

Two independent axes, each proven against the CMCP + ATP captures and the Federal Funding form:

| Layer | Determined by | Evidence |
|---|---|---|
| Which **service** an outcome maps to | **projectType** only (program-independent) | CMCP & ATP both map Safety→`RPArtExpSafety`, SGR→`RPArtSGRSGR`, identically |
| Which **outcomes** are in the report, and whether the user may choose them | **program** | CMCP fired all 8 (user-selectable); ATP fired a fixed 5; Federal shows fixed full sets |

### Service maps (universal per project type)

**Non-Freeway Investment** (`ptype` = `"Non-Freeway Investment"`):

| Outcome | Service | Folder |
|---|---|---|
| Multimodal/Transportation Choice (Reduce VMT) | `RPArtExpVMT` | `rp_artexp_vmt` |
| Multimodal/Transportation Choice (Reduce Congestion) | `RPArtExpCongestion` | `rp_artexp_cong` |
| Multimodal/Transportation Choice (Encourage Multimodal Travel) | `RPArtExpMultiModal` | `rp_artexp_mm` |
| Freight Movement (Economic Prosperity) | `RPArtExpEconProsp` | `rp_artexp_econ` |
| Freight Movement (Freight Mobility) | `RPArtExpFreight` | `rp_artexp_frgt` |
| Safety or Security | `RPArtExpSafety` | `rp_artexp_saf` |
| Maintain State of Good Repair | `RPArtSGRSGR` | `rp_artsgr_sgr` *(cross-family)* |
| Benefits to the Transportation Network and Impacted Communities | `RPArtExpEquity` | `rp_artexp_eq` |
| *(title, always first)* | `RPTitleAndGuide` | `rp_title_guidepg` |

**Freeway Investment** (`ptype` = `"Freeway Investment"`):

| Outcome | Service | Folder |
|---|---|---|
| Multimodal/Transportation Choice (Reduce VMT) | `RPFwyExpVMT` | `rp_fwyexp_vmt` |
| Multimodal/Transportation Choice (Reduce Congestion) | `RPFwyExpCongestion` | `rp_fwyexp_cong` |
| Multimodal/Transportation Choice (Encourage Multimodal Travel) | `RPFwyExpMultiModal` | `rp_fwyexp_mm` |
| Freight Movement (Economic Prosperity) | `RPFwyExpEconProsp` | `rp_fwyexp_econ` |
| Freight Movement (Freight Mobility) | `RPFwyExpFreight` | `rp_fwyexp_frgt` |
| Safety or Security | `RPFwyExpSafety` | `rp_fwyexp_saf` |
| *(title, always first)* | `RPTitleAndGuide` | `rp_title_guidepg` |

(Freeway has no SGR or Impacted-Communities outcome, per the tool documentation.)

### Program presets (outcome set + selection mode)

| Program | Non-Freeway | Freeway | Mode |
|---|---|---|---|
| **STIP** | full 8 | full 6 | user-selectable |
| **CMCP US50** | full 8 *(captured)* | full 6 *(inferred)* | user-selectable |
| **ATP** | fixed 5: VMT, Safety, Multimodal, Econ, SGR *(captured)* | n/a (confirmed — non-freeway only) | fixed |
| **Federal Funding** | fixed 8 *(form screenshot)* | fixed 6 *(form screenshot)* | fixed |

"Fixed" ≠ "curated": Federal is fixed **and full**; ATP is fixed **and curated**. The two axes are
truly independent.

### Why Federal Funding routes through a two-button screen (not cosmetic)

Federal Funding is the only program presented as a **parent** with two child entries
("Federal Funding Non-Freeway / Freeway Investment"); STIP, CMCP, and ATP are single leaf entries.
The reason follows from the fixed-vs-selectable distinction and is load-bearing:

- The project form is a **shared component** with a project-type dropdown + an outcomes area.
- **Selectable** programs (STIP, CMCP) use one form for both types — the type dropdown drives which
  outcome checkboxes appear, so the user enters with either type and can switch live. No pre-selection.
- **Fixed** programs have an outcome set that *depends on project type* (Non-Freeway = fixed 8,
  Freeway = fixed 6). A fixed program offering **both** types cannot render a single pre-filled form
  until the type is known — so Federal resolves the type up front via two buttons, each launching the
  form pre-loaded and locked to that type's fixed outcome set.
- **ATP** is also fixed but offers only **one** type (non-freeway; freeway confirmed n/a by SACOG),
  so it needs no pre-selector — a single button suffices. This is corroborating evidence for the rule.

**Harness implication:** dispatch is unchanged (projectType→services, program→outcome-set), but the
harness records Federal as **two reportName variants** ("Federal Funding Non-Freeway Investment" /
"Federal Funding Freeway Investment"), not one, matching the tool. `PROGRAM_PRESETS` already keys by
(program, projectType), so both resolve correctly. This explanation is reasoned from observed
behavior; the menu definition lives in the VertiGIS viewer-app config (not in the captured HARs).
A Federal run capture would confirm the exact reportName strings.

---

## Components

### 1. `dispatch.py` (new; pure Python, no arcpy)

Single source of truth for "what fires." No hard-coded project-type logic in the orchestrator.

- **`load_workflow_config(path)`** — parses a workflow-config JSON. Must tolerate the repo files'
  leading `={` prefix and the two observed schema shapes (`stip_config.json` and
  `wfconfig_regpgm_*.json`). Default path: repo `gp-services/workflow-configs/stip2025/stip_config.json`,
  validated against the live CMCP/ATP captures and two real report PDFs.
- **`SERVICE_REGISTRY`** — static table mapping each service short-name (e.g. `RPArtExpVMT`) →
  `(folder, entry_module, entry_function)`. Folds in and replaces `run_local.py`'s current
  `ENTRYPOINTS` dict so there is one registry, not two. 15 live rows (see service maps above).
- **`PROGRAM_PRESETS`** — the four-program table above, as data: per (program, projectType), the
  ordered outcome list + a `mode` of `"selectable"` or `"fixed"`. Seeded from the captures/screenshots;
  editable. Presets whose data we only inferred (CMCP-Freeway) or that are program-absent (ATP-Freeway)
  are marked so in comments.
- **`resolve_dispatch(program, project_type, selected_outcomes=None)`** → ordered list of
  `(outcome_name, service_short_name, folder, entry_module, entry_function)`, title first. For
  `"selectable"` programs it filters the catalog by `selected_outcomes`; for `"fixed"` it ignores the
  argument and returns the preset set. This is the exact `titleReport + reports[]` the live tool sends.

Pure logic → fully unit-testable without arcpy or a server.

### 2. `PPA3_LOCAL_CONFIG` roll-out (15 `rp_*` `config_links.py` files)

Apply the **identical** env-var override already proven in `rp_artexp_cong`/`rp_artexp_vmt`
(Task 2 of the Tier-1 plan) to the remaining **13** live folders. The switch: when
`PPA3_LOCAL_CONFIG` is set, `config_dir` resolves to the local globalconfig; unset → production,
byte-for-byte unchanged. The 4 non-live folders (`rp_artexp_sgr`, `rp_artsgr_{cong,econ,frgt}`) are
**not** wired now — no live program dispatches them; add on demand if a future config references them.

### 3. `orchestrator.py` (new)

- **`run_report(inputs)`** — `inputs` is a dict mirroring the live `/job/run` body
  (program, projectType, outcomes, projectLine path, name, jurisdiction, ADT, PCI, speed, email).
- Calls `dispatch.resolve_dispatch(...)`, creates `out/runs/<timestamp>/`, writes an initial
  `manifest.json` (status `pending` per service).
- For each service in order: invokes `run_local.py <service> <generated-sample.json>` as an ArcGIS
  Pro python **subprocess** (reusing the existing runner + its pre-run safety gate), captures
  stdout/stderr/exit/timing to `<service>.log`, copies the produced result JSON to `<service>.json`,
  updates that service's entry in `manifest.json` to `ok`/`failed(reason)` **incrementally** (so the
  dashboard can show progress mid-run).
- After all services: assembles `merged.json` = `{ service_short_name: <its result JSON> }` for the
  Phase-2 renderer.
- **Input translation** is centralized here: map the UI/`inputs` fields to the `params.user_inputs.*`
  keys each `make_*(input_dict)` expects (`geom`, `name`, `jur`, `ptype`, `perf_outcomes`, `aadt`,
  `posted_spd`, `pci`, `email`), exactly as `run_local.py` does today.

### 4. Sample project-line library

- **`testing/local_env/samples/lines.json`** — registry: `name → { fc_path, valid_project_types }`.
  Seeded with `TestTruxelBridge` (the known-good line already used by Tier-1) plus 1–2 more staged
  from the shared `I:` drive (or the local GDB). Drives the form's line dropdown. No in-browser map
  or geometry drawing — a dropdown of pre-staged feature classes only (chosen deliberately; the GP
  logic only cares about the resulting geometry, not how it was drawn).

### 5. Flask web app (`testing/local_env/webapp/`)

Runs under the same ArcGIS Pro python env as the rest of Tier-1; launched via PowerShell per the
established convention. Localhost only. Pages:

- **Input form** — program dropdown (STIP/CMCP/ATP/Federal); project-type dropdown
  (Non-Freeway/Freeway); performance-outcome checkboxes with an **All/None** control; when a fixed-mode
  program is chosen the checkboxes pre-fill and lock to its preset (with a "load preset" affordance —
  the dev may still unlock to test arbitrary combinations, since this is a test tool); project-line
  dropdown; text/number fields for name, jurisdiction, ADT, PCI, posted speed, email. On submit →
  `orchestrator.run_report(...)`.
- **Run view** — polls `manifest.json`, shows the dispatch order and each service's live status as it
  runs.
- **Run history / run detail** — lists past `out/runs/*`; detail page shows the per-service status
  table, timings, the dispatch order that fired, expandable raw output JSON, and log links.

The "visualization of what GP services are called for what report type" the user asked for **is** the
run-detail page: the dispatch order + per-service status + raw output, driven straight off
`dispatch.resolve_dispatch`.

---

## Error handling

- A service subprocess that fails (e.g. the **known** local log-write failure documented in the
  Tier-1 README — `PPA3Testing_run.gdb` lacks the archive tables) is caught, recorded in `manifest.json`
  as `failed` with the captured reason, and **the run continues**. One failing service never kills the
  dashboard or the other services. `run_local.py` already recovers the result JSON from scratch when the
  post-computation log-write fails; the orchestrator surfaces that as `ok (log-write skipped)`.
- The `run_local.py` **safety gate** (refuses to run if prod strings appear outside the allowed
  `config_links.py` fallback) runs before every service. Prod-safety invariant from Tier-1 is preserved:
  local mode never opens the SDE and never writes the production run gdb.
- Dispatch errors (unknown program/type, a service in the config with no `SERVICE_REGISTRY` row) fail
  fast with a clear message **before** any subprocess starts.

---

## Testing

- **`dispatch.py`** — unit tests in the existing no-arcpy suite
  (`gp-services/regionalprogram/tests/test_no_server_tasks.py` or a sibling):
  - Feeding the CMCP capture's (program, projectType, all-outcomes) reproduces its captured
    `reports[]` service list exactly (order included).
  - Feeding the ATP capture's (program=ATP, projectType, fixed) reproduces its captured 5-service list.
  - Outcome filtering: STIP/CMCP with a 2-outcome selection yields exactly those + title.
  - Federal Non-Freeway/Freeway presets resolve to full 8 / full 6.
  - Every `SERVICE_REGISTRY` folder + entry function exists on disk.
- **`orchestrator.py`** — one arcpy-gated smoke test: a 2-service Non-Freeway run against the local
  sandbox produces a run folder with a `manifest.json`, both `<service>.json` files, and a `merged.json`.
- **Config parsing** — a test that `load_workflow_config` handles the `={` prefix and both schema shapes.

---

## Golden references (for Phase 2, captured now)

- `PPA3_Handoff/report.pdf` — real "Trell Test" report, CMCP, Non-Freeway, all 9 sections.
- `PPA3_Handoff/report transportion_test.pdf` — real ATP report, Non-Freeway, 5 outcomes + ATP intro page.
- `PPA3_Handoff/live_config_cmcp_run.json`, `live_config_atp_run.json` — exact input contracts.
- `PPA3_Handoff/atp_ppa_run_submit.har` — full run capture; its `job/artifacts` responses likely hold
  the actual per-service **result JSONs** the tool received — the ground-truth Phase-2 will render.

---

## Open items (non-blocking)

1. **Federal Funding & CMCP-Freeway not run-captured.** Their presets come from screenshots/inference,
   not a HAR. Faithful, but a future run capture would confirm dataSourceName/reportUrl strings and the
   exact Federal reportName variants. Presets are editable data, so any correction is a one-line change.
2. **ATP-Freeway — confirmed n/a** by SACOG (ATP is non-freeway/bike-ped only). No preset needed.
3. **Live workflow config is authored in VertiGIS Designer, not on the file share** (confirmed by an
   exhaustive name+content search of `\\Arcserverppa-svr\...\PPA_03_01`, and by the captured workflow
   items being execution definitions that `ForEach` over the browser-supplied `reports[]`, not menus).
   `stip_config.json` + the captures are the validated stand-in. If the live 4-program config is ever
   exported (browser DevTools or VertiGIS), drop it in and point `dispatch.load_workflow_config` at it —
   no code change.
4. **`project_master`/`rp_*` archive tables** are absent from the local run gdb, so the log-write step
   fails locally (expected, prod-safe — it runs *after* the result JSON is written and targets the local
   empty gdb, never production). **Now resolvable:** with VPN access, the real table schemas can be read
   read-only from the production `PPA3_run_data.gdb` and recreated as empty local tables, enabling a
   fully clean end-to-end local run through the log write. Previously deferred only because the schemas
   were unspecified; reading them from prod removes that blocker. Optional add-on to the plan.

---

## Build order (for the implementation plan)

1. `dispatch.py` — `SERVICE_REGISTRY` (15 rows) + `PROGRAM_PRESETS` (4 programs) + `resolve_dispatch`
   + `load_workflow_config`; unit tests green against the CMCP/ATP captures.
2. Roll `PPA3_LOCAL_CONFIG` into the 13 remaining live `config_links.py` files; verify local resolves
   local and prod resolves prod for each.
3. `orchestrator.py` — run folder, incremental manifest, subprocess loop reusing `run_local.py`, merged
   output; arcpy-gated smoke test on a 2-service Non-Freeway run.
4. `samples/lines.json` + stage 1–2 sample lines.
5. Flask app — form → orchestrator; run view; run history/detail dashboard.
6. End-to-end: run CMCP Non-Freeway (all outcomes) and ATP Non-Freeway (its 5) through the UI; confirm
   dispatch order matches the captures and every service's output JSON lands in the run folder.
