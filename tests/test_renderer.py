import os
import tempfile
import unittest
from io import BytesIO

from PIL import Image

from services.image_renderer import HEIGHT, WIDTH, render_slide


class RenderSlideTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.bg_path = os.path.join(self.tempdir.name, "background.png")
        Image.new("RGB", (1400, 900), "#224466").save(self.bg_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def assert_png_dimensions(self, buffer: BytesIO):
        with Image.open(buffer) as rendered:
            self.assertEqual(rendered.size, (WIDTH, HEIGHT))
            self.assertEqual(rendered.format, "PNG")

    def test_render_slide_supports_all_vertical_positions(self):
        for position in ("top", "center", "bottom"):
            with self.subTest(position=position):
                buffer = render_slide(
                    self.bg_path,
                    "AI operator for Yandex Direct",
                    "Find wasted spend, suggest negative keywords, and prepare "
                    "changes for approval.",
                    text_position=position,
                )
                self.assert_png_dimensions(buffer)

    def test_render_slide_handles_long_copy_without_crashing(self):
        buffer = render_slide(
            self.bg_path,
            "What happens when one long title needs to fit into a portrait "
            "carousel cover without clipping",
            "This slide intentionally uses a longer paragraph so the renderer "
            "has to wrap text reliably across multiple lines while still "
            "producing a valid output image.",
            text_position="center",
        )
        self.assert_png_dimensions(buffer)

    def test_render_slide_accepts_slide_metadata_for_auto_layout(self):
        buffer = render_slide(
            self.bg_path,
            "5 tasks an AI operator can handle every day",
            "Find wasted spend, suggest negative keywords, rewrite weak ads, "
            "flag bid issues, and prepare changes for approval.",
            text_position="center",
            slide_index=1,
            total_slides=7,
        )
        self.assert_png_dimensions(buffer)


if __name__ == "__main__":
    unittest.main()
