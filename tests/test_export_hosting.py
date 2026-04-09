import json
import tempfile
import unittest
from pathlib import Path

from services.export_hosting import build_public_export_info


class ExportHostingTests(unittest.TestCase):
    def test_build_public_export_info_uses_export_slug_and_base_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "20260409-123000-42-demo"
            export_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "export_id": "abc123def456",
                "export_slug": "20260409-123000-42-demo",
                "slides": ["slide_01.png", "slide_02.png"],
            }
            (export_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (export_dir / "caption.txt").write_text("Caption", encoding="utf-8")

            info = build_public_export_info(
                export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertEqual(info.export_id, "abc123def456")
            self.assertEqual(
                info.slide_urls[0],
                "https://cdn.example.com/exports/20260409-123000-42-demo/slide_01.png",
            )
            self.assertEqual(
                info.caption_url,
                "https://cdn.example.com/exports/20260409-123000-42-demo/caption.txt",
            )


if __name__ == "__main__":
    unittest.main()
