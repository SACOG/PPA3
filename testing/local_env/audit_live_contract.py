"""Compare the checked-in PPA workflow contract with SACOG's public VertiGIS definitions.

This is an optional maintainer check; normal local runs are intentionally offline and use
``live_contract.json``. The command is read-only and never starts a workflow or GP service.
"""

import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORTAL_DATA_URL = (
    "https://portal.sacog.org/portal/sharing/rest/content/items/{item_id}/data?f=json"
)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _expression_source(expression):
    if isinstance(expression, str):
        return expression
    if isinstance(expression, dict):
        return expression.get("source") or expression.get("expression")
    return None


def extract_workflow(payload):
    """Extract the embedded workflowConfiguration JSON and form metadata."""
    config = None
    for node in _walk(payload):
        if node.get("name") != "workflowConfiguration":
            continue
        source = _expression_source(node.get("inputs", {}).get("expression"))
        if source:
            try:
                config = json.loads(source)
            except ValueError:
                continue
    if config is None:
        raise ValueError("workflowConfiguration JSON was not found")

    funding_programs = []
    for form in payload.get("forms", []):
        field = form.get("elements", {}).get("fundingProgramDropDownList")
        if field:
            funding_programs = [
                item.get("value") for item in field.get("items", {}).values()
                if item.get("value")
            ]
            break
    return {
        "report_name": config.get("reportName"),
        "funding_programs": funding_programs,
        "project_types": {
            project["name"]: [
                [report["name"], report.get("dataUrl", "").split("/GPServer/")[0].rsplit("/", 1)[-1]]
                for report in project.get("report", [])
            ]
            for project in config.get("projects", [])
        },
    }


def fetch_item(item_id):
    request = urllib.request.Request(
        PORTAL_DATA_URL.format(item_id=item_id),
        headers={"User-Agent": "PPA3-local-contract-audit/1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def expected_for(program):
    return {
        "report_name": program["report_name"],
        "funding_programs": program["funding_programs"] if program["funding_program_visible"] else [],
        "project_types": {
            name: preset["outcomes"] for name, preset in program["project_types"].items()
        },
    }


def audit(contract):
    differences = []
    for program_name, program in contract["programs"].items():
        item_ids = program.get("workflow_items") or {"all": program["workflow_item"]}
        expected = expected_for(program)
        for variant, item_id in item_ids.items():
            live = extract_workflow(fetch_item(item_id))
            # Some workflows carry a reusable catalog for project types the form does not expose
            # (ATP contains a freeway catalog but its disabled control is fixed to non-freeway).
            # The user-reachable contract is the checked-in project_types set.
            live["project_types"] = {
                name: live["project_types"].get(name)
                for name in expected["project_types"]
            }
            if live != expected:
                differences.append({
                    "program": program_name,
                    "variant": variant,
                    "workflow_item": item_id,
                    "expected": expected,
                    "live": live,
                })
            else:
                print(f"OK  {program_name} / {variant} ({item_id})")
    return differences


def main():
    with open(os.path.join(HERE, "live_contract.json"), encoding="utf-8") as f:
        contract = json.load(f)
    differences = audit(contract)
    if differences:
        print(json.dumps(differences, indent=2))
        print("LIVE CONTRACT DRIFT DETECTED; review before updating the snapshot.")
        return 1
    print("Checked-in contract matches every public live workflow definition.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
