import unittest
from types import SimpleNamespace

from services.html_renderer import build_slide_html
from services.layout_engine import build_fallback_instagram_plan, build_instagram_layout_specs, parse_carousel_plan


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

        self.assertIn("Фреймворк", html)
        self.assertIn("section-label", html)
        self.assertIn("mag-card", html)

    def test_build_slide_html_renders_editorial_chrome(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Собрал себе систему знаний", "body": "которая помнит больше, чем я сам."}],
            theme_hint="memory_archive",
        )
        spec = build_instagram_layout_specs(plan, visual_mode="editorial")[0]
        html = build_slide_html(spec, logo_text="Evdokimov AI")

        self.assertIn("Собрал себе систему знаний", html)
        self.assertIn("Evdokimov AI", html)
        self.assertIn("watermark", html)
        self.assertIn("section-label", html)
        self.assertIn("footer", html)
        self.assertIn("mag-card", html)

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

        self.assertIn("Product memo", html)
        self.assertIn("chu ai", html)
        self.assertIn("mag-card", html)
        self.assertIn("section-label", html)

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

        self.assertIn("80 моделей", html)
        self.assertIn("chu ai", html)
        self.assertIn("html", html.lower())
        self.assertEqual(html.count(body), 1)

    def test_build_slide_html_keeps_custom_background_in_html_renderer(self):
        data_url = "data:image/png;base64,ZmFrZQ=="
        plan = build_fallback_instagram_plan(
            [{"title": "Свой фон", "body": "Типографика остается в выбранном HTML-стиле."}],
            theme_hint="growth_black",
        )
        spec = build_instagram_layout_specs(plan, visual_mode="editorial")[0]

        html = build_slide_html(spec, logo_text="chu ai", custom_background_data_url=data_url)

        self.assertIn("custom-bg", html)
        self.assertIn(data_url, html)
        self.assertIn("Свой фон", html)

    def test_build_slide_html_supports_stronger_background_treatment(self):
        data_url = "data:image/png;base64,ZmFrZQ=="
        plan = build_fallback_instagram_plan(
            [{"title": "Фон заметен", "body": "Пользовательский фон должен читаться визуально сильнее."}],
            theme_hint="growth_black",
        )
        spec = build_instagram_layout_specs(plan, visual_mode="editorial")[0]

        html = build_slide_html(
            spec,
            logo_text="chu ai",
            custom_background_data_url=data_url,
            background_intensity="strong",
        )

        # With custom_bg the background should remain visually prominent:
        # - opacity at least 0.95 (or 1.0) — background should NOT be muted away
        # - no grayscale (was killing color saturation in poster/terminal)
        # - no opaque overlay that hides the user image
        self.assertIn(data_url, html)
        self.assertIn("Фон заметен", html)
        self.assertNotIn("grayscale", html)

    def test_build_slide_html_prefers_ai_html_body_when_present(self):
        data_url = "data:image/png;base64,ZmFrZQ=="
        plan = parse_carousel_plan(
            {
                "carousel": {"layout_style": "poster", "theme_hint": "creator_bold"},
                "slides": [
                    {
                        "index": 1,
                        "role": "hook",
                        "title": "Шаблонный заголовок",
                        "body": "Этот текст не должен попасть в итоговый HTML.",
                        "html_body": (
                            '<section style="font-family: Manrope; background:#101820; color:#f6f1e8; '
                            'width:100%; height:100%; padding:72px;"><h1>AI slide</h1><p>Уникальная вёрстка.</p></section>'
                        ),
                    }
                ],
            }
        )
        spec = build_instagram_layout_specs(plan, layout_style="poster")[0]

        html = build_slide_html(
            spec,
            logo_text="chu ai",
            custom_background_data_url=data_url,
            background_intensity="strong",
        )

        self.assertIn("AI slide", html)
        self.assertIn("Уникальная вёрстка.", html)
        self.assertIn("Manrope", html)
        self.assertIn("justify-content: space-between", html)
        self.assertIn("min-height: 100%", html)
        self.assertIn("ai-texture", html)
        self.assertIn(data_url, html)
        self.assertNotIn("Шаблонный заголовок", html)
        # When custom bg is provided, it must remain visible — no grayscale desaturation
        self.assertNotIn("grayscale", html)

    def test_build_slide_html_falls_back_when_ai_html_body_missing_markup(self):
        plan = parse_carousel_plan(
            {
                "carousel": {"layout_style": "terminal", "theme_hint": "research_mono"},
                "slides": [
                    {
                        "index": 1,
                        "role": "hook",
                        "title": "Фолбэк заголовок",
                        "body": "Фолбэк текст.",
                        "html_body": "просто текст без html",
                    }
                ],
            }
        )
        spec = build_instagram_layout_specs(plan, layout_style="terminal")[0]

        html = build_slide_html(spec, logo_text="chu ai")

        self.assertIn("Фолбэк заголовок", html)
        self.assertIn("ascii-box", html)
        self.assertNotIn("просто текст без html", html)

    def test_build_slide_html_is_backward_compatible_without_html_body_field(self):
        legacy_spec = SimpleNamespace(
            layout_style="magazine",
            title="Legacy",
            body="Legacy body",
            badge_text="Заметка",
            slide_index=1,
            total_slides=2,
            text_position="top",
            theme="memory_archive",
            footer_tags=[],
            supporting_cards=[],
        )

        html = build_slide_html(legacy_spec, logo_text="chu ai")

        self.assertIn("Legacy", html)
        self.assertIn("<html", html.lower())


if __name__ == "__main__":
    unittest.main()
