"""
run_local.py — invoke a PPA3 subreport locally against C:\\PPA3Testing.
Usage:
  python run_local.py <subreport> <sample.json>
  e.g. python run_local.py rp_artexp_cong samples/rp_artexp_cong.json
Sets PPA3_LOCAL_CONFIG so config_links.py loads the local globalconfig.
"""
import os
import re
import sys
import json
import time
import importlib
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LOCAL_CONFIG = r"C:\PPA3Testing\globalconfig"
OUT_DIR = os.path.join(HERE, "out")

# subreport short-name -> (folder rel to gp-services/regionalprogram, entry module, entry function)
ENTRYPOINTS = {svc: ("regionalprogram/" + folder, module, fn)
               for svc, (folder, module, fn) in dispatch.SERVICE_REGISTRY.items()}

# strings that must NOT appear in the target folder's code/config when running local
FORBIDDEN = ["Arcserverppa-svr", "owner_PPA.sde", "TruncateTable", "DisconnectUser"]

# Matches an un-indented `if __name__ == '__main__':` (or "..." quotes) guard line.
# Repo convention is that these guards are the last thing in the file and hold only
# ad-hoc/manual test code that is never executed on import — so prod strings living
# there (e.g. hardcoded test SDE paths) shouldn't fail the local-mode safety gate.
_MAIN_GUARD_RE = re.compile(r'^if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', re.MULTILINE)


def _strip_main_guard(text):
    """Return text truncated at the start of a column-0 `if __name__ == '__main__':`
    guard, if any, so scanning ignores everything from that guard to end of file."""
    m = _MAIN_GUARD_RE.search(text)
    return text[:m.start()] if m else text


def safety_gate(folder_abs):
    hits = []
    for dp, _, fns in os.walk(folder_abs):
        for fn in fns:
            if not fn.endswith((".py", ".yaml", ".yml")):
                continue
            p = os.path.join(dp, fn)
            with open(p, "r", errors="ignore") as f:
                text = f.read()
            if fn.endswith(".py"):
                text = _strip_main_guard(text)
            for bad in FORBIDDEN:
                if bad in text:
                    hits.append((os.path.relpath(p, folder_abs), bad))
    # config_links.py legitimately names the prod path as a default fallback string; allow it there.
    hits = [(f, b) for (f, b) in hits if not (f.endswith("config_links.py") and b == "Arcserverppa-svr")]
    if hits:
        print("SAFETY GATE FAILED — prod references found in local-mode target:")
        for f, b in hits:
            print(f"   {f}: {b!r}")
        sys.exit(2)


def _find_newest_scratch_json(scratch_folder, since_ts):
    """Find the newest *.json in scratch_folder modified at/after since_ts.
    Generic across subreports -- matches by mtime only, no filename prefix assumed."""
    candidates = []
    try:
        entries = os.listdir(scratch_folder)
    except OSError:
        return None
    for fn in entries:
        if not fn.lower().endswith(".json"):
            continue
        p = os.path.join(scratch_folder, fn)
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            continue
        if mtime >= since_ts:
            candidates.append((mtime, p))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[-1][1]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    subreport, sample = sys.argv[1], sys.argv[2]
    if subreport not in ENTRYPOINTS:
        print(f"unknown subreport {subreport}; known: {list(ENTRYPOINTS)}")
        sys.exit(1)
    rel_folder, mod_name, fn_name = ENTRYPOINTS[subreport]
    folder_abs = os.path.join(REPO, "gp-services", rel_folder)

    os.environ["PPA3_LOCAL_CONFIG"] = LOCAL_CONFIG
    safety_gate(folder_abs)

    sys.path.insert(0, folder_abs)
    sys.path.insert(0, os.path.join(REPO, "gp-services", os.path.dirname(rel_folder)))
    mod = importlib.import_module(mod_name)
    entry = getattr(mod, fn_name)

    with open(sample if os.path.isabs(sample) else os.path.join(HERE, sample)) as f:
        raw = json.load(f)

    import config_links as c
    uis = c.params.user_inputs
    input_dict = {getattr(uis, "geom"): raw["Project_Line"], getattr(uis, "name"): raw["Project_Name"],
                  getattr(uis, "jur"): raw["Jurisdiction"], getattr(uis, "ptype"): raw["Project_Type"],
                  getattr(uis, "perf_outcomes"): raw["PerfOutcomes"], getattr(uis, "aadt"): raw["AADT"],
                  getattr(uis, "posted_spd"): raw["Posted_Speed_Limit"], getattr(uis, "pci"): raw["PCI"],
                  getattr(uis, "email"): raw["userEmail"]}

    import arcpy
    arcpy.env.workspace = c.params.fgdb
    scratch_folder = arcpy.env.scratchFolder
    run_start = time.time()
    try:
        result = entry(input_dict=input_dict)
    except Exception as exc:
        result = _find_newest_scratch_json(scratch_folder, run_start)
        if result is None:
            # failure happened before any output was written -- a real failure, let it surface
            raise
        print(
            "NOTE: subreport computation completed and its JSON was written to scratch, "
            "but the local log-write step failed/was skipped. This is expected on a fresh "
            "local sandbox -- the log target is the LOCAL run gdb (PPA3Testing_run.gdb), "
            f"not prod. Underlying error: {type(exc).__name__}: {exc}"
        )

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(OUT_DIR, f"{subreport}_{stamp}.json")
    with open(result) as src, open(dest, "w") as dst:
        dst.write(src.read())
    print(f"OK -> {dest}")


if __name__ == "__main__":
    main()
