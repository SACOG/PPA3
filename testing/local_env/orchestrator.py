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
import threading
import time
import platform
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dispatch
import config

RUN_LOCAL = os.path.join(HERE, "run_local.py")
DEFAULT_RUNS_ROOT = os.path.join(HERE, "out", "runs")


def _prepare_private_runtime(run_dir):
    """Give this run its own config and archive GDB so concurrent runs cannot lock each other."""
    source_config = str(config.local_config_dir())
    private_config = os.path.join(run_dir, "globalconfig")
    os.makedirs(private_config, exist_ok=True)
    shutil.copy2(os.path.join(source_config, "parameters.py"), private_config)
    with open(os.path.join(source_config, "data_paths.yaml"), encoding="utf-8") as stream:
        paths = yaml.safe_load(stream)

    archive_template = os.path.join(str(config.local_root()), "PPA3Testing_run.gdb")
    private_archive = os.path.join(run_dir, "PPA3Testing_run.gdb")
    shutil.copytree(
        archive_template, private_archive,
        ignore=shutil.ignore_patterns("*.lock", "*.sr.lock"),
    )
    paths["server_data"]["gisdir"]["archived_run_db"] = private_archive
    with open(os.path.join(private_config, "data_paths.yaml"), "w", encoding="utf-8") as stream:
        yaml.safe_dump(paths, stream, sort_keys=False)
    return private_config, private_archive


def _write_sample(inputs, out_dir):
    """Build the run_local sample JSON (keys match run_local's expected raw[...] fields)."""
    sample = {
        "Project_Line": inputs["project_line"],
        "Project_Name": inputs["project_name"],
        "Jurisdiction": inputs["jurisdiction"],
        "Funding_Program": inputs["funding_program"],
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
    timeout = int(os.environ.get("PPA3_SERVICE_TIMEOUT_SECONDS", "1800"))
    try:
        child_env = os.environ.copy()
        child_env["PPA3_LOCAL_CONFIG"] = os.path.join(out_dir, "globalconfig")
        proc = subprocess.run(
            [config.find_arcgis_python(), RUN_LOCAL, service, sample_path],
            capture_output=True, text=True, timeout=timeout, env=child_env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        _cleanup_private_scratch(out_dir, service)
        return ("failed", None, f"TIMEOUT after {timeout}s\n{stdout}\n{stderr}")
    _cleanup_private_scratch(out_dir, service)
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


def _cleanup_private_scratch(run_dir, service):
    prefix = f"scratch_{service}_"
    try:
        names = os.listdir(run_dir)
    except OSError:
        return
    for name in names:
        if not name.startswith(prefix):
            continue
        path = os.path.join(run_dir, name)
        config.assert_within_root(path, run_dir)
        shutil.rmtree(path, ignore_errors=True)


def _write_json_atomic(path, value):
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, path)


def prepare_report(inputs, runs_root=None):
    runs_root = runs_root or DEFAULT_RUNS_ROOT
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = os.path.join(runs_root, stamp)
    os.makedirs(run_dir, exist_ok=True)

    plan = dispatch.resolve_dispatch(
        inputs["program"], inputs["project_type"], inputs.get("selected_outcomes"),
        allow_fixed_override=inputs.get("developer_override", False),
    )
    private_config, private_archive = _prepare_private_runtime(run_dir)
    manifest = {
        "timestamp": stamp,
        "status": "running",
        "report_status": "pending",
        "contract_captured_at": dispatch.LIVE_CONTRACT["captured_at"],
        "environment": {
            "machine": platform.node(),
            "sandbox_root": str(config.local_root()),
            "python": config.find_arcgis_python(),
            "private_config": private_config,
            "private_archive_gdb": private_archive,
        },
        "inputs": {k: v for k, v in inputs.items()},
        "services": [{"service": p["service"], "outcome": p["outcome"], "status": "pending",
                      "duration_seconds": None, "error": None}
                     for p in plan],
    }
    manifest_path = os.path.join(run_dir, "manifest.json")
    _write_json_atomic(manifest_path, manifest)
    _write_sample(inputs, run_dir)
    return run_dir


def execute_report(run_dir, _runner=None):
    runner = _runner or _subprocess_runner
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    sample_path = os.path.join(run_dir, "_sample.json")

    def _flush():
        _write_json_atomic(manifest_path, manifest)

    merged = {}
    for entry in manifest["services"]:
        service = entry["service"]
        entry["status"] = "running"
        entry["started_at"] = dt.datetime.now().isoformat(timespec="seconds")
        _flush()
        started = time.monotonic()
        try:
            status, result_path, log = runner(service, sample_path, run_dir)
        except Exception as exc:
            status, result_path = "failed", None
            log = f"HARNESS RUNNER ERROR: {type(exc).__name__}: {exc}\n"
        entry["duration_seconds"] = round(time.monotonic() - started, 3)
        entry["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
        with open(os.path.join(run_dir, service + ".log"), "w", encoding="utf-8") as f:
            f.write(log or "")
        if result_path and os.path.isfile(result_path):
            try:
                with open(result_path, encoding="utf-8") as f:
                    merged[service] = json.load(f)
            except (OSError, ValueError):
                status = "failed"
                entry["error"] = "service output was not valid JSON"
        if status == "failed" and not entry["error"]:
            entry["error"] = next((line for line in (log or "").splitlines() if line.strip()),
                                  "service did not produce output")
        entry["status"] = status
        _flush()

    _write_json_atomic(os.path.join(run_dir, "merged.json"), merged)
    completion_status = (
        "complete" if all(item["status"] == "ok" for item in manifest["services"])
        else "complete_with_errors"
    )
    manifest["report_status"] = "generating"
    _flush()
    try:
        from reporting import render as report_render
        report_path = report_render.render_report(run_dir)
        manifest["report_status"] = "ok"
        manifest["report_path"] = os.path.basename(report_path)
    except Exception as exc:
        manifest["report_status"] = "failed"
        manifest["report_error"] = f"{type(exc).__name__}: {exc}"
        completion_status = "complete_with_errors"
    manifest["status"] = completion_status
    manifest["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
    _flush()
    return run_dir


def run_report(inputs, runs_root=None, _runner=None):
    """Synchronous entry point used by tests and command-line callers."""
    run_dir = prepare_report(inputs, runs_root)
    return execute_report(run_dir, _runner)


def start_report(inputs, runs_root=None, _runner=None):
    """Create a run immediately and execute it in a background thread for the web UI."""
    run_dir = prepare_report(inputs, runs_root)
    worker = threading.Thread(
        target=execute_report, args=(run_dir, _runner),
        name="ppa-run-" + os.path.basename(run_dir), daemon=True,
    )
    worker.start()
    return run_dir
