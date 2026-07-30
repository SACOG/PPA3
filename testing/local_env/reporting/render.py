"""render.py — turns a Phase-1 harness run into report.html.

Task 3 introduces render_html(sections, project_title) — pure templating, no file I/O.
Task 4 adds build_project_context/build_sections/render_report/CLI around it.
"""

import os

import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")


def _env():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(sections, project_title):
    template = _env().get_template("report.html.j2")
    return template.render(sections=sections, project_title=project_title)
