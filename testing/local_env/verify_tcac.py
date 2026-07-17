"""
verify_tcac.py - single-file verification + visual report for the TCAC opportunity-score indicator.

What it does (in one run):
  1. Runs the pure-logic UNIT TESTS for _select_max_tcac (no arcpy).
  2. Runs the REAL indicator get_max_tcac() against the local TCAC_2021 layer and a
     test project line (the INPUT data).
  3. Compares the live OUTPUT to a committed GOLDEN reference (a run known to be correct).
  4. Writes a self-contained visual HTML dashboard to out/tcac_verification.html and opens it.

Run (PowerShell, on the SACOG network so the I: project line resolves):
  & "C:\\Users\\tenoru\\AppData\\Local\\Programs\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" testing\\local_env\\verify_tcac.py

Flags:
  --no-open         write the HTML but do not launch a browser
  --update-golden   re-capture the golden reference from the current live run (use only
                    after you have confirmed the run is correct)

Requires: ArcGIS Pro python (arcpy), the local sandbox C:\\PPA3Testing\\PPA3Testing.gdb with
TCAC_2021 (built by build_test_gdb.py), and network access to the I: project-line fixture.
"""

import os
import sys
import io
import json
import html
import argparse
import datetime
import unittest
import webbrowser

# ---- paths -----------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CDP = os.path.join(REPO, "gp-services", "commdesign", "cdp_housingchoice")
TESTS = os.path.join(REPO, "gp-services", "regionalprogram", "tests")
OUT_DIR = os.path.join(HERE, "out")
GOLDEN_PATH = os.path.join(HERE, "tcac_golden.json")

# ---- fixtures (must match tcac_golden.json) --------------------------------
LOCAL_GDB = r"C:\PPA3Testing\PPA3Testing.gdb"
TCAC_FC = "TCAC_2021"
# The project-line fixture. It is auto-staged into the local gdb on the first run that
# has SACOG-network access, so every later run works fully OFFLINE (no I: / VPN needed).
LOCAL_PROJECT_LINE = os.path.join(LOCAL_GDB, "TestTruxelBridge")
NETWORK_PROJECT_LINE = r"I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge"
TOL = 1e-6  # float tolerance for index comparison


# ---- steps -----------------------------------------------------------------
def run_unit_tests():
    """Run the real _select_max_tcac unit tests in-process. Returns a result dict."""
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)
    if CDP not in sys.path:
        sys.path.insert(0, CDP)
    from test_no_server_tasks import TestTcacMaxSelection
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTcacMaxSelection)
    names = [t.id().split(".")[-1] for t in suite]
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    bad = {str(t).split(" ")[0] for t, _ in (res.failures + res.errors)}
    return {
        "ran": res.testsRun,
        "passed": res.testsRun - len(res.failures) - len(res.errors),
        "ok": res.wasSuccessful(),
        "cases": [{"name": n, "ok": n not in bad} for n in names],
    }


def run_live():
    """Run the real indicator against local data. Returns (output_dict, intersecting_polys)."""
    import arcpy
    arcpy.env.overwriteOutput = True
    tcac_path = os.path.join(LOCAL_GDB, TCAC_FC)
    if not arcpy.Exists(tcac_path):
        raise RuntimeError(
            f"{TCAC_FC} not found in local gdb ({LOCAL_GDB}). Run build_test_gdb.py to build it."
        )

    # Resolve the project line: prefer the local staged copy (offline). If it isn't staged
    # yet, copy it from the network fixture (needs SACOG access) so future runs are offline.
    project_line = LOCAL_PROJECT_LINE
    if not arcpy.Exists(project_line):
        if arcpy.Exists(NETWORK_PROJECT_LINE):
            arcpy.management.CopyFeatures(NETWORK_PROJECT_LINE, project_line)
            print(f"  (staged project line into local gdb - future runs are offline)")
        else:
            raise RuntimeError(
                "project line not staged locally and the network fixture is unreachable "
                f"({NETWORK_PROJECT_LINE}). Run once on the SACOG network to stage it, "
                "then it works offline."
            )

    if CDP not in sys.path:
        sys.path.insert(0, CDP)
    import tcac_score
    arcpy.env.workspace = LOCAL_GDB
    output = tcac_score.get_max_tcac(project_line, TCAC_FC)

    lyr = "verify_tcac_lyr"
    if arcpy.Exists(lyr):
        arcpy.management.Delete(lyr)
    arcpy.management.MakeFeatureLayer(TCAC_FC, lyr)
    arcpy.management.SelectLayerByLocation(lyr, "INTERSECT", project_line)
    polys = [{"index_": r[0], "oppcat": r[1]}
             for r in arcpy.da.SearchCursor(lyr, ["index_", "oppcat"])]
    arcpy.management.Delete(lyr)
    return output, polys


def _num_eq(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < TOL


def compare_output(live, golden):
    return {
        "tcac_index": _num_eq(live.get("tcac_index"), golden.get("tcac_index")),
        "tcac_category": live.get("tcac_category") == golden.get("tcac_category"),
    }


def compare_input(live_polys, golden_polys):
    """Order-independent match of the intersecting polygons (the input the indicator saw)."""
    if len(live_polys) != len(golden_polys):
        return False
    lp = sorted(live_polys, key=lambda p: (p["index_"] if p["index_"] is not None else -9e9, p["oppcat"] or ""))
    gp = sorted(golden_polys, key=lambda p: (p["index_"] if p["index_"] is not None else -9e9, p["oppcat"] or ""))
    return all(_num_eq(a["index_"], b["index_"]) and a["oppcat"] == b["oppcat"] for a, b in zip(lp, gp))


# ---- HTML rendering --------------------------------------------------------
def _fmt(v):
    if v is None:
        return "null"
    if isinstance(v, float):
        return f"{v:.8g}"
    return str(v)


def _badge(ok, pass_txt="MATCH", fail_txt="MISMATCH"):
    cls = "ok" if ok else "bad"
    return f'<span class="badge {cls}">{pass_txt if ok else fail_txt}</span>'


def build_html(ctx):
    e = html.escape
    live_err = ctx.get("live_error")
    overall = ctx["overall"]
    ut = ctx["unit"]
    golden = ctx["golden"]

    # unit test rows
    ut_rows = "".join(
        f'<tr><td class="mono">{e(c["name"])}</td><td>{_badge(c["ok"], "PASS", "FAIL")}</td></tr>'
        for c in ut["cases"]
    )

    # input polygons table (live)
    if live_err:
        input_polys_html = f'<p class="err">Could not read live input: {e(live_err)}</p>'
        output_html = '<p class="err">No live output (run did not complete).</p>'
        cmp_html = '<p class="err">Comparison unavailable - the live run did not complete.</p>'
    else:
        live_polys = ctx["live_polys"]
        rows = "".join(
            f'<tr><td class="mono">{_fmt(p["index_"])}</td><td>{e(str(p["oppcat"]))}</td>'
            f'{"<td><span class=chip>max</span></td>" if _num_eq(p["index_"], ctx["live_out"]["tcac_index"]) and p["oppcat"]==ctx["live_out"]["tcac_category"] else "<td></td>"}</tr>'
            for p in sorted(live_polys, key=lambda x: -(x["index_"] if x["index_"] is not None else -9e9))
        )
        input_polys_html = (
            f'<p>Project line intersects <b>{len(live_polys)}</b> TCAC opportunity '
            f'{"area" if len(live_polys)==1 else "areas"}:</p>'
            f'<table><thead><tr><th>index_ (score)</th><th>oppcat (category)</th><th></th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )
        lo = ctx["live_out"]
        output_html = (
            '<div class="kv"><span>tcacIndex</span><b class="mono">' + _fmt(lo["tcac_index"]) + '</b></div>'
            '<div class="kv"><span>tcacCategory</span><b>' + e(str(lo["tcac_category"])) + '</b></div>'
        )
        go = golden["expected_output"]
        cm = ctx["out_cmp"]
        cmp_html = (
            '<table><thead><tr><th>field</th><th>golden (known-correct)</th><th>this run</th><th>result</th></tr></thead><tbody>'
            f'<tr><td>tcac_index</td><td class="mono">{_fmt(go["tcac_index"])}</td><td class="mono">{_fmt(lo["tcac_index"])}</td><td>{_badge(cm["tcac_index"])}</td></tr>'
            f'<tr><td>tcac_category</td><td>{e(str(go["tcac_category"]))}</td><td>{e(str(lo["tcac_category"]))}</td><td>{_badge(cm["tcac_category"])}</td></tr>'
            f'<tr><td>intersecting input</td><td colspan="2">{len(golden["input"]["intersecting_polygons"])} polygons (golden) vs {len(ctx["live_polys"])} (this run)</td><td>{_badge(ctx["in_cmp"])}</td></tr>'
            '</tbody></table>'
        )

    banner = "PASS" if overall else "FAIL"
    ts = ctx["timestamp"]
    gi = golden["input"]

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TCAC Indicator Verification</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#ffffff; --ink:#1a1f2b; --muted:#5b6472; --line:#e4e7ec;
    --ok:#15803d; --okbg:#dcfce7; --bad:#b91c1c; --badbg:#fee2e2; --chip:#e0e7ff; --chipink:#3730a3;
    --accent:#2563eb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0f1420; --card:#161c2b; --ink:#e8ecf4; --muted:#9aa4b6; --line:#26304a;
      --ok:#4ade80; --okbg:#0f2f1c; --bad:#f87171; --badbg:#3a1414; --chip:#1e2a52; --chipink:#a5b4fc; --accent:#60a5fa; }}
  }}
  :root[data-theme="dark"] {{ --bg:#0f1420; --card:#161c2b; --ink:#e8ecf4; --muted:#9aa4b6; --line:#26304a;
    --ok:#4ade80; --okbg:#0f2f1c; --bad:#f87171; --badbg:#3a1414; --chip:#1e2a52; --chipink:#a5b4fc; --accent:#60a5fa; }}
  :root[data-theme="light"] {{ --bg:#f6f7f9; --card:#ffffff; --ink:#1a1f2b; --muted:#5b6472; --line:#e4e7ec;
    --ok:#15803d; --okbg:#dcfce7; --bad:#b91c1c; --badbg:#fee2e2; --chip:#e0e7ff; --chipink:#3730a3; --accent:#2563eb; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; padding:24px; }}
  .wrap {{ max-width:920px; margin:0 auto; }}
  h1 {{ font-size:20px; margin:0 0 2px; }}
  .sub {{ color:var(--muted); font-size:13px; margin-bottom:18px; }}
  .banner {{ border-radius:14px; padding:20px 24px; margin-bottom:20px; display:flex;
    align-items:center; gap:16px; }}
  .banner.pass {{ background:var(--okbg); }}
  .banner.fail {{ background:var(--badbg); }}
  .banner .big {{ font-size:30px; font-weight:800; letter-spacing:.5px; }}
  .banner.pass .big {{ color:var(--ok); }}
  .banner.fail .big {{ color:var(--bad); }}
  .banner .desc {{ color:var(--muted); font-size:13px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media (max-width:680px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 18px; }}
  .card h2 {{ font-size:12px; text-transform:uppercase; letter-spacing:.6px; color:var(--muted);
    margin:0 0 12px; font-weight:700; }}
  .span2 {{ grid-column:1 / -1; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th, td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-weight:600; font-size:12px; }}
  tr:last-child td {{ border-bottom:none; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
  .badge {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:11.5px; font-weight:700; }}
  .badge.ok {{ background:var(--okbg); color:var(--ok); }}
  .badge.bad {{ background:var(--badbg); color:var(--bad); }}
  .chip {{ background:var(--chip); color:var(--chipink); padding:1px 8px; border-radius:999px; font-size:11px; font-weight:700; }}
  .kv {{ display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--line); }}
  .kv:last-child {{ border-bottom:none; }}
  .kv span {{ color:var(--muted); font-size:13px; }}
  .kv b {{ font-size:15px; }}
  .err {{ color:var(--bad); font-size:13.5px; }}
  .meta {{ font-size:12px; color:var(--muted); margin-top:6px; }}
  code {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12.5px;
    background:var(--bg); padding:1px 5px; border-radius:5px; }}
  .foot {{ color:var(--muted); font-size:12px; margin-top:18px; text-align:center; }}
</style></head>
<body><div class="wrap">
  <h1>TCAC Opportunity Score - Indicator Verification</h1>
  <div class="sub">Wishlist: "TCAC score in community design only" &middot; <code>get_max_tcac()</code> in <code>cdp_housingchoice/tcac_score.py</code></div>

  <div class="banner {'pass' if overall else 'fail'}">
    <div class="big">{banner}</div>
    <div class="desc">Test completed {e(ts)}.<br>
      {"Logic tests passed, live run matched the golden reference." if overall else "One or more checks did not match - see below."}</div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>1 &middot; Logic unit tests</h2>
      <div class="kv"><span>_select_max_tcac cases</span><b>{ut["passed"]} / {ut["ran"]} passed {_badge(ut["ok"], "OK", "FAIL")}</b></div>
      <table style="margin-top:8px"><tbody>{ut_rows}</tbody></table>
    </div>

    <div class="card">
      <h2>3 &middot; Live output</h2>
      {output_html}
      <div class="meta">Written to the subreport JSON as <code>tcacIndex</code> / <code>tcacCategory</code>.</div>
    </div>

    <div class="card span2">
      <h2>2 &middot; Input data (what the indicator saw)</h2>
      <div class="meta" style="margin-bottom:8px">Project line: <code>{e(gi["project_line"])}</code> &nbsp;&middot;&nbsp; TCAC layer: <code>{e(gi["tcac_fc"])}</code> (local sandbox)</div>
      {input_polys_html}
    </div>

    <div class="card span2">
      <h2>4 &middot; Comparison vs golden run (known-correct, captured {e(golden.get("captured","?"))})</h2>
      {cmp_html}
    </div>
  </div>

  <div class="foot">Regenerate anytime: <code>verify_tcac.py</code> &middot; golden reference: <code>tcac_golden.json</code></div>
</div>
<script>
  // honor a ?theme=dark/light override if opened that way; otherwise prefers-color-scheme drives it
  var p = new URLSearchParams(location.search).get('theme');
  if (p === 'dark' || p === 'light') document.documentElement.setAttribute('data-theme', p);
</script>
</body></html>"""


# ---- main ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Verify the TCAC indicator and emit a visual report.")
    ap.add_argument("--no-open", action="store_true", help="write HTML but don't open a browser")
    ap.add_argument("--update-golden", action="store_true", help="re-capture golden from this live run")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. unit tests
    unit = run_unit_tests()

    # 2/3. live run
    live_error = None
    live_out = None
    live_polys = None
    try:
        live_out, live_polys = run_live()
    except Exception as ex:  # network/gdb/arcpy problems reported, not crashed
        live_error = f"{type(ex).__name__}: {ex}"

    # --update-golden: capture and exit (only if the run worked)
    if args.update_golden:
        if live_error:
            print(f"cannot update golden - live run failed: {live_error}")
            sys.exit(2)
        golden = {
            "description": "Golden reference for the TCAC opportunity-score indicator.",
            "indicator": "get_max_tcac (gp-services/commdesign/cdp_housingchoice/tcac_score.py)",
            "captured": datetime.date.today().isoformat(),
            "input": {"project_line": PROJECT_LINE, "tcac_fc": TCAC_FC,
                      "intersecting_polygons": live_polys},
            "expected_output": live_out,
        }
        with open(GOLDEN_PATH, "w") as f:
            json.dump(golden, f, indent=2)
        print(f"golden updated -> {GOLDEN_PATH}")
        return

    # load golden + compare
    with open(GOLDEN_PATH) as f:
        golden = json.load(f)

    out_cmp = in_cmp = None
    if not live_error:
        out_cmp = compare_output(live_out, golden["expected_output"])
        in_cmp = compare_input(live_polys, golden["input"]["intersecting_polygons"])

    overall = (
        unit["ok"]
        and not live_error
        and out_cmp is not None and all(out_cmp.values())
        and in_cmp
    )

    ctx = {
        "timestamp": ts, "overall": overall, "unit": unit, "golden": golden,
        "live_error": live_error, "live_out": live_out, "live_polys": live_polys,
        "out_cmp": out_cmp, "in_cmp": in_cmp,
    }
    out_path = os.path.join(OUT_DIR, "tcac_verification.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_html(ctx))

    # terminal summary
    print("=" * 60)
    print("TCAC INDICATOR VERIFICATION")
    print("=" * 60)
    print(f"  logic unit tests : {unit['passed']}/{unit['ran']} passed" + ("" if unit["ok"] else "  <-- FAIL"))
    if live_error:
        print(f"  live run         : ERROR - {live_error}")
    else:
        print(f"  live output      : index={_fmt(live_out['tcac_index'])}  category={live_out['tcac_category']!r}")
        print(f"  input            : {len(live_polys)} intersecting TCAC polygons")
        print(f"  vs golden        : index {'MATCH' if out_cmp['tcac_index'] else 'MISMATCH'}, "
              f"category {'MATCH' if out_cmp['tcac_category'] else 'MISMATCH'}, "
              f"input {'MATCH' if in_cmp else 'MISMATCH'}")
    print("-" * 60)
    print(f"  OVERALL          : {'PASS' if overall else 'FAIL'}")
    print(f"  report           : {out_path}")
    print("=" * 60)

    if not args.no_open:
        webbrowser.open(out_path)
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
