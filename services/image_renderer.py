import logging
import os
from dataclasses import dataclass
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH = 1080
HEIGHT = 1350
PADDING_X = 80
PADDING_Y = 100
LOGO_TEXT = "chu ai"
DEFAULT_BG = (30, 41, 59, 255)

PALETTES = {
    "standard": {"accent": "#7dd3fc", "muted": "#cbd5e1", "panel": (8, 15, 30, 172)},
    "prosto": {"accent": "#f9a8d4", "muted": "#f5d0fe", "panel": (43, 10, 24, 178)},
    "rampart": {"accent": "#f59e0b", "muted": "#fde68a", "panel": (41, 24, 3, 178)},
    "dela": {"accent": "#86efac", "muted": "#dcfce7", "panel": (6, 33, 27, 178)},
}


@dataclass(frozen=True)
class SlideLayout:
    variant: str
    title_size: int
    body_size: int
    title_max_lines: int
    body_max_lines: int
    card: tuple[int, int, int, int]
    eyebrow: str
    show_progress: bool


def render_slide(
    bg_source,
    title: str,
    body: str,
    text_position: str = "center",
    font_style: str = "standard",
    logo_text: str = None,
    slide_index: int | None = None,
    total_slides: int | None = None,
) -> BytesIO:
    output = BytesIO()
    try:
        palette = PALETTES.get(font_style, PALETTES["standard"])
        base_image = _load_background(bg_source)
        image = _apply_overlay(base_image, palette)
        draw = ImageDraw.Draw(image)

        title_font_path, body_font_path = _resolve_font_paths(font_style)
        layout = _choose_layout(
            title=title,
            body=body,
            text_position=text_position,
            slide_index=slide_index,
            total_slides=total_slides,
        )

        _draw_frame_chrome(draw, layout, palette, slide_index, total_slides)

        title_font, title_lines = _fit_text_block(
            draw,
            text=title,
            font_path=title_font_path,
            start_size=layout.title_size,
            min_size=44,
            max_width=layout.card[2] - layout.card[0] - 72,
            max_lines=layout.title_max_lines,
        )
        body_font, body_lines = _fit_text_block(
            draw,
            text=body,
            font_path=body_font_path,
            start_size=layout.body_size,
            min_size=28,
            max_width=layout.card[2] - layout.card[0] - 72,
            max_lines=layout.body_max_lines,
        )

        _draw_layout_content(
            draw=draw,
            layout=layout,
            palette=palette,
            title_lines=title_lines,
            body_lines=body_lines,
            title_font=title_font,
            body_font=body_font,
        )

        _draw_logo(draw, logo_text or LOGO_TEXT, body_font_path, palette)

        image.save(output, format="PNG")
        output.seek(0)
        return output
    except Exception as exc:
        logging.error("Error in render_slide: %s", exc, exc_info=True)
        image = Image.new("RGB", (WIDTH, HEIGHT), color="gray")
        draw = ImageDraw.Draw(image)
        draw.text((50, 50), "Error rendering slide", fill="red")
        image.save(output, format="PNG")
        output.seek(0)
        return output


def _load_background(bg_source) -> Image.Image:
    if isinstance(bg_source, BytesIO):
        bg_source.seek(0)
        bg_img = Image.open(bg_source).convert("RGBA")
    elif isinstance(bg_source, str) and bg_source.startswith("http"):
        response = requests.get(bg_source, timeout=20)
        response.raise_for_status()
        bg_img = Image.open(BytesIO(response.content)).convert("RGBA")
    elif isinstance(bg_source, str) and os.path.exists(bg_source):
        bg_img = Image.open(bg_source).convert("RGBA")
    else:
        bg_img = Image.new("RGBA", (WIDTH, HEIGHT), DEFAULT_BG)
    return ImageOps.fit(bg_img, (WIDTH, HEIGHT))


def _apply_overlay(bg_img: Image.Image, palette: dict) -> Image.Image:
    base = bg_img.convert("RGBA")
    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for y in range(HEIGHT):
        alpha = int(80 + (y / HEIGHT) * 120)
        gradient_draw.line((0, y, WIDTH, y), fill=(3, 7, 18, alpha))

    tinted = Image.new("RGBA", (WIDTH, HEIGHT), palette["panel"])
    image = Image.alpha_composite(base, gradient)
    image = Image.alpha_composite(image, tinted)
    return image


def _resolve_font_paths(font_style: str) -> tuple[str, str]:
    font_paths = {
        "standard": "assets/fonts/font.ttf",
        "elegant": "assets/fonts/elegant.ttf",
        "rough": "assets/fonts/rough.ttf",
        "prosto": "assets/fonts/ProstoOne-Regular.ttf",
        "rampart": "assets/fonts/RampartOne-Regular.ttf",
        "dela": "assets/fonts/DelaGothicOne-Regular.ttf",
    }
    requested = font_paths.get(font_style, font_paths["standard"])
    fallback = font_paths["standard"]
    title_path = requested if os.path.exists(requested) else fallback
    body_path = requested if os.path.exists(requested) else fallback
    return title_path, body_path


def _choose_layout(
    title: str,
    body: str,
    text_position: str,
    slide_index: int | None,
    total_slides: int | None,
) -> SlideLayout:
    progress_known = bool(slide_index and total_slides)
    is_cover = progress_known and slide_index == 1 and total_slides > 1
    is_final = progress_known and slide_index == total_slides and total_slides > 1
    short_body = len(body) < 140
    short_title = len(title) < 46

    if is_cover:
        return SlideLayout(
            variant="cover",
            title_size=88,
            body_size=34,
            title_max_lines=3,
            body_max_lines=4,
            card=(64, 128, WIDTH - 64, HEIGHT - 180),
            eyebrow="Hook",
            show_progress=True,
        )

    if is_final:
        return SlideLayout(
            variant="closing",
            title_size=72,
            body_size=32,
            title_max_lines=3,
            body_max_lines=5,
            card=(72, 330, WIDTH - 72, HEIGHT - 220),
            eyebrow="CTA",
            show_progress=True,
        )

    if short_body and short_title:
        y_map = {"top": 180, "center": 320, "bottom": 500}
        card_top = y_map.get(text_position, 320)
        return SlideLayout(
            variant="spotlight",
            title_size=78,
            body_size=30,
            title_max_lines=3,
            body_max_lines=4,
            card=(64, card_top, WIDTH - 64, HEIGHT - 210),
            eyebrow="Key idea",
            show_progress=progress_known,
        )

    y_map = {"top": 120, "center": 230, "bottom": 330}
    card_top = y_map.get(text_position, 230)
    return SlideLayout(
        variant="editorial",
        title_size=68,
        body_size=30,
        title_max_lines=4,
        body_max_lines=6,
        card=(64, card_top, WIDTH - 64, HEIGHT - 180),
        eyebrow="Deep dive",
        show_progress=progress_known,
    )


def _draw_frame_chrome(
    draw: ImageDraw.ImageDraw,
    layout: SlideLayout,
    palette: dict,
    slide_index: int | None,
    total_slides: int | None,
):
    left, top, right, bottom = layout.card
    draw.rounded_rectangle(layout.card, radius=44, fill=palette["panel"], outline=(255, 255, 255, 32), width=2)
    draw.rounded_rectangle((left + 28, top + 28, left + 208, top + 82), radius=28, fill=(255, 255, 255, 24))
    eyebrow_font = _load_font("assets/fonts/font.ttf", 22)
    draw.text((left + 50, top + 42), layout.eyebrow.upper(), font=eyebrow_font, fill=palette["accent"])

    if layout.show_progress and slide_index and total_slides:
        progress = f"{slide_index}/{total_slides}"
        progress_bbox = draw.textbbox((0, 0), progress, font=eyebrow_font)
        progress_w = progress_bbox[2] - progress_bbox[0]
        badge = (right - progress_w - 82, top + 28, right - 28, top + 82)
        draw.rounded_rectangle(badge, radius=28, fill=(255, 255, 255, 24))
        draw.text((badge[0] + 26, top + 42), progress, font=eyebrow_font, fill="#f8fafc")

    accent_y = bottom - 30
    draw.rounded_rectangle((left + 28, accent_y, left + 220, accent_y + 10), radius=8, fill=palette["accent"])


def _fit_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    start_size: int,
    min_size: int,
    max_width: int,
    max_lines: int,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
    for size in range(start_size, min_size - 1, -2):
        font = _load_font(font_path, size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines

    font = _load_font(font_path, min_size)
    lines = _wrap_text(draw, text, font, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _ellipsize(draw, lines[-1], font, max_width)
    return font, lines


def _load_font(font_path: str, size: int):
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    except Exception as exc:
        logging.warning("Failed to load font %s: %s", font_path, exc)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current_line: list[str] = []
    for word in words:
        candidate = " ".join(current_line + [word])
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _ellipsize(draw: ImageDraw.ImageDraw, line: str, font, max_width: int) -> str:
    candidate = line
    while candidate:
        if draw.textbbox((0, 0), candidate + "…", font=font)[2] <= max_width:
            return candidate + "…"
        candidate = candidate[:-1]
    return "…"


def _draw_layout_content(
    draw: ImageDraw.ImageDraw,
    layout: SlideLayout,
    palette: dict,
    title_lines: list[str],
    body_lines: list[str],
    title_font,
    body_font,
):
    left, top, right, bottom = layout.card
    content_left = left + 36
    content_top = top + 110
    content_width = right - left - 72

    title_line_gap = 18
    body_line_gap = 14
    title_height = _measure_block_height(draw, title_lines, title_font, title_line_gap)
    body_height = _measure_block_height(draw, body_lines, body_font, body_line_gap)

    if layout.variant == "cover":
        title_y = content_top + 20
        body_y = min(title_y + title_height + 34, bottom - body_height - 150)
        cue_y = bottom - 120
        _draw_lines(draw, title_lines, title_font, "#f8fafc", content_left, title_y, title_line_gap, content_width)
        _draw_lines(draw, body_lines, body_font, palette["muted"], content_left, body_y, body_line_gap, content_width)
        cue_font = _load_font("assets/fonts/font.ttf", 24)
        draw.text((content_left, cue_y), "Swipe for the breakdown →", font=cue_font, fill="#e2e8f0")
        return

    if layout.variant == "closing":
        title_y = content_top + 20
        body_y = title_y + title_height + 28
        _draw_lines(draw, title_lines, title_font, "#f8fafc", content_left, title_y, title_line_gap, content_width)
        _draw_lines(draw, body_lines, body_font, palette["muted"], content_left, body_y, body_line_gap, content_width)
        cta_font = _load_font("assets/fonts/font.ttf", 24)
        draw.rounded_rectangle((content_left, bottom - 122, content_left + 310, bottom - 58), radius=24, fill=(255, 255, 255, 28))
        draw.text((content_left + 22, bottom - 106), "Save this carousel", font=cta_font, fill="#f8fafc")
        return

    if layout.variant == "spotlight":
        title_y = content_top + 10
        body_card_top = max(title_y + title_height + 40, bottom - body_height - 120)
        draw.rounded_rectangle((content_left, body_card_top - 24, right - 36, body_card_top + body_height + 32), radius=28, fill=(255, 255, 255, 22))
        _draw_lines(draw, title_lines, title_font, "#f8fafc", content_left, title_y, title_line_gap, content_width)
        _draw_lines(draw, body_lines, body_font, palette["muted"], content_left + 18, body_card_top, body_line_gap, content_width - 36)
        return

    title_y = content_top + 10
    divider_y = title_y + title_height + 28
    body_y = divider_y + 34
    draw.line((content_left, divider_y, right - 36, divider_y), fill=(255, 255, 255, 38), width=3)
    _draw_lines(draw, title_lines, title_font, "#f8fafc", content_left, title_y, title_line_gap, content_width)
    _draw_lines(draw, body_lines, body_font, palette["muted"], content_left, body_y, body_line_gap, content_width)


def _measure_block_height(draw: ImageDraw.ImageDraw, lines: list[str], font, gap: int) -> int:
    if not lines:
        return 0
    total = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total += (bbox[3] - bbox[1]) + gap
    return max(0, total - gap)


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font,
    fill,
    x: int,
    y: int,
    gap: int,
    max_width: int,
):
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        current_y += (bbox[3] - bbox[1]) + gap


def _draw_logo(draw: ImageDraw.ImageDraw, logo_text: str, font_path: str, palette: dict):
    logo_font = _load_font(font_path, 28)
    bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
    width = bbox[2] - bbox[0]
    x = WIDTH - width - PADDING_X
    y = HEIGHT - PADDING_Y + 6
    draw.text((x, y), logo_text, font=logo_font, fill=palette["muted"])
