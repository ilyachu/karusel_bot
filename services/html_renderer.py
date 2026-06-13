import html
import logging

from services.layout_engine import LayoutSpec, LAYOUT_STYLE_FONTS


def _google_fonts_link(layout_style: str) -> str:
    """Build Google Fonts @import URL for a given layout style."""
    fonts = LAYOUT_STYLE_FONTS.get(layout_style, LAYOUT_STYLE_FONTS["magazine"])
    families = fonts["google"]
    if not families:
        return ""
    return f'https://fonts.googleapis.com/css2?{families}&display=swap'


def build_slide_html(spec: LayoutSpec, logo_text: str = "chu ai", custom_background_data_url: str = "") -> str:
    """Route to the correct HTML builder based on layout_style."""
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
    return builder(spec, logo_text, custom_background_data_url)


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


# ═══════════════════════════════════════════════════════════════
# СТИЛЬ 1: MAGAZINE (журнальный)
# Вдохновение: The New Yorker, Wired — serif, воздух, элегантность
# ═══════════════════════════════════════════════════════════════

def _build_magazine_slide_html(
    spec: LayoutSpec,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
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

    # Палитра: тёмная или светлая в зависимости от темы
    if theme in {"research_mono", "founder_brief"}:
        bg = "#f8f7f3" if theme == "research_mono" else "#f8fbff"
        text_color = "#111827"
        muted = "#6b7280"
        accent = "#b91c1c" if theme == "research_mono" else "#0369a1"
        line = "rgba(17,24,39,0.10)"
        tag_bg = "rgba(0,0,0,0.04)"
        watermark = "rgba(17,24,39,0.04)"
    else:
        bg = "#09070f"
        text_color = "#f5f1ff"
        muted = "#9ca3af"
        accent = "#b89cff"
        line = "rgba(255,255,255,0.10)"
        tag_bg = "rgba(255,255,255,0.05)"
        watermark = "rgba(255,255,255,0.04)"

    safe_bg = _safe_data_image_url(custom_background_data_url)
    custom_bg_html = f'''
    .custom-bg {{
      position: absolute; inset: 0; z-index: 0;
      background: url("{safe_bg}") center/cover no-repeat;
      filter: contrast(1.08) saturate(0.82);
      opacity: 0.24;
    }}
    .custom-bg::after {{
      content: ""; position: absolute; inset: 0;
      background: linear-gradient(135deg, {bg}, transparent 60%);
    }}
    ''' if safe_bg else ""
    custom_bg_div = '<div class="custom-bg"></div>' if safe_bg else ""
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
    .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: {"60px" if is_cover else "40px"}; position: relative; z-index: 1; }}
    .section-label {{ font-family: {fonts["heading"]}; font-size: 18px; letter-spacing: 0.2em; text-transform: uppercase; color: {muted}; }}
    .brand {{ font-family: {fonts["heading"]}; font-size: 20px; font-style: italic; color: {accent}; }}
    .stage {{ position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; {stage_align}}}
    .watermark {{ position: absolute; top: {"40px" if is_cover else "0"}; right: 0; font-family: {fonts["heading"]}; font-size: {"160px" if is_cover else "120px"}; color: {watermark}; line-height: 0.8; pointer-events: none; user-select: none; z-index: 0; }}
    .title {{ font-family: {fonts["heading"]}; font-size: {"88px" if is_cover else "64px" if is_cta else "54px"}; line-height: 0.96; font-weight: 900; max-width: {"860px" if is_cover else "720px"}; letter-spacing: -0.03em; position: relative; z-index: 2; margin-bottom: {"32px" if is_cover else "24px"}; }}
    .title.cta {{ font-style: italic; font-size: 72px; color: {accent}; }}
    .divider {{ width: 80px; height: 3px; background: {accent}; margin-bottom: 24px; }}
    .body {{ font-family: {fonts["body"]}; font-size: {"30px" if is_cover else "26px"}; line-height: 1.5; color: {muted}; max-width: {"740px" if is_cover else "620px"}; }}
    .supporting {{ display: {"grid" if supporting_html else "none"}; grid-template-columns: repeat({min(len(spec.supporting_cards[:3]), 2)}, 1fr); gap: 14px; margin-top: 28px; max-width: 700px; }}
    .mag-card {{ padding: 18px; border: 1px solid {line}; background: {tag_bg}; }}
    .mag-card span {{ font-family: {fonts["heading"]}; font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: {accent}; display: block; margin-bottom: 6px; }}
    .mag-card strong {{ font-family: {fonts["body"]}; font-size: 20px; font-weight: 500; color: {text_color}; display: block; }}
    .footer {{ position: absolute; left: 72px; right: 72px; bottom: 56px; display: flex; justify-content: space-between; font-family: {fonts["body"]}; font-size: 18px; color: {muted}; z-index: 2; }}
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
    custom_bg_css = f'''
    .custom-bg {{
      position: absolute; inset: 0; z-index: 0;
      background: url("{safe_bg}") center/cover no-repeat;
      opacity: 0.12; filter: grayscale(1) contrast(1.4);
    }}
    ''' if safe_bg else ""
    custom_bg_div = '<div class="custom-bg"></div>' if safe_bg else ""
    google_fonts = _google_fonts_link("terminal")

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <link href="{google_fonts}" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: #0a0e0a; color: {accent}; font-family: {fonts["heading"]}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; padding: 48px; display: flex; flex-direction: column; }}
    {custom_bg_css}
    .header-bar {{ font-size: 22px; color: {dim_accent}; margin-bottom: 36px; padding: 12px 20px; border: 1px solid {dim_accent}; background: rgba(0,0,0,0.4); position: relative; z-index: 1; }}
    .header-bar::before {{ content: "{"> " if is_warm else "$ "}"; color: {accent}; }}
    .stage {{ flex: 1; padding: {"80px 28px" if is_cover else "40px 28px"}; position: relative; z-index: 1; {stage_align}}}
    .ascii-box {{ border: 1px solid {dim_accent}; padding: {"36px" if is_cover else "28px"}; margin-bottom: 24px; background: rgba(0,0,0,0.3); position: relative; }}
    .ascii-box::before {{ content: "┌─── " attr(data-label) " ───"; position: absolute; top: -14px; left: 20px; background: #0a0e0a; padding: 0 10px; font-size: 16px; color: {dim_accent}; }}
    .ascii-box::after {{ content: ""; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: {dim_accent}; }}
    .title {{ font-size: {"46px" if is_cover else "34px"}; font-weight: 800; line-height: 1.1; color: {accent}; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .body {{ font-size: 24px; line-height: 1.5; color: {"#d4d4d4" if is_cta else "#b8c8b8"}; }}
    .body.cta-text {{ color: {accent}; font-weight: 700; font-size: 28px; }}
    .progress-line {{ font-size: 20px; color: {dim_accent}; margin-top: {"auto" if not is_cover else "48px"}; font-family: {fonts["heading"]}; }}
    .progress-bar {{ display: flex; gap: 4px; margin-top: 8px; }}
    .progress-fill {{ flex: none; color: {accent}; font-size: 22px; letter-spacing: 2px; }}
    .progress-empty {{ flex: none; color: {dim_accent}; font-size: 22px; letter-spacing: 2px; }}
    .supporting {{ margin-top: 20px; padding: 14px 18px; border-left: 2px solid {dim_accent}; font-size: 20px; color: #889988; }}
    .footer {{ position: absolute; left: 48px; right: 48px; bottom: 40px; display: flex; justify-content: space-between; font-size: 18px; color: {dim_accent}; z-index: 2; }}
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
    custom_bg_div = f'''
    <div class="custom-bg" style="background: url("{safe_bg}") center/cover no-repeat; filter: grayscale(0.6) contrast(1.2); opacity: 0.18;"></div>
    ''' if safe_bg else ""
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
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: {text_color}; color: {block_color}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; display: flex; flex-direction: column; }}
    .block {{ position: absolute; {"top: 0; left: 0; right: 0; height: 58%;" if not is_cta else "top: 0; left: 0; right: 0; bottom: 0;"} background: {block_color}; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
    .block-text {{ font-family: {fonts["heading"]}; font-size: {"120px" if is_cover else "96px" if not is_cta else "80px"}; font-weight: 900; color: {text_color}; line-height: 0.92; text-align: center; max-width: 880px; padding: 40px; letter-spacing: -0.04em; word-break: break-word; }}
    .block-text.small {{ font-size: 60px; }}
    .footer-zone {{ position: absolute; {"top: 58%;" if not is_cta else "top: auto;"} bottom: 0; left: 0; right: 0; height: {"42%" if not is_cta else "auto"}; display: flex; flex-direction: column; justify-content: center; padding: {"60px 80px" if not is_cta else "48px 80px"}; }}
    .body-text {{ font-family: {fonts["body"]}; font-size: 32px; line-height: 1.4; color: {block_color}; max-width: 760px; }}
    .meta {{ position: absolute; left: 72px; right: 72px; bottom: 48px; display: flex; justify-content: space-between; font-family: {fonts["body"]}; font-size: 18px; color: {block_color}; opacity: 0.6; z-index: 2; }}
    .badge {{ font-family: {fonts["heading"]}; font-size: 18px; letter-spacing: 0.2em; text-transform: uppercase; color: {text_color if not is_cta else block_color}; margin-bottom: {"24px" if is_cta else "0"}; }}
    .accent-line {{ width: 60px; height: 4px; background: {block_color}; margin-bottom: 16px; }}
    .progress-dot {{ position: absolute; right: 72px; bottom: 80px; display: flex; gap: 10px; z-index: 2; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; background: {block_color}; opacity: 0.2; }}
    .dot.active {{ width: 14px; height: 14px; opacity: 1; background: {block_color}; }}
  </style>
</head>
<body>
  <div class="canvas">
    {custom_bg_div}
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
) -> str:
    fonts = LAYOUT_STYLE_FONTS["carddeck"]
    title = html.escape(spec.title)
    body = html.escape(spec.body).replace("\n", "<br>")
    logo = html.escape(logo_text)
    is_cover = spec.slide_index == 1
    is_cta = spec.slide_index == spec.total_slides
    card_align = "justify-content: center; align-items: center; text-align: center;" if spec.text_position == "center" and not is_cover else ""

    accent = "#6366f1"
    bg = "#0f0f1a"
    card_bg = "rgba(255,255,255,0.04)"
    text_color = "#f1f5f9"
    muted = "#94a3b8"
    border = "rgba(255,255,255,0.08)"

    safe_bg = _safe_data_image_url(custom_background_data_url)
    custom_bg_div = f'''
    <div class="custom-bg" style="position:absolute; inset:0; z-index:0; background:url("{safe_bg}") center/cover no-repeat; filter:contrast(1.06) saturate(0.88); opacity:0.18;"></div>
    <div class="custom-bg-overlay" style="position:absolute; inset:0; z-index:0; background:linear-gradient(180deg, rgba(15,15,26,0.6), rgba(15,15,26,0.9));"></div>
    ''' if safe_bg else ""
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
    body {{ width: 1080px; height: 1350px; overflow: hidden; background: {bg}; color: {text_color}; font-family: {fonts["body"]}; }}
    .canvas {{ position: relative; width: 1080px; height: 1350px; padding: 48px; display: flex; flex-direction: column; }}
    {custom_bg_div}
    .card {{ position: relative; z-index: 1; flex: 1; margin: 0; border-radius: 32px; background: {card_bg}; border: 1px solid {border}; backdrop-filter: blur(16px); padding: {"52px 48px" if is_cover else "44px 44px"}; display: flex; flex-direction: column; {card_align}}}
    .card.cover {{ justify-content: center; align-items: center; text-align: center; }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
    .badge {{ font-size: 14px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: {accent}; padding: 6px 14px; border-radius: 999px; background: rgba(99,102,241,0.10); border: 1px solid rgba(99,102,241,0.15); }}
    .counter {{ font-size: 16px; color: {muted}; font-weight: 500; }}
    .title {{ font-family: {fonts["body"]}; font-size: {"64px" if is_cover else "44px" if is_cta else "38px"}; font-weight: 800; line-height: 1.08; margin-bottom: {"24px" if is_cover else "16px"}; letter-spacing: -0.03em; }}
    .body {{ font-size: {"26px" if is_cover else "24px"}; line-height: 1.5; color: {muted}; max-width: {"640px" if is_cover else "580px"}; }}
    .body.cta {{ font-size: 28px; color: {accent}; font-weight: 600; }}
    .supporting {{ display: {"flex" if supporting_html else "none"}; flex-wrap: wrap; gap: 12px; margin-top: auto; padding-top: 24px; }}
    .chip {{ display: flex; flex-direction: column; gap: 4px; padding: 14px 18px; border-radius: 16px; background: rgba(255,255,255,0.03); border: 1px solid {border}; min-width: 180px; }}
    .chip span {{ font-size: 13px; letter-spacing: 0.1em; text-transform: uppercase; color: {accent}; }}
    .chip strong {{ font-size: 18px; font-weight: 600; color: {text_color}; }}
    .progress-dots {{ display: flex; gap: 8px; justify-content: center; margin-top: 24px; }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {border}; transition: all 0.2s; }}
    .dot.active {{ width: 28px; border-radius: 999px; background: {accent}; }}
    .footer {{ position: absolute; left: 72px; right: 72px; bottom: 48px; display: flex; justify-content: space-between; font-size: 16px; color: {muted}; z-index: 2; }}
  </style>
</head>
<body>
  <div class="canvas">
    {custom_bg_div}
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
) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not installed") from exc

    html_content = build_slide_html(
        spec,
        logo_text=logo_text,
        custom_background_data_url=custom_background_data_url,
    )
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


def browser_binaries_hint() -> str:
    return (
        "⚠️ Для рендера через Chromium нужно установить Playwright: "
        "`python -m playwright install chromium`"
    )
