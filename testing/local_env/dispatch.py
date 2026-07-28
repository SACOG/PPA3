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
