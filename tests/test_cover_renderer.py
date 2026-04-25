import unittest

from services.cover_renderer import (
    COVER_AUTHOR,
    COVER_FORMATS,
    COVER_STYLES,
    CoverPlan,
    build_cover_html,
    image_bytes_to_data_url,
    normalize_cover_plan,
    render_cover_html,
)


class CoverRendererTests(unittest.TestCase):
    def test_normalize_cover_plan_defaults_and_author(self):
        plan = normalize_cover_plan(
            {"headline": "", "footer_right": "@other", "symbol": "unknown"},
            "Как разработчику перейти от git push до прода. Семь шагов без хаоса.",
            "unknown",
            "unknown",
        )

        self.assertTrue(plan.headline)
        self.assertEqual(plan.style, "orange_poster")
        self.assertEqual(plan.format_key, "post")
        self.assertEqual(plan.footer_right, COVER_AUTHOR)
        self.assertEqual(plan.symbol, "arrow")

    def test_build_cover_html_contains_style_classes_and_format_size(self):
        for style in COVER_STYLES:
            with self.subTest(style=style):
                plan = CoverPlan(
                    headline="<От git push до прода>",
                    subtitle="Короткий маршрут",
                    eyebrow_left="ГАЙД · № 01",
                    eyebrow_right="07 ШАГОВ · ВЕЧЕР",
                    footer_left="ДЛЯ РАЗРАБОТЧИКОВ",
                    symbol="arrow",
                    style=style,
                    format_key="wide",
                )
                html = build_cover_html(plan)

                self.assertIn(f'width: {COVER_FORMATS["wide"]["width"]}px', html)
                self.assertIn(f'height: {COVER_FORMATS["wide"]["height"]}px', html)
                self.assertIn(f"cover-{style.replace('_', '-')}", html)
                self.assertIn("&lt;От git push до прода&gt;", html)
                self.assertIn("chu_il", html)

    def test_retro_polaroid_contains_film_burn_structure(self):
        plan = CoverPlan(
            headline="ретро запуск",
            subtitle="плёночная заметка",
            eyebrow_left="FILM · 01",
            eyebrow_right="ISO 400",
            footer_left="ДЛЯ ЧИТАТЕЛЕЙ",
            symbol="dot",
            style="retro_polaroid",
            format_key="post",
        )

        html = build_cover_html(plan)

        self.assertIn("film-frame", html)
        self.assertIn("Retro Film Burn", COVER_STYLES["retro_polaroid"]["label"])
        self.assertIn("linear-gradient(128deg", html)
        self.assertIn("FILM · 01", html)
        self.assertIn("ISO 400", html)

    def test_poster_headline_does_not_allow_mid_word_breaks(self):
        plan = CoverPlan(
            headline="вы пользуетесь но не деплоите",
            subtitle="разрыв между прогрессом и реализацией",
            eyebrow_left="РАЗБОР · PROMPT",
            eyebrow_right="TECH · TODAY",
            footer_left="ОТРИЦАНИЕ / PRODUCTION",
            symbol="slash",
            style="orange_poster",
            format_key="post",
        )

        html = build_cover_html(plan)

        self.assertIn(">пользуетесь<", html)
        self.assertIn(">но не деплоите<", html)
        self.assertIn("word-break: normal", html)
        self.assertNotIn("overflow-wrap: anywhere", html)

    def test_custom_background_is_embedded_as_data_url(self):
        data_url = image_bytes_to_data_url(b"fake-image", "image/png")
        plan = CoverPlan(
            headline="свой фон",
            subtitle="типографика поверх изображения",
            eyebrow_left="ФОН · TEST",
            eyebrow_right="CUSTOM",
            footer_left="ДЛЯ ОБЛОЖКИ",
            symbol="dot",
            style="blur_field",
            format_key="post",
            background_data_url=data_url,
        )

        html = build_cover_html(plan)

        self.assertIn("custom-background", html)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("cover-blur-field", html)

    def test_render_cover_html_returns_png_for_all_styles(self):
        for style in COVER_STYLES:
            with self.subTest(style=style):
                plan = CoverPlan(
                    headline="от git push до прода",
                    subtitle="семь шагов без хаоса",
                    eyebrow_left="ГАЙД · № 01",
                    eyebrow_right="07 ШАГОВ · ВЕЧЕР",
                    footer_left="ДЛЯ РАЗРАБОТЧИКОВ",
                    symbol="arrow",
                    style=style,
                    format_key="wide",
                )

                png = render_cover_html(plan)

                self.assertTrue(png.startswith(b"\x89PNG"))
                self.assertGreater(len(png), 10_000)


if __name__ == "__main__":
    unittest.main()
