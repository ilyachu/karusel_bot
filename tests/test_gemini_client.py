import unittest

from services.gemini_client import (
    _cover_plan_looks_english,
    _is_russian_source,
    _looks_english_heavy,
    _sanitize_threads_summary,
)
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
                        "archetype": "hero_center",
                    }
                ],
            }
        )

        self.assertEqual(plan.slides[0].html_body, "<div><h1>Unique</h1></div>")
        self.assertEqual(plan.slides[0].archetype, "hero_center")

        spec = build_instagram_layout_specs(plan, layout_style="magazine")[0]
        self.assertEqual(spec.html_body, "<div><h1>Unique</h1></div>")
        self.assertEqual(spec.archetype, "hero_center")

    def test_is_russian_source_detects_cyrillic_text(self):
        self.assertTrue(_is_russian_source("Привет, это русский текст"))
        self.assertFalse(_is_russian_source("Hello, this is English text"))
        # Mixed with more Russian
        self.assertTrue(_is_russian_source("AI-скиллы для генерации HTML"))

    def test_looks_english_heavy_detects_english_dominant(self):
        self.assertTrue(_looks_english_heavy(
            "HTML as a System Interface. Stop treating HTML as just markup."
        ))
        self.assertFalse(_looks_english_heavy("Просто короткий текст"))
        # Short text is never flagged
        self.assertFalse(_looks_english_heavy("HTML skill"))

    def test_cover_plan_looks_english_flags_english_plan(self):
        english_plan = {
            "headline": "HTML as a System Interface",
            "subtitle": "Stop treating HTML as just markup. It is a structural language for complex logic and visualization.",
            "eyebrow_left": "RESEARCH MONO // VOL. 01",
            "eyebrow_right": "POSTER · TODAY",
            "footer_left": "FOR READERS",
            "cta_text": "",
        }
        self.assertTrue(_cover_plan_looks_english(english_plan))

        russian_plan = {
            "headline": "HTML как система",
            "subtitle": "Хватит считать HTML просто разметкой. Это структурный язык для сложной логики и визуализации.",
            "eyebrow_left": "РАЗБОР · № 01",
            "eyebrow_right": "ПОСТЕР · СЕГОДНЯ",
            "footer_left": "ДЛЯ ЧИТАТЕЛЕЙ",
            "cta_text": "",
        }
        self.assertFalse(_cover_plan_looks_english(russian_plan))


if __name__ == "__main__":
    unittest.main()
