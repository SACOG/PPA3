r"""
app.py — Flask UI for the PPA3 test harness. No arcpy: it imports dispatch (pure) and calls
orchestrator.run_report, which shells out to the Pro python per service. Run:
  & "...\arcgispro-py3\python.exe" testing\local_env\webapp\app.py   (then open http://127.0.0.1:5000)
"""
import os
import re
import sys
import json

from flask import Flask, render_template, request, redirect, url_for, abort, send_from_directory, jsonify

_STAMP_RE = re.compile(r"^\d{8}_\d{6}(?:_\d{6})?$")

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_ENV = os.path.dirname(HERE)
sys.path.insert(0, LOCAL_ENV)
import dispatch
import orchestrator
import line_registry
sys.path.insert(0, os.path.join(LOCAL_ENV, "reporting"))
import render as report_render

app = Flask(__name__)
app.config["RUN_REPORT"] = orchestrator.start_report
app.config["RUNS_ROOT"] = os.path.join(LOCAL_ENV, "out", "runs")

LINES = line_registry.load()


@app.route("/")
def _render_form(error=None, status=200):
    return render_template(
        "form.html", programs=dispatch.PROGRAMS,
        programs_json=json.dumps(dispatch.PROGRAMS), lines=LINES, error=error,
    ), status


def form():
    return _render_form()


def _parse_nonnegative_int(form_data, name):
    try:
        value = int(form_data.get(name, "0"))
    except (TypeError, ValueError):
        raise ValueError(f"{name.replace('_', ' ').title()} must be a whole number")
    if value < 0:
        raise ValueError(f"{name.replace('_', ' ').title()} cannot be negative")
    return value


def _build_inputs(form_data):
    program_name = form_data.get("program", "")
    if program_name not in dispatch.PROGRAMS:
        raise ValueError("Choose a valid report program")
    program = dispatch.PROGRAMS[program_name]
    project_type = form_data.get("project_type", "")
    if project_type not in program["project_types"]:
        raise ValueError("Choose a project type offered by this program")

    line_key = form_data.get("project_line", "")
    if line_key not in LINES:
        raise ValueError("Choose a registered candidate project line")
    valid_types = LINES[line_key].get("valid_project_types", [])
    if valid_types and project_type not in valid_types:
        raise ValueError(f"{line_key} is not registered for {project_type}")

    project_name = form_data.get("project_name", "").strip()
    if not project_name or not re.fullmatch(r"[A-Za-z0-9 ]+", project_name):
        raise ValueError("Project name may contain only letters, numbers, and spaces")
    jurisdiction = form_data.get("jurisdiction", "").strip()
    if not jurisdiction:
        raise ValueError("Jurisdiction is required")
    email = form_data.get("email", "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address")
    if email != form_data.get("confirm_email", "").strip():
        raise ValueError("Email and Confirm Email must match")

    funding_programs = program["funding_programs"]
    funding_program = form_data.get("funding_program", "")
    if not program["funding_program_visible"]:
        funding_program = funding_programs[0]
    if funding_program not in funding_programs:
        raise ValueError("Choose a valid funding program")

    developer_override = form_data.get("developer_override") == "1"
    selected = form_data.getlist("outcomes")
    return dict(
        program=program_name, report_name=program["report_name"],
        funding_program=funding_program, project_type=project_type,
        selected_outcomes=selected, developer_override=developer_override,
        project_line=LINES[line_key]["fc_path"], project_line_name=line_key,
        project_name=project_name, jurisdiction=jurisdiction,
        aadt=_parse_nonnegative_int(form_data, "aadt"),
        posted_speed=_parse_nonnegative_int(form_data, "posted_speed"),
        pci=_parse_nonnegative_int(form_data, "pci"), email=email,
    )


@app.route("/run", methods=["POST"])
def run():
    try:
        inputs = _build_inputs(request.form)
    except ValueError as exc:
        return _render_form(str(exc), 400)
    run_dir = app.config["RUN_REPORT"](inputs)
    stamp = os.path.basename(run_dir.rstrip("/\\"))
    return redirect(url_for("run_detail", stamp=stamp))


@app.route("/api/dispatch-preview", methods=["POST"])
def dispatch_preview():
    payload = request.get_json(silent=True) or {}
    try:
        plan = dispatch.resolve_dispatch(
            payload.get("program"), payload.get("project_type"),
            payload.get("selected_outcomes"),
            allow_fixed_override=bool(payload.get("developer_override")),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"services": plan})


def _load_run(stamp):
    if not _STAMP_RE.fullmatch(stamp):
        return None, None
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
                with open(jp, encoding="utf-8") as stream:
                    outputs[svc["service"]] = json.dumps(json.load(stream), indent=2)
            except (OSError, ValueError):
                outputs[svc["service"]] = None
    return manifest, outputs


@app.route("/run/<stamp>")
def run_detail(stamp):
    manifest, outputs = _load_run(stamp)
    if manifest is None:
        abort(404)
    return render_template("detail.html", stamp=stamp, manifest=manifest, outputs=outputs)


@app.route("/run/<stamp>/report")
def run_report_view(stamp):
    if not _STAMP_RE.fullmatch(stamp):
        abort(404)
    run_dir = os.path.join(app.config["RUNS_ROOT"], stamp)
    if not os.path.isfile(os.path.join(run_dir, "manifest.json")):
        abort(404)
    if not os.path.isfile(os.path.join(run_dir, "merged.json")):
        abort(409, "report is not ready; the local GP services are still running")
    try:
        out_path = report_render.render_report(run_dir)
    except Exception as exc:
        abort(500, f"report render failed: {exc}")
    return send_from_directory(run_dir, os.path.basename(out_path))


@app.route("/run/<stamp>/artifact/<filename>")
def run_artifact(stamp, filename):
    manifest, _ = _load_run(stamp)
    if manifest is None:
        abort(404)
    allowed = {"manifest.json", "merged.json"}
    for entry in manifest.get("services", []):
        service = entry.get("service")
        if service:
            allowed.update({service + ".json", service + ".log"})
    if filename not in allowed:
        abort(404)
    run_dir = os.path.join(app.config["RUNS_ROOT"], stamp)
    if not os.path.isfile(os.path.join(run_dir, filename)):
        abort(404)
    return send_from_directory(run_dir, filename)


@app.route("/runs")
def history():
    root = app.config["RUNS_ROOT"]
    stamps = sorted([d for d in os.listdir(root)
                     if os.path.isfile(os.path.join(root, d, "manifest.json"))],
                    reverse=True) if os.path.isdir(root) else []
    runs = []
    for stamp in stamps:
        manifest, _ = _load_run(stamp)
        if manifest is None:
            continue
        inputs = manifest.get("inputs", {})
        runs.append({
            "stamp": stamp,
            "project_name": inputs.get("project_name", "(unnamed)"),
            "program": inputs.get("program", "(unknown)"),
            "project_type": inputs.get("project_type", "(unknown)"),
            "status": manifest.get("status", "unknown"),
            "report_status": manifest.get("report_status", "on demand"),
        })
    return render_template("history.html", runs=runs)


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PPA3_PORT", "5000")))
