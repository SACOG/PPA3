# PPA3 Webapp Report Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `GET /run/<stamp>/report` route to the local-env Flask webapp that regenerates
and serves a run's `report.html` via the already-built `reporting.render.render_report()`, plus a
"view report" link on the run-detail page — so a user goes from "submit a project" to "view a
formatted report" without a terminal.

**Architecture:** One new route in `testing/local_env/webapp/app.py` imports
`testing/local_env/reporting/render.py` and calls `render_report(run_dir)` on every request
(regenerate-always, per design decision — the render is sub-second and this guarantees freshness
with zero cache-invalidation logic), then serves the written file via Flask's
`send_from_directory`. One link added to `templates/detail.html`.

**Tech Stack:** Flask (already a dependency of this webapp), the existing `reporting` module
(Jinja2/PyYAML, zero arcpy — already confirmed present in the `arcgispro-py3` env this webapp
runs under).

**Design spec:** `docs/superpowers/specs/2026-07-30-ppa3-webapp-report-link-design.md` — read
this first for full context/rationale; this plan implements it directly, one task.

## Global Constraints

- Repo: `C:\Users\tenoru\Downloads\data_layer_update`, branch `data_layer_update` — never `main`.
- Regenerate `report.html` on every request to `/run/<stamp>/report` — no caching/staleness logic.
- 404 if `<stamp>` doesn't correspond to a real run (no `manifest.json` in that directory) —
  matches the existing `run_detail` route's behavior.
- 500 (with the exception message) if `render_report` itself raises for a whole-run reason
  (missing/corrupt `merged.json`, etc.) — this is distinct from a single service inside a valid
  run being unavailable, which the renderer already handles gracefully (renders 200 with that
  section marked unavailable) and must NOT surface as an error here.
- Tests for this route belong in `testing/local_env/tests/test_webapp.py` and run under the same
  environment the rest of that file already requires (the ArcGIS Pro python env, which has Flask
  installed — plain `python3` does not have Flask, this is a pre-existing constraint, not
  something this plan changes).
- Do not modify anything inside `testing/local_env/reporting/` — this plan only touches the
  webapp.

---

## File Structure

```
testing/local_env/webapp/
  app.py                 # MODIFY: add send_from_directory import, report render import, new route
  templates/detail.html  # MODIFY: add "view report" link
testing/local_env/tests/
  test_webapp.py          # MODIFY: extend TestDashboard fixture with merged.json, add 3 tests
```

---

### Task 1: `/run/<stamp>/report` route + detail-page link

**Files:**
- Modify: `testing/local_env/webapp/app.py`
- Modify: `testing/local_env/webapp/templates/detail.html`
- Modify: `testing/local_env/tests/test_webapp.py`

**Interfaces:**
- Consumes: `reporting.render.render_report(run_dir: str, output_path: str | None = None) -> str`
  (already exists, unchanged — reads `run_dir/manifest.json` + `run_dir/merged.json`, writes
  `run_dir/report.html` by default, returns the path written).
- Produces: `GET /run/<stamp>/report` — no other task depends on this (this plan has one task).

- [ ] **Step 1: Write the failing tests**

Open `testing/local_env/tests/test_webapp.py`. Replace the `TestDashboard` class's `setUp` method
(currently only writes `manifest.json` + one per-service `.json` file) so it also writes a
`merged.json` — `render_report` requires that file to exist, and the current fixture doesn't
create one. Then add three new test methods to the same class. The full updated class:

```python
class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.tmp = tempfile.mkdtemp()
        webapp.app.config["RUNS_ROOT"] = self.tmp
        run_dir = os.path.join(self.tmp, "20260101_000000")
        os.makedirs(run_dir)
        json.dump({"timestamp": "20260101_000000",
                   "inputs": {"program": "STIP", "project_type": "Non-Freeway Investment",
                              "project_name": "t", "jurisdiction": "Sacramento",
                              "aadt": 0, "posted_speed": 0, "pci": 0},
                   "services": [{"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
                                {"service": "RPArtExpSafety", "outcome": "Safety or Security",
                                 "status": "failed"}]},
                  open(os.path.join(run_dir, "manifest.json"), "w"))
        json.dump({"total": 6}, open(os.path.join(run_dir, "RPTitleAndGuide.json"), "w"))
        json.dump({"RPTitleAndGuide": {
                       "Project Length Centerline Miles": 0.5,
                       "Project Community Type": "Established Communities",
                       "Project Unique ID": "test-uid-123",
                   }},
                  open(os.path.join(run_dir, "merged.json"), "w"))

    def test_detail_shows_services_and_statuses(self):
        html = self.client.get("/run/20260101_000000").get_data(as_text=True)
        self.assertIn("RPArtExpSafety", html)
        self.assertIn("failed", html)
        self.assertIn("Safety or Security", html)

    def test_history_lists_the_run(self):
        html = self.client.get("/runs").get_data(as_text=True)
        self.assertIn("20260101_000000", html)

    def test_report_route_renders_html_for_a_valid_run(self):
        resp = self.client.get("/run/20260101_000000/report")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Using This Report", html)
        self.assertIn("t", html)  # project_name from the fixture's inputs

    def test_report_route_404s_for_unknown_stamp(self):
        resp = self.client.get("/run/nonexistent-stamp/report")
        self.assertEqual(resp.status_code, 404)

    def test_detail_page_links_to_report(self):
        html = self.client.get("/run/20260101_000000").get_data(as_text=True)
        self.assertIn('href="/run/20260101_000000/report"', html)
```

Note: `import json, tempfile` already exists near the top of the `TestDashboard` section in this
file (added when `TestDashboard` was first written) — leave it where it is, don't duplicate it.

- [ ] **Step 2: Run tests to verify the three new ones fail**

Run (from the repo root, using the ArcGIS Pro python that has Flask installed):
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_webapp.py -v
```

Expected: `test_detail_shows_services_and_statuses` and `test_history_lists_the_run` still PASS
(unaffected by the `setUp` change). `test_report_route_renders_html_for_a_valid_run` FAILS with
`404 != 200` (no such route exists yet, Flask's own routing 404s it). `test_report_route_404s_for_unknown_stamp`
technically PASSES already by accident (an undefined route also 404s) — that's fine, it'll keep
passing once real per-stamp logic exists; don't worry about it "not really" testing anything yet
at this stage. `test_detail_page_links_to_report` FAILS (`href="/run/20260101_000000/report"` not
found in the page — the link doesn't exist yet).

- [ ] **Step 3: Add the `send_from_directory` import and the `report_render` import**

In `testing/local_env/webapp/app.py`, change line 10:

```python
from flask import Flask, render_template, request, redirect, url_for, abort
```

to:

```python
from flask import Flask, render_template, request, redirect, url_for, abort, send_from_directory
```

Then, directly below the existing `import orchestrator` (currently line 16), add:

```python
sys.path.insert(0, os.path.join(LOCAL_ENV, "reporting"))
import render as report_render
```

- [ ] **Step 4: Add the route**

In `testing/local_env/webapp/app.py`, add this new route directly after the existing
`run_detail` route (currently ends at line 75, right before the `@app.route("/runs")` line):

```python
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

- [ ] **Step 5: Add the detail-page link**

In `testing/local_env/webapp/templates/detail.html`, replace line 4:

```html
<p><a href="/">&larr; new run</a> | <a href="/runs">run history</a></p>
```

with:

```html
<p><a href="/">&larr; new run</a> | <a href="/runs">run history</a> | <a href="/run/{{ stamp }}/report">view report</a></p>
```

- [ ] **Step 6: Run tests to verify everything passes**

Run the same command as Step 2:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest testing/local_env/tests/test_webapp.py -v
```

Expected: all tests in the file `PASSED`, including all 5 in `TestDashboard`.

- [ ] **Step 7: Manual smoke check against a real run**

Run the webapp and confirm the new route works end-to-end against real data, not just the test
fixture:
```powershell
& "C:\Users\tenoru\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" testing\local_env\webapp\app.py
```
Then, in a browser, visit `http://127.0.0.1:5000/run/20260729_172109` (an existing real run
already on disk) and confirm the new "view report" link is present, and clicking it loads a
styled report page with charts. Stop the server (Ctrl+C) when done.

- [ ] **Step 8: Commit**

```bash
git add testing/local_env/webapp/app.py testing/local_env/webapp/templates/detail.html testing/local_env/tests/test_webapp.py
git commit -m "webapp: add /run/<stamp>/report route linking to the report renderer"
```

---

## What's Next (not part of this plan)

Nothing planned — this is a small, complete, self-contained follow-on. If a future need arises
(report link on the history list, a "regenerate" vs. "cached" toggle, PDF export via the
plan-deferred Playwright step), those are separate, future asks.
