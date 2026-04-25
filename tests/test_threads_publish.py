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
            self.assertEqual(plan.parent_text, "Первый слайд: Короткое описание. Второй слайд: Ещё один тезис.")
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
            self.assertEqual(payload["parent_text"], "Первый слайд: Короткое описание. Второй слайд: Ещё один тезис.")
            self.assertEqual(len(payload["posts"]), 2)
            self.assertEqual(payload["posts"][1]["text"], "Слайд 2/2")

    def test_parent_text_uses_one_or_two_short_sentences_with_essence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(
                tmpdir,
                slides=2,
                caption="NVIDIA открыли доступ к 80 моделям бесплатно. Подключение идёт через OpenAI-compatible API. #ai #nvidia",
                slide_titles=[
                    "NVIDIA открыли доступ к 80 моделям",
                    "Подключение идёт через OpenAI-compatible API",
                ],
                slide_bodies=[
                    "Каталог уже доступен на build.nvidia.com.",
                    "Код почти не нужно менять.",
                ],
            )

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertIn("NVIDIA", plan.parent_text)
            self.assertIn("OpenAI-compatible API", plan.parent_text)
            self.assertNotIn("#ai", plan.parent_text)
            self.assertLessEqual(plan.parent_text.count("."), 2)
            self.assertLessEqual(len(plan.parent_text), 220)

    def test_parent_text_prefers_explicit_threads_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(tmpdir, slides=2)
            metadata_path = export_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["threads_summary"] = "Короткая суть новости для Threads. Без длинного caption и хэштегов. #skip"
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertEqual(plan.parent_text, "Короткая суть новости для Threads. Без длинного caption и хэштегов.")

    def test_parent_text_skips_cta_slide(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(
                tmpdir,
                slides=3,
                slide_titles=[
                    "Главная новость",
                    "Сохрани карусель",
                    "Что изменилось",
                ],
                slide_bodies=[
                    "Новый API меняет подключение моделей.",
                    "Вернись к разбору позже.",
                    "Командам стало проще тестировать интеграции.",
                ],
            )
            metadata_path = export_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["carousel_plan"]["slides"][1]["role"] = "cta"
            metadata["source_text"] = "Новый API меняет подключение моделей и ускоряет тесты."
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertEqual(plan.parent_text, "Новый API меняет подключение моделей и ускоряет тесты.")
            self.assertNotIn("Сохрани", plan.parent_text)
            self.assertLessEqual(len(plan.parent_text), 220)

    def test_parent_text_prefers_source_text_over_slide_fragments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(
                tmpdir,
                slides=2,
                caption="Длинный Instagram caption с хэштегами. #ai",
                slide_titles=["80 моделей", "Base URL"],
                slide_bodies=["каталог открыт", "код менять почти не нужно"],
            )
            metadata_path = export_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["source_text"] = (
                "NVIDIA открыла каталог из 80 моделей через OpenAI-compatible API. "
                "Для разработчиков это снижает порог тестирования новых моделей."
            )
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertIn("NVIDIA открыла каталог", plan.parent_text)
            self.assertIn("снижает порог", plan.parent_text)
            self.assertNotIn("80 моделей: каталог открыт", plan.parent_text)
            self.assertLessEqual(len(plan.parent_text), 220)

    def test_parent_text_ignores_placeholder_caption_before_slide_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = self._create_export_package(
                tmpdir,
                slides=2,
                caption="Test caption\n",
            )

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertEqual(plan.parent_text, "Первый слайд: Короткое описание. Второй слайд: Ещё один тезис.")

    def test_parent_text_falls_back_to_caption_when_plan_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "20260409-123000-42-carousel"
            export_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "export_id": "export-123",
                "export_slug": export_dir.name,
                "slides": ["slide_01.png"],
            }
            (export_dir / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False),
                encoding="utf-8",
            )
            (export_dir / "caption.txt").write_text(
                "Короткий анонс новой модели. Подключение уже доступно. #ai",
                encoding="utf-8",
            )
            (export_dir / "slide_01.png").write_bytes(b"png")

            plan = build_threads_publish_plan(
                export_dir=export_dir,
                public_base_url="https://cdn.example.com/exports",
            )

            self.assertEqual(plan.parent_text, "Короткий анонс новой модели. Подключение уже доступно.")

    def _create_export_package(
        self,
        tmpdir: str,
        slides: int,
        caption: str = "Test caption\n",
        slide_titles: list[str] | None = None,
        slide_bodies: list[str] | None = None,
    ) -> Path:
        export_dir = Path(tmpdir) / "20260409-123000-42-carousel"
        export_dir.mkdir(parents=True, exist_ok=True)
        default_titles = ["Первый слайд", "Второй слайд", "Третий слайд"]
        default_bodies = ["Короткое описание", "Ещё один тезис", "Финальный акцент"]
        slide_titles = (slide_titles or []) + default_titles
        slide_bodies = (slide_bodies or []) + default_bodies
        metadata = {
            "export_id": "export-123",
            "export_slug": export_dir.name,
            "slides": [f"slide_{index:02d}.png" for index in range(1, slides + 1)],
            "carousel_plan": {
                "slides": [
                    {"title": slide_titles[0], "body": slide_bodies[0]},
                    {"title": slide_titles[1], "body": slide_bodies[1]},
                    {"title": slide_titles[2], "body": slide_bodies[2]},
                ][:slides]
            },
        }
        (export_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8",
        )
        (export_dir / "caption.txt").write_text(caption, encoding="utf-8")
        for slide_name in metadata["slides"]:
            (export_dir / slide_name).write_bytes(b"png")
        return export_dir


if __name__ == "__main__":
    unittest.main()
