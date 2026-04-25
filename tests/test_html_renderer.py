import unittest

from services.html_renderer import build_slide_html
from services.layout_engine import build_fallback_instagram_plan, build_instagram_layout_specs


class HtmlRendererTests(unittest.TestCase):
    def test_build_slide_html_contains_layout_content(self):
        plan = build_fallback_instagram_plan(
            [{"title": "5 задач AI-оператора", "body": "Контроль бюджета и минус-слов."}]
        )
        spec = build_instagram_layout_specs(plan)[0]
        html = build_slide_html(spec, logo_text="chu ai")

        self.assertIn("5 задач AI-оператора", html)
        self.assertIn("Контроль бюджета и минус-слов.", html)
        self.assertIn("chu ai", html)
        self.assertIn("<html", html.lower())

    def test_build_slide_html_supports_new_theme_systems(self):
        for theme in ("founder_brief", "growth_black", "research_mono"):
            with self.subTest(theme=theme):
                plan = build_fallback_instagram_plan(
                    [{"title": "Founder note", "body": "Short strategic brief for the next move."}],
                    theme_hint=theme,
                )
                spec = build_instagram_layout_specs(plan)[0]
                html = build_slide_html(spec, logo_text="chu ai")
                self.assertIn("Founder note", html)
                self.assertIn("<style>", html)

    def test_build_slide_html_renders_badges_and_support_cards(self):
        raw_plan = {
            "carousel": {"theme_hint": "research_mono"},
            "slides": [
                {"index": 1, "role": "hook", "title": "Обложка", "body": "Вводный слайд.", "density": "low"},
                {
                    "index": 2,
                    "role": "context",
                    "title": "Фреймворк",
                    "body": "Первый блок, второй блок, третий блок, четвертый блок.",
                    "density": "high",
                },
            ],
        }
        from services.layout_engine import parse_carousel_plan

        spec = build_instagram_layout_specs(parse_carousel_plan(raw_plan))[1]
        html = build_slide_html(spec, logo_text="chu ai")

        self.assertIn("support-card", html)
        self.assertIn("Контекст", html)
        self.assertIn("variant-framework-grid", html)

    def test_build_slide_html_renders_editorial_chrome(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Собрал себе систему знаний", "body": "которая помнит больше, чем я сам."}],
            theme_hint="memory_archive",
        )
        spec = build_instagram_layout_specs(plan, visual_mode="editorial")[0]
        html = build_slide_html(spec, logo_text="Evdokimov AI")

        self.assertIn("variant-editorial-cover", html)
        self.assertIn("editorial-watermark", html)
        self.assertIn("editorial-progress", html)
        self.assertIn("editorial-stage", html)
        self.assertIn("editorial-rail", html)
        self.assertIn("display: none", html)
        self.assertIn(spec.section_label, html)

    def test_build_slide_html_renders_brief_preset(self):
        from services.layout_engine import parse_carousel_plan

        plan = parse_carousel_plan(
            {
                "carousel": {"theme_hint": "founder_brief"},
                "slides": [
                    {
                        "index": 1,
                        "role": "hook",
                        "title": "Product memo",
                        "body": "Фаундер меняет pricing, GTM и roadmap запуска.",
                        "supporting_cards": [{"title": "выбор", "body": "один ICP вместо трех"}],
                    },
                    {"index": 2, "role": "cta", "title": "Финал", "body": "Сохрани карусель."},
                ],
            }
        )
        spec = build_instagram_layout_specs(plan, visual_mode="brief")[0]
        html = build_slide_html(spec, logo_text="chu ai")

        self.assertIn("mode-brief", html)
        self.assertIn("variant-brief-cover", html)
        self.assertIn("editorial-rail-card", html)
        self.assertNotIn('<div class="editorial-tag">', html)

    def test_build_slide_html_renders_data_preset_stat_block(self):
        body = "Каталог доступен через base URL и API key."
        plan = build_fallback_instagram_plan(
            [
                {"title": "NVIDIA открыли 80 моделей", "body": "Подключение через OpenAI-compatible API."},
                {"title": "80 моделей", "body": body},
            ],
            theme_hint="research_mono",
        )
        spec = build_instagram_layout_specs(plan, visual_mode="data")[1]
        html = build_slide_html(spec, logo_text="chu ai")

        self.assertIn("mode-data", html)
        self.assertIn("variant-data-stat", html)
        self.assertIn("data-stat-block", html)
        self.assertEqual(html.count(body), 1)
        self.assertNotIn("Каталог доступен через base URL и API key.…", html)
        self.assertIn("display: none", html)


if __name__ == "__main__":
    unittest.main()
