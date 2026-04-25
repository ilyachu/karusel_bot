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
    if spec.visual_mode in {"editorial", "brief", "data"}:
        return _build_editorial_slide_html(spec, logo_text)

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


def _build_editorial_slide_html(spec: LayoutSpec, logo_text: str = "chu ai") -> str:
    palette = _editorial_tokens(spec.theme, spec.visual_mode)
    title = _apply_accent_markup(html.escape(spec.title), spec.accent_spans, palette["accent"])
    body = _apply_accent_markup(html.escape(spec.body).replace("\n", "<br>"), spec.accent_spans, palette["accent_soft"])
    progress_percent = int((spec.slide_index / max(spec.total_slides, 1)) * 100)
    is_cover = spec.variant.endswith("_cover")
    is_cta = spec.variant.endswith("_cta")
    is_stat = spec.variant in {"editorial_stat", "data_stat"}
    is_brief = spec.visual_mode == "brief"
    is_data = spec.visual_mode == "data"
    show_tags = spec.visual_mode == "editorial" and bool(spec.footer_tags)
    tags_html = "".join(f'<div class="editorial-tag">{html.escape(tag)}</div>' for tag in spec.footer_tags[:4]) if show_tags else ""
    rail_cards = [] if is_stat else spec.supporting_cards[:3]
    support_html = "".join(
        (
            '<div class="editorial-rail-card">'
            f'<span>{html.escape(card.get("title", ""))}</span>'
            f'<strong>{html.escape(card.get("body", ""))}</strong>'
            '</div>'
        )
        for card in rail_cards
    )
    variant_class = spec.variant.replace("_", "-")
    mode_class = spec.visual_mode.replace("_", "-")
    brand = html.escape(spec.brand_mark or logo_text)
    show_brand = "flex" if spec.brand_mark else "none"
    title_size = "86px" if is_cover else "74px" if is_stat else "64px" if is_brief else "62px"
    body_max_width = "760px" if is_cover else "620px" if is_stat else "690px"
    stage_top = "214px" if is_cover else "250px" if is_stat else "300px" if is_cta else "276px"
    stage_bottom = "156px"
    title_block_max_width = "840px" if is_cover else "700px" if is_stat else "650px"
    body_margin_top = "26px" if is_cover else "20px"
    body_font_size = "32px" if is_cover else "28px" if is_brief else "30px"
    stat_value = html.escape((spec.supporting_cards[0].get("title", "") if spec.supporting_cards else spec.watermark_number).strip())
    stat_detail = html.escape(
        (spec.supporting_cards[0].get("body", "") if spec.supporting_cards else "ключевой показатель").strip()
    )
    stat_html = (
        f'<div class="data-stat-block"><span>{stat_value}</span><strong>{stat_detail}</strong></div>'
        if is_stat
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      width: 1080px;
      height: 1350px;
      overflow: hidden;
      background:
        radial-gradient(circle at 26% 22%, {palette["glow"]}, transparent 34%),
        radial-gradient(circle at 82% 76%, {palette["glow2"]}, transparent 28%),
        linear-gradient(135deg, {palette["bg0"]} 0%, {palette["bg1"]} 58%, {palette["bg2"]} 100%);
      color: {palette["text"]};
      font-family: {palette["body_font"]};
    }}
    .canvas {{
      position: relative;
      width: 1080px;
      height: 1350px;
      padding: 96px 72px 70px;
      isolation: isolate;
    }}
    .editorial-aura {{
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, transparent 0%, rgba(255,255,255,0.02) 100%),
        radial-gradient(circle at 22% 34%, {palette["accent_glow"]}, transparent 26%),
        radial-gradient(circle at 72% 78%, {palette["accent_glow_2"]}, transparent 24%);
      pointer-events: none;
      z-index: 0;
    }}
    .editorial-watermark {{
      position: absolute;
      top: 108px;
      right: 70px;
      font-family: {palette["display_font"]};
      font-size: {("118px" if is_stat else "148px")};
      line-height: 1;
      letter-spacing: 0;
      color: {palette["watermark"]};
    }}
    .editorial-topbar {{
      position: absolute;
      top: 96px;
      left: 72px;
      right: 72px;
      z-index: 2;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .editorial-section {{
      color: {palette["muted"]};
      text-transform: uppercase;
      letter-spacing: 0.22em;
      font-size: 20px;
    }}
    .editorial-brand {{
      display: {show_brand};
      color: rgba(255,255,255,0.74);
      font-style: italic;
      font-family: {palette["display_font"]};
      font-size: 24px;
    }}
    .editorial-title {{
      position: relative;
      z-index: 2;
      margin: 0;
      max-width: {title_block_max_width};
      font-family: {palette["display_font"]};
      font-size: {title_size};
      line-height: {("0.95" if spec.variant == "editorial_cover" else "0.88" if spec.variant == "editorial_stat" else "1.04")};
      letter-spacing: 0;
      text-wrap: balance;
    }}
    .editorial-stage {{
      position: absolute;
      top: {stage_top};
      left: 72px;
      right: 72px;
      bottom: {stage_bottom};
      z-index: 2;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
    }}
    .variant-editorial-story {{
      max-width: 610px;
    }}
    .variant-editorial-scenario {{
      max-width: 560px;
    }}
    .variant-brief-insight,
    .variant-brief-decision {{
      max-width: 650px;
      font-family: {palette["body_font"]};
      font-weight: 850;
    }}
    .variant-data-stat {{
      max-width: 560px;
      font-family: {palette["body_font"]};
      font-size: 34px;
      text-transform: uppercase;
      color: {palette["muted"]};
    }}
    .editorial-body {{
      position: relative;
      z-index: 2;
      margin-top: {body_margin_top};
      max-width: {body_max_width};
      color: {palette["muted_text"]};
      font-size: {body_font_size};
      line-height: 1.46;
    }}
    .mode-data .editorial-body {{
      font-family: {palette["body_font"]};
      line-height: 1.38;
    }}
    .mode-brief .editorial-body {{
      color: {palette["muted_text"]};
      max-width: 610px;
    }}
    .editorial-accent {{
      color: {palette["accent"]};
      font-style: italic;
    }}
    .data-stat-block {{
      display: {("flex" if is_stat else "none")};
      flex-direction: column;
      justify-content: center;
      gap: 10px;
      width: 100%;
      min-height: 210px;
      margin: 24px 0 10px;
      padding: 28px 30px;
      border: 1px solid {palette["line"]};
      background: {palette["stat_bg"]};
    }}
    .data-stat-block span {{
      color: {palette["accent"]};
      font-family: {palette["display_font"]};
      font-size: {("128px" if is_data else "112px")};
      line-height: 0.92;
    }}
    .data-stat-block strong {{
      max-width: 700px;
      color: {palette["muted_text"]};
      font-size: 23px;
      line-height: 1.35;
      font-weight: 500;
    }}
    .editorial-rail {{
      position: relative;
      margin-top: auto;
      padding-top: 34px;
      display: {("grid" if support_html else "none")};
      grid-template-columns: repeat({(3 if len(rail_cards) >= 3 else 2)}, minmax(0, 1fr));
      gap: 12px;
      z-index: 2;
      width: 100%;
      max-width: {("870px" if is_cover else "760px")};
    }}
    .editorial-rail-card {{
      min-height: {("132px" if is_cover else "118px")};
      padding: 18px 18px;
      border: 1px solid {palette["line"]};
      background: {palette["rail_bg"]};
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 10px;
    }}
    .editorial-rail-card span {{
      color: {palette["accent"]};
      font-size: 15px;
      line-height: 1.2;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .editorial-rail-card strong {{
      color: {palette["text"]};
      font-size: 21px;
      line-height: 1.22;
      font-weight: 650;
    }}
    .editorial-tags {{
      position: relative;
      margin-top: {("22px" if support_html else "auto")};
      padding-top: {("0" if support_html else "36px")};
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      z-index: 2;
      max-width: 680px;
    }}
    .editorial-tag {{
      padding: 10px 18px;
      border-radius: {("8px" if is_data else "999px")};
      border: 1px solid {palette["line"]};
      background: {palette["tag_bg"]};
      color: {palette["tag_text"]};
      font-size: 18px;
      letter-spacing: 0.08em;
      text-transform: lowercase;
    }}
    .mode-brief .editorial-footer,
    .mode-data .editorial-footer {{
      font-size: 20px;
    }}
    .editorial-footer {{
      position: absolute;
      left: 72px;
      right: 72px;
      bottom: 60px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 2;
      color: rgba(255,255,255,0.62);
      font-size: 24px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .editorial-footer .brand {{
      opacity: 0.78;
    }}
    .editorial-progress {{
      position: absolute;
      left: 72px;
      right: 72px;
      bottom: 24px;
      height: 4px;
      border-radius: 999px;
      background: rgba(255,255,255,0.14);
      overflow: hidden;
      z-index: 2;
    }}
    .editorial-progress-fill {{
      width: {progress_percent}%;
      height: 100%;
      background: linear-gradient(90deg, rgba(255,255,255,0.95), {palette["accent"]} 58%, {palette["accent_2"]});
    }}
  </style>
</head>
<body>
  <div class="canvas mode-{mode_class}">
    <div class="editorial-aura"></div>
    <div class="editorial-watermark">{html.escape(spec.watermark_number)}</div>
    <div class="editorial-topbar">
      <div class="editorial-section">{html.escape(spec.section_number)} · {html.escape(spec.section_label)}</div>
      <div class="editorial-brand">{brand}</div>
    </div>
    <div class="editorial-stage">
      <div class="editorial-title variant-{variant_class}">{title}</div>
      {stat_html}
      <div class="editorial-body">{body}</div>
      <div class="editorial-rail">{support_html}</div>
      <div class="editorial-tags">{tags_html}</div>
    </div>
    <div class="editorial-footer">
      <div class="brand">{html.escape(logo_text.lower())}</div>
      <div>{spec.slide_index}/{spec.total_slides}</div>
    </div>
    <div class="editorial-progress"><div class="editorial-progress-fill"></div></div>
  </div>
</body>
</html>
"""


def _apply_accent_markup(text: str, accent_spans: list[str], accent_color: str) -> str:
    rendered = text
    for span in accent_spans[:2]:
        safe_span = html.escape(span)
        if safe_span and safe_span in rendered:
            rendered = rendered.replace(
                safe_span,
                f'<span class="editorial-accent" style="color: {accent_color};">{safe_span}</span>',
                1,
            )
    return rendered


def _editorial_tokens(theme: str, visual_mode: str = "editorial") -> dict[str, str]:
    palettes = {
        "memory_archive": {
            "bg0": "#09070f",
            "bg1": "#171329",
            "bg2": "#100f19",
            "glow": "rgba(128, 118, 255, 0.22)",
            "glow2": "rgba(93, 129, 255, 0.12)",
            "text": "#f5f1ff",
            "muted": "#8d85b0",
            "muted_text": "#d6d0e6",
            "accent": "#b89cff",
            "accent_soft": "#cab8ff",
            "accent_2": "#8cb6ff",
            "accent_glow": "rgba(132, 118, 255, 0.12)",
            "accent_glow_2": "rgba(110, 174, 255, 0.08)",
        },
        "growth_black": {
            "bg0": "#09070a",
            "bg1": "#181117",
            "bg2": "#100d0a",
            "glow": "rgba(255, 153, 91, 0.20)",
            "glow2": "rgba(243, 194, 108, 0.12)",
            "text": "#fff8f2",
            "muted": "#b89d90",
            "muted_text": "#e6d8cf",
            "accent": "#ffab6f",
            "accent_soft": "#ffc299",
            "accent_2": "#ffd56f",
            "accent_glow": "rgba(255, 153, 91, 0.10)",
            "accent_glow_2": "rgba(255, 213, 111, 0.08)",
        },
        "research_mono": {
            "bg0": "#090a12",
            "bg1": "#141726",
            "bg2": "#0d0f18",
            "glow": "rgba(121, 150, 255, 0.18)",
            "glow2": "rgba(86, 114, 180, 0.12)",
            "text": "#f3f4fb",
            "muted": "#8e94b7",
            "muted_text": "#d7dcef",
            "accent": "#9eafff",
            "accent_soft": "#b9c4ff",
            "accent_2": "#92d0ff",
            "accent_glow": "rgba(121, 150, 255, 0.10)",
            "accent_glow_2": "rgba(146, 208, 255, 0.07)",
        },
    }
    base = palettes.get(theme, palettes["memory_archive"])
    if visual_mode == "brief":
        base = {
            "bg0": "#f7f9fc",
            "bg1": "#eaf0f7",
            "bg2": "#f9fbfd",
            "glow": "rgba(3, 105, 161, 0.10)",
            "glow2": "rgba(15, 23, 42, 0.06)",
            "text": "#101828",
            "muted": "#475467",
            "muted_text": "#344054",
            "accent": "#0369a1",
            "accent_soft": "#0f749f",
            "accent_2": "#0f172a",
            "accent_glow": "rgba(3, 105, 161, 0.08)",
            "accent_glow_2": "rgba(15, 23, 42, 0.04)",
        }
    elif visual_mode == "data":
        base = {
            "bg0": "#08090d",
            "bg1": "#10131b",
            "bg2": "#080a10",
            "glow": "rgba(125, 211, 252, 0.16)",
            "glow2": "rgba(190, 242, 100, 0.10)",
            "text": "#f8fafc",
            "muted": "#a3adbd",
            "muted_text": "#d7dde8",
            "accent": "#7dd3fc",
            "accent_soft": "#bae6fd",
            "accent_2": "#bef264",
            "accent_glow": "rgba(125, 211, 252, 0.08)",
            "accent_glow_2": "rgba(190, 242, 100, 0.07)",
        }
    tokens = {
        **base,
        "display_font": ("'SFMono-Regular', 'Menlo', 'Monaco', monospace" if visual_mode == "data" else "Georgia, 'Times New Roman', serif"),
        "body_font": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }
    tokens["line"] = "rgba(16,24,40,0.14)" if visual_mode == "brief" else "rgba(255,255,255,0.12)"
    tokens["rail_bg"] = "rgba(255,255,255,0.62)" if visual_mode == "brief" else "linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.018))"
    tokens["tag_bg"] = "rgba(255,255,255,0.58)" if visual_mode == "brief" else "linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))"
    tokens["tag_text"] = "#344054" if visual_mode == "brief" else "rgba(255,255,255,0.78)"
    tokens["stat_bg"] = "rgba(255,255,255,0.62)" if visual_mode == "brief" else "rgba(2,6,23,0.34)"
    tokens["watermark"] = "rgba(16,24,40,0.05)" if visual_mode == "brief" else "rgba(255,255,255,0.06)"
    return tokens


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
