r"""
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
