from __future__ import annotations

import base64
import logging
from dataclasses import asdict, dataclass
import html
import re


COVER_AUTHOR = "chu_il"

VISUAL_MODE_TO_COVER_STYLE = {
    "auto": "orange_poster",
    "calm": "quiet_editorial",
    "business": "paper_brief",
    "facts": "blue_type",
    "contrast": "red_manifesto",
    "editorial": "quiet_editorial",
    "brief": "paper_brief",
    "data": "blue_type",
    "classic": "orange_poster",
}

COVER_FORMATS = {
    "wide": {"label": "16:9", "width": 1920, "height": 1080},
    "post": {"label": "4:5", "width": 1080, "height": 1350},
    "story": {"label": "9:16", "width": 1080, "height": 1920},
}

COVER_STYLES = {
    "orange_poster": {
        "label": "Оранжевый постер",
        "class": "cover-orange-poster",
        "bg": "#f45124",
        "text": "#07080b",
        "muted": "#07080b",
        "pill_bg": "#05070a",
        "pill_text": "#fff3e8",
        "line": "#05070a",
    },
    "acid_poster": {
        "label": "Кислотный постер",
        "class": "cover-acid-poster",
        "bg": "#d7ff37",
        "text": "#071006",
        "muted": "#071006",
        "pill_bg": "#071006",
        "pill_text": "#f8ffe1",
        "line": "#071006",
    },
    "retro_polaroid": {
        "label": "Плёночный архив",
        "class": "cover-retro-polaroid",
        "bg": "#161b1c",
        "text": "#fff2d3",
        "muted": "#ffd17a",
        "pill_bg": "#fff2d3",
        "pill_text": "#15191a",
        "line": "#fff2d3",
    },
    "blue_type": {
        "label": "Синяя типографика",
        "class": "cover-blue-type",
        "bg": "#f3f0ec",
        "text": "#1048ff",
        "muted": "#1048ff",
        "pill_bg": "#1048ff",
        "pill_text": "#f8f5ef",
        "line": "#1048ff",
    },
    "grid_steps": {
        "label": "Сетка и шаги",
        "class": "cover-grid-steps",
        "bg": "#f6f5f0",
        "text": "#141414",
        "muted": "#141414",
        "pill_bg": "#1551ff",
        "pill_text": "#ffffff",
        "line": "#1551ff",
    },
    "blur_field": {
        "label": "Размытое движение",
        "class": "cover-blur-field",
        "bg": "#ee321f",
        "text": "#161616",
        "muted": "#161616",
        "pill_bg": "#161616",
        "pill_text": "#fff7f0",
        "line": "#161616",
    },
    "red_manifesto": {
        "label": "Красный манифест",
        "button": "Красный манифест",
        "class": "cover-red-manifesto",
        "bg": "#ecebe3",
        "text": "#c91f27",
        "muted": "#111111",
        "pill_bg": "#c91f27",
        "pill_text": "#fffaf1",
        "line": "#111111",
    },
    "paper_brief": {
        "label": "Бумажный разбор",
        "button": "Бумажный разбор",
        "class": "cover-paper-brief",
        "bg": "#f4f1e8",
        "text": "#d21d24",
        "muted": "#151515",
        "pill_bg": "#151515",
        "pill_text": "#f4f1e8",
        "line": "#d21d24",
    },
    "quiet_editorial": {
        "label": "Тихий журнал",
        "button": "Тихий журнал",
        "class": "cover-quiet-editorial",
        "bg": "#f7f3ea",
        "text": "#18221f",
        "muted": "#56615c",
        "pill_bg": "#18221f",
        "pill_text": "#f7f3ea",
        "line": "#a46a3f",
    },
    "chalk_notes": {
        "label": "Ручные заметки",
        "button": "Ручные заметки",
        "class": "cover-chalk-notes",
        "bg": "#fffefd",
        "text": "#2457bc",
        "muted": "#222222",
        "pill_bg": "#fffefd",
        "pill_text": "#222222",
        "line": "#ef5b2d",
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
    cta_text: str = ""
    html_body: str = ""

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
        cta_text=_clean_text(str(raw_plan.get("cta_text") or ""), 32),
        html_body=str(raw_plan.get("html_body") or "").strip(),
    )


def build_cover_html(plan: CoverPlan) -> str:
    if not plan.background_data_url:
        ai_html = _build_ai_cover_html(plan)
        if ai_html:
            return ai_html

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
    footer_right = html.escape(plan.footer_right or COVER_AUTHOR)
    style_class = style_tokens["class"]
    is_retro = plan.style == "retro_polaroid"
    custom_background = _safe_background_data_url(plan.background_data_url)
    background_markup = (
        f'<div class="custom-background" style="background-image: url(&quot;{custom_background}&quot;)"></div>'
        if custom_background
        else ""
    )

    _template_map = {
        "retro_polaroid": "retro",
        "quiet_editorial": "magazine",
        "paper_brief": "magazine",
        "blue_type": "terminal",
        "grid_steps": "terminal",
    }
    template = _template_map.get(plan.style, "poster")

    if template == "retro":
        body_markup = _retro_markup(
            headline=headline,
            subtitle=subtitle,
            eyebrow_left=eyebrow_left,
            eyebrow_right=eyebrow_right,
            footer_left=footer_left,
            footer_right=footer_right,
            symbol=symbol,
        )
    elif template == "magazine":
        body_markup = _magazine_markup(
            headline=headline,
            subtitle=subtitle,
            eyebrow_left=eyebrow_left,
            eyebrow_right=eyebrow_right,
            footer_left=footer_left,
            footer_right=footer_right,
            symbol=symbol,
        )
    elif template == "terminal":
        body_markup = _terminal_markup(
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
    cta_markup = ""
    if plan.cta_text:
        cta_bottom = str(int(line_bottom.replace("px", "")) - 16) + "px"
        cta_markup = f"""
    <div class="cover-cta">{html.escape(plan.cta_text)}</div>
    """

    _overlay_map = {
        "orange_poster": ("0.56", "contrast(1.05) saturate(0.9)", "rgba(244,81,36,0.22)"),
        "acid_poster": ("0.52", "contrast(1.08) saturate(0.85)", "rgba(215,255,55,0.18)"),
        "retro_polaroid": ("0.74", "contrast(1.08) saturate(0.92)", "linear-gradient(90deg, rgba(10,14,16,0.42), rgba(255,140,48,0.24)), radial-gradient(circle at 14% 78%, rgba(255,220,40,0.38), transparent 28%)"),
        "blue_type": ("0.54", "contrast(1.04) saturate(0.95)", "rgba(16,72,255,0.14)"),
        "grid_steps": ("0.56", "contrast(1.06) saturate(0.92)", "rgba(21,81,255,0.16)"),
        "blur_field": ("0.62", "contrast(1.1) saturate(0.88)", "linear-gradient(180deg, rgba(0,0,0,0.28), rgba(210,50,30,0.18))"),
        "red_manifesto": ("0.54", "contrast(1.04) saturate(0.94)", "rgba(201,31,39,0.16)"),
        "paper_brief": ("0.56", "contrast(1.02) saturate(0.96)", "rgba(210,29,36,0.12)"),
        "quiet_editorial": ("0.58", "contrast(1.03) saturate(0.95)", "rgba(164,106,63,0.14)"),
        "chalk_notes": ("0.56", "contrast(1.04) saturate(0.94)", "rgba(36,87,188,0.12)"),
    }
    ov = _overlay_map.get(plan.style, ("0.58", "contrast(1.05) saturate(0.9)", "rgba(255,255,255,0.18)"))

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Unbounded:wght@400;700;900&family=JetBrains+Mono:wght@400;700;900&display=swap');
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
      opacity: {ov[0]};
      filter: {ov[1]};
      z-index: 0;
    }}
    .custom-background::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: {ov[2]};
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
      font-family: "JetBrains Mono", Arial, "Helvetica Neue", sans-serif;
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
    .cover-terminal-prompt {{
      color: {style_tokens["text"]};
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: {("28" if plan.format_key != "story" else "36")}px;
      font-weight: 400;
      margin-bottom: 16px;
      opacity: 0.6;
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
        linear-gradient(180deg, rgba(16,12,10,0.72), rgba(24,18,14,0.1) 36%, rgba(9,6,6,0.8)),
        linear-gradient(180deg, #17100e 0 18%, #6d2a20 18% 42%, #d3b88f 42% 58%, #9c2d20 58% 76%, #120c0b 76% 100%);
      filter: contrast(1.08) saturate(0.94);
    }}
    .cover-blur-field .cover-canvas::before {{
      background:
        linear-gradient(0deg, transparent 0 18%, rgba(255,255,255,0.42) 18.2% 18.8%, transparent 19.2% 72%, rgba(255,255,255,0.36) 72.3% 73%, transparent 73.5%),
        linear-gradient(90deg, rgba(255,255,255,0.12), transparent 20%, rgba(255,255,255,0.18) 52%, transparent 74%);
      background-size: 100% 100%;
      opacity: 0.58;
    }}
    .cover-blur-field .cover-canvas::after {{
      content: "";
      position: absolute;
      left: -18%;
      right: -18%;
      top: {("250px" if plan.format_key == "wide" else "330px" if plan.format_key == "post" else "560px")};
      height: {("360px" if plan.format_key == "wide" else "470px" if plan.format_key == "post" else "640px")};
      background:
        linear-gradient(0deg, transparent 0 10%, rgba(255,255,255,0.32) 10% 17%, transparent 17% 47%, rgba(255,255,255,0.22) 47% 56%, transparent 56%),
        linear-gradient(90deg, rgba(112,32,24,0.92), rgba(210,160,112,0.72) 34%, rgba(235,214,174,0.82) 51%, rgba(154,41,27,0.9) 72%, rgba(95,24,20,0.94));
      filter: blur(22px);
      transform: scaleX(1.18);
      opacity: 0.78;
      z-index: 1;
    }}
    .cover-blur-field .cover-main {{
      left: {("120px" if plan.format_key == "wide" else "72px")};
      right: {("120px" if plan.format_key == "wide" else "72px")};
      top: {("600px" if plan.format_key == "wide" else "810px" if plan.format_key == "post" else "1180px")};
      z-index: 5;
    }}
    .cover-blur-field .cover-headline {{
      color: #ffffff;
      font-family: "Unbounded", Impact, "Arial Black", "Arial Narrow", Arial, sans-serif;
      font-size: {("118" if plan.format_key == "wide" else "104" if plan.format_key == "post" else "112")}px;
      line-height: 0.82;
      font-weight: 950;
      text-transform: uppercase;
      opacity: 1;
      text-shadow: 0 16px 42px rgba(0,0,0,0.46);
    }}
    .cover-blur-field .cover-subtitle {{
      color: rgba(255,255,255,0.92);
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: {("26" if plan.format_key != "story" else "30")}px;
      letter-spacing: 9px;
      text-transform: uppercase;
      margin-top: 34px;
      max-width: none;
    }}
    .cover-blur-field .cover-pill,
    .cover-blur-field .cover-meta {{
      color: #fff;
      background: transparent;
      letter-spacing: 7px;
    }}
    .cover-blur-field .cover-symbol {{
      display: none;
    }}
    .cover-blur-field .cover-bottom-line {{
      height: 4px;
      background: rgba(255,255,255,0.92);
      bottom: {("178px" if plan.format_key != "story" else "250px")};
    }}
    .cover-blur-field .cover-footer {{
      color: rgba(255,255,255,0.92);
      letter-spacing: 8px;
    }}
    .cover-red-manifesto .cover-canvas {{
      background:
        radial-gradient(circle at 62% 46%, rgba(0,0,0,0.11), transparent 16%),
        linear-gradient(0deg, rgba(0,0,0,0.035) 0 1px, transparent 1px),
        #ecebe3;
      background-size: 100% 100%, 100% 142px, 100% 100%;
    }}
    .cover-red-manifesto .cover-canvas::after {{
      content: "";
      position: absolute;
      left: {("760px" if plan.format_key == "wide" else "360px")};
      top: {("310px" if plan.format_key == "wide" else "520px" if plan.format_key == "post" else "810px")};
      width: {("520px" if plan.format_key == "wide" else "610px")};
      height: {("520px" if plan.format_key == "wide" else "610px")};
      background:
        linear-gradient(88deg, transparent 0 38%, rgba(0,0,0,0.76) 38% 53%, transparent 53%),
        linear-gradient(171deg, transparent 0 44%, rgba(0,0,0,0.76) 44% 59%, transparent 59%);
      transform: rotate(-10deg);
      z-index: 1;
    }}
    .cover-red-manifesto .cover-top {{
      top: {("46px" if plan.format_key != "story" else "76px")};
    }}
    .cover-red-manifesto .cover-pill {{
      border-radius: 0;
      min-height: 42px;
      padding: 0 14px;
      font-size: 15px;
    }}
    .cover-red-manifesto .cover-main {{
      left: {("44px" if plan.format_key == "wide" else "42px")};
      right: {("44px" if plan.format_key == "wide" else "34px")};
      top: {("178px" if plan.format_key == "wide" else "246px" if plan.format_key == "post" else "390px")};
      z-index: 4;
    }}
    .cover-red-manifesto .cover-headline {{
      max-width: {("1780px" if plan.format_key == "wide" else "980px")};
      color: #c91f27;
      font-family: Impact, "Arial Narrow", "Arial Black", Arial, sans-serif;
      font-size: {("188" if plan.format_key == "wide" else "156" if plan.format_key == "post" else "164")}px;
      line-height: 0.84;
      font-stretch: condensed;
      font-weight: 950;
      text-transform: uppercase;
    }}
    .cover-red-manifesto .cover-subtitle {{
      max-width: {("470px" if plan.format_key == "wide" else "360px")};
      margin-top: {("36px" if plan.format_key != "story" else "52px")};
      color: #151515;
      font-size: {("26" if plan.format_key == "wide" else "24")}px;
      font-weight: 500;
      line-height: 1.08;
    }}
    .cover-red-manifesto .cover-symbol {{
      display: none;
    }}
    .cover-paper-brief .cover-canvas {{
      background:
        linear-gradient(90deg, rgba(0,0,0,0.05), transparent 14%, transparent 86%, rgba(0,0,0,0.05)),
        radial-gradient(circle at 50% 0, rgba(0,0,0,0.08), transparent 34%),
        linear-gradient(#f7f4eb, #e4dfd2);
    }}
    .cover-paper-brief .cover-canvas::after {{
      content: "";
      position: absolute;
      left: {("150px" if plan.format_key == "wide" else "64px")};
      right: {("150px" if plan.format_key == "wide" else "64px")};
      top: {("96px" if plan.format_key == "wide" else "116px" if plan.format_key == "post" else "210px")};
      bottom: {("96px" if plan.format_key == "wide" else "116px" if plan.format_key == "post" else "210px")};
      background: rgba(255,255,255,0.9);
      box-shadow: 0 26px 72px rgba(0,0,0,0.18);
      z-index: 1;
    }}
    .cover-paper-brief .cover-top {{
      left: {("210px" if plan.format_key == "wide" else "98px")};
      right: {("210px" if plan.format_key == "wide" else "98px")};
      top: {("132px" if plan.format_key == "wide" else "160px" if plan.format_key == "post" else "270px")};
      z-index: 5;
    }}
    .cover-paper-brief .cover-pill {{
      display: none;
    }}
    .cover-paper-brief .cover-meta {{
      margin-left: auto;
      color: #d21d24;
      font-size: 24px;
      font-family: "Arial Narrow", Arial, sans-serif;
      font-weight: 950;
    }}
    .cover-paper-brief .cover-main {{
      left: {("210px" if plan.format_key == "wide" else "98px")};
      right: {("210px" if plan.format_key == "wide" else "98px")};
      top: {("210px" if plan.format_key == "wide" else "250px" if plan.format_key == "post" else "390px")};
      z-index: 5;
    }}
    .cover-paper-brief .cover-headline {{
      max-width: {("1420px" if plan.format_key == "wide" else "880px")};
      color: #d21d24;
      font-family: "Unbounded", Impact, "Arial Narrow", "Arial Black", Arial, sans-serif;
      font-size: {("162" if plan.format_key == "wide" else "136" if plan.format_key == "post" else "144")}px;
      line-height: 0.82;
      text-transform: uppercase;
      font-weight: 950;
    }}
    .cover-paper-brief .cover-subtitle {{
      position: absolute;
      top: {("360px" if plan.format_key == "wide" else "470px" if plan.format_key == "post" else "780px")};
      left: 0;
      max-width: {("460px" if plan.format_key == "wide" else "360px")};
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      color: #151515;
      font-size: {("19" if plan.format_key == "wide" else "18")}px;
      line-height: 1.05;
      font-weight: 500;
    }}
    .cover-paper-brief .cover-subtitle::before {{
      content: "(1)";
      display: block;
      margin-bottom: 8px;
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 18px;
      color: #151515;
    }}
    .cover-paper-brief .cover-symbol {{
      right: {("210px" if plan.format_key == "wide" else "110px")};
      top: auto;
      bottom: {("170px" if plan.format_key == "wide" else "214px" if plan.format_key == "post" else "320px")};
      width: 34px;
      height: 34px;
      overflow: hidden;
      background: #d21d24;
      color: #d21d24;
      font-size: 1px;
    }}
    .cover-paper-brief .cover-footer {{
      left: {("210px" if plan.format_key == "wide" else "98px")};
      right: {("210px" if plan.format_key == "wide" else "98px")};
      bottom: {("126px" if plan.format_key == "wide" else "154px" if plan.format_key == "post" else "244px")};
      color: #151515;
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 16px;
      font-weight: 600;
    }}
    .cover-paper-brief .cover-bottom-line {{
      left: {("210px" if plan.format_key == "wide" else "98px")};
      right: {("210px" if plan.format_key == "wide" else "98px")};
      bottom: {("190px" if plan.format_key == "wide" else "230px" if plan.format_key == "post" else "360px")};
      height: 1px;
      background: rgba(0,0,0,0.28);
    }}
    .cover-quiet-editorial .cover-canvas {{
      background:
        radial-gradient(circle at 18% 18%, rgba(164,106,63,0.14), transparent 22%),
        linear-gradient(90deg, rgba(24,34,31,0.05) 0 1px, transparent 1px),
        #f7f3ea;
      background-size: 100% 100%, 96px 100%, 100% 100%;
    }}
    .cover-quiet-editorial .cover-top {{
      left: {("110px" if plan.format_key == "wide" else "76px")};
      right: {("110px" if plan.format_key == "wide" else "76px")};
      top: {("74px" if plan.format_key != "story" else "118px")};
    }}
    .cover-quiet-editorial .cover-pill {{
      min-height: 38px;
      border-radius: 999px;
      padding: 0 16px;
      background: transparent;
      border: 1px solid rgba(24,34,31,0.34);
      color: #18221f;
      font-size: 14px;
      font-weight: 700;
    }}
    .cover-quiet-editorial .cover-main {{
      left: {("110px" if plan.format_key == "wide" else "76px")};
      right: {("420px" if plan.format_key == "wide" else "96px")};
      top: {("220px" if plan.format_key == "wide" else "360px" if plan.format_key == "post" else "560px")};
    }}
    .cover-quiet-editorial .cover-headline {{
      max-width: {("900px" if plan.format_key == "wide" else "720px")};
      color: #18221f;
      font-family: "Playfair Display", Georgia, "Times New Roman", serif;
      font-size: {("104" if plan.format_key == "wide" else "90" if plan.format_key == "post" else "96")}px;
      line-height: 0.96;
      font-weight: 400;
      text-transform: none;
    }}
    .cover-quiet-editorial .cover-subtitle {{
      max-width: 520px;
      color: #56615c;
      font-size: {("28" if plan.format_key != "story" else "32")}px;
      font-family: Arial, "Helvetica Neue", sans-serif;
      font-weight: 500;
      line-height: 1.22;
    }}
    .cover-quiet-editorial .cover-symbol {{
      right: {("118px" if plan.format_key == "wide" else "76px")};
      top: {("260px" if plan.format_key == "wide" else "210px" if plan.format_key == "post" else "300px")};
      color: #a46a3f;
      font-family: Georgia, "Times New Roman", serif;
      font-size: {("140" if plan.format_key == "wide" else "118")}px;
      opacity: 0.62;
    }}
    .cover-quiet-editorial .cover-bottom-line {{
      height: 1px;
      background: rgba(164,106,63,0.55);
    }}
    .cover-chalk-notes .cover-canvas {{
      background:
        radial-gradient(circle at 12% 24%, rgba(239,91,45,0.08), transparent 12%),
        radial-gradient(circle at 70% 18%, rgba(35,153,102,0.08), transparent 12%),
        #fffefd;
    }}
    .cover-chalk-notes .cover-canvas::after {{
      content: "";
      position: absolute;
      left: {("90px" if plan.format_key == "wide" else "52px")};
      right: {("90px" if plan.format_key == "wide" else "52px")};
      top: {("110px" if plan.format_key == "wide" else "150px" if plan.format_key == "post" else "240px")};
      height: {("380px" if plan.format_key == "wide" else "520px" if plan.format_key == "post" else "760px")};
      background:
        linear-gradient(92deg, transparent 0 18%, rgba(239,91,45,0.36) 18.3% 18.8%, transparent 19.2%),
        linear-gradient(176deg, transparent 0 58%, rgba(36,87,188,0.28) 58.1% 58.8%, transparent 59.1%);
      opacity: 0.75;
      z-index: 1;
    }}
    .cover-chalk-notes .cover-top {{
      display: none;
    }}
    .cover-chalk-notes .cover-main {{
      left: {("96px" if plan.format_key == "wide" else "60px")};
      right: {("96px" if plan.format_key == "wide" else "60px")};
      top: {("130px" if plan.format_key == "wide" else "180px" if plan.format_key == "post" else "290px")};
      z-index: 5;
    }}
    .cover-chalk-notes .cover-headline {{
      max-width: {("1520px" if plan.format_key == "wide" else "910px")};
      font-family: "Comic Sans MS", "Trebuchet MS", Arial, sans-serif;
      font-size: {("122" if plan.format_key == "wide" else "108" if plan.format_key == "post" else "118")}px;
      line-height: 1.06;
      font-weight: 500;
      text-transform: uppercase;
      color: #2457bc;
      text-shadow:
        1px 1px 0 #ef5b2d,
        -1px 1px 0 #239966,
        2px -1px 0 #f2ce3d;
    }}
    .cover-chalk-notes .cover-headline .headline-line:nth-child(2n) {{
      color: #ef5b2d;
      padding-left: {("150px" if plan.format_key == "wide" else "80px")};
    }}
    .cover-chalk-notes .cover-headline .headline-line:nth-child(3n) {{
      color: #239966;
      padding-left: {("40px" if plan.format_key == "wide" else "24px")};
    }}
    .cover-chalk-notes .cover-subtitle {{
      max-width: {("700px" if plan.format_key == "wide" else "620px")};
      margin-top: {("42px" if plan.format_key != "story" else "70px")};
      color: #222222;
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: {("30" if plan.format_key == "wide" else "32")}px;
      line-height: 1.18;
      font-weight: 600;
    }}
    .cover-chalk-notes .cover-symbol {{
      display: none;
    }}
    .cover-chalk-notes .cover-bottom-line {{
      display: none;
    }}
    .cover-chalk-notes .cover-footer {{
      color: #222222;
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 18px;
      font-weight: 700;
      text-transform: lowercase;
    }}
    .cover-cta {{
      position: absolute;
      left: 60px;
      right: 60px;
      bottom: {("132px" if plan.format_key != "story" else "196px")};
      display: flex;
      align-items: center;
      gap: 10px;
      z-index: 6;
    }}
    .cover-cta::before {{
      content: "";
      width: 8px;
      height: 8px;
      background: {style_tokens["text"]};
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .cover-cta {{
      color: {style_tokens["muted"]};
      font-family: "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
  </style>
</head>
<body class="{style_class}">
  <div class="cover-canvas">
    {background_markup}
    {body_markup}
    {cta_markup}
  </div>
</body>
</html>"""


AI_FONT_QUERIES = {
    "inter": "Inter:wght@400;500;600;700;800",
    "playfair display": "Playfair+Display:wght@400;700;900",
    "unbounded": "Unbounded:wght@400;700;900",
    "cormorant garamond": "Cormorant+Garamond:wght@400;500;600;700",
    "jetbrains mono": "JetBrains+Mono:wght@400;500;700;800",
    "manrope": "Manrope:wght@400;500;700;800",
    "space grotesk": "Space+Grotesk:wght@400;500;700",
    "sora": "Sora:wght@400;600;700;800",
    "dm serif display": "DM+Serif+Display:ital@0;1",
}


def _build_ai_cover_html(plan: CoverPlan) -> str:
    html_body = _sanitize_ai_html_body(plan.html_body)
    if not html_body:
        return ""

    fmt = COVER_FORMATS.get(plan.format_key, COVER_FORMATS["post"])
    width = fmt["width"]
    height = fmt["height"]
    imports = _google_font_imports_for_html(html_body)
    texture_css = _texture_css_for_cover(plan.style)
    fonts_block = f'<link href="https://fonts.googleapis.com/css2?{imports}&display=swap" rel="stylesheet">' if imports else ""
    safe_bg = _safe_background_data_url(plan.background_data_url)
    background_markup = (
        f'<div class="ai-custom-bg" style="background-image:url(&quot;{safe_bg}&quot;);"></div>'
        if safe_bg
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width={width}, initial-scale=1">
  {fonts_block}
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; }}
    body {{ position: relative; background: #f4f1e8; }}
    .ai-custom-bg {{
      position: absolute;
      inset: 0;
      background-position: center;
      background-size: cover;
      opacity: 0.24;
      filter: contrast(1.04) saturate(0.9);
      z-index: 0;
    }}
    .ai-custom-bg::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(244, 241, 232, 0.12), rgba(244, 241, 232, 0.22));
    }}
    .ai-texture {{ position: absolute; inset: 0; z-index: 1; pointer-events: none; opacity: 0.24; {texture_css} }}
    .ai-stage {{ position: relative; z-index: 2; width: {width}px; height: {height}px; }}
    .ai-stage > * {{
      width: 100%;
      min-height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
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


def _google_font_imports_for_html(html_body: str) -> str:
    imports: list[str] = []
    seen: set[str] = set()

    for family in _extract_font_families(html_body):
        query = AI_FONT_QUERIES.get(family.lower())
        if query and query not in seen:
            seen.add(query)
            imports.append(query)

    return "|".join(imports)


def _extract_font_families(html_body: str) -> list[str]:
    families: list[str] = []
    for raw_value in re.findall(r"font-family\s*:\s*([^;\"']+|\"[^\"]+\"|'[^']+')", html_body, flags=re.IGNORECASE):
        for family in str(raw_value).split(","):
            clean = family.strip().strip("'\"")
            if clean:
                families.append(clean)
    return families


def _texture_css_for_cover(style: str) -> str:
    textures = {
        "orange_poster": "background-image: radial-gradient(circle at 15% 20%, rgba(7,8,11,0.10), transparent 18%), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px); background-size: 100% 100%, 30px 30px;",
        "acid_poster": "background-image: radial-gradient(circle at 20% 30%, rgba(7,16,6,0.12), transparent 16%), radial-gradient(circle at 80% 70%, rgba(7,16,6,0.08), transparent 18%);",
        "retro_polaroid": "background-image: radial-gradient(circle at 10% 10%, rgba(255,242,211,0.10), transparent 12%), radial-gradient(circle at 80% 70%, rgba(255,209,122,0.10), transparent 14%);",
        "blue_type": "background-image: linear-gradient(rgba(16,72,255,0.06) 1px, transparent 1px); background-size: 100% 24px;",
        "grid_steps": "background-image: linear-gradient(rgba(21,81,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(21,81,255,0.05) 1px, transparent 1px); background-size: 100% 28px, 28px 100%;",
        "blur_field": "background-image: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.10), transparent 18%), radial-gradient(circle at 70% 60%, rgba(0,0,0,0.08), transparent 20%);",
        "red_manifesto": "background-image: linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px); background-size: 100% 18px;",
        "paper_brief": "background-image: linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px); background-size: 100% 26px;",
        "quiet_editorial": "background-image: radial-gradient(circle, rgba(24,34,31,0.04) 1px, transparent 1px); background-size: 18px 18px;",
        "chalk_notes": "background-image: radial-gradient(circle at 20% 20%, rgba(36,87,188,0.08), transparent 12%), radial-gradient(circle at 70% 60%, rgba(239,91,45,0.08), transparent 14%);",
    }
    return textures.get(style, textures["quiet_editorial"])


def render_cover_html(plan: CoverPlan) -> bytes:
    fmt = COVER_FORMATS.get(plan.format_key, COVER_FORMATS["post"])
    width = fmt["width"]
    height = fmt["height"]
    html_content = build_cover_html(plan)

    # Try Playwright first, fall back to Pillow screenshot
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            page.set_content(html_content, wait_until="load")
            png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": width, "height": height})
            browser.close()
        return png
    except Exception as exc:
        logging.warning("Playwright cover render failed, using Pillow fallback: %s", exc)

    # Pillow fallback: render HTML to image via simple approach
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw headline
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        except Exception:
            font = ImageFont.load_default()
        text = (plan.headline or "Обложка").strip()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2
        draw.text((x, y), text, fill=(20, 20, 30), font=font)
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc2:
        logging.warning("Pillow cover fallback also failed: %s", exc2)
        # Absolute last resort: return a minimal valid PNG
        import struct, zlib
        def _make_png(w, h):
            raw = b""
            for _ in range(h):
                raw += b"\x00" + b"\xff" * w * 3
            def _chunk(t, d):
                c = t + d
                return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return (b"\x89PNG\r\n\x1a\n" +
                    _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                    _chunk(b"IDAT", zlib.compress(raw)) +
                    _chunk(b"IEND", b""))
        return _make_png(width, height)


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


def _magazine_markup(
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
      <div class="cover-subtitle">{subtitle}</div>
      <h1 class="cover-headline">{headline}</h1>
    </main>
    <div class="cover-bottom-line"></div>
    <footer class="cover-footer">
      <span>{footer_left}</span>
      <span>{footer_right}</span>
    </footer>
    """


def _terminal_markup(
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
      <div class="cover-terminal-prompt">&gt; _</div>
      <h1 class="cover-headline">{headline}</h1>
      <div class="cover-subtitle">{subtitle}</div>
    </main>
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
