from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import EXPORT_PUBLIC_BASE_URL
from services.meta_publish import load_export_package


@dataclass(frozen=True)
class PublicExportInfo:
    export_id: str
    export_slug: str
    export_dir: str
    public_base_url: str
    slide_urls: tuple[str, ...]
    caption_url: str
    metadata_url: str


def build_public_export_info(export_dir: str | Path, public_base_url: str | None = None) -> PublicExportInfo:
    export_package = load_export_package(export_dir)
    metadata = export_package.metadata
    base = (public_base_url if public_base_url is not None else EXPORT_PUBLIC_BASE_URL).strip()
    if not base:
        raise ValueError("EXPORT_PUBLIC_BASE_URL is not configured.")

    export_slug = metadata.get("export_slug") or export_package.export_slug
    export_id = metadata.get("export_id") or export_slug

    slide_urls = tuple(_join(base, export_slug, slide) for slide in export_package.slides)
    return PublicExportInfo(
        export_id=export_id,
        export_slug=export_slug,
        export_dir=str(export_package.export_dir),
        public_base_url=base.rstrip("/"),
        slide_urls=slide_urls,
        caption_url=_join(base, export_slug, "caption.txt"),
        metadata_url=_join(base, export_slug, "metadata.json"),
    )


def _join(base: str, export_slug: str, filename: str) -> str:
    return f"{base.rstrip('/')}/{export_slug.strip('/')}/{filename.lstrip('/')}"
