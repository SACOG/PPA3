"""
run_local.py — invoke a PPA3 subreport locally against C:\\PPA3Testing.
Usage:
  python run_local.py <subreport> <sample.json>
  e.g. python run_local.py rp_artexp_cong samples/rp_artexp_cong.json
Sets PPA3_LOCAL_CONFIG so config_links.py loads the local globalconfig.
"""
import os
import sys
import json
import importlib
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LOCAL_CONFIG = r"C:\PPA3Testing\globalconfig"
OUT_DIR = os.path.join(HERE, "out")

# subreport -> (folder rel to gp-services, entry module, entry function)
ENTRYPOINTS = {
    "rp_artexp_cong": ("regionalprogram/rp_artexp_cong", "run_congestion_report", "make_congestion_rpt_artexp"),
}

# strings that must NOT appear in the target folder's code/config when running local
FORBIDDEN = ["Arcserverppa-svr", "owner_PPA.sde", "TruncateTable", "DisconnectUser"]


def safety_gate(folder_abs):
    hits = []
    for dp, _, fns in os.walk(folder_abs):
        for fn in fns:
            if not fn.endswith((".py", ".yaml", ".yml")):
                continue
            p = os.path.join(dp, fn)
            with open(p, "r", errors="ignore") as f:
                text = f.read()
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
    result = entry(input_dict=input_dict)

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(OUT_DIR, f"{subreport}_{stamp}.json")
    with open(result) as src, open(dest, "w") as dst:
        dst.write(src.read())
    print(f"OK -> {dest}")


if __name__ == "__main__":
    main()
