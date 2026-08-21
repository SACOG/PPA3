"""
dispatch.py — the capture-proven PPA dispatch model, as pure data + resolution.

Given a (program, projectType, selected_outcomes), reproduces the ordered
titleReport + reports[] list the live tool sends to its server workflow. No arcpy.

Data is grounded in real run captures (PPA3_Handoff/live_config_*_run.json) and the
tool documentation. See docs/superpowers/specs/2026-07-27-ppa3-test-harness-design.md.
"""

import json
import os
import re

TITLE_SERVICE = "RPTitleAndGuide"
HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT_PATH = os.path.join(HERE, "live_contract.json")


def load_contract(path=CONTRACT_PATH):
    with open(path, encoding="utf-8") as f:
        contract = json.load(f)
    if contract.get("schema_version") != 1:
        raise ValueError("unsupported live-contract schema")
    return contract


LIVE_CONTRACT = load_contract()

# service short-name -> (folder, entry_module, entry_function)
SERVICE_REGISTRY = {
    "RPTitleAndGuide":    ("rp_title_guidepg", "run_title_guidepg",         "make_title_guidepg_regpgm"),
    "RPArtExpVMT":        ("rp_artexp_vmt",     "run_vmt_report",            "make_vmt_report_artexp"),
    "RPArtExpCongestion": ("rp_artexp_cong",    "run_congestion_report",     "make_congestion_rpt_artexp"),
    "RPArtExpMultiModal": ("rp_artexp_mm",      "run_artexp_mm_report",      "make_mm_report_artexp"),
    "RPArtExpEconProsp":  ("rp_artexp_econ",    "run_econprosp_report",      "make_econ_report_artexp"),
    "RPArtExpFreight":    ("rp_artexp_frgt",    "run_artexp_freight_report", "make_frgt_report_artexp"),
    "RPArtExpSafety":     ("rp_artexp_saf",     "run_artexp_safety_report",  "make_safety_report_artexp"),
    "RPArtSGRSGR":        ("rp_artsgr_sgr",     "run_artsgr_sgr_report",     "make_sgr_report_artsgr"),
    "RPArtExpEquity":     ("rp_artexp_eq",      "run_equity_report",         "make_equity_rpt_artexp"),
    "RPFwyExpVMT":        ("rp_fwyexp_vmt",     "run_vmt_report",            "make_vmt_report_fwyexp"),
    "RPFwyExpCongestion": ("rp_fwyexp_cong",    "run_congestion_report",     "make_congestion_rpt_fwyexp"),
    "RPFwyExpMultiModal": ("rp_fwyexp_mm",      "run_mm_report",             "make_mm_report_fwyexp"),
    "RPFwyExpEconProsp":  ("rp_fwyexp_econ",    "run_econprosp_report",      "make_econ_report_fwyexp"),
    "RPFwyExpFreight":    ("rp_fwyexp_frgt",    "run_fwy_freight_report",    "make_freight_rept_fwyexp"),
    "RPFwyExpSafety":     ("rp_fwyexp_saf",     "run_fwyexp_safety_report",  "make_safety_report_fwyexp"),
}

# Outcome display-name -> service short-name, per projectType. The current live definitions agree
# across programs; validate that invariant while building this convenience map.
def _build_outcome_map():
    result = {}
    for program in LIVE_CONTRACT["programs"].values():
        for project_type, preset in program["project_types"].items():
            mapping = dict(preset["outcomes"])
            current = result.setdefault(project_type, {})
            for outcome, service in mapping.items():
                if outcome in current and current[outcome] != service:
                    raise ValueError(
                        f"live contract disagrees for {project_type!r} / {outcome!r}"
                    )
                current[outcome] = service
    return result


OUTCOME_SERVICE_MAP = {
    **_build_outcome_map(),
}

PROGRAMS = LIVE_CONTRACT["programs"]
PROGRAM_PRESETS = {
    program_name: {
        project_type: {
            "mode": preset["mode"],
            "outcomes": [outcome for outcome, _ in preset["outcomes"]],
        }
        for project_type, preset in program["project_types"].items()
    }
    for program_name, program in PROGRAMS.items()
}


def _registry_entry(service):
    folder, module, fn = SERVICE_REGISTRY[service]
    return {"folder": folder, "module": module, "entry_function": fn}


def resolve_dispatch(program, project_type, selected_outcomes=None, allow_fixed_override=False):
    """Return the ordered dispatch list [{outcome, service, folder, module, entry_function}, ...],
    title first — mirroring the live tool's titleReport + reports[]."""
    if program not in PROGRAM_PRESETS:
        raise ValueError(f"unknown program {program!r}; known: {list(PROGRAM_PRESETS)}")
    if project_type not in PROGRAM_PRESETS[program]:
        raise ValueError(f"program {program!r} does not offer project type {project_type!r}")
    preset = PROGRAM_PRESETS[program][project_type]
    catalog = preset["outcomes"]

    if (preset["mode"] == "fixed" and not allow_fixed_override) or selected_outcomes is None:
        outcomes = list(catalog)
    else:
        chosen = set(selected_outcomes)
        outcomes = [o for o in catalog if o in chosen]   # preserve catalog order

    svc_map = dict(PROGRAMS[program]["project_types"][project_type]["outcomes"])
    result = [dict(outcome="(title)", service=TITLE_SERVICE, **_registry_entry(TITLE_SERVICE))]
    for o in outcomes:
        svc = svc_map[o]
        result.append(dict(outcome=o, service=svc, **_registry_entry(svc)))
    return result


# stip_config.json uses projectType name "Non-Freeway Investment"; older wfconfig_regpgm files
# use "Arterial or Transit Expansion" etc. We only need the two names our maps use, so we map
# the config's project "name" through this alias table; unknown names pass through unchanged.
_PTYPE_ALIASES = {
    "Non-Freeway Investment": "Non-Freeway Investment",
    "Freeway Investment": "Freeway Investment",
    "Arterial or Transit Expansion": "Non-Freeway Investment",
    "Freeway Expansion": "Freeway Investment",
}
_SVC_RE = re.compile(r"services/(\w+)/GPServer")


def load_workflow_config(path):
    """Parse a workflow-config JSON (tolerating a leading '=' and either schema shape) into
    {projectType: [(outcome_name, service_short), ...]}. Used to cross-check / regenerate
    OUTCOME_SERVICE_MAP if a live config is ever dropped in."""
    with open(path, "r", encoding="ascii", errors="ignore") as f:
        text = f.read()
    text = text.lstrip().lstrip("=").strip()
    data = json.loads(text)
    out = {}
    for proj in data.get("projects", []):
        ptype = _PTYPE_ALIASES.get(proj.get("name"), proj.get("name"))
        pairs = []
        for rep in proj.get("report", []):
            m = _SVC_RE.search(rep.get("dataUrl", ""))
            if m:
                pairs.append((rep.get("name"), m.group(1)))
        out[ptype] = pairs
    return out
