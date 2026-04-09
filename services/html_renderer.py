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
        "bg": "linear-gradient(180deg, #f5f1e8 0%, #ebe4d7 100%)",
        "panel": "rgba(255, 251, 245, 0.82)",
        "text": "#1f2933",
        "muted": "#52606d",
        "accent": "#2f6f62",
        "chip": "rgba(47,111,98,0.08)",
        "line": "rgba(31,41,51,0.08)",
        "display_font": "Georgia, 'Times New Roman', serif",
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "founder_brief": {
        "bg": "radial-gradient(circle at top left, rgba(99,102,241,0.18), transparent 26%), linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
        "panel": "rgba(255,255,255,0.78)",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#4f46e5",
        "chip": "rgba(79,70,229,0.08)",
        "line": "rgba(79,70,229,0.08)",
        "display_font": "'Arial Black', 'Segoe UI', sans-serif",
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "growth_black": {
        "bg": "radial-gradient(circle at top right, rgba(163,230,53,0.26), transparent 24%), linear-gradient(180deg, #030712 0%, #111827 100%)",
        "panel": "rgba(3,7,18,0.84)",
        "text": "#f9fafb",
        "muted": "#d1d5db",
        "accent": "#a3e635",
        "chip": "rgba(163,230,53,0.10)",
        "line": "rgba(255,255,255,0.06)",
        "display_font": "'Arial Black', 'Trebuchet MS', sans-serif",
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    "research_mono": {
        "bg": "linear-gradient(180deg, #f7f7f5 0%, #ecece8 100%)",
        "panel": "rgba(255,255,255,0.80)",
        "text": "#111827",
        "muted": "#374151",
        "accent": "#111827",
        "chip": "rgba(17,24,39,0.06)",
        "line": "rgba(17,24,39,0.08)",
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

    cards = _secondary_cards(spec, tokens)

    title_size = _title_size(spec.variant)
    body_size = _body_size(spec.variant)
    title_max_width = "620px" if spec.theme == "memory_archive" and spec.variant not in {"cover", "closing"} else "860px"
    body_max_width = "600px" if spec.theme == "memory_archive" and spec.variant not in {"cover", "closing"} else "840px"
    supporting_style = _supporting_cards_style(spec)

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
      border-radius: 42px;
      background: {tokens["panel"]};
      border: 1px solid {_frame_border(tokens, spec.theme)};
      box-shadow: {_frame_shadow(spec.theme)};
      padding: {_frame_padding(spec.variant)};
      display: flex;
      flex-direction: column;
      justify-content: {_frame_justify(spec.variant)};
      gap: 26px;
      backdrop-filter: blur(22px);
      overflow: hidden;
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
    }}
    .badge, .progress {{
      display: inline-flex;
      align-items: center;
      min-height: 46px;
      padding: 0 18px;
      border-radius: {("12px" if spec.theme == "research_mono" else "999px")};
      background: {tokens["chip"]};
      font-size: 20px;
      line-height: 1;
    }}
    .badge {{
      color: {tokens["accent"]};
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 700;
    }}
    .progress {{
      color: {tokens["text"]};
      opacity: 0.9;
    }}
    .title {{
      font-size: {title_size}px;
      line-height: 1.02;
      font-weight: 900;
      letter-spacing: -0.03em;
      max-width: {title_max_width};
      white-space: pre-wrap;
      font-family: {display_font};
      position: relative;
      z-index: 1;
    }}
    .body {{
      font-size: {body_size}px;
      line-height: 1.38;
      color: {tokens["muted"]};
      max-width: {body_max_width};
      white-space: normal;
      font-family: {body_font};
      position: relative;
      z-index: 1;
    }}
    .divider {{
      width: 180px;
      height: 8px;
      border-radius: {("12px" if spec.theme == "research_mono" else "999px")};
      background: {tokens["accent"]};
      position: relative;
      z-index: 1;
    }}
    .supporting-cards {{
      position: absolute;
      {supporting_style}
      display: flex;
      flex-direction: column;
      gap: 14px;
      width: 270px;
      z-index: 0;
      transform: {(_supporting_transform(spec))};
      opacity: {("1" if cards else "0")};
    }}
    .support-card {{
      padding: 16px 18px;
      border-radius: {("12px" if spec.theme == "research_mono" else "24px")};
      background: {(_support_card_bg(tokens, spec.theme))};
      border: 1px solid {_support_border(spec.theme)};
      box-shadow: {_support_shadow(spec.theme)};
      color: {tokens["text"]};
      font-size: 22px;
      line-height: 1.25;
      font-family: {body_font};
    }}
    .support-card strong {{
      display: block;
      margin-bottom: 8px;
      color: {tokens["accent"]};
      font-size: 16px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .cta-note {{
      display: {("block" if spec.variant == "closing" else "none")};
      color: {tokens["accent"]};
      font-size: 20px;
      line-height: 1.4;
      font-weight: 700;
      position: relative;
      z-index: 1;
      letter-spacing: 0.01em;
    }}
    .footer {{
      position: absolute;
      left: 72px;
      right: 72px;
      bottom: 62px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: {tokens["muted"]};
      font-size: 24px;
      font-family: {body_font};
    }}
    .footer .swipe {{
      opacity: {("0.92" if spec.variant == "cover" else "0.0")};
    }}
  </style>
</head>
<body>
  <div class="canvas">
    <div class="frame">
      <div class="topbar">
        <div class="badge">{badge}</div>
        <div class="progress">{progress}</div>
      </div>
      <div class="title">{title}</div>
      <div class="divider"></div>
      <div class="body">{body}</div>
      <div class="cta-note">Сохрани пост и вернись к нему позже.</div>
      <div class="supporting-cards">{cards}</div>
    </div>
    <div class="footer">
      <div class="swipe">Swipe →</div>
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
        png = page.screenshot(type="png")
        browser.close()
    return png


def browser_binaries_hint() -> str:
    return (
        "Playwright Chromium binaries are required. Run `python -m playwright install chromium` "
        "locally or during deployment."
    )


def _frame_inset(variant: str) -> str:
    if variant == "cover":
        return "78px 54px 150px 54px"
    if variant == "closing":
        return "300px 62px 160px 62px"
    if variant == "stat_focus":
        return "220px 54px 170px 54px"
    return "138px 54px 150px 54px"


def _frame_padding(variant: str) -> str:
    if variant == "cover":
        return "34px 40px 36px"
    return "34px 38px 34px"


def _frame_justify(variant: str) -> str:
    if variant in {"cover", "closing"}:
        return "center"
    return "flex-start"


def _title_size(variant: str) -> int:
    return {
        "cover": 82,
        "closing": 68,
        "spotlight": 76,
        "stat_focus": 80,
        "checklist": 60,
    }.get(variant, 64)


def _body_size(variant: str) -> int:
    return {
        "cover": 30,
        "closing": 28,
        "spotlight": 28,
        "stat_focus": 28,
        "checklist": 26,
    }.get(variant, 28)


def _secondary_cards(spec: LayoutSpec, tokens: dict) -> str:
    return "".join(
        f'<div class="support-card"><strong>{html.escape(card["label"])}</strong>{html.escape(card["text"])}</div>'
        for card in spec.supporting_cards[:3]
    )


def _background_lines(tokens: dict) -> str:
    line = tokens.get("line", "rgba(0,0,0,0.05)")
    return f"linear-gradient({line} 1px, transparent 1px), linear-gradient(90deg, {line} 1px, transparent 1px)"


def _frame_texture(tokens: dict) -> str:
    return f"linear-gradient(180deg, rgba(255,255,255,0.28), transparent 22%), radial-gradient(circle at top left, {tokens['chip']}, transparent 40%)"


def _support_card_bg(tokens: dict, theme: str) -> str:
    if theme == "memory_archive":
        return "rgba(255, 248, 238, 0.94)"
    if theme == "research_mono":
        return "rgba(255,255,255,0.92)"
    if theme == "growth_black":
        return "rgba(17,24,39,0.94)"
    return "rgba(255,255,255,0.06)"


def _supporting_cards_style(spec: LayoutSpec) -> str:
    if spec.theme != "memory_archive":
        return "right: 34px; bottom: 42px;"
    if spec.variant == "cover":
        return "right: 34px; bottom: 42px;"
    if spec.variant == "closing":
        return "right: 34px; bottom: 42px;"
    return "right: 34px; top: 300px;"


def _supporting_transform(spec: LayoutSpec) -> str:
    if spec.theme != "memory_archive":
        if spec.theme == "founder_brief":
            return "rotate(-2deg)"
        if spec.theme == "growth_black":
            return "rotate(-1deg)"
        return "none"
    if len(spec.supporting_cards) >= 2:
        return "rotate(-4deg)"
    return "none"


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
