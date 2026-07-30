"""cards.py — pure functions that turn a layout-config "card" spec plus a service's
merged.json data into the context dict each card_*.html.j2 template renders. No I/O, no
arcpy — every function here is testable with synthetic dicts alone.
"""

import json


def _format_value(value, fmt="number"):
    if value is None:
        return "(no data)"
    if fmt == "percent" and isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    if fmt == "number" and isinstance(value, float):
        return f"{value:,.2f}"
    if fmt == "number" and isinstance(value, int):
        return f"{value:,}"
    return str(value)


def build_kpi_card(card_cfg, service_data):
    raw_value = service_data.get(card_cfg["source"])
    return {
        "type": "kpi",
        "sub_outcome": card_cfg.get("sub_outcome"),
        "subtitle": card_cfg.get("subtitle"),
        "question": card_cfg.get("question"),
        "note": card_cfg.get("note"),
        "footnote": card_cfg.get("footnote"),
        "missing": raw_value is None,
        "value_display": _format_value(raw_value, card_cfg.get("value_format", "number")),
    }


def build_table_card(card_cfg, service_data):
    raw = service_data.get(card_cfg["source"])
    missing = raw is None
    fmt = card_cfg.get("value_format", "number")
    rows = []
    if not missing:
        for key, label in card_cfg["row_labels"].items():
            rows.append({"label": label, "value_display": _format_value(raw.get(key), fmt)})
    return {
        "type": "table",
        "subtitle": card_cfg.get("subtitle"),
        "question": card_cfg.get("question"),
        "label": card_cfg.get("label"),
        "footnote": card_cfg.get("footnote"),
        "missing": missing,
        "rows": rows,
    }


def build_chart_card(card_cfg, service_data):
    charts = service_data.get("charts", {})
    raw = charts.get(card_cfg["source_chart"])
    missing = raw is None
    categories = []
    series_data = {s["field"]: [] for s in card_cfg["series"]}
    if not missing:
        for feature in raw["features"]:
            attrs = feature["attributes"]
            categories.append(str(attrs.get(card_cfg["x_field"])))
            for s in card_cfg["series"]:
                series_data[s["field"]].append(attrs.get(s["field"]))
    chart_spec = {
        "categories": categories,
        "series": [
            {"label": s["label"], "data": series_data[s["field"]]}
            for s in card_cfg["series"]
        ],
    }
    return {
        "type": "chart",
        "sub_outcome": card_cfg.get("sub_outcome"),
        "subtitle": card_cfg.get("subtitle"),
        "question": card_cfg.get("question"),
        "note": card_cfg.get("note"),
        "y_label": card_cfg.get("y_label"),
        "footnote": card_cfg.get("footnote"),
        "missing": missing,
        "chart_json": json.dumps(chart_spec),
    }


def build_image_card(card_cfg, service_data):
    # "missing" means the field is structurally absent (a layout-config wiring bug), not that
    # its value happens to be null -- Image Url fields are legitimately null locally (no .aprx
    # staged) without that being an error, so a plain None-check would misclassify every image
    # card in every local run as "missing".
    return {
        "type": "image",
        "caption": card_cfg.get("caption"),
        "url": service_data.get(card_cfg["source"]),
        "missing": card_cfg["source"] not in service_data,
    }


_BUILDERS = {
    "kpi": build_kpi_card,
    "table": build_table_card,
    "chart": build_chart_card,
    "image": build_image_card,
}


def build_card(card_cfg, service_data):
    return _BUILDERS[card_cfg["type"]](card_cfg, service_data)


def build_section(layout_cfg, service_data):
    return {
        "service": layout_cfg["service"],
        "section_title": layout_cfg["section_title"],
        "unavailable": False,
        "cards": [build_card(c, service_data) for c in layout_cfg["cards"]],
    }
