import unittest

from services.gemini_client import _sanitize_threads_summary
from services.layout_engine import build_instagram_layout_specs, parse_carousel_plan


class GeminiClientTests(unittest.TestCase):
    def test_sanitize_threads_summary_removes_social_tail(self):
        summary = _sanitize_threads_summary(
            "NVIDIA открыла доступ к 80 моделям через OpenAI-compatible API. "
            "Сохрани, чтобы вернуться позже. #ai"
        )

        self.assertEqual(summary, "NVIDIA открыла доступ к 80 моделям через OpenAI-compatible API")

    def test_sanitize_threads_summary_limits_length(self):
        summary = _sanitize_threads_summary(" ".join(["важный контекст"] * 40))

        self.assertLessEqual(len(summary), 220)
        self.assertTrue(summary.endswith("…"))

    def test_parse_carousel_plan_preserves_slide_html_body(self):
        plan = parse_carousel_plan(
            {
                "carousel": {"layout_style": "magazine"},
                "slides": [
                    {
                        "index": 1,
                        "role": "hook",
                        "title": "AI HTML",
                        "body": "body",
                        "html_body": "<div><h1>Unique</h1></div>",
                    }
                ],
            }
        )

        self.assertEqual(plan.slides[0].html_body, "<div><h1>Unique</h1></div>")

        spec = build_instagram_layout_specs(plan, layout_style="magazine")[0]
        self.assertEqual(spec.html_body, "<div><h1>Unique</h1></div>")


if __name__ == "__main__":
    unittest.main()
