import json
import tempfile
import unittest
from pathlib import Path

from services.threads_publish import build_threads_publish_plan, serialize_threads_publish_plan


class ThreadsPublishPlanTests(unittest.TestCase):
    def test_build_threads_publish_plan_maps_every_slide_to_public_post(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=3)

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertEqual(plan.public_export.export_id, "export-123")
            self.assertEqual(len(plan.posts), 3)
            self.assertEqual(
                plan.posts[0].slide_url,
                "https://cdn.example.com/exports/20260409-123000-42-carousel/slide_01.png",
            )
            self.assertEqual(plan.posts[0].text, "Test caption")
            self.assertEqual(plan.posts[1].text, "Слайд 2/3")
            self.assertIn("Первый слайд", plan.posts[0].alt_text)

    def test_serialize_threads_publish_plan_returns_json_safe_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=2)
            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            payload = serialize_threads_publish_plan(plan)

            self.assertEqual(payload["public_export"]["export_slug"], "20260409-123000-42-carousel")
            self.assertEqual(len(payload["posts"]), 2)
            self.assertEqual(payload["posts"][1]["text"], "Слайд 2/2")

    def _create_export_package(self, tmpdir: str, slides: int) -> Path:
        export_dir = Path(tmpdir) / "20260409-123000-42-carousel"
        export_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "export_id": "export-123",
            "export_slug": export_dir.name,
            "slides": [f"slide_{index:02d}.png" for index in range(1, slides + 1)],
            "carousel_plan": {
                "slides": [
                    {"title": "Первый слайд", "body": "Короткое описание"},
                    {"title": "Второй слайд", "body": "Ещё один тезис"},
                    {"title": "Третий слайд", "body": "Финальный акцент"},
                ][:slides]
            },
        }
        (export_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8",
        )
        (export_dir / "caption.txt").write_text("Test caption\n", encoding="utf-8")
        for slide_name in metadata["slides"]:
            (export_dir / slide_name).write_bytes(b"png")
        return export_dir


if __name__ == "__main__":
    unittest.main()
