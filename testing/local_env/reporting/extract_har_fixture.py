"""extract_har_fixture.py -- pulls the one fully-captured GP-service result payload out of a
PPA3_Handoff/*.har file into a manifest.json + merged.json pair shaped like a Phase-1 harness
run, for use as a real prod-shape fixture in reporting tests.

The captured run is CMCP US50, project "random proj" (Non-Freeway, all 8 outcomes) -- a
different project than either golden PDF ("Trell Test" / "Active Transportation Program Report
Test"), confirmed by inspecting every entry in the HAR: only one response body contains a
completed run with reports[] data. So this fixture validates STRUCTURE (every field/chart name
a layout config references exists in real prod output), not project-level NUMBERS against a
golden PDF.
"""

import json
import os
import sys


def _find_completed_run(har_path):
    with open(har_path, encoding="utf-8") as f:
        har = json.load(f)
    for entry in har["log"]["entries"]:
        text = entry["response"]["content"].get("text", "")
        if not text:
            continue
        try:
            body = json.loads(text)
        except ValueError:
            continue
        results = body.get("results")
        if not results:
            continue
        output = results[0].get("outputs", {}).get("output")
        if isinstance(output, dict) and output.get("reports"):
            return output
    raise ValueError(f"no completed run with reports[] found in {har_path}")


def build_fixture(har_path):
    output = _find_completed_run(har_path)
    merged = {"RPTitleAndGuide": output["titleReport"]["data"]}
    services_manifest = [{"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"}]
    for report in output["reports"]:
        service = report["dataUrl"].rsplit("/", 1)[-1]
        merged[service] = report["data"]
        services_manifest.append({"service": service, "outcome": report["name"], "status": "ok"})
    manifest = {
        "timestamp": "20260727_000000",
        "inputs": {
            "program": output["fundingProgram"],
            "project_type": output["projectType"],
            "selected_outcomes": None,
            "project_line": None,
            "project_name": output["projectName"],
            "jurisdiction": output["jurisdiction"],
            "aadt": output["ADT"],
            "posted_speed": output["postedSpeedLimit"],
            "pci": output["PCI"],
            "email": output["email"],
        },
        "services": services_manifest,
    }
    return manifest, merged


if __name__ == "__main__":
    har_path = sys.argv[1]
    out_dir = sys.argv[2]
    manifest, merged = build_fixture(har_path)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    with open(os.path.join(out_dir, "merged.json"), "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"wrote fixture to {out_dir}")
