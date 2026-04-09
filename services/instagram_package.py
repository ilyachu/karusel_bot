import json
import os
import re
from datetime import datetime, timezone
from io import BytesIO

from config import EXPORTS_DIR


def build_instagram_export(
    slides: list[BytesIO],
    caption: str,
    source_text: str,
    chat_id: int,
    extra_metadata: dict | None = None,
) -> str:
    """
    Persist an Instagram-ready export package with slides, caption, and metadata.
    Returns the export directory path.
    """
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y%m%d-%H%M%S")
    slug = _slugify(source_text[:60]) or "carousel"
    export_dir = os.path.join(EXPORTS_DIR, f"{timestamp}-{chat_id}-{slug}")
    os.makedirs(export_dir, exist_ok=True)

    for index, buffer in enumerate(slides, start=1):
        slide_path = os.path.join(export_dir, f"slide_{index:02d}.png")
        with open(slide_path, "wb") as f:
            f.write(buffer.getvalue())

    caption_path = os.path.join(export_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption.strip() + "\n")

    metadata = {
        "created_at_utc": now_utc.isoformat(),
        "chat_id": chat_id,
        "slides_count": len(slides),
        "caption_file": "caption.txt",
        "slides": [f"slide_{index:02d}.png" for index in range(1, len(slides) + 1)],
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    with open(os.path.join(export_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return export_dir


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-zа-я0-9]+", "-", value, flags=re.IGNORECASE)
    return value.strip("-")[:48]
