import os
import tempfile
import unittest
import json
from io import BytesIO
from unittest.mock import patch

from services.instagram_package import build_instagram_export


class InstagramPackageTests(unittest.TestCase):
    def test_build_instagram_export_writes_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            slides = [BytesIO(b"slide-one"), BytesIO(b"slide-two")]
            with patch("services.instagram_package.EXPORTS_DIR", tmpdir):
                export_dir = build_instagram_export(
                    slides=slides,
                    caption="Test caption",
                    source_text="AI operator for Yandex Direct",
                    chat_id=42,
                )

            self.assertTrue(os.path.isdir(export_dir))
            self.assertTrue(os.path.isfile(os.path.join(export_dir, "slide_01.png")))
            self.assertTrue(os.path.isfile(os.path.join(export_dir, "slide_02.png")))
            self.assertTrue(os.path.isfile(os.path.join(export_dir, "caption.txt")))
            self.assertTrue(os.path.isfile(os.path.join(export_dir, "metadata.json")))

    def test_build_instagram_export_persists_extra_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("services.instagram_package.EXPORTS_DIR", tmpdir):
                export_dir = build_instagram_export(
                    slides=[BytesIO(b"slide")],
                    caption="Caption",
                    source_text="Source text",
                    chat_id=7,
                    extra_metadata={"theme": "business_dark"},
                )

            with open(os.path.join(export_dir, "metadata.json"), "r", encoding="utf-8") as f:
                metadata = json.load(f)

            self.assertEqual(metadata["theme"], "business_dark")


if __name__ == "__main__":
    unittest.main()
