"""Content length guidelines for carousel plans (DTC-inspired).

Keeps LLM output within readable bounds for the experimental renderer
(1080×1350) and Insta Auto HTML path. Limits are approximate character
ceilings — the renderer also applies adaptive font sizing.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from services.layout_engine import CarouselPlan, SlidePlanEntry

# Approximate character ceilings (adapted from DataTalksClub CONTENT_GUIDELINES).
LIMITS = {
    "hook_title": 100,
    "hook_body": 200,
    "body_title": 80,
    "body_text": 280,
    "list_title": 80,
    "list_item": 100,
    "list_min_items": 3,
    "list_max_items": 6,
    "cta_title": 70,
    "cta_body": 200,
    "quote_text": 250,
    "stat_value": 24,
    "stat_explanation": 150,
    "comparison_item": 80,
    "badge": 40,
    "emphasis_word": 28,
    "supporting_card_title": 24,
    "supporting_card_body": 48,
}

_ARCHETYPE_ROLE_HINTS = {
    "hero_center": "hook",
    "soft_cta": "cta",
    "quote_poster": "quote",
    "stat_panel": "stat",
    "checklist_stack": "list",
    "timeline_steps": "list",
    "comparison_grid": "comparison",
    "split_story": "body",
}


def content_limits_prompt_block() -> str:
    """Prompt fragment describing hard copy limits for the LLM."""

    return f"""Лимиты символов (строго, иначе текст обрежется на слайде):
- hook: title до {LIMITS['hook_title']}, body до {LIMITS['hook_body']}
- content: title до {LIMITS['body_title']}, body до {LIMITS['body_text']}
- checklist/list: title до {LIMITS['list_title']}, 3-6 пунктов по {LIMITS['list_item']} символов; разбивай body на короткие строки
- stat_panel: title — короткая цифра/метрика (до {LIMITS['stat_value']}), body — пояснение до {LIMITS['stat_explanation']}
- quote_poster: title — цитата до {LIMITS['quote_text']}, body — источник/контекст до {LIMITS['body_text']}
- cta: title до {LIMITS['cta_title']}, body до {LIMITS['cta_body']}
- emphasis: до 3 слов, каждое до {LIMITS['emphasis_word']} символов
- supporting_cards: title 1-2 слова, body до 6 слов
Одна мысль на слайд. Без длинных абзацев."""


def _truncate(text: str, max_chars: int, *, ellipsis: bool = True) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= max_chars:
        return cleaned
    if max_chars <= 3 or not ellipsis:
        return cleaned[:max_chars].rstrip()
    return cleaned[: max_chars - 1].rstrip() + "…"


def _slide_role_hint(slide: dict[str, Any]) -> str:
    role = str(slide.get("role", "")).strip().lower()
    archetype = str(slide.get("archetype", "")).strip().lower()
    if role in {"hook", "cta"}:
        return role
    if archetype in _ARCHETYPE_ROLE_HINTS:
        return _ARCHETYPE_ROLE_HINTS[archetype]
    if role == "checklist":
        return "list"
    density = str(slide.get("density", "")).strip().lower()
    body = str(slide.get("body", ""))
    if density == "high" and ("\n" in body or body.count(". ") >= 2):
        return "list"
    return "body"


def _clamp_list_body(body: str) -> str:
    lines = [line.strip() for line in (body or "").splitlines() if line.strip()]
    if not lines:
        fragments = [frag.strip() for frag in (body or "").split(". ") if frag.strip()]
        lines = [_truncate(frag, LIMITS["list_item"], ellipsis=False) for frag in fragments]
    lines = [_truncate(line, LIMITS["list_item"]) for line in lines]
    lines = lines[: LIMITS["list_max_items"]]
    while len(lines) < LIMITS["list_min_items"] and lines:
        # Pad by splitting the longest item if we have fewer than 3 bullets.
        longest_index = max(range(len(lines)), key=lambda idx: len(lines[idx]))
        longest = lines[longest_index]
        midpoint = len(longest) // 2
        if midpoint < 12:
            break
        left = _truncate(longest[:midpoint].strip(), LIMITS["list_item"], ellipsis=False)
        right = _truncate(longest[midpoint:].strip(), LIMITS["list_item"], ellipsis=False)
        if not left or not right:
            break
        lines = lines[:longest_index] + [left, right] + lines[longest_index + 1 :]
        lines = lines[: LIMITS["list_max_items"]]
    return "\n".join(lines)


def clamp_slide_dict(slide: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a raw slide dict with copy fields clamped."""

    result = deepcopy(slide)
    hint = _slide_role_hint(result)

    if hint == "hook":
        result["title"] = _truncate(str(result.get("title", "")), LIMITS["hook_title"])
        result["body"] = _truncate(str(result.get("body", "")), LIMITS["hook_body"])
    elif hint == "cta":
        result["title"] = _truncate(str(result.get("title", "")), LIMITS["cta_title"])
        result["body"] = _truncate(str(result.get("body", "")), LIMITS["cta_body"])
    elif hint == "quote":
        result["title"] = _truncate(str(result.get("title", "")), LIMITS["quote_text"])
        result["body"] = _truncate(str(result.get("body", "")), LIMITS["body_text"])
    elif hint == "stat":
        result["title"] = _truncate(str(result.get("title", "")), LIMITS["stat_value"])
        result["body"] = _truncate(str(result.get("body", "")), LIMITS["stat_explanation"])
    elif hint == "list":
        result["title"] = _truncate(str(result.get("title", "")), LIMITS["list_title"])
        result["body"] = _clamp_list_body(str(result.get("body", "")))
        result["density"] = "high"
    else:
        result["title"] = _truncate(str(result.get("title", "")), LIMITS["body_title"])
        result["body"] = _truncate(str(result.get("body", "")), LIMITS["body_text"])

    emphasis = result.get("emphasis")
    if isinstance(emphasis, list):
        result["emphasis"] = [
            _truncate(str(word), LIMITS["emphasis_word"], ellipsis=False)
            for word in emphasis[:3]
            if str(word).strip()
        ]

    cards = result.get("supporting_cards")
    if isinstance(cards, list):
        clamped_cards = []
        for card in cards[:3]:
            if not isinstance(card, dict):
                continue
            clamped_cards.append(
                {
                    "title": _truncate(
                        str(card.get("title", "")),
                        LIMITS["supporting_card_title"],
                        ellipsis=False,
                    ),
                    "body": _truncate(
                        str(card.get("body", "")),
                        LIMITS["supporting_card_body"],
                    ),
                }
            )
        result["supporting_cards"] = clamped_cards

    return result


def clamp_carousel_plan_dict(raw_plan: dict[str, Any]) -> dict[str, Any]:
    """Clamp all slide copy in a raw LLM plan dict."""

    if not isinstance(raw_plan, dict):
        return raw_plan
    result = deepcopy(raw_plan)
    slides = result.get("slides")
    if not isinstance(slides, list):
        return result
    result["slides"] = [clamp_slide_dict(slide) for slide in slides if isinstance(slide, dict)]
    return result


def clamp_carousel_plan(plan: CarouselPlan) -> CarouselPlan:
    """Clamp copy on a parsed ``CarouselPlan``."""

    clamped_slides: list[SlidePlanEntry] = []
    for slide in plan.slides:
        raw = {
            "role": slide.role,
            "archetype": slide.archetype,
            "title": slide.title,
            "body": slide.body,
            "density": slide.density,
            "emphasis": slide.emphasis,
            "supporting_cards": slide.supporting_cards,
        }
        clamped = clamp_slide_dict(raw)
        clamped_slides.append(
            SlidePlanEntry(
                index=slide.index,
                role=slide.role,
                title=str(clamped.get("title", "")),
                body=str(clamped.get("body", "")),
                emphasis=list(clamped.get("emphasis") or []),
                density=str(clamped.get("density", slide.density)),
                theme_hint=slide.theme_hint,
                supporting_cards=list(clamped.get("supporting_cards") or []),
                html_body=slide.html_body,
                archetype=slide.archetype,
            )
        )
    return CarouselPlan(
        goal=plan.goal,
        audience=plan.audience,
        tone=plan.tone,
        theme_hint=plan.theme_hint,
        cta=plan.cta,
        layout_style=plan.layout_style,
        slides=clamped_slides,
    )