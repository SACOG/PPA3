import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, render


class TestRenderHtmlSkeleton(unittest.TestCase):
    def test_renders_section_titles_and_chart_canvas(self):
        layout = {
            "service": "RPArtSGRSGR",
            "section_title": "Maintain State of Good Repair",
            "cards": [
                {"type": "kpi", "source": "ADT", "subtitle": "Average Daily Traffic (ADT)"},
                {
                    "type": "chart",
                    "source_chart": "Jobs and Dwelling",
                    "x_field": "year",
                    "series": [{"field": "jobs", "label": "Jobs"}],
                },
            ],
        }
        data = {"ADT": 15000, "charts": {"Jobs and Dwelling": {"features": [
            {"attributes": {"year": "2020", "jobs": 100}},
        ]}}}
        section = cards.build_section(layout, data)
        html = render.render_html([section], project_title="Test Project")

        self.assertIn("Test Project", html)
        self.assertIn("Maintain State of Good Repair", html)
        self.assertIn("Average Daily Traffic (ADT)", html)
        self.assertIn("15,000", html)
        self.assertIn('class="chart-canvas"', html)
        self.assertIn("chart.umd.min.js", html)

    def test_unavailable_section_renders_placeholder(self):
        section = {"service": "RPArtExpEquity", "section_title": "Equity", "unavailable": True, "cards": []}
        html = render.render_html([section], project_title="Test Project")
        self.assertIn("section-unavailable", html)


if __name__ == "__main__":
    unittest.main()
