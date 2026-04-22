from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.export_hosting import PublicExportInfo, build_public_export_info
from services.meta_publish import ExportPackage, load_export_package


@dataclass(frozen=True)
class ThreadsPostSpec:
    index: int
    slide_filename: str
    slide_url: str
    text: str
    alt_text: str


@dataclass(frozen=True)
class ThreadsPublishPlan:
    export_package: ExportPackage
    public_export: PublicExportInfo
    posts: tuple[ThreadsPostSpec, ...]


def build_threads_publish_plan(
    export_dir: str | Path,
    public_base_url: str | None = None,
    caption_override: str | None = None,
) -> ThreadsPublishPlan:
    export_package = load_export_package(export_dir)
    public_export = build_public_export_info(export_dir, public_base_url=public_base_url)
    caption = (caption_override or export_package.caption).strip()
    total = len(export_package.slides)

    posts: list[ThreadsPostSpec] = []
    for index, (slide_filename, slide_url) in enumerate(
        zip(export_package.slides, public_export.slide_urls),
        start=1,
    ):
        posts.append(
            ThreadsPostSpec(
                index=index,
                slide_filename=slide_filename,
                slide_url=slide_url,
                text=_build_post_text(caption, index=index, total=total),
                alt_text=_build_alt_text(export_package.metadata, index=index, total=total),
            )
        )

    return ThreadsPublishPlan(
        export_package=export_package,
        public_export=public_export,
        posts=tuple(posts),
    )


def serialize_threads_publish_plan(plan: ThreadsPublishPlan) -> dict[str, Any]:
    return {
        "public_export": {
            "export_id": plan.public_export.export_id,
            "export_slug": plan.public_export.export_slug,
            "public_base_url": plan.public_export.public_base_url,
            "caption_url": plan.public_export.caption_url,
            "metadata_url": plan.public_export.metadata_url,
        },
        "posts": [
            {
                "index": post.index,
                "slide_filename": post.slide_filename,
                "slide_url": post.slide_url,
                "text": post.text,
                "alt_text": post.alt_text,
            }
            for post in plan.posts
        ],
    }


def _build_post_text(caption: str, index: int, total: int) -> str:
    if index == 1:
        return caption
    return f"Слайд {index}/{total}"


def _build_alt_text(metadata: dict[str, Any], index: int, total: int) -> str:
    carousel_plan = metadata.get("carousel_plan") or {}
    slides = carousel_plan.get("slides") or []
    if 0 <= index - 1 < len(slides):
        slide = slides[index - 1]
        title = str(slide.get("title", "")).strip()
        body = str(slide.get("body", "")).strip()
        summary = " — ".join(part for part in (title, body) if part)
        if summary:
            return summary[:1000]
    return f"Карусель, слайд {index} из {total}"
