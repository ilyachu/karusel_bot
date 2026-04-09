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

    chips = "".join(
        f'<span class="chip">{html.escape(word)}</span>'
        for word in spec.highlight_words[:2]
        if word
    )
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
      border: 1px solid rgba(255,255,255,0.09);
      box-shadow: 0 18px 80px rgba(0,0,0,0.22);
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
      border-radius: 999px;
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
      border-radius: 999px;
      background: {tokens["accent"]};
      position: relative;
      z-index: 1;
    }}
    .chips {{
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      position: relative;
      z-index: 1;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      min-height: 40px;
      padding: 0 16px;
      border-radius: 999px;
      background: {tokens["chip"]};
      color: {tokens["accent"]};
      font-size: 18px;
      font-weight: 700;
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
      border-radius: 24px;
      background: {(_support_card_bg(tokens, spec.theme))};
      border: 1px solid rgba(255,255,255,0.14);
      box-shadow: 0 12px 32px rgba(0,0,0,0.08);
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
    .cta {{
      display: {("inline-flex" if spec.variant == "closing" else "none")};
      align-items: center;
      width: fit-content;
      padding: 16px 24px;
      border-radius: 20px;
      background: rgba(255,255,255,0.07);
      color: {tokens["text"]};
      font-size: 22px;
      font-weight: 700;
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
      <div class="chips">{chips}</div>
      <div class="cta">Save this carousel</div>
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
        return "none"
    if len(spec.supporting_cards) >= 2:
        return "rotate(-4deg)"
    return "none"
