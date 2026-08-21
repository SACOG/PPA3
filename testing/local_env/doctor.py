"""Actionable health check for the PPA3 local test environment."""

import argparse
import importlib.util
import json
import os
import socket
import sys

import config
import dispatch
import run_local
import line_registry


def _check(name, ok, detail, required=True):
    return {"name": name, "ok": bool(ok), "detail": str(detail), "required": required}


def _port_available(port):
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def collect(root=None, port=5000):
    root = os.path.abspath(root or str(config.local_root()))
    checks = []
    try:
        import arcpy
    except Exception as exc:
        arcpy = None
        checks.append(_check("ArcGIS arcpy", False, exc))
    else:
        checks.append(_check("ArcGIS arcpy", True, arcpy.GetInstallInfo().get("Version", "available")))

    for module in ("flask", "jinja2", "yaml"):
        checks.append(_check(f"Python package: {module}", importlib.util.find_spec(module), "installed"))

    required_paths = [
        ("sandbox root", root, os.path.isdir),
        ("input geodatabase", os.path.join(root, "PPA3Testing.gdb"),
         arcpy.Exists if arcpy else os.path.exists),
        ("run geodatabase", os.path.join(root, "PPA3Testing_run.gdb"),
         arcpy.Exists if arcpy else os.path.exists),
        ("local parameters", os.path.join(root, "globalconfig", "parameters.py"), os.path.isfile),
        ("local data paths", os.path.join(root, "globalconfig", "data_paths.yaml"), os.path.isfile),
        ("JSON templates", os.path.join(root, "json_templates"), os.path.isdir),
        ("reference CSVs", os.path.join(root, "CSV"), os.path.isdir),
        ("accessibility rasters", os.path.join(root, "access_tif"), os.path.isdir),
    ]
    for label, path, predicate in required_paths:
        checks.append(_check(label, predicate(path), path))

    registry_root = os.path.join(str(config.REPO_ROOT), "gp-services", "regionalprogram")
    for service, (folder, _, _) in dispatch.SERVICE_REGISTRY.items():
        folder_path = os.path.join(registry_root, folder)
        try:
            run_local.safety_gate(folder_path, exit_on_failure=False)
        except RuntimeError as exc:
            checks.append(_check(f"safety gate: {service}", False, exc))
        else:
            checks.append(_check(f"safety gate: {service}", True, folder))

    lines = line_registry.load(root)
    for name, entry in lines.items():
        path = entry["fc_path"]
        exists = arcpy.Exists(path) if arcpy else os.path.exists(path)
        checks.append(_check(f"candidate line: {name}", exists, path, required=True))

    checks.append(_check(f"port {port}", _port_available(port), "available"))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(config.local_root()))
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    checks = collect(args.root, args.port)
    if args.json:
        print(json.dumps(checks, indent=2))
    else:
        for check in checks:
            marker = "PASS" if check["ok"] else ("WARN" if not check["required"] else "FAIL")
            print(f"{marker:4} {check['name']}: {check['detail']}")
    failures = [check for check in checks if check["required"] and not check["ok"]]
    if failures:
        print(f"\n{len(failures)} required check(s) failed. Run setup.ps1 or address the paths above.")
        return 1
    print("\nPPA3 local environment is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
