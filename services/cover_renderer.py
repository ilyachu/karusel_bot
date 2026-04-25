from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import html
import re


COVER_AUTHOR = "chu_il"

COVER_FORMATS = {
    "wide": {"label": "16:9", "width": 1920, "height": 1080},
    "post": {"label": "4:5", "width": 1080, "height": 1350},
    "story": {"label": "9:16", "width": 1080, "height": 1920},
}

COVER_STYLES = {
    "orange_poster": {
        "label": "Orange Poster",
        "class": "cover-orange-poster",
        "bg": "#f45124",
        "text": "#07080b",
        "muted": "#07080b",
        "pill_bg": "#05070a",
        "pill_text": "#fff3e8",
        "line": "#05070a",
    },
    "acid_poster": {
        "label": "Acid Poster",
        "class": "cover-acid-poster",
        "bg": "#d7ff37",
        "text": "#071006",
        "muted": "#071006",
        "pill_bg": "#071006",
        "pill_text": "#f8ffe1",
        "line": "#071006",
    },
    "retro_polaroid": {
        "label": "Retro Film Burn",
        "class": "cover-retro-polaroid",
        "bg": "#161b1c",
        "text": "#fff2d3",
        "muted": "#ffd17a",
        "pill_bg": "#fff2d3",
        "pill_text": "#15191a",
        "line": "#fff2d3",
    },
    "blue_type": {
        "label": "Blue Type",
        "class": "cover-blue-type",
        "bg": "#f3f0ec",
        "text": "#1048ff",
        "muted": "#1048ff",
        "pill_bg": "#1048ff",
        "pill_text": "#f8f5ef",
        "line": "#1048ff",
    },
    "grid_steps": {
        "label": "Grid Steps",
        "class": "cover-grid-steps",
        "bg": "#f6f5f0",
        "text": "#141414",
        "muted": "#141414",
        "pill_bg": "#1551ff",
        "pill_text": "#ffffff",
        "line": "#1551ff",
    },
    "blur_field": {
        "label": "Blur Field",
        "class": "cover-blur-field",
        "bg": "#ee321f",
        "text": "#161616",
        "muted": "#161616",
        "pill_bg": "#161616",
        "pill_text": "#fff7f0",
        "line": "#161616",
    },
}


@dataclass(frozen=True)
class CoverPlan:
    headline: str
    subtitle: str
    eyebrow_left: str
    eyebrow_right: str
    footer_left: str
    symbol: str
    style: str
    format_key: str
    footer_right: str = COVER_AUTHOR
    background_data_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_cover_plan(raw_plan: dict | None, base_text: str, style: str, format_key: str) -> CoverPlan:
    raw_plan = raw_plan if isinstance(raw_plan, dict) else {}
    normalized_style = style if style in COVER_STYLES else "orange_poster"
    normalized_format = format_key if format_key in COVER_FORMATS else "post"
    fallback_headline, fallback_subtitle = _fallback_headline_parts(base_text)
    headline = _clean_text(str(raw_plan.get("headline") or fallback_headline), 56)
    subtitle = _clean_text(str(raw_plan.get("subtitle") or fallback_subtitle), 96)
    eyebrow_left = _clean_text(str(raw_plan.get("eyebrow_left") or "РАЗБОР · № 01"), 24)
    eyebrow_right = _clean_text(str(raw_plan.get("eyebrow_right") or "POSTER · TODAY"), 36)
    footer_left = _clean_text(str(raw_plan.get("footer_left") or "ДЛЯ ЧИТАТЕЛЕЙ"), 42)
    symbol = str(raw_plan.get("symbol") or "arrow").strip().lower()
    if symbol not in {"arrow", "asterisk", "slash", "dot"}:
        symbol = "arrow"
    return CoverPlan(
        headline=headline or "Главная мысль",
        subtitle=subtitle,
        eyebrow_left=eyebrow_left,
        eyebrow_right=eyebrow_right,
        footer_left=footer_left,
        symbol=symbol,
        style=normalized_style,
        format_key=normalized_format,
        footer_right=COVER_AUTHOR,
        background_data_url=_safe_background_data_url(str(raw_plan.get("background_data_url") or "")),
    )


def build_cover_html(plan: CoverPlan) -> str:
    style_tokens = COVER_STYLES.get(plan.style, COVER_STYLES["orange_poster"])
    fmt = COVER_FORMATS.get(plan.format_key, COVER_FORMATS["post"])
    width = fmt["width"]
    height = fmt["height"]
    symbol = _symbol_html(plan.symbol)
    headline = _headline_html(plan.headline, plan.format_key, plan.style)
    subtitle = html.escape(plan.subtitle)
    eyebrow_left = html.escape(plan.eyebrow_left)
    eyebrow_right = html.escape(plan.eyebrow_right)
    footer_left = html.escape(plan.footer_left)
    footer_right = html.escape(COVER_AUTHOR)
    style_class = style_tokens["class"]
    is_retro = plan.style == "retro_polaroid"
    custom_background = _safe_background_data_url(plan.background_data_url)
    background_markup = (
        f'<div class="custom-background" style="background-image: url(&quot;{custom_background}&quot;)"></div>'
        if custom_background
        else ""
    )

    if is_retro:
        body_markup = _retro_markup(
            headline=headline,
            subtitle=subtitle,
            eyebrow_left=eyebrow_left,
            eyebrow_right=eyebrow_right,
            footer_left=footer_left,
            footer_right=footer_right,
            symbol=symbol,
        )
    else:
        body_markup = _poster_markup(
            headline=headline,
            subtitle=subtitle,
            eyebrow_left=eyebrow_left,
            eyebrow_right=eyebrow_right,
            footer_left=footer_left,
            footer_right=footer_right,
            symbol=symbol,
        )

    headline_size = _headline_size(plan.format_key, is_retro, plan.headline)
    poster_top = "48px" if plan.format_key != "story" else "72px"
    poster_bottom = "58px" if plan.format_key != "story" else "84px"
    content_top = {
        "wide": "210px",
        "post": "302px",
        "story": "500px",
    }.get(plan.format_key, "302px")
    line_bottom = "118px" if plan.format_key != "story" else "158px"

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
      width: {width}px;
      height: {height}px;
      overflow: hidden;
      background:
        radial-gradient(circle at 75% 20%, rgba(255,255,255,0.08), transparent 18%),
        {style_tokens["bg"]};
      color: {style_tokens["text"]};
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .cover-canvas {{
      position: relative;
      width: {width}px;
      height: {height}px;
      background: {style_tokens["bg"]};
      overflow: hidden;
    }}
    .custom-background {{
      position: absolute;
      inset: 0;
      background-size: cover;
      background-position: center;
      opacity: {("0.74" if is_retro else "0.58")};
      filter: {("contrast(1.08) saturate(0.92)" if is_retro else "contrast(1.05) saturate(0.9)")};
      z-index: 0;
    }}
    .custom-background::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: {("linear-gradient(90deg, rgba(10,14,16,0.42), rgba(255,140,48,0.24)), radial-gradient(circle at 14% 78%, rgba(255,220,40,0.38), transparent 28%)" if is_retro else "rgba(255,255,255,0.18)")};
    }}
    .cover-canvas::before {{
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
      background-size: 54px 54px;
      opacity: {("0.18" if plan.style == "acid_poster" else "0.08")};
      pointer-events: none;
    }}
    .cover-top {{
      position: absolute;
      left: 60px;
      right: 60px;
      top: {poster_top};
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 6;
    }}
    .cover-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 48px;
      padding: 0 18px;
      border-radius: 18px;
      background: {style_tokens["pill_bg"]};
      color: {style_tokens["pill_text"]};
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 17px;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .cover-meta {{
      color: {style_tokens["muted"]};
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 18px;
      font-weight: 900;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .cover-main {{
      position: absolute;
      left: 60px;
      right: 60px;
      top: {content_top};
      z-index: 5;
    }}
    .cover-headline {{
      margin: 0;
      max-width: {("1280px" if plan.format_key == "wide" else "900px")};
      color: {style_tokens["text"]};
      font-family: "Arial Black", "Arial", "Helvetica Neue", sans-serif;
      font-size: {headline_size}px;
      line-height: 0.91;
      font-weight: 950;
      letter-spacing: 0;
      text-transform: lowercase;
      overflow-wrap: normal;
      word-break: normal;
      hyphens: none;
    }}
    .cover-headline .headline-line {{
      display: block;
      white-space: nowrap;
    }}
    .cover-subtitle {{
      display: {("block" if subtitle else "none")};
      max-width: {("880px" if plan.format_key == "wide" else "720px")};
      margin-top: 28px;
      color: {style_tokens["muted"]};
      font-size: {("34" if plan.format_key != "wide" else "30")}px;
      line-height: 1.18;
      font-weight: 800;
      letter-spacing: 0;
    }}
    .cover-symbol {{
      display: flex;
      align-items: center;
      justify-content: center;
      position: absolute;
      right: {("80px" if plan.format_key == "wide" else "90px")};
      top: {("72px" if plan.format_key == "wide" else "126px" if plan.format_key == "post" else "188px")};
      color: {style_tokens["text"]};
      font-size: {max(78, headline_size - 30)}px;
      line-height: 0.8;
      font-family: "Arial Black", Arial, sans-serif;
      z-index: 5;
    }}
    .cover-bottom-line {{
      position: absolute;
      left: 60px;
      right: 60px;
      bottom: {line_bottom};
      height: 3px;
      background: {style_tokens["line"]};
      z-index: 6;
    }}
    .cover-footer {{
      position: absolute;
      left: 60px;
      right: 60px;
      bottom: {poster_bottom};
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: {style_tokens["muted"]};
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 18px;
      font-weight: 900;
      letter-spacing: 0;
      text-transform: uppercase;
      z-index: 6;
    }}
    .cover-acid-poster .cover-canvas::after {{
      content: "";
      position: absolute;
      right: 60px;
      top: 160px;
      width: 180px;
      height: 180px;
      background-image: radial-gradient({style_tokens["text"]} 3px, transparent 4px);
      background-size: 24px 24px;
      opacity: 0.22;
    }}
    .cover-retro-polaroid .cover-canvas {{
      background:
        radial-gradient(circle at 7% 82%, rgba(255,228,36,0.92), transparent 22%),
        radial-gradient(circle at 87% 13%, rgba(255,176,64,0.72), transparent 28%),
        linear-gradient(90deg, #1f2829 0 42%, #572b23 58%, #c06a34 100%);
    }}
    .cover-retro-polaroid .cover-canvas::before {{
      background-image:
        linear-gradient(128deg, transparent 0 38%, rgba(255,255,255,0.46) 38.4% 38.7%, transparent 39.1%),
        linear-gradient(2deg, transparent 0 58%, rgba(255,255,255,0.34) 58.2% 58.7%, transparent 59%),
        linear-gradient(84deg, transparent 0 18%, rgba(255,255,255,0.18) 18.2% 18.4%, transparent 18.8%),
        linear-gradient(90deg, rgba(0,0,0,0.34), transparent 30%, rgba(255,132,36,0.35));
      background-size: 100% 100%, 100% 100%, 31px 37px, 100% 100%;
      opacity: 0.58;
      z-index: 2;
    }}
    .cover-retro-polaroid .cover-canvas::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(176deg, transparent 0 68%, rgba(255,255,255,0.32) 68.2% 68.8%, transparent 69%),
        linear-gradient(91deg, transparent 0 44%, rgba(0,0,0,0.24) 44.5% 45.2%, transparent 46%),
        radial-gradient(circle at 12% 76%, rgba(255,213,26,0.62), transparent 24%);
      mix-blend-mode: screen;
      opacity: 0.52;
      z-index: 1;
    }}
    .film-frame {{
      position: absolute;
      left: 60px;
      right: 60px;
      top: {("190px" if plan.format_key == "wide" else "260px" if plan.format_key == "post" else "430px")};
      bottom: {("166px" if plan.format_key == "wide" else "190px" if plan.format_key == "post" else "270px")};
      border: 0;
      background: transparent;
      box-shadow: none;
      z-index: 4;
      overflow: hidden;
    }}
    .film-frame::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, rgba(0,0,0,0.16), transparent 42%, rgba(255,207,105,0.18));
      opacity: 0.9;
    }}
    .film-sprockets {{
      display: none;
    }}
    .film-sprockets.left {{
      left: 0;
    }}
    .film-sprockets.right {{
      right: 0;
    }}
    .film-content {{
      position: absolute;
      left: 118px;
      right: 118px;
      top: 96px;
      bottom: 96px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .film-label {{
      position: absolute;
      left: 118px;
      top: 42px;
      color: #fff2d3;
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-weight: 900;
      font-size: 20px;
      text-transform: uppercase;
    }}
    .film-label-right {{
      left: auto;
      right: 118px;
    }}
    .film-title {{
      color: #fff2d3;
      font-family: "Arial Black", Arial, sans-serif;
      font-size: {("82" if plan.format_key == "wide" else "78" if plan.format_key == "post" else "92")}px;
      line-height: 0.94;
      font-weight: 950;
      letter-spacing: 0;
      text-transform: lowercase;
      text-shadow: 0 10px 38px rgba(0,0,0,0.62);
    }}
    .film-title .headline-line {{
      display: block;
      white-space: nowrap;
    }}
    .film-note {{
      color: rgba(255,242,211,0.88);
      font-size: 28px;
      font-weight: 800;
      line-height: 1.12;
      margin-top: 26px;
      display: {("block" if subtitle else "none")};
    }}
    .film-code {{
      position: absolute;
      left: 118px;
      bottom: 42px;
      color: rgba(255,242,211,0.82);
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-weight: 900;
      font-size: 18px;
      text-transform: uppercase;
    }}
    .cover-blue-type .cover-main {{
      top: {("150px" if plan.format_key == "wide" else "92px" if plan.format_key == "post" else "150px")};
    }}
    .cover-blue-type .cover-headline {{
      max-width: {("1460px" if plan.format_key == "wide" else "970px")};
      font-family: Arial, "Helvetica Neue", sans-serif;
      font-size: {headline_size}px;
      line-height: 0.82;
      font-weight: 950;
      text-transform: lowercase;
    }}
    .cover-blue-type .cover-pill,
    .cover-blue-type .cover-meta,
    .cover-blue-type .cover-symbol,
    .cover-blue-type .cover-bottom-line {{
      display: none;
    }}
    .cover-grid-steps .cover-canvas::after {{
      content: "";
      position: absolute;
      left: -40px;
      bottom: -40px;
      width: {("760px" if plan.format_key == "wide" else "720px")};
      height: {("760px" if plan.format_key == "wide" else "920px")};
      background:
        linear-gradient(45deg, #1551ff 25%, transparent 25% 75%, #1551ff 75%),
        linear-gradient(45deg, #1551ff 25%, transparent 25% 75%, #1551ff 75%);
      background-size: 156px 156px;
      background-position: 0 0, 78px 78px;
      opacity: 0.96;
      z-index: 1;
    }}
    .cover-grid-steps .cover-main {{
      left: {("520px" if plan.format_key == "wide" else "180px")};
      top: {("280px" if plan.format_key == "wide" else "330px" if plan.format_key == "post" else "560px")};
    }}
    .cover-grid-steps .cover-headline {{
      font-family: Arial, "Helvetica Neue", sans-serif;
      font-size: {max(86, headline_size - 8)}px;
      line-height: 0.86;
      text-transform: none;
      filter: contrast(1.18);
    }}
    .cover-grid-steps .cover-symbol,
    .cover-grid-steps .cover-pill,
    .cover-grid-steps .cover-bottom-line {{
      display: none;
    }}
    .cover-blur-field .cover-canvas {{
      background:
        radial-gradient(circle at 20% 10%, #fff 0 12%, transparent 18%),
        radial-gradient(circle at 82% 34%, #fff 0 12%, transparent 19%),
        radial-gradient(circle at 40% 58%, #fff 0 13%, transparent 21%),
        radial-gradient(circle at 78% 88%, #fff 0 11%, transparent 18%),
        #ee321f;
      filter: contrast(1.04);
    }}
    .cover-blur-field .cover-canvas::before {{
      background: radial-gradient(rgba(255,255,255,0.12) 1px, transparent 1px);
      background-size: 5px 5px;
      opacity: 0.4;
    }}
    .cover-blur-field .cover-headline {{
      font-family: Arial, "Helvetica Neue", sans-serif;
      font-size: {max(74, headline_size - 18)}px;
      line-height: 0.94;
      font-weight: 800;
      text-transform: uppercase;
      opacity: 0.88;
      text-shadow: -18px 0 10px rgba(0,0,0,0.22);
    }}
  </style>
</head>
<body class="{style_class}">
  <div class="cover-canvas">
    {background_markup}
    {body_markup}
  </div>
</body>
</html>"""


def render_cover_html(plan: CoverPlan) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not installed") from exc

    fmt = COVER_FORMATS.get(plan.format_key, COVER_FORMATS["post"])
    width = fmt["width"]
    height = fmt["height"]
    html_content = build_cover_html(plan)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.set_content(html_content, wait_until="load")
        png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()
    return png


def _poster_markup(
    headline: str,
    subtitle: str,
    eyebrow_left: str,
    eyebrow_right: str,
    footer_left: str,
    footer_right: str,
    symbol: str,
) -> str:
    return f"""
    <div class="cover-top">
      <div class="cover-pill">{eyebrow_left}</div>
      <div class="cover-meta">{eyebrow_right}</div>
    </div>
    <main class="cover-main">
      <h1 class="cover-headline">{headline}</h1>
      <div class="cover-symbol">{symbol}</div>
      <div class="cover-subtitle">{subtitle}</div>
    </main>
    <div class="cover-bottom-line"></div>
    <footer class="cover-footer">
      <span>{footer_left}</span>
      <span>{footer_right}</span>
    </footer>
    """


def _retro_markup(
    headline: str,
    subtitle: str,
    eyebrow_left: str,
    eyebrow_right: str,
    footer_left: str,
    footer_right: str,
    symbol: str,
) -> str:
    return f"""
    <div class="cover-top">
      <div class="cover-pill">{eyebrow_left}</div>
      <div class="cover-meta">{eyebrow_right}</div>
    </div>
    <section class="film-frame">
      <div class="film-label">FILM · 01</div>
      <div class="film-label film-label-right">ISO 400</div>
      <div class="film-content">
        <div class="film-title">{headline} <span>{symbol}</span></div>
        <div class="film-note">{subtitle}</div>
      </div>
      <div class="film-code">CHU_IL · COLOR NEGATIVE</div>
    </section>
    <div class="cover-bottom-line"></div>
    <footer class="cover-footer">
      <span>{footer_left}</span>
      <span>{footer_right}</span>
    </footer>
    """


def _symbol_html(symbol: str) -> str:
    if symbol == "asterisk":
        return "*"
    if symbol == "slash":
        return "/"
    if symbol == "dot":
        return "•"
    return "↘"


def image_bytes_to_data_url(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    mime_type = mime_type if mime_type in {"image/jpeg", "image/png", "image/webp"} else "image/jpeg"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _headline_size(format_key: str, is_retro: bool, headline: str) -> int:
    length = len((headline or "").replace("\n", " "))
    lines = _headline_lines(
        headline,
        format_key,
        "retro_polaroid" if is_retro else "orange_poster",
    )
    longest_line = max((len(line) for line in lines), default=14)
    if is_retro:
        base = {"wide": 84, "post": 78, "story": 92}.get(format_key, 78)
        available_width = {"wide": 1340, "post": 730, "story": 780}.get(format_key, 730)
        char_ratio = 0.58
    else:
        base = {"wide": 132, "post": 112, "story": 112}.get(format_key, 112)
        available_width = {"wide": 1680, "post": 900, "story": 900}.get(format_key, 900)
        char_ratio = 0.62
    if length > 46:
        base = int(base * 0.78)
    elif length > 34:
        base = int(base * 0.88)
    fit_size = int(available_width / max(1, longest_line * char_ratio))
    return max(58 if not is_retro else 48, min(base, fit_size))


def _headline_html(headline: str, format_key: str, style: str) -> str:
    lines = _headline_lines(headline, format_key, style)
    return "".join(
        f'<span class="headline-line">{html.escape(line)}</span>'
        for line in lines
    )


def _headline_lines(headline: str, format_key: str, style: str) -> list[str]:
    max_lines = {"wide": 2, "post": 3, "story": 4}.get(format_key, 3)
    target = {
        ("wide", "poster"): 22,
        ("post", "poster"): 13,
        ("story", "poster"): 11,
        ("wide", "retro"): 22,
        ("post", "retro"): 16,
        ("story", "retro"): 13,
    }.get((format_key, "retro" if style == "retro_polaroid" else "poster"), 15)
    words = [word for word in re.split(r"\s+", (headline or "").strip()) if word]
    if not words:
        return ["главная мысль"]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= target or len(lines) >= max_lines - 1:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :])]
    return lines


def _fallback_headline_parts(text: str) -> tuple[str, str]:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+|[\n:;]+", clean) if part.strip()]
    headline_source = parts[0] if parts else "Новая обложка"
    subtitle_source = parts[1] if len(parts) > 1 else ""
    return _clean_text(headline_source, 46), _clean_text(subtitle_source, 86)


def _clean_text(text: str, limit: int) -> str:
    text = re.sub(r"#\w+", "", text or "")
    text = re.sub(r"\s+", " ", text).strip(" \n\t\"'`*_")
    if len(text) <= limit:
        return text
    clipped = text[:limit].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,.;:-") + "…"


def _safe_background_data_url(value: str) -> str:
    value = (value or "").strip()
    if re.match(r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=\s]+$", value):
        return re.sub(r"\s+", "", value)
    return ""
