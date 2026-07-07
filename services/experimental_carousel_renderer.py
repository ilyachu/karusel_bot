"""Experimental deterministic carousel renderer.

This module provides an opt-in, second rendering path for the carousel
pipeline. It is intentionally simple: 4 slide types (``hook``, ``body``,
``list``, ``cta``), inline HTML templates, and a 1080x1350 output size.

Compared to ``services/html_renderer.py``:

* The LLM-generated ``html_body`` on a ``LayoutSpec`` is **never** read.
  This makes the experimental renderer the control variable: if a custom
  background looks good here, the issue is AI HTML, not backgrounds.
* External backgrounds always get a fixed dark overlay and forced light
  text. Readability is structural, not a CSS afterthought.
* The renderer is fully synchronous. Callers (async handlers) wrap calls
  in ``asyncio.to_thread(...)``.

The module never raises on Playwright failure. A Pillow-based stub is the
last-resort fallback so the caller always receives a list of bytes.
"""

from __future__ import annotations

import html
import io
import logging
import re
import struct
import zlib
from dataclasses import dataclass, field
from typing import Sequence

from services.background_registry import (
    load_background_preset_data_url,
    pick_background_preset,
)
from services.layout_engine import LayoutSpec, _extract_stat_token

logger = logging.getLogger(__name__)

# Output dimensions for every experimental slide. Pinned for Instagram feed.
SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1350

# Readability palette.
DARK_SURFACE = "#0a0a0a"
LIGHT_TEXT = "#f8fafc"
PANEL_BG = "rgba(10, 14, 24, 0.76)"
PANEL_BORDER = "rgba(255, 255, 255, 0.20)"

# Overlay alpha for external backgrounds (top -> bottom gradient).
OVERLAY_TOP = "rgba(7, 10, 18, 0.62)"
OVERLAY_BOTTOM = "rgba(7, 10, 18, 0.76)"

# Bullet-split rules for ``density="high" -> list``.
MAX_BULLET_LENGTH = 80
MIN_BULLETS_FOR_LIST = 2

# ---------------------------------------------------------------------------
# 4-axis style system (inspired by threads-carousel-claude-skill presets.ts)
# ---------------------------------------------------------------------------

# Font families loaded via Google Fonts CDN. Each entry has a body font
# family and an optional display/hook font family.
FONT_STYLES: dict[str, dict[str, str | None]] = {
    "minimal": {
        "family": "'Unbounded', system-ui, sans-serif",
        "hook": "'Unbounded', system-ui, sans-serif",
    },
    "editorial": {
        "family": "'Playfair Display', Georgia, serif",
        "hook": "'Playfair Display', Georgia, serif",
    },
    "clean": {
        "family": "'Inter', system-ui, sans-serif",
        "hook": "'Inter', system-ui, sans-serif",
    },
    "mono": {
        "family": "'JetBrains Mono', 'Menlo', monospace",
        "hook": "'JetBrains Mono', 'Menlo', monospace",
    },
}

# Surfaces define the background and text colors. Only dark / paper / white
# are exposed via STYLE_PRESETS in v1; ember and neon are reserved for v2.
SURFACES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0a0a0a",
        "text": "#f8fafc",
        "secondary": "rgba(248, 250, 252, 0.72)",
    },
    "paper": {
        "bg": "#f4ede0",
        "text": "#1a1815",
        "secondary": "rgba(26, 24, 21, 0.62)",
    },
    "white": {
        "bg": "#ffffff",
        "text": "#0a0a0a",
        "secondary": "rgba(10, 10, 10, 0.62)",
    },
    "ember": {
        "bg": "linear-gradient(135deg, #1a0a05, #3d1a08)",
        "text": "#fef3c7",
        "secondary": "rgba(254, 243, 199, 0.70)",
    },
    "neon": {
        "bg": "linear-gradient(135deg, #0f172a, #312e81)",
        "text": "#e0e7ff",
        "secondary": "rgba(224, 231, 255, 0.70)",
    },
}

# Accent colors for highlighted words and decorative elements.
ACCENTS: dict[str, str] = {
    "yellow": "#facc15",
    "teal": "#2dd4bf",
    "orange": "#fb923c",
    "coral": "#fb7185",
    "violet": "#a78bfa",
    "lime": "#a3e635",
    "blue": "#60a5fa",
}

# Background decorations. Placeholders {ACCENT_22} and {ACCENT_55} are
# replaced with the chosen accent color at 22% / 55% opacity.
BACKGROUNDS: dict[str, str] = {
    "none": "",
    "glow": (
        "radial-gradient(circle at 30% 20%, {ACCENT_22}, transparent 60%), "
        "radial-gradient(circle at 80% 80%, {ACCENT_22}, transparent 50%)"
    ),
    "dots": (
        "radial-gradient(circle, {ACCENT_55} 1px, transparent 1px) 0 0 / 24px 24px"
    ),
    "ruled": (
        "linear-gradient(180deg, transparent 79px, {ACCENT_22} 80px) 0 0 / 100% 80px"
    ),
    "grid": (
        "linear-gradient(180deg, transparent 79px, {ACCENT_22} 80px) 0 0 / 100% 80px, "
        "linear-gradient(90deg, transparent 79px, {ACCENT_22} 80px) 0 0 / 80px 100%"
    ),
}


def _render_background_css(background_id: str, accent_color: str) -> str:
    """Resolve a background decoration string for a concrete accent color."""

    template = BACKGROUNDS.get(background_id, BACKGROUNDS["none"])
    if not template:
        return ""

    def _with_alpha(hex_color: str, alpha: float) -> str:
        """Convert #RRGGBB to rgba(..., alpha)."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return hex_color
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    return template.replace("{ACCENT_22}", _with_alpha(accent_color, 0.22)).replace(
        "{ACCENT_55}", _with_alpha(accent_color, 0.55)
    )


@dataclass(frozen=True)
class StylePreset:
    """A concrete composition of the 4 style axes.

    ``id`` is the machine key; ``label`` is shown on Telegram buttons.
    ``font_family`` is used for body text; ``hook_font_family`` is used for
    hook slide titles when set.
    """

    id: str
    label: str
    font_family: str
    hook_font_family: str | None
    surface_bg: str
    surface_text: str
    surface_text_secondary: str
    accent_color: str
    background_css: str


STYLE_PRESETS: dict[str, StylePreset] = {
    "dark_teal": StylePreset(
        id="dark_teal",
        label="Dark+Teal",
        font_family=FONT_STYLES["clean"]["family"],  # Inter
        hook_font_family=None,
        surface_bg=SURFACES["dark"]["bg"],
        surface_text=SURFACES["dark"]["text"],
        surface_text_secondary=SURFACES["dark"]["secondary"],
        accent_color=ACCENTS["teal"],
        background_css=_render_background_css("glow", ACCENTS["teal"]),
    ),
    "paper_orange": StylePreset(
        id="paper_orange",
        label="Paper+Orange",
        font_family=FONT_STYLES["editorial"]["family"],  # Playfair Display
        hook_font_family=None,
        surface_bg=SURFACES["paper"]["bg"],
        surface_text=SURFACES["paper"]["text"],
        surface_text_secondary=SURFACES["paper"]["secondary"],
        accent_color=ACCENTS["orange"],
        background_css=_render_background_css("ruled", ACCENTS["orange"]),
    ),
    "white_coral": StylePreset(
        id="white_coral",
        label="White+Coral",
        font_family=FONT_STYLES["minimal"]["family"],  # Unbounded
        hook_font_family=FONT_STYLES["minimal"]["hook"],
        surface_bg=SURFACES["white"]["bg"],
        surface_text=SURFACES["white"]["text"],
        surface_text_secondary=SURFACES["white"]["secondary"],
        accent_color=ACCENTS["coral"],
        background_css=_render_background_css("dots", ACCENTS["coral"]),
    ),
    "ember_violet": StylePreset(
        id="ember_violet",
        label="Ember+Violet",
        font_family=FONT_STYLES["editorial"]["family"],
        hook_font_family=None,
        surface_bg=SURFACES["ember"]["bg"],
        surface_text=SURFACES["ember"]["text"],
        surface_text_secondary=SURFACES["ember"]["secondary"],
        accent_color=ACCENTS["violet"],
        background_css=_render_background_css("glow", ACCENTS["violet"]),
    ),
    "neon_lime": StylePreset(
        id="neon_lime",
        label="Neon+Lime",
        font_family=FONT_STYLES["clean"]["family"],
        hook_font_family=None,
        surface_bg=SURFACES["neon"]["bg"],
        surface_text=SURFACES["neon"]["text"],
        surface_text_secondary=SURFACES["neon"]["secondary"],
        accent_color=ACCENTS["lime"],
        background_css=_render_background_css("grid", ACCENTS["lime"]),
    ),
}

# Default style is the tech/dark look so existing tests keep passing.
DEFAULT_STYLE = STYLE_PRESETS["dark_teal"]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentalSlide:
    """The minimal schema for an experimental slide.

    ``type`` is one of: ``hook``, ``body``, ``list``, ``cta``, ``quote``,
    ``stat``, ``comparison``.
    ``items`` is populated for ``list`` / ``comparison`` layouts.
    ``highlights`` is copied from ``LayoutSpec.highlight_words`` and is used
    by the style system to color accent words in ``title`` / ``body`` / ``items``.
    """

    type: str
    title: str
    body: str = ""
    items: tuple[str, ...] = field(default_factory=tuple)
    badge: str = ""
    highlight: str = ""
    highlights: tuple[str, ...] = field(default_factory=tuple)
    supporting_cards: tuple[dict, ...] = field(default_factory=tuple)
    archetype: str = ""


# ---------------------------------------------------------------------------
# Mapping: LayoutSpec -> ExperimentalSlide
# ---------------------------------------------------------------------------


def _split_bullets(body: str) -> tuple[str, ...]:
    """Try to split ``body`` into short bullets.

    Returns a tuple of items. Empty tuple means "no safe split" and the
    caller should fall back to ``type="body"``.

    Rules (in order):
    1. Split on newlines. Use the result if >=2 non-empty lines exist.
    2. Else split on ``". "`` (period + space). Use each fragment that
       is non-empty and <= ``MAX_BULLET_LENGTH`` characters. Return the
       list if >=2 fragments remain.
    3. Else return ``()``.
    """

    if not body:
        return ()

    raw_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(raw_lines) >= MIN_BULLETS_FOR_LIST:
        return tuple(raw_lines)

    fragments = [frag.strip() for frag in body.split(". ") if frag.strip()]
    short_fragments = tuple(frag for frag in fragments if len(frag) <= MAX_BULLET_LENGTH)
    if len(short_fragments) >= MIN_BULLETS_FOR_LIST:
        return short_fragments

    return ()


def _resolve_stat_copy(title: str, body: str) -> tuple[str, str]:
    """Pick a prominent stat token and a short explanation line."""

    title = (title or "").strip()
    body = (body or "").strip()
    stat = _extract_stat_token(f"{title} {body}")
    if not stat:
        return title, body
    if stat in title:
        explanation = body or title.replace(stat, "").strip(" —–-:")
        return stat, explanation or body
    return stat, title or body


def _comparison_items_from_spec(spec: LayoutSpec) -> tuple[str, ...]:
    cards = list(spec.supporting_cards or [])
    if len(cards) >= 2:
        left = f"{cards[0].get('title', '').strip()}: {cards[0].get('body', '').strip()}".strip(": ")
        right = f"{cards[1].get('title', '').strip()}: {cards[1].get('body', '').strip()}".strip(": ")
        return (left, right)

    body = (spec.body or "").strip()
    for separator in (" vs ", " / ", " | ", "\n"):
        if separator in body:
            left, right = body.split(separator, 1)
            return (left.strip(), right.strip())
    return (spec.title or "", body)


def map_layout_spec_to_experimental_slide(
    spec: LayoutSpec,
    style: StylePreset | None = None,
) -> ExperimentalSlide:
    """Map a production ``LayoutSpec`` to an ``ExperimentalSlide``.

    Priority: ``role`` (hook/cta) -> ``archetype`` -> ``density`` -> body.

    The LLM-generated ``spec.html_body`` is never read.
    """

    _ = style

    highlights = tuple(word.strip() for word in (spec.highlight_words or ()) if word.strip())
    supporting_cards = tuple(dict(card) for card in (spec.supporting_cards or []) if isinstance(card, dict))
    archetype = (spec.archetype or "").strip().lower()
    role = (spec.role or "").strip().lower()
    density = (spec.density or "").strip().lower()

    base_kwargs = {
        "highlights": highlights,
        "supporting_cards": supporting_cards,
        "archetype": archetype,
        "badge": spec.badge_text or "",
    }

    if role == "hook" or archetype == "hero_center":
        return ExperimentalSlide(
            type="hook",
            title=spec.title or "",
            body=spec.body or "",
            **base_kwargs,
        )
    if role == "cta" or archetype == "soft_cta":
        return ExperimentalSlide(
            type="cta",
            title=spec.title or "",
            body=spec.body or "",
            **base_kwargs,
        )
    if archetype == "stat_panel":
        stat, explanation = _resolve_stat_copy(spec.title or "", spec.body or "")
        return ExperimentalSlide(
            type="stat",
            title=stat,
            body=explanation,
            **base_kwargs,
        )
    if archetype == "quote_poster":
        quote = (spec.body or "").strip() if len(spec.title or "") > 90 else (spec.title or "")
        attribution = (spec.body or "") if quote != (spec.body or "") else ""
        return ExperimentalSlide(
            type="quote",
            title=quote,
            body=attribution,
            **base_kwargs,
        )
    if archetype == "comparison_grid":
        return ExperimentalSlide(
            type="comparison",
            title=spec.title or "",
            body=spec.body or "",
            items=_comparison_items_from_spec(spec),
            **base_kwargs,
        )
    if archetype in {"checklist_stack", "timeline_steps"} or role == "checklist":
        items = _split_bullets(spec.body or "")
        if not items and supporting_cards:
            items = tuple(
                f"{card.get('title', '').strip()}: {card.get('body', '').strip()}".strip(": ")
                for card in supporting_cards
                if card.get("title") or card.get("body")
            )
        if items:
            return ExperimentalSlide(
                type="list",
                title=spec.title or "",
                body="",
                items=items,
                **base_kwargs,
            )

    if density == "high":
        items = _split_bullets(spec.body or "")
        if items:
            return ExperimentalSlide(
                type="list",
                title=spec.title or "",
                body="",
                items=items,
                **base_kwargs,
            )

    return ExperimentalSlide(
        type="body",
        title=spec.title or "",
        body=spec.body or "",
        **base_kwargs,
    )


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------


def _title_font_size(title: str, slide_type: str) -> int:
    length = len((title or "").strip())
    if slide_type in {"quote", "hook"}:
        if length <= 40:
            return 72
        if length <= 70:
            return 60
        if length <= 110:
            return 52
        return 44
    if length <= 28:
        return 72
    if length <= 45:
        return 64
    if length <= 65:
        return 56
    return 48


def _body_font_size(body: str, slide_type: str, item_count: int = 0) -> int:
    length = len((body or "").strip())
    if slide_type == "list":
        if item_count >= 5:
            return 26
        if item_count >= 4:
            return 28
        return 30
    if slide_type == "stat":
        if length <= 80:
            return 34
        return 30
    if length <= 90:
        return 32
    if length <= 160:
        return 28
    return 26


def _stat_font_size(stat: str) -> int:
    length = len((stat or "").strip())
    if length <= 4:
        return 132
    if length <= 8:
        return 112
    if length <= 14:
        return 96
    return 80


def _is_light_surface(surface_bg: str) -> bool:
    """Heuristic: light surfaces start with white / cream / linear-gradient
    containing light tones. Used to pick the right external-bg overlay.
    """

    lower = surface_bg.lower()
    return any(token in lower for token in ("#ffffff", "#f4ede0", "#fef3c7", "#e0e7ff", "paper", "white", "light"))


def _google_fonts_link(families: list[str | None]) -> str:
    """Build a Google Fonts stylesheet link for the requested families."""

    clean_names = []
    for family in families:
        if not family:
            continue
        # The stored font_family value is a CSS stack, e.g.
        # "'Inter', system-ui, sans-serif". Take only the first family,
        # strip surrounding quotes and whitespace.
        first_family = family.split(",")[0]
        name = first_family.strip().strip("'\"").strip()
        # Map common Google Font families to their canonical names with
        # weight ranges we need (400;600;700;800). System fallbacks are
        # appended in CSS.
        if name.lower() == "unbounded":
            clean_names.append("Unbounded:wght@400;600;700;800")
        elif name.lower() == "playfair display":
            clean_names.append("Playfair+Display:wght@400;600;700;800")
        elif name.lower() == "inter":
            clean_names.append("Inter:wght@400;500;600;700;800")
        elif name.lower() == "jetbrains mono":
            clean_names.append("JetBrains+Mono:wght@400;500;600;700;800")
    if not clean_names:
        return ""
    families_part = "|".join(clean_names)
    return f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={families_part}&display=swap">'


def _wrap_highlights(text: str, highlights: tuple[str, ...]) -> str:
    """Wrap whole-word occurrences of any highlight word in a span.hl.

    Case-insensitive matching. Escaped HTML is preserved.
    """

    if not highlights:
        return html.escape(text)

    escaped = html.escape(text)
    if not escaped:
        return escaped

    # Build a list of (start, end, original_word) positions for any
    # whole-word match.
    positions: list[tuple[int, int, str]] = []
    for word in highlights:
        word_escaped = html.escape(word.strip())
        if not word_escaped:
            continue
        pattern = re.compile(re.escape(word_escaped), re.IGNORECASE)
        for match in pattern.finditer(escaped):
            positions.append((match.start(), match.end(), match.group(0)))

    if not positions:
        return escaped

    # Sort by start index; keep non-overlapping earliest matches.
    positions.sort(key=lambda item: item[0])
    kept: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, word in positions:
        if start >= last_end:
            kept.append((start, end, word))
            last_end = end

    # Build the final string in reverse order so indices stay valid.
    parts = list(escaped)
    for start, end, word in reversed(kept):
        replacement = f'<span class="hl">{word}</span>'
        parts[start:end] = list(replacement)

    return "".join(parts)


def _shared_css(
    style: StylePreset,
    custom_or_preset: str,
    *,
    title_size: int = 72,
    body_size: int = 32,
    stat_size: int = 112,
) -> str:
    """Return CSS shared by every slide for the chosen style preset.

    ``custom_or_preset`` is the resolved data URL for an external
    background, or ``""`` when only the styled surface is used.
    """

    is_light = _is_light_surface(style.surface_bg)

    if custom_or_preset:
        # External background takes full-bleed priority. The surface_bg is
        # used only as a fallback color while the image loads.
        background_rule = (
            f"background: {style.surface_bg};\n"
            f"  --external-bg: url('{custom_or_preset}');"
        )
        # For light surfaces, a dark overlay keeps text readable; for
        # dark surfaces, a softer dark overlay is enough.
        if is_light:
            overlay_top = OVERLAY_TOP
            overlay_bottom = OVERLAY_BOTTOM
        else:
            overlay_top = "rgba(7, 10, 18, 0.56)"
            overlay_bottom = "rgba(7, 10, 18, 0.70)"
        overlay_vars = (
            f"  --overlay-top: {overlay_top};\n"
            f"  --overlay-bottom: {overlay_bottom};"
        )
        background_rule = background_rule + "\n" + overlay_vars
    else:
        # No external background: use the surface background, plus any
        # background decoration as a second layer.
        if style.background_css:
            bg_layers = f"{style.background_css}, {style.surface_bg}"
        else:
            bg_layers = style.surface_bg
        background_rule = f"background: {bg_layers};"
        overlay_vars = ""

    # Determine panel colors depending on surface brightness.
    if is_light:
        panel_bg = "rgba(255, 255, 255, 0.86)"
        panel_border = "rgba(10, 10, 10, 0.12)"
        shadow_color = "rgba(0, 0, 0, 0.10)"
    else:
        panel_bg = PANEL_BG
        panel_border = PANEL_BORDER
        shadow_color = "rgba(0, 0, 0, 0.28)"

    # Text shadows are stronger when an external bg is present so the
    # text pops off any photo.
    text_shadow = (
        "0 2px 12px rgba(0,0,0,0.86), 0 0 2px rgba(0,0,0,0.96)"
        if custom_or_preset
        else "0 2px 8px rgba(0,0,0,0.20)"
    )

    return f"""
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      width: {SLIDE_WIDTH}px;
      height: {SLIDE_HEIGHT}px;
      overflow: hidden;
      font-family: {style.font_family}, -apple-system, BlinkMacSystemFont,
                   "Segoe UI", system-ui, "Helvetica Neue", Arial, sans-serif;
      {background_rule}
      color: {style.surface_text};
    }}
    .slide {{
      position: relative;
      width: {SLIDE_WIDTH}px;
      height: {SLIDE_HEIGHT}px;
      padding: 80px;
      display: flex;
      flex-direction: column;
    }}
    .external-bg {{
      position: absolute;
      inset: 0;
      background-image: var(--external-bg);
      background-size: cover;
      background-position: center;
      z-index: 0;
    }}
    .overlay {{
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, var(--overlay-top), var(--overlay-bottom));
      z-index: 1;
    }}
    .content {{
      position: relative;
      z-index: 2;
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .panel {{
      background: {panel_bg};
      border: 1px solid {panel_border};
      border-radius: 32px;
      padding: 40px;
      color: {style.surface_text};
      box-shadow: 0 18px 44px {shadow_color};
      opacity: 1;
    }}
    .badge {{
      display: inline-block;
      padding: 8px 16px;
      border-radius: 999px;
      background: {style.accent_color}22;
      border: 1px solid {style.accent_color}55;
      color: {style.surface_text};
      font-size: 18px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 24px;
    }}
    h1.title {{
      font-size: {title_size}px;
      line-height: 1.1;
      font-weight: 800;
      margin: 0 0 24px 0;
      color: {style.surface_text};
      opacity: 1;
      text-shadow: {text_shadow};
    }}
    .slide.hook h1.title, .slide.quote h1.title {{
      font-family: {style.hook_font_family or style.font_family}, -apple-system,
                   BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    }}
    p.body {{
      font-size: {body_size}px;
      line-height: 1.4;
      font-weight: 500;
      margin: 0;
      color: {style.surface_text};
      opacity: 1;
      text-shadow: {text_shadow};
    }}
    .stat-value {{
      font-size: {stat_size}px;
      line-height: 0.95;
      font-weight: 800;
      margin: 0 0 20px 0;
      color: {style.accent_color};
      letter-spacing: -0.03em;
      text-shadow: {text_shadow};
    }}
    .quote-mark {{
      font-size: {max(48, title_size // 2)}px;
      line-height: 1;
      color: {style.accent_color};
      margin-bottom: 16px;
      opacity: 0.9;
    }}
    ul.items {{
      margin: 0;
      padding-left: 28px;
      font-size: {body_size}px;
      line-height: 1.5;
      font-weight: 500;
    }}
    ul.items.steps {{
      list-style: none;
      padding-left: 0;
      counter-reset: step;
    }}
    ul.items.steps li {{
      position: relative;
      padding-left: 56px;
      margin-bottom: 18px;
    }}
    ul.items.steps li::before {{
      counter-increment: step;
      content: counter(step);
      position: absolute;
      left: 0;
      top: 2px;
      width: 40px;
      height: 40px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      font-size: 18px;
      font-weight: 700;
      color: {style.surface_text};
      background: {style.accent_color}33;
      border: 1px solid {style.accent_color}88;
    }}
    ul.items li {{
      margin-bottom: 12px;
      color: {style.surface_text};
      opacity: 1;
      text-shadow: {text_shadow};
    }}
    .comparison-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}
    .comparison-col {{
      background: {panel_bg};
      border: 1px solid {panel_border};
      border-radius: 24px;
      padding: 24px;
      min-height: 180px;
    }}
    .comparison-col h2 {{
      margin: 0 0 12px 0;
      font-size: {max(24, body_size)}px;
      color: {style.accent_color};
      font-weight: 700;
    }}
    .comparison-col p {{
      margin: 0;
      font-size: {body_size}px;
      line-height: 1.35;
      color: {style.surface_text};
      text-shadow: {text_shadow};
    }}
    .hl {{
      color: {style.accent_color};
      font-weight: 700;
    }}
    .footer {{
      position: absolute;
      left: 80px;
      right: 80px;
      bottom: 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 18px;
      letter-spacing: 0.06em;
      color: {style.surface_text_secondary};
      z-index: 2;
    }}
    """


def _layout_html(
    slide_type: str,
    inner_content: str,
    logo_text: str,
    slide_index: int,
    total_slides: int,
    style: StylePreset,
    custom_or_preset: str,
    *,
    title_size: int = 72,
    body_size: int = 32,
    stat_size: int = 112,
    archetype: str = "",
) -> str:
    """Wrap inner slide content in the standard 1080x1350 document."""

    bg_block = ""
    overlay_block = ""
    if custom_or_preset:
        bg_block = '<div class="external-bg"></div>'
        overlay_block = '<div class="overlay"></div>'

    google_fonts = _google_fonts_link([style.font_family, style.hook_font_family])
    archetype_class = f" archetype-{archetype}" if archetype else ""

    return (
        "<!doctype html>\n"
        '<html lang="ru">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"{google_fonts}\n"
        f"<style>{_shared_css(style, custom_or_preset, title_size=title_size, body_size=body_size, stat_size=stat_size)}</style>\n"
        "</head>\n"
        "<body>\n"
        f'<div class="slide {slide_type}{archetype_class}">\n'
        f"{bg_block}\n"
        f"{overlay_block}\n"
        '<div class="content">\n'
        f"{inner_content}\n"
        "</div>\n"
        '<div class="footer">\n'
        f'<span class="logo">{html.escape(logo_text or "chu ai")}</span>\n'
        f'<span class="counter">{slide_index}/{total_slides}</span>\n'
        "</div>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def _hook_html(slide: ExperimentalSlide) -> str:
    badge = ""
    if slide.badge:
        badge = f'<div class="badge">{_wrap_highlights(slide.badge, slide.highlights)}</div>'
    return (
        f"{badge}"
        f'<h1 class="title">{_wrap_highlights(slide.title, slide.highlights)}</h1>'
        f'<p class="body">{_wrap_highlights(slide.body, slide.highlights)}</p>'
    )


def _body_html(slide: ExperimentalSlide) -> str:
    body = _wrap_highlights(slide.body, slide.highlights) if slide.body else ""
    return (
        '<div class="panel">'
        f'<h1 class="title">{_wrap_highlights(slide.title, slide.highlights)}</h1>'
        f'<p class="body">{body}</p>'
        "</div>"
    )


def _list_html(slide: ExperimentalSlide) -> str:
    list_class = "items steps" if slide.archetype in {"timeline_steps", "checklist_stack"} else "items"
    items_html = "\n".join(
        f"        <li>{_wrap_highlights(item, slide.highlights)}</li>"
        for item in slide.items
    )
    return (
        '<div class="panel">'
        f'<h1 class="title">{_wrap_highlights(slide.title, slide.highlights)}</h1>'
        f'      <ul class="{list_class}">\n{items_html}\n      </ul>'
        "</div>"
    )


def _quote_html(slide: ExperimentalSlide) -> str:
    attribution = (
        f'<p class="body">{_wrap_highlights(slide.body, slide.highlights)}</p>'
        if slide.body
        else ""
    )
    return (
        '<div class="panel">'
        '<div class="quote-mark">“</div>'
        f'<h1 class="title">{_wrap_highlights(slide.title, slide.highlights)}</h1>'
        f"{attribution}"
        "</div>"
    )


def _stat_html(slide: ExperimentalSlide) -> str:
    return (
        '<div class="panel">'
        f'<p class="stat-value">{_wrap_highlights(slide.title, slide.highlights)}</p>'
        f'<p class="body">{_wrap_highlights(slide.body, slide.highlights)}</p>'
        "</div>"
    )


def _comparison_html(slide: ExperimentalSlide) -> str:
    left = slide.items[0] if len(slide.items) > 0 else slide.title
    right = slide.items[1] if len(slide.items) > 1 else slide.body
    heading = ""
    if slide.title and slide.title not in {left, right}:
        heading = f'<h1 class="title">{_wrap_highlights(slide.title, slide.highlights)}</h1>'
    return (
        '<div class="panel">'
        f"{heading}"
        '<div class="comparison-grid">'
        f'<div class="comparison-col"><h2>A</h2><p>{_wrap_highlights(left, slide.highlights)}</p></div>'
        f'<div class="comparison-col"><h2>B</h2><p>{_wrap_highlights(right, slide.highlights)}</p></div>'
        "</div>"
        "</div>"
    )


def _cta_html(slide: ExperimentalSlide) -> str:
    body = _wrap_highlights(slide.body, slide.highlights) if slide.body else ""
    return (
        '<div class="panel">'
        f'<h1 class="title">{_wrap_highlights(slide.title, slide.highlights)}</h1>'
        f'<p class="body">{body}</p>'
        "</div>"
    )


def build_experimental_slide_html(
    slide: ExperimentalSlide,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    preset_background_data_url: str = "",
    slide_index: int = 1,
    total_slides: int = 1,
    style: StylePreset | None = None,
) -> str:
    """Build a complete 1080x1350 HTML document for the slide.

    If ``style`` is omitted, the module-level ``DEFAULT_STYLE``
    (``dark_teal``) is used so existing callers keep working.

    Readability rules (always applied):

    * surface and text colors come from ``style``;
    * if ``custom_background_data_url`` or ``preset_background_data_url``
      is present: full-bleed external image at z-index 0,
      linear-gradient overlay at z-index 1;
      light surfaces get a strong dark overlay so text remains readable;
    * body/list content inside a semi-transparent panel;
    * Google Fonts link for the active style's font family, with system
      fonts as a fallback.
    """

    active_style = style or DEFAULT_STYLE
    custom_or_preset = (custom_background_data_url or preset_background_data_url or "").strip()

    if slide.type == "hook":
        inner = _hook_html(slide)
    elif slide.type == "list":
        inner = _list_html(slide)
    elif slide.type == "cta":
        inner = _cta_html(slide)
    elif slide.type == "quote":
        inner = _quote_html(slide)
    elif slide.type == "stat":
        inner = _stat_html(slide)
    elif slide.type == "comparison":
        inner = _comparison_html(slide)
    else:
        inner = _body_html(slide)

    title_size = _title_font_size(slide.title, slide.type)
    body_size = _body_font_size(
        slide.body,
        slide.type,
        item_count=len(slide.items),
    )
    stat_size = _stat_font_size(slide.title) if slide.type == "stat" else 112

    return _layout_html(
        slide_type=slide.type,
        inner_content=inner,
        logo_text=logo_text,
        slide_index=slide_index,
        total_slides=total_slides,
        style=active_style,
        custom_or_preset=custom_or_preset,
        title_size=title_size,
        body_size=body_size,
        stat_size=stat_size,
        archetype=slide.archetype,
    )


# ---------------------------------------------------------------------------
# Playwright + Pillow rendering
# ---------------------------------------------------------------------------


def _render_with_playwright(html_content: str) -> bytes:
    """Render HTML to a 1080x1350 PNG via headless Chromium.

    Raises on any failure. Caller is responsible for fallback.
    """

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
                device_scale_factor=1,
            )
            page.set_content(html_content, wait_until="load")
            png = page.screenshot(
                type="png",
                clip={"x": 0, "y": 0, "width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
            )
        finally:
            browser.close()
    return png


def _render_with_pillow_fallback(
    title: str,
    body: str,
    slide_index: int,
    total_slides: int,
    logo_text: str,
    style: StylePreset | None = None,
) -> bytes:
    """Render a style-aware PNG with the title centered.

    Last-resort fallback. Visual quality is intentionally minimal so the
    caller knows Chromium was unavailable. Honors the style's surface and
    text colors.
    """

    from PIL import Image, ImageDraw, ImageFont

    active_style = style or DEFAULT_STYLE
    is_light = _is_light_surface(active_style.surface_bg)

    # Resolve a simple background color for the fallback image.
    bg_hex = active_style.surface_bg.lstrip("#")
    if len(bg_hex) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in bg_hex):
        bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
    else:
        bg_rgb = (245, 245, 245) if is_light else (10, 10, 10)

    text_hex = active_style.surface_text.lstrip("#")
    if len(text_hex) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in text_hex):
        text_rgb = tuple(int(text_hex[i:i+2], 16) for i in (0, 2, 4))
    else:
        text_rgb = (10, 10, 10) if is_light else (248, 250, 252)

    img = Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64
        )
        body_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22
        )
    except Exception:
        title_font = ImageFont.load_default()
        body_font = title_font
        small_font = title_font

    safe_title = (title or "Без заголовка").strip()
    bbox = draw.textbbox((0, 0), safe_title, font=title_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SLIDE_WIDTH - tw) // 2
    y = (SLIDE_HEIGHT - th) // 2 - 40
    draw.text((x, y), safe_title, fill=text_rgb, font=title_font)

    if body:
        truncated = body[:140]
        secondary = tuple(int(c * 0.75 + (255 - c) * 0.25) for c in text_rgb)
        draw.text((80, y + th + 30), truncated, fill=secondary, font=body_font)

    draw.text((80, 1280), logo_text or "chu ai", fill=text_rgb, font=small_font)
    draw.text(
        (900, 1280),
        f"{slide_index}/{total_slides}",
        fill=text_rgb,
        font=small_font,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_empty_png(width: int, height: int) -> bytes:
    """Build a minimal solid-color PNG without Pillow."""

    raw = b""
    for _ in range(height):
        raw += b"\x00" + b"\x99" * width * 3

    def _chunk(t: bytes, d: bytes) -> bytes:
        c = t + d
        return (
            struct.pack(">I", len(d))
            + c
            + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def render_experimental_carousel(
    layout_specs: Sequence[LayoutSpec],
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    preset_background_data_url: str = "",
    style: StylePreset | None = None,
) -> list[bytes]:
    """Render a list of ``LayoutSpec`` to a list of PNG bytes.

    Synchronous. Never raises. Order matches the input order.

    If ``style`` is omitted, ``DEFAULT_STYLE`` (``dark_teal``) is used so
    existing callers keep working.
    """

    active_style = style or DEFAULT_STYLE
    specs = list(layout_specs)
    total = len(specs)
    if total == 0:
        return []

    out: list[bytes] = []
    custom = (custom_background_data_url or "").strip()
    global_preset = (preset_background_data_url or "").strip()

    for index, spec in enumerate(specs, start=1):
        slide_preset = global_preset
        if not custom and not slide_preset:
            preset = pick_background_preset(
                layout_style=getattr(spec, "layout_style", "magazine") or "magazine",
                theme_hint=getattr(spec, "theme", "business_dark") or "business_dark",
                slide_role=getattr(spec, "role", "point") or "point",
                archetype=getattr(spec, "archetype", "") or "",
            )
            if preset:
                slide_preset = load_background_preset_data_url(preset.preset_id)

        slide = map_layout_spec_to_experimental_slide(spec, style=active_style)
        html_content = build_experimental_slide_html(
            slide,
            logo_text=logo_text,
            custom_background_data_url=custom,
            preset_background_data_url=slide_preset,
            slide_index=index,
            total_slides=total,
            style=active_style,
        )
        try:
            png = _render_with_playwright(html_content)
        except Exception as exc:
            logger.warning(
                "Experimental renderer: Playwright failed (slide %s/%s): %s. "
                "Falling back to Pillow stub.",
                index,
                total,
                exc,
            )
            try:
                png = _render_with_pillow_fallback(
                    title=slide.title,
                    body=slide.body,
                    slide_index=index,
                    total_slides=total,
                    logo_text=logo_text,
                    style=active_style,
                )
            except Exception as exc2:
                logger.error(
                    "Experimental renderer: Pillow fallback failed "
                    "(slide %s/%s): %s. Returning empty PNG.",
                    index,
                    total,
                    exc2,
                )
                png = _make_empty_png(SLIDE_WIDTH, SLIDE_HEIGHT)
        out.append(png)
    return out
