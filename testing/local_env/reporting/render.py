"""render.py — turns a Phase-1 harness run into report.html. No arcpy dependency; runs
under plain python3.
"""

import json
import os
import sys
from datetime import datetime

import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")
STATIC_DIR = os.path.join(HERE, "static")
sys.path.insert(0, HERE)
import cards  # noqa: E402
import layout_loader  # noqa: E402


def _env():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _load_inline_assets():
    """Read the vendored CSS/JS so they can be inlined into the rendered HTML, making the
    output a genuinely single-file, fully-offline report (see Fix 1: relative static/ paths
    only exist next to templates, not next to a rendered report.html in an arbitrary run_dir).
    """
    with open(os.path.join(STATIC_DIR, "report.css"), encoding="utf-8") as f:
        css = f.read()
    with open(os.path.join(STATIC_DIR, "chart.umd.min.js"), encoding="utf-8") as f:
        js = f.read()
    return css, js


def render_html(sections, project_title, inline_css="", inline_js=""):
    template = _env().get_template("report.html.j2")
    return template.render(
        sections=sections,
        project_title=project_title,
        project={"name": project_title},
        show_atp_intro=False,
        inline_css=inline_css,
        inline_js=inline_js,
    )


def load_run(run_dir):
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    with open(os.path.join(run_dir, "merged.json"), encoding="utf-8") as f:
        merged = json.load(f)
    return manifest, merged


def _format_stamp(stamp):
    dt = None
    for pattern in ("%Y%m%d_%H%M%S_%f", "%Y%m%d_%H%M%S"):
        try:
            dt = datetime.strptime(stamp, pattern)
            break
        except (TypeError, ValueError):
            pass
    if dt is None:
        return "(unknown)"
    return dt.strftime("%A, %B %d, %Y %I:%M %p")


def build_project_context(manifest, merged, report_generated):
    inputs = manifest["inputs"]
    title = merged.get("RPTitleAndGuide", {})
    length = title.get("Project Length Centerline Miles")
    return {
        "name": inputs.get("project_name"),
        "jurisdiction": inputs.get("jurisdiction"),
        "project_type": inputs.get("project_type"),
        "report_program": inputs.get("report_name") or inputs.get("program"),
        "funding_program": inputs.get("funding_program") or inputs.get("program"),
        "aadt": inputs.get("aadt"),
        "pci": inputs.get("pci"),
        "posted_speed": inputs.get("posted_speed"),
        "length_miles": round(length, 2) if length is not None else None,
        "community_type": title.get("Project Community Type"),
        "uid": title.get("Project Unique ID"),
        "report_generated": report_generated,
    }


def build_sections(manifest, merged):
    sections = []
    for entry in manifest.get("services", []):
        service = entry.get("service")
        if not service:
            # Malformed manifest entry -- nothing to key a section on, skip rather than crash.
            continue
        if service == "RPTitleAndGuide":
            continue
        ok = entry.get("status") == "ok" and service in merged
        layout_cfg = layout_loader.load_layout(service) if ok else None
        if ok and layout_cfg is not None:
            try:
                section = cards.build_section(layout_cfg, merged[service])
                section["unavailable"] = False
            except Exception as exc:
                section = _generic_section(
                    service, entry, merged[service],
                    "The specialized layout could not read this result: " + str(exc),
                )
        elif ok:
            section = _generic_section(
                service, entry, merged[service],
                "A specialized local report layout has not been authored for this service yet.",
            )
        else:
            section = {
                "service": service,
                "section_title": entry.get("outcome", service),
                "unavailable": True,
                "unavailable_reason": entry.get("error") or (
                    "The service did not produce a usable result (status: %s)."
                    % entry.get("status", "unknown")
                ),
                "cards": [],
            }
        sections.append(section)
    return sections


def _display_summary(value):
    if value is None:
        return "(no data)"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dict):
        return "Object (%d fields)" % len(value)
    if isinstance(value, list):
        return "List (%d items)" % len(value)
    if isinstance(value, float):
        return f"{value:,.4g}"
    return str(value)


def _generic_section(service, entry, data, reason):
    """Preserve successful output even when a presentation-specific layout is absent/broken."""
    if isinstance(data, dict):
        rows = [
            {"label": str(key), "value_display": _display_summary(value)}
            for key, value in data.items()
        ]
    else:
        rows = [{"label": "Result", "value_display": _display_summary(data)}]
    return {
        "service": service,
        "section_title": entry.get("outcome", service),
        "unavailable": False,
        "generic": True,
        "fallback_reason": reason,
        "summary_rows": rows,
        "raw_json": json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
        "cards": [],
    }


def render_report(run_dir, output_path=None):
    manifest, merged = load_run(run_dir)
    report_generated = _format_stamp(manifest.get("timestamp"))
    project = build_project_context(manifest, merged, report_generated)
    sections = build_sections(manifest, merged)
    show_atp_intro = manifest["inputs"].get("program") == "Active Transportation Program"
    inline_css, inline_js = _load_inline_assets()

    template = _env().get_template("report.html.j2")
    html = template.render(
        sections=sections,
        project_title=project["name"],
        project=project,
        show_atp_intro=show_atp_intro,
        inline_css=inline_css,
        inline_js=inline_js,
    )

    if output_path is None:
        output_path = os.path.join(run_dir, "report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


if __name__ == "__main__":
    out = render_report(sys.argv[1])
    print(f"wrote {out}")
