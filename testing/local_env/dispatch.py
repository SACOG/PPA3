"""
dispatch.py — the capture-proven PPA dispatch model, as pure data + resolution.

Given a (program, projectType, selected_outcomes), reproduces the ordered
titleReport + reports[] list the live tool sends to its server workflow. No arcpy.

Data is grounded in real run captures (PPA3_Handoff/live_config_*_run.json) and the
tool documentation. See docs/superpowers/specs/2026-07-27-ppa3-test-harness-design.md.
"""

TITLE_SERVICE = "RPTitleAndGuide"

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

# Outcome display-name -> service short-name, per projectType. Program-independent.
_NONFREEWAY = {
    "Multimodal/Transportation Choice (Reduce VMT)":                          "RPArtExpVMT",
    "Multimodal/Transportation Choice (Reduce Congestion)":                   "RPArtExpCongestion",
    "Multimodal/Transportation Choice (Encourage Multimodal Travel)":        "RPArtExpMultiModal",
    "Freight Movement (Economic Prosperity)":                                 "RPArtExpEconProsp",
    "Freight Movement (Freight Mobility)":                                     "RPArtExpFreight",
    "Safety or Security":                                                     "RPArtExpSafety",
    "Maintain State of Good Repair":                                          "RPArtSGRSGR",
    "Benefits to the Transportation Network and Impacted Communities":        "RPArtExpEquity",
}
_FREEWAY = {
    "Multimodal/Transportation Choice (Reduce VMT)":                          "RPFwyExpVMT",
    "Multimodal/Transportation Choice (Reduce Congestion)":                   "RPFwyExpCongestion",
    "Multimodal/Transportation Choice (Encourage Multimodal Travel)":        "RPFwyExpMultiModal",
    "Freight Movement (Economic Prosperity)":                                 "RPFwyExpEconProsp",
    "Freight Movement (Freight Mobility)":                                     "RPFwyExpFreight",
    "Safety or Security":                                                     "RPFwyExpSafety",
}
OUTCOME_SERVICE_MAP = {
    "Non-Freeway Investment": _NONFREEWAY,
    "Freeway Investment":     _FREEWAY,
}

# --- Full ordered outcome catalogs per projectType (dict preserves insertion order) ---
_NF_CATALOG = list(_NONFREEWAY.keys())   # the full 8, in canonical order
_FW_CATALOG = list(_FREEWAY.keys())      # the full 6, in canonical order

# ATP sends a fixed, curated 5 in this exact order (from live_config_atp_run.json).
_ATP_NF_FIXED = [
    "Multimodal/Transportation Choice (Reduce VMT)",
    "Safety or Security",
    "Multimodal/Transportation Choice (Encourage Multimodal Travel)",
    "Freight Movement (Economic Prosperity)",
    "Maintain State of Good Repair",
]

# program -> projectType -> {mode, outcomes}. "selectable" = user picks (checkboxes);
# "fixed" = program predetermines the set. Capture-backed where noted in the spec.
PROGRAM_PRESETS = {
    "STIP": {
        "Non-Freeway Investment": {"mode": "selectable", "outcomes": _NF_CATALOG},
        "Freeway Investment":     {"mode": "selectable", "outcomes": _FW_CATALOG},
    },
    "CMCP US50": {
        "Non-Freeway Investment": {"mode": "selectable", "outcomes": _NF_CATALOG},   # captured
        "Freeway Investment":     {"mode": "selectable", "outcomes": _FW_CATALOG},   # inferred
    },
    "Active Transportation Program": {
        "Non-Freeway Investment": {"mode": "fixed", "outcomes": _ATP_NF_FIXED},      # captured
        # ATP freeway: confirmed n/a (non-freeway only)
    },
    "Regional Federal Funding Program": {
        "Non-Freeway Investment": {"mode": "fixed", "outcomes": _NF_CATALOG},        # captured
        "Freeway Investment":     {"mode": "fixed", "outcomes": _FW_CATALOG},        # captured
    },
}


def _registry_entry(service):
    folder, module, fn = SERVICE_REGISTRY[service]
    return {"folder": folder, "module": module, "entry_function": fn}


def resolve_dispatch(program, project_type, selected_outcomes=None):
    """Return the ordered dispatch list [{outcome, service, folder, module, entry_function}, ...],
    title first — mirroring the live tool's titleReport + reports[]."""
    if program not in PROGRAM_PRESETS:
        raise ValueError(f"unknown program {program!r}; known: {list(PROGRAM_PRESETS)}")
    if project_type not in PROGRAM_PRESETS[program]:
        raise ValueError(f"program {program!r} does not offer project type {project_type!r}")
    preset = PROGRAM_PRESETS[program][project_type]
    catalog = preset["outcomes"]

    if preset["mode"] == "fixed" or selected_outcomes is None:
        outcomes = list(catalog)
    else:
        chosen = set(selected_outcomes)
        outcomes = [o for o in catalog if o in chosen]   # preserve catalog order

    svc_map = OUTCOME_SERVICE_MAP[project_type]
    result = [dict(outcome="(title)", service=TITLE_SERVICE, **_registry_entry(TITLE_SERVICE))]
    for o in outcomes:
        svc = svc_map[o]
        result.append(dict(outcome=o, service=svc, **_registry_entry(svc)))
    return result
