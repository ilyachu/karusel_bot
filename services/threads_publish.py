from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
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
    parent_text: str
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
    parent_text = _build_parent_text(caption, export_package.metadata)

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
        parent_text=parent_text,
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
        "parent_text": plan.parent_text,
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


def _build_parent_text(caption: str, metadata: dict[str, Any]) -> str:
    explicit_summary = _normalize_summary_text(str(metadata.get("threads_summary") or "").strip())
    if explicit_summary:
        return _clip_summary(_ensure_sentence(explicit_summary))

    source_text = _normalize_summary_text(str(metadata.get("source_text") or "").strip())
    summary_sentences = _extract_short_sentences(source_text, limit=2) if _is_usable_parent_source(source_text) else []
    if summary_sentences:
        return _clip_summary(" ".join(summary_sentences[:2]).strip())

    caption_text = _normalize_summary_text((caption or "").strip())
    summary_sentences = _extract_short_sentences(caption_text, limit=2) if _is_usable_parent_source(caption_text) else []
    if summary_sentences:
        return _clip_summary(" ".join(summary_sentences[:2]).strip())

    carousel = metadata.get("carousel_plan") or {}
    slides = carousel.get("slides") or []
    summary_sentences = []

    for slide in [slide for slide in slides if not _is_cta_slide(slide)][:2]:
        title = _normalize_summary_text(str(slide.get("title", "")).strip())
        body = _normalize_summary_text(str(slide.get("body", "")).strip())
        sentence = _compose_slide_summary(title, body)
        if sentence and sentence not in summary_sentences:
            summary_sentences.append(_ensure_sentence(sentence))
        if len(summary_sentences) == 2:
            break

    summary = " ".join(summary_sentences[:2]).strip()
    if summary:
        return _clip_summary(summary)
    if caption_text:
        return _clip_summary(_ensure_sentence(caption_text))
    return ""


def _clip_summary(summary: str) -> str:
    if len(summary) <= 220:
        return summary
    clipped = summary[:219].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,.;:-") + "…"


def _normalize_summary_text(text: str) -> str:
    text = re.sub(r"#\w+", "", text).strip()
    text = re.sub(r"\b(?:https?://)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/\S*)?", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_usable_parent_source(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if len(lowered) < 28:
        return False
    if lowered in {"test caption", "caption", "source text", "test"}:
        return False
    return True


def _compose_slide_summary(title: str, body: str) -> str:
    title = title.strip()
    body_sentence = (_extract_short_sentences(body, limit=1) or [""])[0].rstrip(".!?")
    if title and body_sentence and body_sentence.lower() not in title.lower():
        combined = f"{title}: {body_sentence}"
        return combined if len(combined) <= 160 else title
    return title or body_sentence


def _is_cta_slide(slide: dict[str, Any]) -> bool:
    role = str(slide.get("role") or "").lower()
    title = str(slide.get("title") or "").lower()
    body = str(slide.get("body") or "").lower()
    text = " ".join([role, title, body])
    return any(
        marker in text
        for marker in (
            "cta", "сохрани", "подпис", "follow", "вернись к разбору", "шапке профиля",
        )
    )


def _extract_short_sentences(text: str, limit: int = 2) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return [_ensure_sentence(part) for part in parts[:limit]]


def _ensure_sentence(text: str) -> str:
    text = text.strip().rstrip(" ,;:-")
    if not text:
        return ""
    if text.endswith((".", "!", "?")):
        return text
    return text + "."


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
