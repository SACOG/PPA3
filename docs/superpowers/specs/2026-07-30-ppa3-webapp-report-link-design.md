# PPA3 Webapp → Report Renderer Link (Design)

> **For agentic workers:** REQUIRED SUB-SKILL: this design is implemented via superpowers:writing-plans
> → superpowers:subagent-driven-development (or executing-plans). This doc is the spec; it is not
> itself the implementation plan.

**Goal:** Connect the two pieces of local-env tooling that currently exist in isolation — the
Flask test-harness webapp (`testing/local_env/webapp/`, lets a user submit project inputs and
dispatch the real `gp-services` Python against local test data) and the report renderer
(`testing/local_env/reporting/`, turns a run's `manifest.json`+`merged.json` into a styled
`report.html`) — so a user can go from "submit a project" to "view a formatted report" without
dropping to a terminal in between.

**Non-goal:** This does not change either piece's existing behavior. The renderer is untouched;
the webapp gets one new route and one new link.

---

## Context

- `testing/local_env/webapp/app.py` is a small Flask app: `/` (submit form), `/run` (POST,
  dispatches `orchestrator.run_report` and redirects to the new run), `/run/<stamp>` (detail page:
  service dispatch order, status, raw per-service JSON), `/runs` (history list).
- It runs under the ArcGIS Pro python env (`arcgispro-py3`) because `orchestrator.run_report`
  shells out to that env per service. Confirmed: `jinja2` (3.1.6) and `pyyaml` (6.0.2) — the
  reporting module's only two dependencies — are already present in that same env, so importing
  `reporting.render` from `app.py` needs no new installs.
- Every run directory (`RUNS_ROOT/<stamp>/`) already contains both `manifest.json` and
  `merged.json` (confirmed against a real run: `testing/local_env/out/runs/20260729_172109/`) —
  exactly the two inputs `render.render_report(run_dir)` needs. No new data plumbing required.
- `reporting.render.render_report(run_dir, output_path=None)` already defaults to writing
  `report.html` into `run_dir` itself and returns the path written.

## Design

**One new route in `app.py`:** `GET /run/<stamp>/report`.

```python
sys.path.insert(0, os.path.join(LOCAL_ENV, "reporting"))
import render as report_render

@app.route("/run/<stamp>/report")
def run_report_view(stamp):
    run_dir = os.path.join(app.config["RUNS_ROOT"], stamp)
    if not os.path.isfile(os.path.join(run_dir, "manifest.json")):
        abort(404)
    try:
        out_path = report_render.render_report(run_dir)
    except (OSError, ValueError, KeyError) as exc:
        abort(500, f"report render failed: {exc}")
    return send_from_directory(run_dir, os.path.basename(out_path))
```

- **Regenerates on every request** (per the approved decision) — `render_report` is a pure
  Jinja2/YAML render with no arcpy and no network I/O, sub-second even for the 5-section ATP
  report. This guarantees a viewed report always reflects the current layout configs, even for an
  old run, with no cache-invalidation logic to write or reason about.
- **404** if the stamp doesn't correspond to a real run (same existence check `run_detail`
  already uses: does `manifest.json` exist).
- **500 with the render error message** if `render_report` itself raises (e.g. `merged.json`
  missing or corrupt for some other reason) — this is a "something's wrong with this specific
  run's data" case, distinct from "unknown stamp." A per-service failure inside a valid run does
  **not** hit this path — `build_sections()`'s existing try/except degrades that to an
  "unavailable" section inside a still-successfully-rendered report, per the report renderer's
  own "never crash" constraint. This route's error handling only covers the outer, whole-run
  failure modes (missing files, unparseable top-level JSON).
- Served via `send_from_directory(run_dir, "report.html")` — Flask serves the just-written file
  directly off disk, no template involved, no second copy held in memory beyond what
  `render_report` already wrote.

**One new link in `templates/detail.html`,** next to the existing nav line:

```html
<p><a href="/">&larr; new run</a> | <a href="/runs">run history</a> | <a href="/run/{{ stamp }}/report">view report</a></p>
```

Not added to `templates/history.html`'s list view — a user is already on the detail page for a
specific run before they'd want its report; keeping the change to the one place avoids touching
the history template's loop structure for a feature that reads naturally as "one more thing you
can do with a run you're already looking at."

## Data Flow

```
user clicks "view report" on /run/<stamp>
  -> GET /run/<stamp>/report
  -> run_dir = RUNS_ROOT/<stamp>
  -> render.render_report(run_dir)          # reads manifest.json + merged.json, writes report.html
  -> send_from_directory(run_dir, "report.html")
  -> browser renders the returned HTML (CSS/JS inline, fully self-contained per the renderer's
     existing offline-asset fix — no additional static-file wiring needed in the webapp)
```

## Error Handling

| Condition | Response |
|---|---|
| Unknown `stamp` (no `manifest.json` in that dir) | 404, matches existing `run_detail` behavior |
| `render_report` raises (missing/corrupt `merged.json`, etc.) | 500 with the exception message |
| One service inside a valid run is malformed/failed | Not an error at this route's level — the report still renders 200, with that section shown as "unavailable" (existing renderer behavior) |

## Testing

Add to `testing/local_env/tests/test_webapp.py`'s existing `TestDashboard` class (runs under the
Pro python env, same as the rest of that file — Flask isn't installed under plain `python3`, this
is a pre-existing, documented, out-of-scope constraint, not something this work changes):

- Extend `setUp` to also write a `merged.json` for the `20260101_000000` fixture run (currently it
  only writes `manifest.json` + a per-service `.json` file; `render_report` needs `merged.json`
  too — at minimum a `RPTitleAndGuide` key with the fields `build_project_context` reads, since
  the fixture's `manifest.json` inputs are minimal).
- `test_report_route_renders_html_for_a_valid_run`: GET `/run/20260101_000000/report`, assert
  200 and that the response contains recognizable report output (e.g. the project name from the
  fixture's inputs, or the "Using This Report" boilerplate heading — something that proves the
  real renderer ran, not a vacuous "response exists" check).
- `test_report_route_404s_for_unknown_stamp`: GET `/run/nonexistent-stamp/report`, assert 404.
- `test_detail_page_links_to_report`: assert `/run/<stamp>/report` appears as an `href` in the
  detail page's HTML.

## Scope Boundary

This does not add a "generate report" step to the `/run` POST flow itself, does not add the link
to `history.html`, does not add any report-specific error page/template (a plain Flask `abort()`
is sufficient, matching the existing app's error-handling style), and does not change anything
inside `testing/local_env/reporting/`.
