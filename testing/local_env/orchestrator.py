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
