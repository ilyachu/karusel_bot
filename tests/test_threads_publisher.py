import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from services.threads_publisher import ThreadsPublisher


class FakeThreadsPublisher(ThreadsPublisher):
    def __init__(self):
        super().__init__(
            access_token="token",
            bot=Mock(),
            user_id="me",
            api_base="https://graph.threads.net/v1.0",
            media_proxy_base_url="https://meta.chuchuchu.online",
            media_proxy_secret="secret123",
        )
        self.calls = []
        self._status_attempts: dict[str, int] = {}
        file_obj = Mock()
        file_obj.file_path = "photos/file_1.jpg"
        self.bot.get_file = AsyncMock(return_value=file_obj)

    async def _request_json(self, method, url, *, data=None, params=None):
        self.calls.append((method, url, data, params))
        if url.endswith("/me/threads") and data and data.get("is_carousel_item") == "true":
            child_no = len([call for call in self.calls if call[1].endswith("/me/threads") and call[2] and call[2].get("is_carousel_item") == "true"])
            return {"id": f"child-{child_no}"}
        if url.endswith("/me/threads") and data and data.get("media_type") == "CAROUSEL":
            return {"id": "carousel-1"}
        if url.endswith("/me/threads_publish"):
            return {"id": "threads-post-1"}
        if url.endswith("/child-1") or url.endswith("/child-2") or url.endswith("/carousel-1"):
            container_id = url.rsplit("/", 1)[-1]
            self._status_attempts[container_id] = self._status_attempts.get(container_id, 0) + 1
            return {"status": "FINISHED"}
        raise AssertionError(f"Unexpected call: {method} {url} data={data} params={params}")


class ThreadsPublisherTests(unittest.TestCase):
    def test_publish_export_creates_children_then_parent_then_publish(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=2)
            publisher = FakeThreadsPublisher()

            result = asyncio.run(
                publisher.publish_export(
                    export_dir=str(export_dir),
                    public_base_url="https://cdn.example.com/exports",
                )
            )

            self.assertTrue(result.success)
            self.assertEqual(result.creation_id, "carousel-1")
            self.assertEqual(result.published_id, "threads-post-1")

            thread_posts = [call for call in publisher.calls if call[1].endswith("/me/threads")]
            self.assertEqual(len(thread_posts), 3)
            self.assertIn("https://meta.chuchuchu.online/proxy/telegram-media?", thread_posts[0][2]["image_url"])
            self.assertIn("https://meta.chuchuchu.online/proxy/telegram-media?", thread_posts[1][2]["image_url"])
            self.assertEqual(thread_posts[2][2]["children"], "child-1,child-2")
            self.assertNotIn("text", thread_posts[2][2])

    def _create_export_package(self, tmpdir: str, slides: int) -> Path:
        export_dir = Path(tmpdir) / "20260409-123000-42-carousel"
        export_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "export_id": "export-123",
            "export_slug": export_dir.name,
            "slides": [f"slide_{index:02d}.png" for index in range(1, slides + 1)],
            "telegram_media_items": [
                {"file_id": "telegram-file-id", "media_type": "photo", "order_index": index}
                for index in range(1, slides + 1)
            ],
            "carousel_plan": {"slides": []},
        }
        (export_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8",
        )
        (export_dir / "caption.txt").write_text("Carousel caption\n", encoding="utf-8")
        for slide_name in metadata["slides"]:
            (export_dir / slide_name).write_bytes(b"png")
        return export_dir


if __name__ == "__main__":
    unittest.main()
