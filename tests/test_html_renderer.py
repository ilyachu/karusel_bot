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


if __name__ == "__main__":
    unittest.main()
