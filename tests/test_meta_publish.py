import json
import tempfile
import unittest
from pathlib import Path

from services.meta_publish import (
    MAX_CAROUSEL_ITEMS,
    MetaAppConfig,
    MetaCredentials,
    build_carousel_publish_plan,
    load_export_package,
)


class MetaPublishTests(unittest.TestCase):
    def setUp(self):
        self.config = MetaAppConfig(
            app_id="app-id",
            app_secret="app-secret",
            redirect_uri="https://example.com/callback",
            graph_host="graph.instagram.com",
            graph_api_version="v24.0",
        )
        self.credentials = MetaCredentials(
            ig_user_id="17890000000000000",
            access_token="token",
        )

    def test_load_export_package_reads_caption_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=2)

            export_package = load_export_package(export_dir)

            self.assertEqual(export_package.caption, "Test caption")
            self.assertEqual(export_package.metadata["theme"], "memory_archive")
            self.assertEqual(export_package.slides, ("slide_01.png", "slide_02.png"))

    def test_build_plan_creates_child_parent_and_publish_requests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=2)

            plan = build_carousel_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
                config=self.config,
                credentials=self.credentials,
            )

            self.assertEqual(len(plan.media_uploads), 2)
            child_request = plan.media_uploads[0].request.render(
                self.config,
                {"access_token": self.credentials.access_token},
            )
            self.assertEqual(child_request.method, "POST")
            self.assertEqual(
                child_request.url,
                "https://graph.instagram.com/v24.0/17890000000000000/media",
            )
            self.assertEqual(child_request.payload["is_carousel_item"], "true")
            self.assertEqual(child_request.payload["access_token"], "token")
            self.assertIn("/slide_01.png", child_request.payload["image_url"])

            carousel_request = plan.create_carousel_request.render(
                self.config,
                {
                    "child_01_container_id": "child-a",
                    "child_02_container_id": "child-b",
                    "access_token": self.credentials.access_token,
                },
            )
            self.assertEqual(carousel_request.payload["media_type"], "CAROUSEL")
            self.assertEqual(carousel_request.payload["children"], "child-a,child-b")
            self.assertEqual(carousel_request.payload["caption"], "Test caption")
            self.assertEqual(carousel_request.payload["access_token"], "token")

            publish_request = plan.publish_request.render(
                self.config,
                {
                    "carousel_container_id": "carousel-123",
                    "access_token": self.credentials.access_token,
                },
            )
            self.assertEqual(
                publish_request.url,
                "https://graph.instagram.com/v24.0/17890000000000000/media_publish",
            )
            self.assertEqual(
                publish_request.payload,
                {"creation_id": "carousel-123", "access_token": "token"},
            )

    def test_build_plan_rejects_more_than_ten_slides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=11)

            with self.assertRaisesRegex(ValueError, "up to 10 items"):
                build_carousel_publish_plan(
                    export_dir=export_dir,
                    public_base_url="https://cdn.example.com/exports",
                    config=self.config,
                    credentials=self.credentials,
                )

    def test_poll_plan_uses_one_minute_interval_and_status_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=1)

            plan = build_carousel_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
                config=self.config,
                credentials=self.credentials,
            )

            self.assertEqual(plan.poll_carousel_plan.interval_seconds, 60)
            self.assertEqual(plan.poll_carousel_plan.max_attempts, 5)
            request = plan.poll_carousel_plan.render(self.config, "container-1")
            self.assertEqual(
                request.url,
                "https://graph.instagram.com/v24.0/container-1",
            )
            self.assertEqual(
                request.payload,
                {"fields": "status_code", "access_token": "{access_token}"},
            )

    def _create_export_package(self, tmpdir: str, slides: int) -> Path:
        export_dir = Path(tmpdir) / "20260409-123000-42-carousel"
        export_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "slides": [f"slide_{index:02d}.png" for index in range(1, slides + 1)],
            "theme": "memory_archive",
        }
        (export_dir / "metadata.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )
        (export_dir / "caption.txt").write_text("Test caption\n", encoding="utf-8")
        for slide_name in metadata["slides"]:
            (export_dir / slide_name).write_bytes(b"png")
        return export_dir


if __name__ == "__main__":
    unittest.main()
