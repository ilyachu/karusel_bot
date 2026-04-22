import html
import logging

from services.layout_engine import LayoutSpec


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


def build_slide_html(spec: LayoutSpec, logo_text: str = "chu ai") -> str:
    tokens = THEME_TOKENS.get(spec.theme, THEME_TOKENS["business_dark"])
    font_family = FONT_MAP.get(spec.font_style, FONT_MAP["standard"])
    display_font = tokens.get("display_font", font_family)
    body_font = tokens.get("body_font", font_family)

    title = html.escape(spec.title)
    body = html.escape(spec.body).replace("\n", "<br>")
    badge = html.escape(spec.badge_text)
    logo = html.escape(logo_text)
    progress = f"{spec.slide_index}/{spec.total_slides}" if spec.show_progress else ""
    variant_class = spec.variant.replace("_", "-")

    title_size = _title_size(spec.variant)
    body_size = _body_size(spec.variant)
    title_max_width = _title_max_width(spec.variant)
    body_max_width = _body_max_width(spec.variant)
    divider_display = "none" if spec.variant in {"quote", "framework_grid", "closing"} else "block"
    supporting_cards_html = "".join(
        f'<div class="support-card"><span>{html.escape(card.get("title", ""))}</span></div>'
        for card in spec.supporting_cards
    )
    quote_mark = '<div class="quote-mark">“</div>' if spec.variant == "quote" else ""
    hero_deco = '<div class="hero-orb"></div>' if spec.variant in {"cover", "closing"} else ""
    cta_box = (
        '<div class="cta-box"><span>Сохрани карусель</span><strong>и подпишись на новые разборы</strong></div>'
        if spec.variant == "closing"
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <style>
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      width: 1080px;
      height: 1350px;
      overflow: hidden;
      background: {tokens["bg"]};
      color: {tokens["text"]};
      font-family: {font_family};
    }}
    .canvas {{
      position: relative;
      width: 1080px;
      height: 1350px;
      padding: 48px;
      background-image: {(_background_lines(tokens) if spec.theme == "memory_archive" else "none")};
    }}
    .frame {{
      position: absolute;
      inset: {_frame_inset(spec.variant)};
      border-radius: 46px;
      background: {tokens["panel"]};
      border: 1px solid {_frame_border(tokens, spec.theme)};
      box-shadow: {_frame_shadow(spec.theme)};
      padding: {_frame_padding(spec.variant)};
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 0;
      backdrop-filter: blur(22px);
      overflow: hidden;
    }}
    .frame.variant-cover,
    .frame.variant-closing {{
      padding-top: 42px;
    }}
    .frame::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: {(_frame_texture(tokens) if spec.theme == "memory_archive" else "transparent")};
      pointer-events: none;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: relative;
      z-index: 1;
      min-height: 46px;
      margin-bottom: 24px;
    }}
    .badge, .progress {{
      display: inline-flex;
      align-items: center;
      min-height: 46px;
      padding: 0 16px;
      border-radius: {("12px" if spec.theme == "research_mono" else "999px")};
      background: {tokens["chip"]};
      font-size: 18px;
      line-height: 1;
      border: 1px solid {_support_border(spec.theme)};
    }}
    .badge {{
      color: {tokens["accent"]};
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-weight: 700;
      opacity: {("1" if badge else "0")};
      visibility: {("visible" if badge else "hidden")};
    }}
    .progress {{
      color: {tokens["text"]};
      opacity: 0.9;
    }}
    .title {{
      font-size: {title_size}px;
      line-height: 0.98;
      font-weight: 900;
      letter-spacing: -0.04em;
      max-width: {title_max_width};
      white-space: pre-wrap;
      font-family: {display_font};
      position: relative;
      z-index: 1;
      margin: 0 0 18px 0;
    }}
    .body {{
      font-size: {body_size}px;
      line-height: 1.32;
      color: {tokens["muted"]};
      max-width: {body_max_width};
      white-space: normal;
      font-family: {body_font};
      position: relative;
      z-index: 1;
      margin: 16px 0 0 0;
    }}
    .divider {{
      width: 180px;
      height: 8px;
      border-radius: {("12px" if spec.theme == "research_mono" else "999px")};
      background: {tokens["accent"]};
      position: relative;
      z-index: 1;
      display: {divider_display};
    }}
    .supporting-cards {{
      display: {("grid" if supporting_cards_html else "none")};
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 24px;
      max-width: 760px;
      position: relative;
      z-index: 1;
    }}
    .support-card {{
      padding: 16px 18px;
      border-radius: 22px;
      background: rgba(255,255,255,0.06);
      border: 1px solid {_support_border(spec.theme)};
      box-shadow: {_support_shadow(spec.theme)};
      color: {tokens["text"]};
      min-height: 92px;
      display: flex;
      align-items: flex-start;
    }}
    .support-card span {{
      font-size: 20px;
      line-height: 1.3;
    }}
    .cta-note {{
      display: {("block" if spec.variant == "closing" else "none")};
      color: {tokens["accent"]};
      font-size: 18px;
      line-height: 1.4;
      font-weight: 700;
      position: relative;
      z-index: 1;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-top: 18px;
    }}
    .cta-box {{
      display: none;
      flex-direction: column;
      gap: 8px;
      margin-top: 26px;
      padding: 20px 22px;
      border-radius: 26px;
      background: linear-gradient(135deg, {tokens["chip"]}, rgba(255,255,255,0.04));
      border: 1px solid {_support_border(spec.theme)};
      max-width: 520px;
      position: relative;
      z-index: 1;
    }}
    .cta-box span {{
      font-size: 16px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: {tokens["accent"]};
    }}
    .cta-box strong {{
      font-size: 30px;
      line-height: 1.12;
      color: {tokens["text"]};
    }}
    .quote-mark {{
      display: {("block" if spec.variant == "quote" else "none")};
      font-size: 120px;
      line-height: 0.8;
      color: {tokens["accent"]};
      margin-bottom: 8px;
      position: relative;
      z-index: 1;
    }}
    .hero-orb {{
      position: absolute;
      right: -40px;
      top: 120px;
      width: 260px;
      height: 260px;
      border-radius: 999px;
      background: radial-gradient(circle, {tokens["chip"]} 0%, transparent 70%);
      opacity: 0.9;
      z-index: 0;
      display: {("block" if spec.variant in {"cover", "closing"} else "none")};
    }}
    .content {{
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      min-height: 780px;
      max-width: {title_max_width};
      position: relative;
    }}
    .footer {{
      position: absolute;
      left: 72px;
      right: 72px;
      bottom: 56px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: {tokens["muted"]};
      font-size: 22px;
      font-family: {body_font};
    }}
    .footer .note {{
      opacity: {("0.88" if spec.variant in {"cover", "closing"} else "0.28")};
    }}
    .frame.variant-cover .title {{
      margin-top: 20px;
      max-width: 760px;
    }}
    .frame.variant-cover .body {{
      max-width: 620px;
      font-size: 30px;
    }}
    .frame.variant-closing .title {{
      max-width: 680px;
      font-size: 82px;
    }}
    .frame.variant-closing .body {{
      max-width: 620px;
      font-size: 26px;
    }}
    .frame.variant-quote .title {{
      font-size: 22px;
      line-height: 1.2;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: {tokens["accent"]};
      max-width: 520px;
      margin-bottom: 8px;
    }}
    .frame.variant-quote .body {{
      font-size: 58px;
      line-height: 1.02;
      max-width: 760px;
      color: {tokens["text"]};
      font-family: {display_font};
      letter-spacing: -0.04em;
      margin-top: 0;
    }}
    .frame.variant-framework-grid .title {{
      max-width: 720px;
      font-size: 64px;
    }}
    .frame.variant-framework-grid .body {{
      max-width: 700px;
      font-size: 24px;
    }}
  </style>
</head>
<body>
  <div class="canvas">
    <div class="frame variant-{variant_class}">
      {hero_deco}
      <div class="topbar">
        <div class="badge">{badge}</div>
        <div class="progress">{progress}</div>
      </div>
      <div class="content">
        {quote_mark}
        <div class="title">{title}</div>
        <div class="divider"></div>
        <div class="body">{body}</div>
        <div class="supporting-cards">{supporting_cards_html}</div>
        {cta_box}
        <div class="cta-note">Сохрани пост и вернись к нему позже.</div>
      </div>
    </div>
    <div class="footer">
      <div class="note">Листай дальше</div>
      <div>{logo}</div>
    </div>
  </div>
</body>
</html>
"""


def render_layout_spec_html(spec: LayoutSpec, logo_text: str = "chu ai") -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not installed") from exc

    html_content = build_slide_html(spec, logo_text=logo_text)
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
        "Playwright Chromium binaries are required. Run `python -m playwright install chromium` "
        "locally or during deployment."
    )


def _frame_inset(variant: str) -> str:
    # Keep the card geometry stable across the whole carousel.
    return "104px 54px 150px 54px"


def _frame_padding(variant: str) -> str:
    return "34px 38px 34px"


def _title_size(variant: str) -> int:
    return {
        "cover": 92,
        "closing": 82,
        "quote": 24,
        "framework_grid": 64,
        "spotlight": 70,
        "stat_focus": 70,
        "checklist": 60,
    }.get(variant, 70)


def _body_size(variant: str) -> int:
    return {
        "cover": 30,
        "closing": 26,
        "quote": 58,
        "framework_grid": 24,
        "spotlight": 28,
        "stat_focus": 28,
        "checklist": 26,
    }.get(variant, 28)


def _title_max_width(variant: str) -> str:
    return {
        "cover": "760px",
        "closing": "700px",
        "quote": "520px",
        "framework_grid": "720px",
    }.get(variant, "660px")


def _body_max_width(variant: str) -> str:
    return {
        "cover": "620px",
        "closing": "620px",
        "quote": "760px",
        "framework_grid": "700px",
    }.get(variant, "640px")


def _background_lines(tokens: dict) -> str:
    line = tokens.get("line", "rgba(0,0,0,0.05)")
    return f"linear-gradient({line} 1px, transparent 1px), linear-gradient(90deg, {line} 1px, transparent 1px)"


def _frame_texture(tokens: dict) -> str:
    return f"linear-gradient(180deg, rgba(255,255,255,0.28), transparent 22%), radial-gradient(circle at top left, {tokens['chip']}, transparent 40%)"


def _frame_border(tokens: dict, theme: str) -> str:
    if theme == "research_mono":
        return "rgba(17,24,39,0.10)"
    if theme == "growth_black":
        return "rgba(163,230,53,0.16)"
    if theme == "founder_brief":
        return "rgba(79,70,229,0.10)"
    return "rgba(255,255,255,0.09)"


def _frame_shadow(theme: str) -> str:
    if theme == "founder_brief":
        return "0 18px 80px rgba(79,70,229,0.10)"
    if theme == "growth_black":
        return "0 18px 80px rgba(0,0,0,0.34)"
    if theme == "research_mono":
        return "0 14px 48px rgba(17,24,39,0.10)"
    return "0 18px 80px rgba(0,0,0,0.22)"


def _support_border(theme: str) -> str:
    if theme == "growth_black":
        return "rgba(163,230,53,0.18)"
    if theme == "research_mono":
        return "rgba(17,24,39,0.10)"
    if theme == "founder_brief":
        return "rgba(79,70,229,0.12)"
    return "rgba(255,255,255,0.14)"


def _support_shadow(theme: str) -> str:
    if theme == "growth_black":
        return "0 12px 32px rgba(0,0,0,0.24)"
    if theme == "research_mono":
        return "0 8px 22px rgba(17,24,39,0.08)"
    if theme == "founder_brief":
        return "0 10px 28px rgba(79,70,229,0.08)"
    return "0 12px 32px rgba(0,0,0,0.08)"
