"""Behavior tests for the experimental carousel renderer.

These tests assert on rendered HTML strings and the ``LayoutSpec`` ->
``ExperimentalSlide`` mapping. They do NOT require Playwright; rendering
is mocked.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.experimental_carousel_renderer import (
    ExperimentalSlide,
    STYLE_PRESETS,
    StylePreset,
    build_experimental_slide_html,
    map_layout_spec_to_experimental_slide,
    render_experimental_carousel,
    _split_bullets,
)
from services.layout_engine import LayoutSpec


def _make_spec(
    *,
    role: str = "body",
    density: str = "low",
    title: str = "Заголовок",
    body: str = "Тело",
    badge_text: str = "",
    html_body: str = "",
    **overrides,
) -> LayoutSpec:
    """Build a minimal ``LayoutSpec`` for tests."""

    defaults: dict = dict(
        slide_index=1,
        total_slides=1,
        role=role,
        theme="business_dark",
        visual_mode="classic",
        font_style="magazine",
        variant="",
        text_position="",
        badge_text=badge_text,
        title=title,
        body=body,
        highlight_words=[],
        density=density,
        show_progress=True,
    )
    defaults.update(overrides)
    return LayoutSpec(**defaults)


class ExperimentalSlideHtmlTests(unittest.TestCase):
    def test_build_html_uses_1080x1350_dimensions(self):
        html = build_experimental_slide_html(ExperimentalSlide(type="body", title="T", body="B"))
        self.assertIn("1080px", html)
        self.assertIn("1350px", html)
        self.assertIn("width: 1080px", html)
        self.assertIn("height: 1350px", html)

    def test_build_html_uses_dark_surface_and_light_text(self):
        html = build_experimental_slide_html(ExperimentalSlide(type="body", title="T", body="B"))
        self.assertIn("#0a0a0a", html)
        self.assertIn("#f8fafc", html)

    def test_custom_background_adds_dark_overlay_and_readable_text(self):
        data_url = "data:image/png;base64,ZmFrZQ=="
        html = build_experimental_slide_html(
            ExperimentalSlide(type="body", title="T", body="B"),
            custom_background_data_url=data_url,
        )
        self.assertIn("linear-gradient", html)
        # Default dark surface uses a softer dark overlay; light surfaces
        # get the stronger rgba(7,10,18,0.62->0.76) overlay.
        self.assertIn("rgba(7, 10, 18, 0.56)", html)
        self.assertIn("rgba(7, 10, 18, 0.70)", html)
        self.assertIn("color: #f8fafc", html)
        self.assertIn("opacity: 1", html)
        self.assertIn("text-shadow", html)
        self.assertIn('class="external-bg"', html)
        self.assertIn('class="overlay"', html)
        self.assertIn(data_url, html)

    def test_no_ai_html_body_leaks_into_experimental_html(self):
        # ``map_layout_spec_to_experimental_slide`` must drop html_body.
        # Any ``html_body`` field on the spec must not surface in HTML.
        spec = _make_spec(
            role="body",
            density="low",
            title="T",
            body="B",
            html_body='<script>alert("LEAK_XYZ")</script>',
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        html = build_experimental_slide_html(slide)
        self.assertNotIn("LEAK_XYZ", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("alert(", html)

    def test_html_escapes_long_user_text(self):
        spec = _make_spec(
            role="body",
            density="low",
            title='<script>alert("pwn")</script>',
            body="Body",
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        html = build_experimental_slide_html(slide)
        # The raw <script> tag from user input must NOT survive.
        self.assertNotIn("<script>alert(\"pwn\")</script>", html)
        # And the escaped version MUST be present.
        self.assertIn("&lt;script&gt;", html)


class MapLayoutSpecTests(unittest.TestCase):
    def test_map_hook_role(self):
        spec = _make_spec(role="hook", title="X", body="Y")
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.type, "hook")
        self.assertEqual(slide.title, "X")
        self.assertEqual(slide.body, "Y")
        self.assertEqual(slide.items, ())

    def test_map_cta_role(self):
        spec = _make_spec(role="cta", title="X", body="Y")
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.type, "cta")
        self.assertEqual(slide.title, "X")
        self.assertEqual(slide.body, "Y")
        self.assertEqual(slide.items, ())

    def test_map_default_role_to_body(self):
        spec = _make_spec(role="body", density="low", title="X", body="Y")
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.type, "body")
        self.assertEqual(slide.items, ())

    def test_map_density_high_with_newlines_to_list(self):
        spec = _make_spec(
            role="body", density="high", title="X", body="A\nB\nC"
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.type, "list")
        self.assertEqual(slide.items, ("A", "B", "C"))
        self.assertEqual(slide.body, "")

    def test_map_density_high_without_newlines_short_sentences_to_list(self):
        spec = _make_spec(
            role="body",
            density="high",
            title="X",
            body="Short one. Short two. Short three.",
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.type, "list")
        self.assertEqual(len(slide.items), 3)
        self.assertTrue(all(len(item) <= 80 for item in slide.items))

    def test_map_density_high_long_paragraph_falls_back_to_body(self):
        long = ("This is a single very long sentence that is definitely more than eighty characters long. " * 8).strip()
        spec = _make_spec(role="body", density="high", title="X", body=long)
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.type, "body")
        self.assertEqual(slide.items, ())


class RenderExperimentalCarouselTests(unittest.TestCase):
    def test_render_returns_one_png_per_spec(self):
        specs = [
            _make_spec(slide_index=1, total_slides=2, role="hook", title="A", body="a"),
            _make_spec(slide_index=2, total_slides=2, role="cta", title="B", body="b"),
        ]
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

        with patch(
            "services.experimental_carousel_renderer._render_with_playwright",
            return_value=fake_png,
        ):
            result = render_experimental_carousel(specs)

        self.assertEqual(len(result), 2)
        for png in result:
            self.assertIsInstance(png, bytes)
            self.assertGreater(len(png), 0)

    def test_render_falls_back_when_playwright_unavailable(self):
        specs = [_make_spec(role="hook", title="A", body="a")]

        def _raise(_html: str) -> bytes:
            raise RuntimeError("playwright not available")

        with patch(
            "services.experimental_carousel_renderer._render_with_playwright",
            side_effect=_raise,
        ):
            result = render_experimental_carousel(specs)

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], bytes)
        # PNG signature
        self.assertTrue(result[0].startswith(b"\x89PNG\r\n\x1a\n"))

    def test_render_never_raises(self):
        # Even with empty input, the function must not raise.
        result = render_experimental_carousel([])
        self.assertEqual(result, [])


class SplitBulletsTests(unittest.TestCase):
    def test_empty_body_returns_empty(self):
        self.assertEqual(_split_bullets(""), ())

    def test_single_line_returns_empty(self):
        self.assertEqual(_split_bullets("only one"), ())

    def test_two_newline_lines_returns_them(self):
        self.assertEqual(_split_bullets("alpha\nbeta"), ("alpha", "beta"))

    def test_short_sentences_split_by_period(self):
        result = _split_bullets("First short. Second short. Third short.")
        self.assertGreaterEqual(len(result), 2)
        self.assertTrue(all(len(item) <= 80 for item in result))


class StyleSystemTests(unittest.TestCase):
    def test_three_presets_exist(self):
        self.assertEqual(
            set(STYLE_PRESETS.keys()), {"dark_teal", "paper_orange", "white_coral"}
        )

    def test_presets_have_distinct_surfaces(self):
        surfaces = [preset.surface_bg for preset in STYLE_PRESETS.values()]
        self.assertEqual(len(set(surfaces)), 3)

    def test_presets_have_distinct_accents(self):
        accents = [preset.accent_color for preset in STYLE_PRESETS.values()]
        self.assertEqual(len(set(accents)), 3)

    def test_presets_have_distinct_fonts(self):
        fonts = [preset.font_family for preset in STYLE_PRESETS.values()]
        # All three presets intentionally pick different font families.
        self.assertGreaterEqual(len(set(fonts)), 2)

    def test_build_html_uses_style_surface(self):
        for preset in STYLE_PRESETS.values():
            html = build_experimental_slide_html(
                ExperimentalSlide(type="body", title="T", body="B"),
                style=preset,
            )
            self.assertIn(
                preset.surface_bg,
                html,
                f"{preset.id}: surface background not in HTML",
            )

    def test_build_html_uses_style_accent(self):
        for preset in STYLE_PRESETS.values():
            html = build_experimental_slide_html(
                ExperimentalSlide(type="body", title="T", body="B"),
                style=preset,
            )
            self.assertIn(
                f"color: {preset.accent_color}",
                html,
                f"{preset.id}: accent color not in HTML as .hl color",
            )

    def test_build_html_uses_style_font(self):
        for preset in STYLE_PRESETS.values():
            html = build_experimental_slide_html(
                ExperimentalSlide(type="hook", title="T", body="B"),
                style=preset,
            )
            font_name = preset.font_family.split(",")[0].strip().strip("'\"")
            self.assertIn(font_name, html, f"{preset.id}: font name not in HTML")

    def test_build_html_emits_google_fonts_link(self):
        # The non-system presets require a Google Fonts link.
        for preset in STYLE_PRESETS.values():
            html = build_experimental_slide_html(
                ExperimentalSlide(type="body", title="T", body="B"),
                style=preset,
            )
            self.assertIn("<link", html)
            self.assertIn("fonts.googleapis.com", html)

    def test_map_layout_spec_copies_highlight_words(self):
        spec = _make_spec(
            role="body",
            density="low",
            title="T",
            body="B",
            highlight_words=["foo", "bar"],
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        self.assertEqual(slide.highlights, ("foo", "bar"))

    def test_highlight_words_become_hl_span(self):
        spec = _make_spec(
            role="body",
            density="low",
            title="Soft Skills",
            body="Build Skills every day",
            highlight_words=["Skills"],
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        html = build_experimental_slide_html(slide)
        self.assertIn('<span class="hl">Skills</span>', html)

    def test_highlight_words_are_escaped(self):
        spec = _make_spec(
            role="body",
            density="low",
            title="Escape <script> please",
            body="B",
            highlight_words=["<script>"],
        )
        slide = map_layout_spec_to_experimental_slide(spec)
        html = build_experimental_slide_html(slide)
        self.assertNotIn("<script>", html)
        self.assertIn('<span class="hl">&lt;script&gt;</span>', html)

    def test_light_surface_with_external_bg_uses_dark_overlay(self):
        data_url = "data:image/png;base64,ZmFrZQ=="
        for preset_id in ("paper_orange", "white_coral"):
            preset = STYLE_PRESETS[preset_id]
            html = build_experimental_slide_html(
                ExperimentalSlide(type="body", title="T", body="B"),
                style=preset,
                custom_background_data_url=data_url,
            )
            self.assertIn(
                "rgba(7, 10, 18, 0.62)",
                html,
                f"{preset_id}: light surface must use strong dark overlay",
            )
            self.assertIn("rgba(7, 10, 18, 0.76)", html)

    def test_dark_surface_with_external_bg_keeps_overlay(self):
        data_url = "data:image/png;base64,ZmFrZQ=="
        preset = STYLE_PRESETS["dark_teal"]
        html = build_experimental_slide_html(
            ExperimentalSlide(type="body", title="T", body="B"),
            style=preset,
            custom_background_data_url=data_url,
        )
        self.assertIn("rgba(7, 10, 18, 0.56)", html)
        self.assertIn("rgba(7, 10, 18, 0.70)", html)

    def test_render_with_style_returns_pngs(self):
        specs = [_make_spec(role="hook", title="A", body="a")]
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        for preset in STYLE_PRESETS.values():
            with patch(
                "services.experimental_carousel_renderer._render_with_playwright",
                return_value=fake_png,
            ):
                result = render_experimental_carousel(specs, style=preset)
            self.assertEqual(
                len(result),
                1,
                f"{preset.id}: expected 1 PNG, got {len(result)}",
            )
            self.assertIsInstance(result[0], bytes)

    def test_default_style_is_dark_teal(self):
        # Calling without a style should fall back to the dark_teal preset
        # so existing callers/tests remain valid.
        html = build_experimental_slide_html(
            ExperimentalSlide(type="body", title="T", body="B")
        )
        self.assertIn(STYLE_PRESETS["dark_teal"].surface_bg, html)
        self.assertIn(STYLE_PRESETS["dark_teal"].accent_color, html)


if __name__ == "__main__":
    unittest.main()
