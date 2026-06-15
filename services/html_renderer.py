import html
import logging
import re

from services.layout_engine import LayoutSpec, LAYOUT_STYLE_FONTS


def _google_fonts_link(layout_style: str) -> str:
    """Build Google Fonts @import URL for a given layout style."""
    fonts = LAYOUT_STYLE_FONTS.get(layout_style, LAYOUT_STYLE_FONTS["magazine"])
    families = fonts["google"]
    if not families:
        return ""
    return f'https://fonts.googleapis.com/css2?{families}&display=swap'


def _background_treatment(background_intensity: str) -> dict[str, str]:
    treatments = {
        "soft": {
            "opacity": "0.28",
            "filter": "contrast(1.04) saturate(0.84)",
            "overlay": "linear-gradient(180deg, rgba(7, 10, 18, 0.10), rgba(7, 10, 18, 0.24))",
        },
        "medium": {
            "opacity": "0.46",
            "filter": "contrast(1.08) saturate(0.92)",
            "overlay": "linear-gradient(180deg, rgba(7, 10, 18, 0.12), rgba(7, 10, 18, 0.36))",
        },
        "strong": {
            "opacity": "0.64",
            "filter": "contrast(1.12) saturate(1.02)",
            "overlay": "linear-gradient(180deg, rgba(7, 10, 18, 0.10), rgba(7, 10, 18, 0.44))",
        },
    }
    return treatments.get(background_intensity, treatments["medium"])


def build_slide_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
    allow_ai_html: bool = True,
) -> str:
    """Route to the correct HTML builder based on layout_style."""
    if allow_ai_html:
        ai_html = _build_ai_slide_html(spec, custom_background_data_url, background_intensity)
        if ai_html:
            return ai_html

    style = spec.layout_style
    if style not in LAYOUT_STYLE_FONTS:
        style = "magazine"

    builders = {
        "magazine": _build_magazine_slide_html,
        "terminal": _build_terminal_slide_html,
        "poster": _build_poster_slide_html,
        "carddeck": _build_carddeck_slide_html,
    }
    builder = builders.get(style, _build_magazine_slide_html)
    return builder(spec, logo_text, custom_background_data_url, background_intensity)


THEME_TOKENS = {
    "business_dark": {
        "bg": "radial-gradient(circle at top right, rgba(56,189,248,0.24), transparent 30%), linear-gradient(180deg, #08111f 0%, #111c31 100%)",
        "panel": "rgba(9, 17, 30, 0.82)",
        "text": "#f8fafc",
        "muted": "#dbeafe",
        "accent": "#38bdf8",
        "chip": "rgba(255,255,255,0.08)",
    },
    "minimal_light": {
        "bg": "radial-gradient(circle at top right, rgba(15,23,42,0.10), transparent 28%), linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)",
        "panel": "rgba(255,255,255,0.74)",
        "text": "#0f172a",
        "muted": "#334155",
        "accent": "#0f172a",
        "chip": "rgba(15,23,42,0.07)",
    },
    "creator_bold": {
        "bg": "radial-gradient(circle at top right, rgba(244,114,182,0.30), transparent 32%), linear-gradient(180deg, #2d123c 0%, #1a0b23 100%)",
        "panel": "rgba(49, 16, 58, 0.82)",
        "text": "#fff7fb",
        "muted": "#fce7f3",
        "accent": "#f472b6",
        "chip": "rgba(255,255,255,0.09)",
    },
    "editorial_premium": {
        "bg": "radial-gradient(circle at top right, rgba(245,158,11,0.24), transparent 30%), linear-gradient(180deg, #241808 0%, #141008 100%)",
        "panel": "rgba(41, 28, 8, 0.84)",
        "text": "#fffbeb",
        "muted": "#fef3c7",
        "accent": "#f59e0b",
        "chip": "rgba(255,255,255,0.08)",
    },
    "memory_archive": {
        "bg": "radial-gradient(circle at top left, rgba(164, 116, 73, 0.12), transparent 28%), linear-gradient(180deg, #f6f0e5 0%, #e8decc 100%)",
        "panel": "rgba(255, 250, 242, 0.88)",
        "text": "#1f2933",
        "muted": "#5b6570",
        "accent": "#2f6f62",
        "chip": "rgba(47,111,98,0.10)",
        "line": "rgba(61, 44, 29, 0.10)",
        "display_font": "Georgia, 'Times New Roman', serif",
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "founder_brief": {
        "bg": "radial-gradient(circle at top left, rgba(14,165,233,0.22), transparent 28%), linear-gradient(180deg, #f8fbff 0%, #e8f1fb 100%)",
        "panel": "rgba(255,255,255,0.82)",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0369a1",
        "chip": "rgba(3,105,161,0.08)",
        "line": "rgba(3,105,161,0.10)",
        "display_font": "'Arial Black', 'Segoe UI', sans-serif",
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "growth_black": {
        "bg": "radial-gradient(circle at top right, rgba(190,242,100,0.28), transparent 24%), radial-gradient(circle at bottom left, rgba(249,115,22,0.10), transparent 20%), linear-gradient(180deg, #020617 0%, #0f172a 100%)",
        "panel": "rgba(4,10,22,0.88)",
        "text": "#f9fafb",
        "muted": "#d5dde7",
        "accent": "#bef264",
        "chip": "rgba(190,242,100,0.10)",
        "line": "rgba(255,255,255,0.08)",
        "display_font": "'Arial Black', 'Trebuchet MS', sans-serif",
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "research_mono": {
        "bg": "radial-gradient(circle at top right, rgba(185,28,28,0.08), transparent 20%), linear-gradient(180deg, #f8f7f3 0%, #ece8df 100%)",
        "panel": "rgba(255,255,255,0.84)",
        "text": "#111827",
        "muted": "#4b5563",
        "accent": "#b91c1c",
        "chip": "rgba(185,28,28,0.06)",
        "line": "rgba(17,24,39,0.10)",
        "display_font": "'SFMono-Regular', 'Menlo', 'Monaco', monospace",
        "body_font": "'SFMono-Regular', 'Menlo', 'Monaco', monospace",
    },
}

FONT_MAP = {
    "standard": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "prosto": "'Arial Black', 'Segoe UI', sans-serif",
    "rampart": "'Impact', 'Arial Black', sans-serif",
    "dela": "'Arial Black', 'Trebuchet MS', sans-serif",
}

AI_FONT_QUERIES = {
    "inter": "Inter:wght@400;500;600;700;800",
    "playfair display": "Playfair+Display:wght@400;700;900",
    "cormorant garamond": "Cormorant+Garamond:wght@400;500;600;700",
    "jetbrains mono": "JetBrains+Mono:wght@400;500;700;800",
    "unbounded": "Unbounded:wght@400;700;900",
    "manrope": "Manrope:wght@400;500;700;800",
    "space grotesk": "Space+Grotesk:wght@400;500;700",
    "sora": "Sora:wght@400;600;700;800",
    "dm serif display": "DM+Serif+Display:ital@0;1",
}


def _build_ai_slide_html(
    spec: LayoutSpec,
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
) -> str:
    html_body = _sanitize_ai_html_body(getattr(spec, "html_body", ""))
    if not html_body:
        return ""

    imports = _google_font_imports_for_html(getattr(spec, "layout_style", "magazine"), html_body)
    texture_css = _texture_css_for_slide(getattr(spec, "theme", "business_dark"))
    fonts_block = f'<link href="https://fonts.googleapis.com/css2?{imports}&display=swap" rel="stylesheet">' if imports else ""
    safe_bg = _safe_data_image_url(custom_background_data_url)
    if safe_bg:
        html_body = _soften_ai_root_background(html_body)
    background = _background_treatment(background_intensity)
    background_markup = (
        f'<div class="ai-custom-bg" style="background-image:url(&quot;{safe_bg}&quot;);"></div>'
        if safe_bg
        else ""
    )
    stage_background_css = "background: transparent !important;" if safe_bg else ""
    background_css = f"""
    .ai-custom-bg {{
      position: absolute;
      inset: 0;
      background-position: center;
      background-size: cover;
      opacity: {background["opacity"]};
      filter: {background["filter"]};
      z-index: 0;
    }}
    .ai-custom-bg::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: {background["overlay"]};
    }}
    """ if safe_bg else ""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, initial-scale=1">
  {fonts_block}
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 1080px; height: 1350px; overflow: hidden; }}
    body {{ position: relative; background: #0b1020; }}
    {background_css}
    .ai-texture {{ position: absolute; inset: 0; z-index: 1; pointer-events: none; opacity: 0.24; {texture_css} }}
    .ai-stage {{ position: relative; z-index: 2; width: 1080px; height: 1350px; }}
    .ai-stage > * {{
      width: 100%;
      min-height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
      {stage_background_css}
    }}
  </style>
</head>
<body>
  {background_markup}
  <div class="ai-texture"></div>
  <div class="ai-stage">{html_body}</div>
</body>
</html>"""


def _sanitize_ai_html_body(value: str) -> str:
    html_body = (value or "").strip()
    if not html_body:
        return ""
    if "<script" in html_body.lower():
        return ""
    if not re.search(r"<[a-zA-Z][^>]*>", html_body):
        return ""
    return html_body


def _soften_ai_root_background(html_body: str) -> str:
    match = re.search(r"<([a-zA-Z][^>\s]*)([^>]*)style=(['\"])(.*?)(\3)([^>]*)>", html_body, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return html_body

    style_value = match.group(4)
    softened_style = _soften_root_style_value(style_value)
    if softened_style == style_value:
        return html_body

    start, end = match.span(4)
    return html_body[:start] + softened_style + html_body[end:]


def _soften_root_style_value(style_value: str) -> str:
    background_match = re.search(r"background(?:-color)?\s*:\s*([^;]+)", style_value, flags=re.IGNORECASE)
    if not background_match:
        return style_value

    raw_value = background_match.group(1).strip()
    softened_value = _softened_background_value(raw_value)
    if not softened_value:
        return style_value

    softened_style = re.sub(
        r"background(?:-color)?\s*:\s*([^;]+);?",
        f"background-color:{softened_value};",
        style_value,
        count=1,
        flags=re.IGNORECASE,
    )
    if "backdrop-filter" not in softened_style.lower():
        softened_style += "backdrop-filter:blur(8px);"
    if "border:" not in softened_style.lower():
        softened_style += "border:1px solid rgba(255,255,255,0.14);"
    if "box-shadow" not in softened_style.lower():
        softened_style += "box-shadow:0 18px 44px rgba(0,0,0,0.22);"
    return softened_style


def _softened_background_value(raw_value: str) -> str:
    compact = raw_value.strip().lower()
    if compact.startswith("#"):
        hex_value = compact[1:]
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) != 6:
            return ""
        try:
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)
        except ValueError:
            return ""
        alpha = 0.78 if (r + g + b) / 3 > 160 else 0.62
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"

    rgb_match = re.match(r"rgba?\(([^)]+)\)", compact)
    if rgb_match:
        parts = [part.strip() for part in rgb_match.group(1).split(",")]
        if len(parts) < 3:
            return ""
        try:
            r = int(float(parts[0]))
            g = int(float(parts[1]))
            b = int(float(parts[2]))
        except ValueError:
            return ""
        alpha = 0.78 if (r + g + b) / 3 > 160 else 0.62
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"

    return ""


def _google_font_imports_for_html(layout_style: str, html_body: str) -> str:
    imports: list[str] = []
    seen: set[str] = set()

    def add_query(query: str) -> None:
        if query and query not in seen:
            seen.add(query)
            imports.append(query)

    add_query(LAYOUT_STYLE_FONTS.get(layout_style, LAYOUT_STYLE_FONTS["magazine"])["google"])
    for family in _extract_font_families(html_body):
        query = AI_FONT_QUERIES.get(family.lower())
        if query:
            add_query(query)

    return "|".join(imports)


def _extract_font_families(html_body: str) -> list[str]:
    families: list[str] = []
    for raw_value in re.findall(r"font-family\s*:\s*([^;\"']+|\"[^\"]+\"|'[^']+')", html_body, flags=re.IGNORECASE):
        for family in str(raw_value).split(","):
            clean = family.strip().strip("'\"")
            if clean:
                families.append(clean)
    return families


def _texture_css_for_slide(theme: str) -> str:
    textures = {
        "growth_black": "background-image: linear-gradient(rgba(190,242,100,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 100% 6px, 28px 28px;",
        "business_dark": "background-image: radial-gradient(circle at 20% 20%, rgba(56,189,248,0.18), transparent 18%), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px); background-size: 100% 100%, 32px 32px;",
        "minimal_light": "background-image: radial-gradient(circle, rgba(15,23,42,0.05) 1px, transparent 1px); background-size: 18px 18px;",
        "founder_brief": "background-image: linear-gradient(rgba(3,105,161,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(3,105,161,0.04) 1px, transparent 1px); background-size: 100% 28px, 28px 100%;",
        "memory_archive": "background-image: radial-gradient(circle at 10% 20%, rgba(61,44,29,0.08), transparent 16%), radial-gradient(circle at 80% 70%, rgba(164,106,63,0.08), transparent 18%);",
        "creator_bold": "background-image: radial-gradient(circle at 15% 20%, rgba(244,114,182,0.18), transparent 18%), radial-gradient(circle at 85% 30%, rgba(99,102,241,0.18), transparent 20%);",
        "editorial_premium": "background-image: linear-gradient(135deg, rgba(245,158,11,0.08), transparent 32%), radial-gradient(circle at 80% 15%, rgba(255,251,235,0.08), transparent 14%);",
        "research_mono": "background-image: linear-gradient(rgba(17,24,39,0.05) 1px, transparent 1px); background-size: 100% 5px;",
    }
    return textures.get(theme, textures["business_dark"])


# ═══════════════════════════════════════════════════════════════
# СТИЛЬ 1: MAGAZINE (журнальный)
# Вдохновение: The New Yorker, Wired — serif, воздух, элегантность
# ═══════════════════════════════════════════════════════════════

def _build_magazine_slide_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
) -> str:
    fonts = LAYOUT_STYLE_FONTS["magazine"]
    title = html.escape(spec.title)
    body = html.escape(spec.body).replace("\n", "<br>")
    logo = html.escape(logo_text)
    section = html.escape(spec.badge_text).upper() if spec.badge_text else "ЗАМЕТКА"
    section_num = f"{spec.slide_index:02d}"
    is_cover = spec.slide_index == 1
    is_cta = spec.slide_index == spec.total_slides
    theme = spec.theme if spec.theme in {"memory_archive", "founder_brief", "research_mono"} else "memory_archive"
    stage_align = "justify-content: center;" if spec.text_position == "center" else ""

    safe_bg = _safe_data_image_url(custom_background_data_url)
    has_custom_bg = bool(safe_bg)

    # Палитра: тёмная или светлая в зависимости от темы.
    # Если есть кастомный фон — выбираем контрастные цвета текста
    # и НЕ накладываем непрозрачные заливки поверх.
    if theme in {"research_mono", "founder_brief"}:
        text_color = "#111827"
        muted = "#1f2937"
        accent = "#b91c1c" if theme == "research_mono" else "#0369a1"
        line = "rgba(17,24,39,0.45)"
        tag_bg = "rgba(255,255,255,0.55)"
        watermark = "rgba(17,24,39,0.18)"
        text_shadow = "0 2px 12px rgba(255,255,255,0.55), 0 0 2px rgba(255,255,255,0.7)"
        muted_shadow = "0 1px 8px rgba(255,255,255,0.45)"
    else:
        text_color = "#ffffff"
        muted = "#f5f5f5"
        accent = "#b89cff"
        line = "rgba(255,255,255,0.75)"
        tag_bg = "rgba(0,0,0,0.40)"
        watermark = "rgba(255,255,255,0.22)"
        text_shadow = "0 2px 14px rgba(0,0,0,0.70), 0 0 2px rgba(0,0,0,0.85)"
        muted_shadow = "0 1px 10px rgba(0,0,0,0.60)"

    if has_custom_bg:
        # Прозрачный фон body, без overlay — кастомное изображение видно
        bg = "transparent"
        bg_opacity = "1.0"
        bg_filter = "none"
    else:
        bg = "#f8f7f3" if theme == "research_mono" else "#f8fbff" if theme == "founder_brief" else "#09070f"
        bg_opacity = "0"
        bg_filter = "none"
        text_shadow = "none"
        muted_shadow = "none"

    custom_bg_html = f'''
    .custom-bg {{
      position: absolute; inset: 0; z-index: 0;
      background: url("{safe_bg}") center/cover no-repeat;
      filter: {bg_filter};
      opacity: {bg_opacity};
    }}
    .custom-bg-overlay {{
      position: absolute; inset: 0; z-index: 0;
      background: {"linear-gradient(180deg, rgba(0,0,0,0.30) 0%, rgba(0,0,0,0.45) 100%)" if theme in {"research_mono","founder_brief"} else "linear-gradient(180deg, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0.50) 100%)"};
    }}
    ''' if has_custom_bg else ""
    custom_bg_div = (
        f'<div class="custom-bg"></div><div class="custom-bg-overlay"></div>'
        if has_custom_bg
        else ""
    )
    google_fonts = _google_fonts_link("magazine")

    supporting_html = "".join(
        f'<div class="mag-card"><span>{html.escape(c.get("title",""))}</span><strong>{html.escape(c.get("body",""))}</strong></div>'
        for c in spec.supporting_cards[:3]
    )

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <link href="{google_fonts}" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: {bg}; color: {text_color}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; padding: 80px 72px 60px; display: flex; flex-direction: column; }}
    {custom_bg_html}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: {"60px" if is_cover else "40px"}; position: relative; z-index: 2; }}
    .section-label {{ font-family: {fonts["heading"]}; font-size: 18px; letter-spacing: 0.2em; text-transform: uppercase; color: {muted}; text-shadow: {muted_shadow}; }}
    .brand {{ font-family: {fonts["heading"]}; font-size: 20px; font-style: italic; color: {accent}; text-shadow: {muted_shadow}; }}
    .stage {{ position: relative; z-index: 2; flex: 1; display: flex; flex-direction: column; {stage_align}}}
    .watermark {{ position: absolute; top: {"40px" if is_cover else "0"}; right: 0; font-family: {fonts["heading"]}; font-size: {"160px" if is_cover else "120px"}; color: {watermark}; line-height: 0.8; pointer-events: none; user-select: none; z-index: 1; text-shadow: {text_shadow}; }}
    .title {{ font-family: {fonts["heading"]}; font-size: {"88px" if is_cover else "64px" if is_cta else "54px"}; line-height: 0.96; font-weight: 900; max-width: {"860px" if is_cover else "720px"}; letter-spacing: -0.03em; position: relative; z-index: 3; margin-bottom: {"32px" if is_cover else "24px"}; text-shadow: {text_shadow}; }}
    .title.cta {{ font-style: italic; font-size: 72px; color: {accent}; }}
    .divider {{ width: 80px; height: 3px; background: {accent}; margin-bottom: 24px; box-shadow: 0 1px 6px rgba(0,0,0,0.45); }}
    .body {{ font-family: {fonts["body"]}; font-size: {"30px" if is_cover else "26px"}; line-height: 1.5; color: {muted}; max-width: {"740px" if is_cover else "620px"}; text-shadow: {muted_shadow}; }}
    .supporting {{ display: {"grid" if supporting_html else "none"}; grid-template-columns: repeat({min(len(spec.supporting_cards[:3]), 2)}, 1fr); gap: 14px; margin-top: 28px; max-width: 700px; }}
    .mag-card {{ padding: 18px; border: 1px solid {line}; background: {tag_bg}; }}
    .mag-card span {{ font-family: {fonts["heading"]}; font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: {accent}; display: block; margin-bottom: 6px; text-shadow: {muted_shadow}; }}
    .mag-card strong {{ font-family: {fonts["body"]}; font-size: 20px; font-weight: 500; color: {text_color}; display: block; text-shadow: {muted_shadow}; }}
    .footer {{ position: absolute; left: 72px; right: 72px; bottom: 56px; display: flex; justify-content: space-between; font-family: {fonts["body"]}; font-size: 18px; color: {muted}; z-index: 3; text-shadow: {muted_shadow}; }}
  </style>
</head>
<body>
  <div class="canvas">
    {custom_bg_div}
    <div class="watermark">{section_num}</div>
    <div class="topbar">
      <div class="section-label">{section_num} · {section}</div>
      <div class="brand">{logo}</div>
    </div>
    <div class="stage">
      <div class="title{" cta" if is_cta else ""}">{title}</div>
      <div class="divider"></div>
      <div class="body">{body}</div>
      <div class="supporting">{supporting_html}</div>
    </div>
    <div class="footer">
      <span>{section}</span>
      <span>{spec.slide_index}/{spec.total_slides}</span>
    </div>
  </div>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════
# СТИЛЬ 2: TERMINAL (терминальный)
# Вдохновение: Warp, iTerm2 — monospace, зелёный на чёрном, ASCII
# ═══════════════════════════════════════════════════════════════

def _build_terminal_slide_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
) -> str:
    fonts = LAYOUT_STYLE_FONTS["terminal"]
    title = html.escape(spec.title)
    body = html.escape(spec.body).replace("\n", "<br>")
    logo = html.escape(logo_text)
    is_cover = spec.slide_index == 1
    is_cta = spec.slide_index == spec.total_slides
    stage_align = "display: flex; flex-direction: column; justify-content: center;" if spec.text_position == "center" else ""

    # Amber (тёплый) или Green (холодный) — выбираем по контексту
    is_warm = spec.theme in {"growth_black", "editorial_premium"}
    accent = "#ffb347" if is_warm else "#00ff41"
    dim_accent = "#8b6914" if is_warm else "#006b1a"
    header = "⚡ ~/chu/carousel.sh" if is_warm else "$ ./generate.sh"

    progress_chars = ("█" * spec.slide_index + "░" * (spec.total_slides - spec.slide_index))
    tags_chars = " ".join(spec.footer_tags[:3]) if spec.footer_tags else "..."

    supporting_text = " | ".join(
        f"{c.get('title','')}: {c.get('body','')}" for c in spec.supporting_cards[:2]
    )

    safe_bg = _safe_data_image_url(custom_background_data_url)
    has_custom_bg = bool(safe_bg)

    if has_custom_bg:
        # Полупрозрачная панель сверху для контраста, но фон виден
        body_bg = "transparent"
        header_bg = "rgba(0,0,0,0.55)"
        ascii_bg = "rgba(0,0,0,0.55)"
        text_shadow = "0 1px 8px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.95)"
        panel_color = "#ffffff"
    else:
        body_bg = "#0a0e0a"
        header_bg = "rgba(0,0,0,0.4)"
        ascii_bg = "rgba(0,0,0,0.3)"
        text_shadow = "none"
        panel_color = accent

    custom_bg_css = f'''
    .custom-bg {{
      position: absolute; inset: 0; z-index: 0;
      background: url("{safe_bg}") center/cover no-repeat;
    }}
    .custom-bg-overlay {{
      position: absolute; inset: 0; z-index: 0;
      background: linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.30) 50%, rgba(0,0,0,0.55) 100%);
    }}
    ''' if has_custom_bg else ""
    custom_bg_div = (
        f'<div class="custom-bg"></div><div class="custom-bg-overlay"></div>'
        if has_custom_bg
        else ""
    )
    google_fonts = _google_fonts_link("terminal")

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <link href="{google_fonts}" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: {body_bg}; color: {accent}; font-family: {fonts["heading"]}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; padding: 48px; display: flex; flex-direction: column; }}
    {custom_bg_css}
    .header-bar {{ font-size: 22px; color: {accent}; margin-bottom: 36px; padding: 12px 20px; border: 1px solid {accent}; background: {header_bg}; position: relative; z-index: 2; text-shadow: {text_shadow}; }}
    .header-bar::before {{ content: "{"> " if is_warm else "$ "}"; color: {accent}; }}
    .stage {{ flex: 1; padding: {"80px 28px" if is_cover else "40px 28px"}; position: relative; z-index: 2; {stage_align}}}
    .ascii-box {{ border: 1px solid {accent}; padding: {"36px" if is_cover else "28px"}; margin-bottom: 24px; background: {ascii_bg}; position: relative; }}
    .ascii-box::before {{ content: "┌─── " attr(data-label) " ───"; position: absolute; top: -14px; left: 20px; background: {"#0a0e0a" if not has_custom_bg else "rgba(0,0,0,0.85)"}; padding: 0 10px; font-size: 16px; color: {accent}; }}
    .ascii-box::after {{ content: ""; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: {accent}; }}
    .title {{ font-size: {"46px" if is_cover else "34px"}; font-weight: 800; line-height: 1.1; color: {accent}; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.04em; text-shadow: {text_shadow}; }}
    .body {{ font-size: 24px; line-height: 1.5; color: {panel_color if has_custom_bg else ("#d4d4d4" if is_cta else "#b8c8b8")}; text-shadow: {text_shadow}; }}
    .body.cta-text {{ color: {accent}; font-weight: 700; font-size: 28px; }}
    .progress-line {{ font-size: 20px; color: {accent}; margin-top: {"auto" if not is_cover else "48px"}; font-family: {fonts["heading"]}; text-shadow: {text_shadow}; }}
    .progress-bar {{ display: flex; gap: 4px; margin-top: 8px; }}
    .progress-fill {{ flex: none; color: {accent}; font-size: 22px; letter-spacing: 2px; }}
    .progress-empty {{ flex: none; color: {dim_accent}; font-size: 22px; letter-spacing: 2px; }}
    .supporting {{ margin-top: 20px; padding: 14px 18px; border-left: 2px solid {accent}; font-size: 20px; color: {panel_color if has_custom_bg else "#889988"}; text-shadow: {text_shadow}; }}
    .footer {{ position: absolute; left: 48px; right: 48px; bottom: 40px; display: flex; justify-content: space-between; font-size: 18px; color: {accent}; z-index: 3; text-shadow: {text_shadow}; }}
    .cursor {{ display: inline-block; width: 12px; height: 24px; background: {accent}; animation: blink 1s step-end infinite; vertical-align: middle; margin-left: 4px; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
  </style>
</head>
<body>
  <div class="canvas">
    {custom_bg_div}
    <div class="header-bar">{header}</div>
    <div class="stage">
      <div class="ascii-box" data-label=" {html.escape(spec.badge_text or "EXEC")} ">
        <div class="title">{title}</div>
        <div class="body{" cta-text" if is_cta else ""}">{body}</div>
      </div>
      {'<div class="supporting">⤷ ' + supporting_text + '</div>' if supporting_text else ''}
      <div class="progress-line">
        <div class="progress-bar">
          {''.join(f'<span class="progress-fill">{"█" if i < spec.slide_index else "░"}</span>' for i in range(spec.total_slides))}
        </div>
        [{spec.slide_index}/{spec.total_slides}] {html.escape(tags_chars)}
      </div>
    </div>
    <div class="footer">
      <span>{logo}</span>
      <span>{'SUCCESS: carousel.sh — exit 0' if is_cta else 'RUNNING: carousel.sh'} <span class="cursor"></span></span>
    </div>
  </div>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════
# СТИЛЬ 3: POSTER (плакатный)
# Вдохновение: Bauhaus, Swiss Design — огромная типографика, контраст
# ═══════════════════════════════════════════════════════════════

def _build_poster_slide_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
) -> str:
    fonts = LAYOUT_STYLE_FONTS["poster"]
    title = html.escape(spec.title)
    body = html.escape(spec.body).replace("\n", "<br>")
    logo = html.escape(logo_text)
    is_cover = spec.slide_index == 1
    is_cta = spec.slide_index == spec.total_slides

    # 4 контрастных цвета плаката
    poster_colors = [
        ("#d63921", "#faf6ed"),  # красный
        ("#1048ff", "#f8f5ef"),  # синий
        ("#000000", "#faf6ed"),  # чёрный
        ("#f45124", "#07080b"),  # оранжевый
    ]
    color_idx = (spec.slide_index - 1) % len(poster_colors)
    block_color, text_color = poster_colors[color_idx]

    body_lines = spec.body.split("\n") if spec.body else []
    body_short = body_lines[0][:60] if body_lines else body

    safe_bg = _safe_data_image_url(custom_background_data_url)
    has_custom_bg = bool(safe_bg)

    if has_custom_bg:
        # Без сплошной заливки — кастомный фон виден
        block_bg = "rgba(0,0,0,0.45)"
        body_bg = "transparent"
        text_color_eff = "#ffffff"
        block_text_color = "#ffffff"
        block_text_shadow = "0 2px 14px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.95)"
    else:
        block_bg = block_color
        body_bg = text_color
        text_color_eff = block_color
        block_text_color = text_color
        block_text_shadow = "none"

    custom_bg_div = (
        f'<div class="custom-bg" style="position:absolute; inset:0; z-index:0; background:url(&quot;{safe_bg}&quot;) center/cover no-repeat;"></div>'
        if has_custom_bg
        else ""
    )
    custom_bg_overlay = (
        '<div class="custom-bg-overlay" style="position:absolute; inset:0; z-index:0; background:linear-gradient(180deg, rgba(0,0,0,0.20) 0%, rgba(0,0,0,0.45) 100%);"></div>'
        if has_custom_bg
        else ""
    )
    google_fonts = _google_fonts_link("poster")

    # progress dots - собираем отдельно, избегая вложенных f-строк
    dots_html_parts = []
    for i in range(spec.total_slides):
        if i == spec.slide_index - 1:
            dots_html_parts.append(f'<div class="dot active"></div>')
        else:
            dots_html_parts.append('<div class="dot"></div>')
    dots_html = "".join(dots_html_parts)

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <link href="{google_fonts}" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: {body_bg}; color: {text_color_eff}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; display: flex; flex-direction: column; }}
    .block {{ position: absolute; {"top: 0; left: 0; right: 0; height: 58%;" if not is_cta else "top: 0; left: 0; right: 0; bottom: 0;"} background: {block_bg}; display: flex; align-items: center; justify-content: center; overflow: hidden; z-index: 1; }}
    .block-text {{ font-family: {fonts["heading"]}; font-size: {"120px" if is_cover else "96px" if not is_cta else "80px"}; font-weight: 900; color: {block_text_color}; line-height: 0.92; text-align: center; max-width: 880px; padding: 40px; letter-spacing: -0.04em; word-break: break-word; text-shadow: {block_text_shadow}; position: relative; z-index: 2; }}
    .block-text.small {{ font-size: 60px; }}
    .footer-zone {{ position: absolute; {"top: 58%;" if not is_cta else "top: auto;"} bottom: 0; left: 0; right: 0; height: {"42%" if not is_cta else "auto"}; display: flex; flex-direction: column; justify-content: center; padding: {"60px 80px" if not is_cta else "48px 80px"}; z-index: 2; }}
    .body-text {{ font-family: {fonts["body"]}; font-size: 32px; line-height: 1.4; color: {text_color_eff}; max-width: 760px; text-shadow: {block_text_shadow}; }}
    .meta {{ position: absolute; left: 72px; right: 72px; bottom: 48px; display: flex; justify-content: space-between; font-family: {fonts["body"]}; font-size: 18px; color: {text_color_eff}; opacity: 0.85; z-index: 3; text-shadow: {block_text_shadow}; }}
    .badge {{ font-family: {fonts["heading"]}; font-size: 18px; letter-spacing: 0.2em; text-transform: uppercase; color: {block_text_color}; margin-bottom: {"24px" if is_cta else "0"}; text-shadow: {block_text_shadow}; }}
    .accent-line {{ width: 60px; height: 4px; background: {block_text_color}; margin-bottom: 16px; }}
    .progress-dot {{ position: absolute; right: 72px; bottom: 80px; display: flex; gap: 10px; z-index: 3; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; background: {block_text_color}; opacity: 0.5; }}
    .dot.active {{ width: 14px; height: 14px; opacity: 1; background: {block_text_color}; }}
  </style>
</head>
<body>
  <div class="canvas">
    {custom_bg_div}
    {custom_bg_overlay}
    <div class="block">
      <div class="block-text{" small" if len(title) > 30 else ""}">{title}</div>
    </div>
    <div class="footer-zone">
      {"<div class='badge'>" + html.escape(spec.badge_text).upper() + "</div>" if not is_cta and spec.badge_text else ""}
      <div class="accent-line"></div>
      <div class="body-text">{body_short}</div>
    </div>
    <div class="progress-dot">{dots_html}</div>
    <div class="meta">
      <span>{logo}</span>
      <span>{spec.slide_index}/{spec.total_slides}</span>
    </div>
  </div>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════
# СТИЛЬ 4: CARDDECK (карточный)
# Вдохновение: Linear, Notion — чистые карточки, скругления, glassmorphism
# ═══════════════════════════════════════════════════════════════

def _build_carddeck_slide_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
) -> str:
    fonts = LAYOUT_STYLE_FONTS["carddeck"]
    title = html.escape(spec.title)
    body = html.escape(spec.body).replace("\n", "<br>")
    logo = html.escape(logo_text)
    is_cover = spec.slide_index == 1
    is_cta = spec.slide_index == spec.total_slides
    card_align = "justify-content: center; align-items: center; text-align: center;" if spec.text_position == "center" and not is_cover else ""

    accent = "#6366f1"
    safe_bg = _safe_data_image_url(custom_background_data_url)
    has_custom_bg = bool(safe_bg)

    if has_custom_bg:
        # Карточка полупрозрачная, без blur — фон виден чётко
        body_bg = "transparent"
        card_bg = "rgba(15, 15, 26, 0.55)"
        text_color = "#ffffff"
        muted = "rgba(255,255,255,0.92)"
        border = "rgba(255,255,255,0.45)"
        text_shadow = "0 1px 10px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.95)"
        backdrop_filter = "none"
    else:
        body_bg = "#0f0f1a"
        card_bg = "rgba(255,255,255,0.04)"
        text_color = "#f1f5f9"
        muted = "#94a3b8"
        border = "rgba(255,255,255,0.08)"
        text_shadow = "none"
        backdrop_filter = "blur(16px)"

    custom_bg_div = (
        f'<div class="custom-bg" style="position:absolute; inset:0; z-index:0; background:url(&quot;{safe_bg}&quot;) center/cover no-repeat;"></div>'
        if has_custom_bg
        else ""
    )
    custom_bg_overlay = (
        '<div class="custom-bg-overlay" style="position:absolute; inset:0; z-index:0; background:linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.35) 100%);"></div>'
        if has_custom_bg
        else ""
    )
    google_fonts = _google_fonts_link("carddeck")

    supporting_html = "".join(
        f'<div class="chip"><span>{html.escape(c.get("title",""))}</span><strong>{html.escape(c.get("body",""))}</strong></div>'
        for c in spec.supporting_cards[:4]
    )

    dot_progress = "".join(
        f'<div class="dot{" active" if i == spec.slide_index - 1 else ""}' +
        (f' style="background: {accent};"' if i == spec.slide_index - 1 else '') +
        '></div>'
        for i in range(spec.total_slides)
    )

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <link href="{google_fonts}" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: {body_bg}; color: {text_color}; font-family: {fonts["body"]}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; padding: 48px; display: flex; flex-direction: column; }}
    .card {{ position: relative; z-index: 2; flex: 1; margin: 0; border-radius: 32px; background: {card_bg}; border: 1px solid {border}; backdrop-filter: {backdrop_filter}; -webkit-backdrop-filter: {backdrop_filter}; padding: {"52px 48px" if is_cover else "44px 44px"}; display: flex; flex-direction: column; {card_align}}}
    .card.cover {{ justify-content: center; align-items: center; text-align: center; }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
    .badge {{ font-size: 14px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: {accent}; padding: 6px 14px; border-radius: 999px; background: rgba(99,102,241,0.10); border: 1px solid rgba(99,102,241,0.15); text-shadow: {text_shadow}; }}
    .counter {{ font-size: 16px; color: {muted}; font-weight: 500; text-shadow: {text_shadow}; }}
    .title {{ font-family: {fonts["body"]}; font-size: {"64px" if is_cover else "44px" if is_cta else "38px"}; font-weight: 800; line-height: 1.08; margin-bottom: {"24px" if is_cover else "16px"}; letter-spacing: -0.03em; text-shadow: {text_shadow}; }}
    .body {{ font-size: {"26px" if is_cover else "24px"}; line-height: 1.5; color: {muted}; max-width: {"640px" if is_cover else "580px"}; text-shadow: {text_shadow}; }}
    .body.cta {{ font-size: 28px; color: {accent}; font-weight: 600; }}
    .supporting {{ display: {"flex" if supporting_html else "none"}; flex-wrap: wrap; gap: 12px; margin-top: auto; padding-top: 24px; }}
    .chip {{ display: flex; flex-direction: column; gap: 4px; padding: 14px 18px; border-radius: 16px; background: rgba(255,255,255,0.06); border: 1px solid {border}; min-width: 180px; }}
    .chip span {{ font-size: 13px; letter-spacing: 0.1em; text-transform: uppercase; color: {accent}; text-shadow: {text_shadow}; }}
    .chip strong {{ font-size: 18px; font-weight: 600; color: {text_color}; text-shadow: {text_shadow}; }}
    .progress-dots {{ display: flex; gap: 8px; justify-content: center; margin-top: 24px; }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {border}; transition: all 0.2s; }}
    .dot.active {{ width: 28px; border-radius: 999px; background: {accent}; }}
    .footer {{ position: absolute; left: 72px; right: 72px; bottom: 48px; display: flex; justify-content: space-between; font-size: 16px; color: {muted}; z-index: 3; text-shadow: {text_shadow}; }}
  </style>
</head>
<body>
  <div class="canvas">
    {custom_bg_div}
    {custom_bg_overlay}
    <div class="card{" cover" if is_cover else ""}">
      {"<div class='topbar'><div class='badge'>" + html.escape(spec.badge_text).upper() + "</div><div class='counter'>" + str(spec.slide_index) + "/" + str(spec.total_slides) + "</div></div>" if not is_cover else ""}
      <div class="title">{title}</div>
      <div class="body{" cta" if is_cta else ""}">{body}</div>
      <div class="supporting">{supporting_html}</div>
      <div class="progress-dots">{dot_progress}</div>
    </div>
    <div class="footer">
      <span>{logo}</span>
      <span>{"сохрани карусель" if is_cta else "листай →"}</span>
    </div>
  </div>
</body>
</html>'''


def _safe_data_image_url(value: str) -> str:
    value = (value or "").strip()
    if not value.startswith("data:image/"):
        return ""
    if '"' in value or ")" in value:
        return ""
    return html.escape(value, quote=True)


def render_layout_spec_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    background_intensity: str = "medium",
    allow_ai_html: bool = True,
) -> bytes:
    html_content = build_slide_html(
        spec,
        logo_text=logo_text,
        custom_background_data_url=custom_background_data_url,
        background_intensity=background_intensity,
        allow_ai_html=allow_ai_html,
    )

    # Try Playwright first
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
            page.set_content(html_content, wait_until="load")
            png = page.screenshot(
                type="png",
                clip={"x": 0, "y": 0, "width": 1080, "height": 1350},
            )
            browser.close()
        return png
    except Exception as exc:
        logging.warning("Playwright HTML render failed, using Pillow fallback: %s", exc)

    # Pillow fallback: create a simple branded slide
    try:
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        img = Image.new("RGB", (1080, 1350), (15, 20, 35))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
            font_small = font
        title = (spec.title or "Без заголовка").strip()
        body = (spec.body or "").strip()
        bbox = draw.textbbox((0, 0), title, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (1080 - tw) // 2
        y = (1350 - th) // 2 - 40
        draw.text((x, y), title, fill=(255, 255, 255), font=font)
        if body:
            draw.text((80, y + th + 30), body[:200], fill=(180, 190, 210), font=font_small)
        # Footer with logo
        draw.text((72, 1240), logo_text or "chu ai", fill=(100, 120, 160), font=font_small)
        draw.text((800, 1240), f"{spec.slide_index}/{spec.total_slides}", fill=(100, 120, 160), font=font_small)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc2:
        logging.error("Pillow HTML fallback also failed: %s", exc2)
        # Last resort: empty PNG
        import struct, zlib
        def _make_png(w, h):
            raw = b""
            for _ in range(h):
                raw += b"\x00" + b"\x99" * w * 3
            def _chunk(t, d):
                c = t + d
                return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return (b"\x89PNG\r\n\x1a\n" +
                    _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                    _chunk(b"IDAT", zlib.compress(raw)) +
                    _chunk(b"IEND", b""))
        return _make_png(1080, 1350)
