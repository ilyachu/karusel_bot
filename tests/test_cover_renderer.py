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
        self.assertIn("Плёночный архив", COVER_STYLES["retro_polaroid"]["label"])
        self.assertIn("linear-gradient(128deg", html)
        self.assertIn("FILM · 01", html)
        self.assertIn("ISO 400", html)

    def test_cover_style_labels_are_clear_russian_names(self):
        expected_labels = {
            "orange_poster": "Оранжевый постер",
            "acid_poster": "Кислотный постер",
            "red_manifesto": "Красный манифест",
            "paper_brief": "Бумажный разбор",
            "retro_polaroid": "Плёночный архив",
            "blue_type": "Синяя типографика",
            "grid_steps": "Сетка и шаги",
            "blur_field": "Размытое движение",
            "quiet_editorial": "Тихий журнал",
            "chalk_notes": "Ручные заметки",
        }

        self.assertEqual(
            {style: tokens["label"] for style, tokens in COVER_STYLES.items()},
            expected_labels,
        )

    def test_new_cover_styles_have_distinct_layout_css(self):
        style_markers = {
            "red_manifesto": ("cover-red-manifesto", "Impact"),
            "paper_brief": ("cover-paper-brief", "box-shadow"),
            "quiet_editorial": ("cover-quiet-editorial", "Georgia"),
            "chalk_notes": ("cover-chalk-notes", "Comic Sans MS"),
        }

        for style, markers in style_markers.items():
            with self.subTest(style=style):
                plan = CoverPlan(
                    headline="не жди идеального момента",
                    subtitle="он уже сейчас",
                    eyebrow_left="РАЗБОР · № 01",
                    eyebrow_right="28/04",
                    footer_left="ДЛЯ ЧИТАТЕЛЕЙ",
                    symbol="slash",
                    style=style,
                    format_key="post",
                )

                html = build_cover_html(plan)

                for marker in markers:
                    self.assertIn(marker, html)

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

    def test_build_cover_html_prefers_ai_html_body_when_present(self):
        plan = CoverPlan(
            headline="Шаблонный headline",
            subtitle="Шаблонный subtitle",
            eyebrow_left="RAZBOR",
            eyebrow_right="TODAY",
            footer_left="ДЛЯ ЧИТАТЕЛЕЙ",
            symbol="arrow",
            style="orange_poster",
            format_key="post",
            html_body=(
                '<section style="width:100%;height:100%;background:#0b1020;color:#f6f3ea;'
                'padding:80px;font-family: Space Grotesk;"><h1>AI cover</h1><p>Своя композиция</p></section>'
            ),
        )

        html = build_cover_html(plan)

        self.assertIn("AI cover", html)
        self.assertIn("Своя композиция", html)
        self.assertIn("Space Grotesk", html)
        self.assertNotIn("Шаблонный headline", html)

    def test_build_cover_html_falls_back_when_ai_html_body_invalid(self):
        plan = CoverPlan(
            headline="Нормальный headline",
            subtitle="Нормальный subtitle",
            eyebrow_left="RAZBOR",
            eyebrow_right="TODAY",
            footer_left="ДЛЯ ЧИТАТЕЛЕЙ",
            symbol="arrow",
            style="orange_poster",
            format_key="post",
            html_body="только текст без тегов",
        )

        html = build_cover_html(plan)

        self.assertIn("Нормальный", html)
        self.assertIn("headline", html)
        self.assertIn("cover-orange-poster", html)
        self.assertNotIn("только текст без тегов", html)

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
